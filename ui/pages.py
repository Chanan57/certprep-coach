"""Top-level pages: home/library/add-exam, mode chooser, setup, quiz, report."""

import os
import time
import tempfile

import streamlit as st
import pandas as pd

from src.pdf_reader import extract_pdf_content
from src.question_parser import parse_questions
from src import library as lib
from src import exam_builder as eb
from src import progress as prog
from src.quiz_engine import (
    shuffle_questions, shuffle_questions_grouped, shuffle_options,
    filter_by_topics, filter_by_types, get_time_remaining,
)

from ui.state import (
    TYPE_LABELS, reset_quiz_progress, full_reset, load_questions_into_state,
    split_scenario_sections, format_body, apply_progress_payload,
)
from ui.header import render_exam_header
from ui.navigator import render_navigator
from ui.questions import (
    render_question_body, render_question_controls, render_footer_nav, render_stem,
)
from ui.report import render_report


# ---------------------------------------------------------------------------
# Home: library + add-exam
# ---------------------------------------------------------------------------

def show_home_page():
    st.title("📘 CertPrep Coach")
    st.subheader("Exam Simulator")

    tab_lib, tab_add, tab_upload = st.tabs(
        ["📚 Question Library", "➕ Add New Exam", "⬆️ Quick Upload"])

    # ---- Library ----
    with tab_lib:
        summary = lib.library_summary()
        if not summary:
            st.info("No exams yet. Use **➕ Add New Exam** to create one.")
        else:
            st.caption("Pick an exam, then choose full-exam or 60-question set mode.")
            exam_names = [s["exam"] for s in summary]
            chosen = st.selectbox("Choose an exam", exam_names, key="lib_exam")
            detail = next(s for s in summary if s["exam"] == chosen)
            st.caption(f"📄 {detail['pdf_count']} PDF(s): " + ", ".join(detail["pdfs"]))
            colA, colB = st.columns(2)
            with colA:
                if st.button("📚 Load this exam", type="primary", key="lib_load"):
                    _load_exam_with_progress(chosen, force=False)
            with colB:
                if st.button("🔄 Re-parse (ignore cache)", key="lib_reparse"):
                    _load_exam_with_progress(chosen, force=True)

    # ---- Add new exam (feature #5) ----
    with tab_add:
        st.caption("Create a new exam folder and upload its PDF(s). They'll appear "
                   "in the library instantly.")
        new_name = st.text_input("Exam name", placeholder="e.g. AZ-104", key="add_name")
        new_files = st.file_uploader("Exam PDF(s)", type=["pdf"],
                                     accept_multiple_files=True, key="add_files")
        if st.button("➕ Create exam", type="primary", key="add_create"):
            try:
                folder, saved = lib.add_exam(new_name, new_files or [])
                st.success(f"Created **{new_name}** with {len(saved)} PDF(s): "
                           + ", ".join(saved))
                st.caption("Switch to the **📚 Question Library** tab to load it.")
            except ValueError as e:
                st.error(str(e))

    # ---- Quick upload (one-off, not saved to library) ----
    with tab_upload:
        st.caption("Practice a one-off PDF without adding it to the library.")
        uploaded = st.file_uploader("Upload a PDF", type=["pdf"], key="quick_up")
        if uploaded is not None:
            if st.session_state.image_dir is None:
                st.session_state.image_dir = tempfile.mkdtemp(prefix="certprep_img_")
            with st.spinner("Parsing..."):
                full_text, page_images = extract_pdf_content(
                    uploaded.read(), st.session_state.image_dir)
                questions = parse_questions(full_text, page_images)
            if not questions:
                st.error("No questions could be parsed from this PDF.")
            else:
                st.success(f"Parsed {len(questions)} questions.")
                load_questions_into_state(questions, uploaded.name, uploaded.name)
                st.rerun()


