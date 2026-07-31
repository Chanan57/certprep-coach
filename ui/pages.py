"""Top-level pages: home/library/add-exam, mode chooser, quiz, report."""

import os
import time
import tempfile

import streamlit as st
import pandas as pd

from src.pdf_reader import extract_pdf_content
from src.question_parser import parse_questions
from src import library as lib
from src import exam_prep
from src import exam_builder as eb
from src import progress as prog
from src.quiz_engine import (
    shuffle_questions, shuffle_questions_grouped, shuffle_options,
    filter_by_topics, filter_by_types, get_time_remaining,
)

try:
    from src import ai_extractor as ai
    HAS_AI = True
except Exception:  # noqa
    HAS_AI = False

from ui.state import (
    TYPE_LABELS, reset_quiz_progress, full_reset, load_questions_into_state,
    split_scenario_sections, group_sections, format_body, apply_progress_payload,
    qid,
)
from ui.header import render_exam_header
from ui.navigator import render_navigator
from ui.questions import (
    render_question_body, render_reading_body, render_question_controls,
    render_footer_nav, render_stem,
)
from ui.report import render_report


# ---------------------------------------------------------------------------
# AI config helpers
#
# TOKEN POLICY: OpenAI is called (tokens spent) ONLY via the explicit "Prepare"
# / "Create & prepare" action, which uses the REAL key (_ai_cfg()).
# Practice, Reading, prewarm and per-question rendering use a CACHE-ONLY config
# (_ai_cfg_cache_only) — it reads the shared/local disk cache for free and never
# calls the API. If a question wasn't prepared, it simply falls back to
# manual / positional rendering (no tokens spent).
# ---------------------------------------------------------------------------

def _ai_cfg():
    """Real config (has the API key) — used ONLY by Prepare."""
    if not HAS_AI:
        return None
    return ai.get_config()


def _ai_cfg_cache_only():
    """
    A config that reads the disk cache but NEVER calls the API, because it has
    no api_key. analyze_question reads the cache BEFORE checking the key, so a
    key-less config = "return cached result if present, else give up" — zero
    tokens. This is what Practice/Reading/prewarm use.
    """
    if not HAS_AI:
        return None
    cfg = dict(ai.get_config())
    cfg["api_key"] = ""     # force cache-only: cache is read, API is skipped
    return cfg


def _get_analysis(question):
    """
    Holistic AI analysis for a question, cached in session. CACHE-ONLY — never
    spends tokens. Returns the prepared analysis if it exists on disk/session,
    else None (caller falls back gracefully).
    """
    if not HAS_AI:
        return None
    cache = st.session_state.setdefault("_ai_analysis", {})
    k = qid(question)
    if k in cache:
        return cache[k]
    if not any(os.path.exists(p) for p in question.get("images", [])):
        cache[k] = None
        return None
    res = ai.analyze_question(question, _ai_cfg_cache_only())   # no tokens
    cache[k] = res if res.get("ok") else None
    return cache[k]


def _categorized_images(question):
    """
    Return (reference_images, answer_images) for a case study.

    Uses the holistic AI analysis roles: 'answer_key' images are the answer
    (hidden in practice); everything else is reference. Falls back to a
    positional rule when there's no AI analysis: for 2+ images the LAST one is
    the answer key.
    """
    imgs = [p for p in question.get("images", []) if os.path.exists(p)]
    if not imgs:
        return [], []

    analysis = _get_analysis(question)      # cache-only, free
    roles = (analysis or {}).get("roles") if analysis else None
    if roles:
        answer = [p for p in imgs if roles.get(p) == "answer_key"]
        reference = [p for p in imgs if p not in answer]
        if reference:                       # never hide everything
            return reference, answer

    # Fallback: positional rule.
    if len(imgs) >= 2:
        return imgs[:-1], imgs[-1:]
    return imgs, []


# ---------------------------------------------------------------------------
# One-click exam preparation (the ONLY place tokens are spent)
# ---------------------------------------------------------------------------

