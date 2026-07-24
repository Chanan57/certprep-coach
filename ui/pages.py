"""Top-level pages: home/library, setup, quiz, and results."""

import os
import time
import tempfile

import streamlit as st
import pandas as pd

from src.pdf_reader import extract_pdf_content
from src.question_parser import parse_questions
from src import library as lib
from src.quiz_engine import (
    calculate_score, shuffle_questions, shuffle_questions_grouped,
    shuffle_options, filter_by_topics, filter_by_types, build_review_set,
    format_seconds, get_time_remaining,
)

from ui.state import (
    TYPE_LABELS, reset_quiz_progress, full_reset, load_questions_into_state,
    section_of, split_scenario_sections,
)
from ui.header import render_exam_header
from ui.navigator import render_navigator
from ui.questions import render_question_body, render_question_controls, render_footer_nav


# ---------------------------------------------------------------------------
# Home / library + upload
# ---------------------------------------------------------------------------

def show_home_page():
    st.title("📘 CertPrep Coach")
    st.subheader("PDF to Practice Quiz Tool — Exam-style UI")

    tab_library, tab_upload = st.tabs(["📚 Question Library", "⬆️ Upload a PDF"])

    with tab_library:
        summary = lib.library_summary()
        if not summary:
            st.info(
                "No exams found yet. Create a **`Sample Inputs`** folder in the "
                "project root with one subfolder per exam (e.g. `MD 102`, "
                "`SC 401`) and put the exam PDFs inside each. Then reload."
            )
        else:
            st.caption("Pick an exam to load its question bank instantly "
                       "(parsed once, then cached).")
            exam_names = [s["exam"] for s in summary]
            chosen = st.selectbox("Choose an exam", exam_names, key="lib_exam")
            detail = next(s for s in summary if s["exam"] == chosen)
            st.caption(f"📄 {detail['pdf_count']} PDF(s): " + ", ".join(detail["pdfs"]))
            colA, colB = st.columns([1, 1])
            with colA:
                if st.button("📚 Load this exam", type="primary", key="lib_load"):
                    _load_exam_with_progress(chosen, force=False)
            with colB:
                if st.button("🔄 Re-parse (ignore cache)", key="lib_reparse"):
                    _load_exam_with_progress(chosen, force=True)
            rows, cached = lib.cache_info()
            if rows:
                st.caption(f"🗄️ Cache: {rows} PDF(s) stored · exams: {', '.join(cached)}")

    with tab_upload:
        st.caption("Upload a one-off PDF that isn't in the library.")
        uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])
        if uploaded_file is not None:
            if st.session_state.image_dir is None:
                st.session_state.image_dir = tempfile.mkdtemp(prefix="certprep_img_")
            with st.spinner("Reading PDF, extracting images, and parsing questions..."):
                file_bytes = uploaded_file.read()
                full_text, page_images = extract_pdf_content(
                    file_bytes, st.session_state.image_dir)
                questions = parse_questions(full_text, page_images)
            if len(questions) == 0:
                st.error("No questions could be parsed from this PDF.")
                with st.expander("Show extracted raw text for troubleshooting"):
                    st.text_area("Extracted Text", full_text[:20000], height=400)
            else:
                st.success(f"Parsed {len(questions)} questions.")
                load_questions_into_state(questions, uploaded_file.name)
                _show_counts(questions)
                st.rerun()


def _load_exam_with_progress(exam, force):
    prog = st.progress(0.0)
    status = st.empty()

    def cb(done, total, fname):
        status.caption(f"Parsing {fname} ({done}/{total})...")
        prog.progress(done / max(total, 1))

    with st.spinner(f"Loading {exam}..."):
        questions = lib.load_exam(exam, force=force, progress=cb)
    status.empty()
    if not questions:
        st.error(f"No questions found for {exam}.")
        return
    st.success(f"Loaded {len(questions)} questions from {exam}.")
    load_questions_into_state(questions, exam)
    _show_counts(questions)
    st.rerun()