def _load_exam_with_progress(exam, force):
    prog_bar = st.progress(0.0)
    status = st.empty()

    def cb(done, total, fname):
        status.caption(f"Parsing {fname} ({done}/{total})...")
        prog_bar.progress(done / max(total, 1))

    with st.spinner(f"Loading {exam}..."):
        questions = lib.load_exam(exam, force=force, progress=cb)
    status.empty()
    if not questions:
        st.error(f"No questions found for {exam}.")
        return
    st.success(f"Loaded {len(questions)} questions from {exam}.")
    load_questions_into_state(questions, exam, exam)
    st.rerun()


# ---------------------------------------------------------------------------
# Exam-mode chooser (feature #4) + resume/fresh (feature #6)
# ---------------------------------------------------------------------------

def show_mode_page():
    st.title("🎯 Choose Exam Mode")
    st.caption(f"Exam: **{st.session_state.exam_name}** · "
               f"{len(st.session_state.all_questions)} questions total")

    all_q = st.session_state.all_questions

    mode = st.radio(
        "How do you want to practise?",
        ["Full exam (all questions in one sitting)",
         "60-question sets (each with case studies + Yes/No)"],
        key="mode_choice")

    chosen_set_idx = 0
    sets = []
    if mode.startswith("60"):
        sets = eb.build_sets(all_q)
        st.session_state.exam_sets = sets
        st.markdown(f"**{len(sets)} set(s)** built from {len(all_q)} questions:")
        rows = []
        for i, s in enumerate(sets):
            summ = eb.set_summary(s)
            rows.append({"Set": f"Set {i+1}", "Questions": summ["total"],
                         "Case-study Qs": summ["case_study_questions"],
                         "Case studies": summ["case_studies"],
                         "Yes/No": summ["yesno"]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        chosen_set_idx = st.selectbox(
            "Which set?", options=list(range(len(sets))),
            format_func=lambda i: f"Set {i+1} ({len(sets[i])} questions)", key="mode_set")

    st.markdown("### ⏱️ Timing")
    timed = st.checkbox("Timed mode", value=False, key="mode_timed")
    limit = st.number_input("Time limit (minutes)", 1, 300, 120, 5,
                            disabled=not timed, key="mode_limit")

    # Determine exam_mode key for progress files.
    exam_mode = "full" if mode.startswith("Full") else f"set{chosen_set_idx + 1}"

    # Resume / fresh (feature #6)
    st.markdown("---")
    summary = prog.progress_summary(st.session_state.exam_name, exam_mode)
    cols = st.columns(2)
    with cols[0]:
        if summary:
            st.info(f"💾 Saved progress found — {summary['answered']}/{summary['total']} "
                    f"answered · saved {summary['saved_at']}")
            if st.button("▶️ Resume previous progress", type="primary", key="resume_btn"):
                _start_exam(exam_mode, sets, chosen_set_idx, timed, limit, resume=True)
        else:
            st.caption("No saved progress for this mode yet.")
    with cols[1]:
        label = "🆕 Start fresh" if summary else "🚀 Start exam"
        if st.button(label, type="primary" if not summary else "secondary", key="fresh_btn"):
            _start_exam(exam_mode, sets, chosen_set_idx, timed, limit, resume=False)

    st.markdown("---")
    if st.button("🏠 Back to home"):
        full_reset()
        st.rerun()


def _start_exam(exam_mode, sets, set_idx, timed, limit, resume):
    # Pick the active question list.
    if exam_mode == "full":
        questions = list(st.session_state.all_questions)
    else:
        questions = list(sets[set_idx])

    st.session_state.questions = questions
    st.session_state.exam_mode = exam_mode
    reset_quiz_progress()
    st.session_state.timed_mode = timed
    st.session_state.time_limit_minutes = limit
    st.session_state.start_time = time.time()

    if resume:
        data = prog.load_progress(st.session_state.exam_name, exam_mode)
        if data:
            apply_progress_payload(data)

    st.session_state.show_mode = False
    st.session_state.quiz_started = True
    st.rerun()


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------

def show_quiz_page():
    questions = st.session_state.questions
    idx = st.session_state.current_question_index
    total = len(questions)
    q = questions[idx]

    render_navigator()

    if st.session_state.timed_mode and st.session_state.start_time is not None:
        if get_time_remaining(st.session_state.start_time,
                              st.session_state.time_limit_minutes * 60) <= 0:
            st.session_state.quiz_completed = True
            st.rerun()

    render_exam_header(q.get("question_number", idx + 1))

    if q.get("is_case_study") and q.get("case_scenario"):
        _render_case_study(q, idx)
    else:
        st.markdown("<div class='exam-card'>", unsafe_allow_html=True)
        render_stem(q)
        render_question_body(q, idx, show_images_in_body=True)
        render_question_controls(q, idx)
        st.markdown("</div>", unsafe_allow_html=True)

    render_footer_nav(idx, total)

    if st.session_state.timed_mode:
        time.sleep(1)
        st.rerun()


def _render_case_study(q, idx):
    pos, size = q.get("case_position"), q.get("case_size")
    sections = split_scenario_sections(q["case_scenario"])
    imgs = [p for p in q.get("images", []) if os.path.exists(p)]

    panel, main = st.columns([1, 3])

    with panel:
        st.markdown("<div class='cs-panel-wrap'>", unsafe_allow_html=True)
        if pos and size:
            st.markdown(f"<div class='cs-qcount'>Case Study Question:<br>{pos} of {size}</div>",
                        unsafe_allow_html=True)
        st.markdown("<div class='cs-nav'>", unsafe_allow_html=True)

        active = st.session_state.cs_view == "__question__"
        if st.button("📝 Question", key=f"csnav_q_{idx}",
                     type="primary" if active else "secondary", use_container_width=True):
            st.session_state.cs_view = "__question__"; st.rerun()

        for si, (title, _b) in enumerate(sections):
            tag = f"sec_{si}"
            active = st.session_state.cs_view == tag
            if st.button(title, key=f"csnav_{idx}_{si}",
                         type="primary" if active else "secondary", use_container_width=True):
                st.session_state.cs_view = tag; st.rerun()

        if imgs:
            active = st.session_state.cs_view == "__exhibits__"
            if st.button(f"🖼️ Tables & exhibits ({len(imgs)})", key=f"csnav_ex_{idx}",
                         type="primary" if active else "secondary", use_container_width=True):
                st.session_state.cs_view = "__exhibits__"; st.rerun()

        st.markdown("</div></div>", unsafe_allow_html=True)

    with main:
        st.markdown("<div class='exam-card'>", unsafe_allow_html=True)
        view = st.session_state.cs_view
        if view == "__question__":
            st.caption("Here is a question that is tied to this case study.")
            render_stem(q)
            render_question_body(q, idx, show_images_in_body=False)
            render_question_controls(q, idx)
        elif view == "__exhibits__":
            st.markdown("### 🖼️ Tables & exhibits")
            for p in imgs:
                st.image(p, use_container_width=True)
            st.info("Use **📝 Question** on the left to return and answer.")
        elif view.startswith("sec_"):
            si = int(view.split("_")[1])
            if 0 <= si < len(sections):
                title, body = sections[si]
                st.markdown(f"### {title}")
                st.markdown(format_body(body))
                if imgs and "table" in body.lower():
                    with st.expander("🖼️ Related tables & exhibits", expanded=True):
                        for p in imgs:
                            st.image(p, use_container_width=True)
            st.info("Use **📝 Question** on the left to return and answer.")
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Report page (feature #8)
# ---------------------------------------------------------------------------

def show_results_page():
    render_report()
    st.markdown("---")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("🔄 Restart this set", type="primary"):
            reset_quiz_progress()
            st.session_state.quiz_started = True
            st.session_state.start_time = time.time()
            st.rerun()
    with b2:
        if st.button("🎯 Choose another mode"):
            reset_quiz_progress()
            st.session_state.show_mode = True
            st.rerun()
    with b3:
        if st.button("🏠 Home"):
            full_reset()
            st.rerun()