def _prepare_exam_ui(exam_name):
    """Run the full prepare_exam pipeline with a live progress bar + summary.
    This is the only path that calls OpenAI (spends tokens)."""
    bar = st.progress(0.0)
    status = st.empty()

    def _prog(frac, msg):
        bar.progress(min(max(frac, 0.0), 1.0))
        status.caption(f"⚙️ {msg}")

    with st.spinner(f"Preparing {exam_name}..."):
        summary = exam_prep.prepare_exam(exam_name, cfg=_ai_cfg(), progress=_prog)

    bar.empty()
    status.empty()

    if summary["questions"] == 0:
        st.error(f"No questions could be parsed from **{exam_name}**.")
        return summary

    st.success(
        f"✅ **{exam_name}** is ready! "
        f"{summary['questions']} questions · "
        f"{summary['with_images']} with images · "
        f"{summary['with_community']} with discussions · "
        f"{summary['ai_analysed']} AI-analysed."
    )
    if not summary["ai_available"]:
        st.info("💡 AI wasn't configured, so image questions use manual/fallback "
                "rendering. Add OPENAI_API_KEY to enable auto-built widgets.")
    # New prepared data invalidates any stale in-session analysis.
    st.session_state.pop("_ai_analysis", None)
    st.session_state.pop("_prewarm_sig", None)
    return summary


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------

def show_home_page():
    st.title("📘 CertPrep Coach")
    st.subheader("Exam Simulator")

    tab_lib, tab_add, tab_upload = st.tabs(
        ["📚 Question Library", "➕ Add New Exam", "⬆️ Quick Upload"])

    with tab_lib:
        summary = lib.library_summary()
        if not summary:
            st.info("No exams yet. Use **➕ Add New Exam** to create one.")
        else:
            st.caption("Pick an exam, then choose Practice or Reading mode.")
            exam_names = [s["exam"] for s in summary]
            chosen = st.selectbox("Choose an exam", exam_names, key="lib_exam")
            detail = next(s for s in summary if s["exam"] == chosen)
            st.caption(f"📄 {detail['pdf_count']} PDF(s): " + ", ".join(detail["pdfs"]))
            colA, colB, colC = st.columns(3)
            with colA:
                if st.button("📚 Load this exam", type="primary", key="lib_load"):
                    _load_exam_with_progress(chosen, force=False)
            with colB:
                if st.button("🔄 Re-parse (ignore cache)", key="lib_reparse"):
                    _load_exam_with_progress(chosen, force=True)
            with colC:
                if st.button("⚙️ Prepare (AI + all)", key="lib_prepare"):
                    _prepare_exam_ui(chosen)
            st.caption("💡 **Prepare** (one-time, spends AI tokens) fully readies an "
                       "exam: parses questions, captures discussions, extracts images, "
                       "and runs AI. After that, **Load / Practice / Reading are free** "
                       "— they only read the cached results.")

    with tab_add:
        st.caption("Create a new exam folder, upload its PDF(s), and fully "
                   "prepare it in one step.")
        new_name = st.text_input("Exam name", placeholder="e.g. AZ-104", key="add_name")
        new_files = st.file_uploader("Exam PDF(s)", type=["pdf"],
                                     accept_multiple_files=True, key="add_files")
        if st.button("➕ Create & prepare exam", type="primary", key="add_create"):
            try:
                folder, saved = lib.add_exam(new_name, new_files or [])
                st.success(f"Created **{new_name}** with {len(saved)} PDF(s): "
                           + ", ".join(saved))
                _prepare_exam_ui(new_name)
                st.caption("Go to **📚 Question Library** to start practising.")
            except ValueError as e:
                st.error(str(e))

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
    # Loading a different exam invalidates prior session analysis + prewarm.
    st.session_state.pop("_ai_analysis", None)
    st.session_state.pop("_prewarm_sig", None)
    load_questions_into_state(questions, exam, exam)
    st.rerun()


# ---------------------------------------------------------------------------
# Mode chooser
# ---------------------------------------------------------------------------