def _show_counts(questions):
    counts = {}
    for q in questions:
        counts[q["type"]] = counts.get(q["type"], 0) + 1
    cols = st.columns(len(counts))
    for col, (t, c) in zip(cols, counts.items()):
        col.metric(TYPE_LABELS.get(t, t), c)
    n_case = sum(1 for q in questions if q["is_case_study"])
    n_img = sum(1 for q in questions if q["images"])
    st.caption(f"📁 {n_case} case-study question(s) · 🖼️ {n_img} with images")


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def show_setup_page():
    st.title("⚙️ Configure Your Practice Session")
    if st.session_state.source_label:
        st.caption(f"Source: **{st.session_state.source_label}**")
    all_q = st.session_state.all_questions

    topics = sorted({q.get("topic", "General") for q in all_q})
    types_present = [t for t in TYPE_LABELS if any(q["type"] == t for q in all_q)]

    st.markdown("### 🏷️ Topics")
    sel_topics = st.multiselect("Filter by topic (empty = all)", topics, default=[])

    st.markdown("### 🧩 Question types")
    sel_types = st.multiselect(
        "Filter by type (empty = all)", types_present, default=[],
        format_func=lambda t: TYPE_LABELS.get(t, t),
    )

    working = filter_by_types(filter_by_topics(all_q, sel_topics), sel_types)
    st.caption(f"Questions in selection: **{len(working)}**")

    st.markdown("---")
    st.markdown("### 🔀 Shuffle")
    c1, c2 = st.columns(2)
    with c1:
        shuffle_q = st.checkbox("Shuffle question order", value=False)
    with c2:
        shuffle_o = st.checkbox("Shuffle answer options (choice questions)", value=False)
    keep_cases = st.checkbox(
        "Keep case-study questions together when shuffling", value=True)

    st.markdown("---")
    st.markdown("### ⏱️ Timed Mode")
    timed = st.checkbox("Enable timed practice", value=False)
    limit = st.number_input("Time limit (minutes)", 1, 300, 30, 5, disabled=not timed)

    st.markdown("---")
    ca, cb = st.columns(2)
    with ca:
        if st.button("🚀 Start Practice", type="primary"):
            if not working:
                st.warning("No questions match your filters.")
            else:
                sess = working
                if shuffle_q:
                    sess = (shuffle_questions_grouped(sess) if keep_cases
                            else shuffle_questions(sess))
                if shuffle_o:
                    sess = [shuffle_options(q) for q in sess]
                st.session_state.questions = sess
                st.session_state.timed_mode = timed
                st.session_state.time_limit_minutes = limit
                reset_quiz_progress()
                st.session_state.quiz_started = True
                st.session_state.show_setup = False
                st.session_state.start_time = time.time()
                st.rerun()
    with cb:
        if st.button("📄 Choose a different exam / PDF"):
            full_reset()
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
        st.write(q["question_text"] or "_(See exhibit image below.)_")
        render_question_body(q, idx, show_images_in_body=True)
        render_question_controls(q, idx)
        st.markdown("</div>", unsafe_allow_html=True)

    render_footer_nav(idx, total)

    if st.session_state.timed_mode:
        time.sleep(1)
        st.rerun()


def _render_case_study(q, idx):
    pos, size = q.get("case_position"), q.get("case_size")
    panel, main = st.columns([1, 2.4])

    with panel:
        st.markdown("<div class='cs-panel'>", unsafe_allow_html=True)
        if pos and size:
            st.markdown(f"<div class='cs-qcount'>Case Study Question:<br>{pos} of {size}</div>",
                        unsafe_allow_html=True)
        for title, body in split_scenario_sections(q["case_scenario"]):
            with st.expander(title, expanded=(title in ("Overview", "Background"))):
                st.markdown(body)
        imgs = [p for p in q.get("images", []) if os.path.exists(p)]
        if imgs:
            with st.expander(f"🖼️ Tables & exhibits ({len(imgs)})", expanded=False):
                for p in imgs:
                    st.image(p, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with main:
        st.markdown("<div class='exam-card'>", unsafe_allow_html=True)
        st.caption("Here is a question that is tied to this case study.")
        st.write(q["question_text"] or "_(See exhibit.)_")
        render_question_body(q, idx, show_images_in_body=False)
        render_question_controls(q, idx)
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

def show_results_page():
    questions = st.session_state.questions
    ua = st.session_state.user_answers
    sa = st.session_state.self_assessed
    flagged = st.session_state.flagged_indexes
    score = calculate_score(ua, questions)

    st.title("🎯 Quiz Results")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Auto-graded", score["gradable_total"])
    c2.metric("Correct", score["correct_count"])
    c3.metric("Incorrect", score["incorrect_count"])
    c4.metric("Score", f"{score['score_percentage']}%")
    st.caption(f"🧪 {score['non_gradable_total']} question(s) were self-assessed.")

    if st.session_state.timed_mode and st.session_state.start_time:
        st.caption(f"⏱️ Time taken: {format_seconds(time.time() - st.session_state.start_time)}")

    st.markdown("---")
    st.subheader("Review your answers")
    rows = []
    for i, q in enumerate(questions):
        if q.get("gradable"):
            sel = "".join(sorted(ua.get(i, "") or "")) or "Not answered"
            cor = "".join(sorted(q["correct_answer"]))
            res = "Correct" if sel == cor else "Incorrect"
        else:
            sel = sa.get(i, "Not assessed")
            cor = "See exhibit"
            res = sa.get(i, "Self-assess")
        rows.append({
            "Q#": q["question_number"], "Section": section_of(q),
            "Case": q.get("case_label") or "", "Type": TYPE_LABELS.get(q["type"]),
            "Your Answer": sel, "Correct": cor, "Result": res,
            "Review": "🚩" if i in flagged else "",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🔁 Practice Again")
    ci, cf = st.columns(2)
    with ci:
        inc = st.checkbox(f"Include incorrect ({score['incorrect_count']})", value=True)
    with cf:
        incf = st.checkbox(f"Include review-later ({len(flagged)})", value=len(flagged) > 0)

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("🎯 Retake Selected", type="primary"):
            rs = build_review_set(ua, questions, flagged, inc, incf)
            if not rs:
                st.warning("No questions selected.")
            else:
                st.session_state.questions = rs
                reset_quiz_progress()
                st.session_state.quiz_started = True
                st.session_state.start_time = time.time()
                st.rerun()
    with b2:
        if st.button("🔄 Restart Full Quiz"):
            reset_quiz_progress()
            st.session_state.quiz_started = True
            st.session_state.start_time = time.time()
            st.rerun()
    with b3:
        if st.button("⚙️ New Session Setup"):
            reset_quiz_progress()
            st.session_state.show_setup = True
            st.rerun()

    st.markdown("---")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download results as CSV", data=csv,
                       file_name="certprep_results.csv", mime="text/csv")