def show_mode_page():
    st.title("🎯 Choose How to Study")
    st.caption(f"Exam: **{st.session_state.exam_name}** · "
               f"{len(st.session_state.all_questions)} questions total")

    all_q = st.session_state.all_questions

    st.markdown("### 📖 Mode")
    app_mode = st.radio(
        "Choose a mode",
        ["Practice mode (answer questions, get scored)",
         "Reading mode (study answers + community discussions)"],
        key="mode_app", label_visibility="collapsed")
    is_reading = app_mode.startswith("Reading")

    st.markdown("### 🧩 Coverage")
    coverage = st.radio(
        "How much at once?",
        ["Full exam (all questions)",
         "60-question sets (each with case studies + Yes/No)",
         "⚡ Quick test (10 mixed-type questions)"],
        key="mode_choice", label_visibility="collapsed")

    chosen_set_idx = 0
    sets = []
    if coverage.startswith("60"):
        sets = eb.build_sets(all_q)
        st.session_state.exam_sets = sets
        rows = []
        for i, s in enumerate(sets):
            su = eb.set_summary(s)
            rows.append({"Set": f"Set {i+1}", "Questions": su["total"],
                         "Case-study Qs": su["case_study_questions"],
                         "Case studies": su["case_studies"], "Yes/No": su["yesno"]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        chosen_set_idx = st.selectbox(
            "Which set?", options=list(range(len(sets))),
            format_func=lambda i: f"Set {i+1} ({len(sets[i])} questions)", key="mode_set")
    elif coverage.startswith("⚡"):
        qt = eb.build_quick_test(all_q, size=10)
        st.session_state.exam_sets = [qt]
        mix = eb.type_breakdown(qt)
        mix_str = " · ".join(f"{TYPE_LABELS.get(t, t)} × {c}" for t, c in mix.items())
        st.caption(f"⚡ Quick test: **{len(qt)} questions** — {mix_str}")
        if st.button("🔀 Reshuffle quick test", key="quick_reshuffle"):
            st.session_state.exam_sets = [eb.build_quick_test(all_q, size=10)]
            st.rerun()

    timed = False
    limit = 120
    if not is_reading:
        st.markdown("### ⏱️ Timing")
        timed = st.checkbox("Timed mode", value=False, key="mode_timed")
        default_limit = 15 if coverage.startswith("⚡") else 120
        limit = st.number_input("Time limit (minutes)", 1, 300, default_limit, 5,
                                disabled=not timed, key="mode_limit")

    if coverage.startswith("Full"):
        exam_mode = "full"
    elif coverage.startswith("⚡"):
        exam_mode = "quick"
    else:
        exam_mode = f"set{chosen_set_idx + 1}"

    st.markdown("---")
    if not is_reading:
        summary = prog.progress_summary(st.session_state.exam_name, exam_mode)
        cols = st.columns(2)
        with cols[0]:
            if summary:
                st.info(f"💾 Saved progress — {summary['answered']}/{summary['total']} "
                        f"answered · saved {summary['saved_at']}")
                if st.button("▶️ Resume previous progress", type="primary", key="resume_btn"):
                    _start(exam_mode, sets, chosen_set_idx, timed, limit, "practice", resume=True)
            else:
                st.caption("No saved progress for this mode yet.")
        with cols[1]:
            label = "🆕 Start fresh" if summary else "🚀 Start practice"
            if st.button(label, type="secondary" if summary else "primary", key="fresh_btn"):
                _start(exam_mode, sets, chosen_set_idx, timed, limit, "practice", resume=False)
    else:
        if st.button("📖 Start reading", type="primary", key="read_btn"):
            _start(exam_mode, sets, chosen_set_idx, False, limit, "reading", resume=False)

    st.markdown("---")
    if st.button("🏠 Back to home"):
        full_reset()
        st.rerun()


def _prewarm_ai(questions):
    """
    Load prepared AI analysis into the session dict so per-question rendering is
    instant. CACHE-ONLY — never spends tokens. Guarded so it runs at most once
    per (exam, mode, size); if nothing is cached on disk it simply does nothing.
    """
    if not HAS_AI:
        return
    targets = [q for q in questions
               if any(os.path.exists(p) for p in q.get("images", []))]
    if not targets:
        return

    # Skip if we've already warmed this exact set.
    sig = (f"{st.session_state.get('exam_name')}|"
           f"{st.session_state.get('exam_mode')}|{len(questions)}")
    if st.session_state.get("_prewarm_sig") == sig:
        return

    analysis_cache = st.session_state.setdefault("_ai_analysis", {})
    cfg = _ai_cfg_cache_only()        # cache-only: NO tokens
    bar = st.progress(0.0)
    status = st.empty()
    status.caption("📂 Loading prepared questions (from cache)...")
    for i, q in enumerate(targets):
        k = qid(q)
        if k not in analysis_cache:
            res = ai.analyze_question(q, cfg)     # reads disk cache only
            analysis_cache[k] = res if res.get("ok") else None
        bar.progress((i + 1) / len(targets))
    status.empty()
    bar.empty()
    st.session_state["_prewarm_sig"] = sig


def _start(exam_mode, sets, set_idx, timed, limit, app_mode, resume):
    if exam_mode == "full":
        questions = list(st.session_state.all_questions)
    elif exam_mode == "quick":
        questions = list(st.session_state.exam_sets[0]) if st.session_state.exam_sets else []
    else:
        questions = list(sets[set_idx])

    st.session_state.questions = questions
    st.session_state.exam_mode = exam_mode
    st.session_state.app_mode = app_mode
    reset_quiz_progress()
    st.session_state.timed_mode = timed
    st.session_state.time_limit_minutes = limit
    st.session_state.start_time = time.time()

    if resume:
        data = prog.load_progress(st.session_state.exam_name, exam_mode)
        if data:
            apply_progress_payload(data)

    _prewarm_ai(questions)     # cache-only, free

    st.session_state.show_mode = False
    st.session_state.quiz_started = True
    st.rerun()


# ---------------------------------------------------------------------------
# Quiz / Reading page
# ---------------------------------------------------------------------------

def show_quiz_page():
    questions = st.session_state.questions
    idx = st.session_state.current_question_index
    total = len(questions)
    q = questions[idx]
    reading = st.session_state.app_mode == "reading"

    render_navigator()

    if not reading and st.session_state.timed_mode and st.session_state.start_time is not None:
        if get_time_remaining(st.session_state.start_time,
                              st.session_state.time_limit_minutes * 60) <= 0:
            st.session_state.quiz_completed = True
            st.rerun()

    render_exam_header(q.get("question_number", idx + 1))
    if reading:
        st.caption("📖 **Reading mode** — answers and community discussion are shown.")

    if q.get("is_case_study") and q.get("case_scenario"):
        _render_case_study(q, idx, reading)
    else:
        with st.container(border=True):
            render_stem(q)
            if reading:
                render_reading_body(q, idx, show_images_in_body=True)
            else:
                render_question_body(q, idx, show_images_in_body=True)
                render_question_controls(q, idx)

    render_footer_nav(idx, total)

    if not reading and st.session_state.timed_mode:
        time.sleep(1)
        st.rerun()


def _render_case_study(q, idx, reading):
    pos, size = q.get("case_position"), q.get("case_size")
    sections = split_scenario_sections(q["case_scenario"])
    nav, content = group_sections(sections)
    reference_imgs, answer_imgs = _categorized_images(q)

    panel, main = st.columns([1, 3])

    with panel:
        if pos and size:
            st.markdown(f"**Case Study Question:** {pos} of {size}")
        st.markdown("<div class='cs-nav'>", unsafe_allow_html=True)

        active = st.session_state.cs_view == "__question__"
        if st.button("📝 Question", key=f"csnav_q_{idx}",
                     type="primary" if active else "secondary", use_container_width=True):
            st.session_state.cs_view = "__question__"; st.rerun()

        for item in nav:
            if item["type"] == "single":
                active = st.session_state.cs_view == item["key"]
                if st.button(item["label"], key=f"csnav_{idx}_{item['key']}",
                             type="primary" if active else "secondary",
                             use_container_width=True):
                    st.session_state.cs_view = item["key"]; st.rerun()
            else:
                st.markdown(f"<div style='margin:.3rem 0 .1rem;font-weight:600;"
                            f"color:#605E5C;font-size:.8rem'>{item['name']}</div>",
                            unsafe_allow_html=True)
                for child in item["children"]:
                    active = st.session_state.cs_view == child["key"]
                    if st.button("• " + child["label"], key=f"csnav_{idx}_{child['key']}",
                                 type="primary" if active else "secondary",
                                 use_container_width=True):
                        st.session_state.cs_view = child["key"]; st.rerun()

        if reference_imgs:
            active = st.session_state.cs_view == "__exhibits__"
            if st.button(f"🖼️ Tables & exhibits ({len(reference_imgs)})",
                         key=f"csnav_ex_{idx}",
                         type="primary" if active else "secondary", use_container_width=True):
                st.session_state.cs_view = "__exhibits__"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with main:
        with st.container(border=True):
            view = st.session_state.cs_view
            if view == "__question__":
                st.caption("Here is a question that is tied to this case study.")
                render_stem(q)
                if answer_imgs and reading:
                    with st.expander("🗝️ Answer area", expanded=True):
                        for p in answer_imgs:
                            st.image(p, use_container_width=True)
                if reading:
                    render_reading_body(q, idx, show_images_in_body=False)
                else:
                    render_question_body(q, idx, show_images_in_body=False)
                    render_question_controls(q, idx)
            elif view == "__exhibits__":
                st.markdown("### 🖼️ Tables & exhibits")
                for p in reference_imgs:
                    st.image(p, use_container_width=True)
                st.info("Use **📝 Question** on the left to return and answer.")
            elif view in content:
                title, body = content[view]
                st.markdown(f"### {title}")
                st.markdown(format_body(body))
                if reference_imgs and "table" in body.lower():
                    with st.expander("🖼️ Related tables & exhibits", expanded=True):
                        for p in reference_imgs:
                            st.image(p, use_container_width=True)
                st.info("Use **📝 Question** on the left to return and answer.")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def show_results_page():
    if st.session_state.app_mode == "reading":
        st.title("📖 Reading complete")
        st.caption("Reading mode isn't scored. Choose what to do next.")
    else:
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
