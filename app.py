import os
import time
import tempfile

import streamlit as st
import pandas as pd

from src.pdf_reader import extract_pdf_content
from src.question_parser import parse_questions
from src.quiz_engine import (
    calculate_score,
    shuffle_questions,
    shuffle_options,
    filter_by_topics,
    filter_by_types,
    build_review_set,
    format_seconds,
    get_time_remaining,
)


st.set_page_config(page_title="CertPrep Coach", page_icon="📘", layout="wide")

TYPE_LABELS = {
    "SINGLE": "Single choice",
    "MULTI": "Multiple choice",
    "HOTSPOT": "Hotspot / dropdown",
    "DRAG DROP": "Drag and drop",
    "SIMULATION": "Simulation",
}


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def initialise_session_state():
    defaults = {
        "all_questions": [],
        "questions": [],
        "current_question_index": 0,
        "user_answers": {},
        "self_assessed": {},
        "flagged_indexes": set(),
        "quiz_started": False,
        "quiz_completed": False,
        "show_setup": False,
        "timed_mode": False,
        "time_limit_minutes": 30,
        "start_time": None,
        "image_dir": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_quiz_progress():
    st.session_state.current_question_index = 0
    st.session_state.user_answers = {}
    st.session_state.self_assessed = {}
    st.session_state.flagged_indexes = set()
    st.session_state.quiz_started = False
    st.session_state.quiz_completed = False
    st.session_state.start_time = None


def full_reset():
    reset_quiz_progress()
    st.session_state.all_questions = []
    st.session_state.questions = []
    st.session_state.show_setup = False


def qid(question):
    """Stable id for a question (used as widget-key prefix)."""
    return f"{question.get('topic','G')}__{question.get('question_number','?')}__{question.get('type','?')}"


# ---------------------------------------------------------------------------
# Question status helpers (used by the navigator)
# ---------------------------------------------------------------------------

def is_answered(i):
    """A question counts as answered if it has a non-empty choice answer or
    a self-assessment recorded."""
    ans = st.session_state.user_answers.get(i)
    if ans:
        return True
    if i in st.session_state.self_assessed:
        return True
    return False


def question_status_icon(i):
    """Return an emoji marker for a question's current status."""
    flagged = i in st.session_state.flagged_indexes
    answered = is_answered(i)
    if flagged and answered:
        return "🚩"          # flagged (takes priority visually)
    if flagged:
        return "🚩"
    if answered:
        return "✅"
    return "⚪"


def goto_question(i):
    st.session_state.current_question_index = i
    st.rerun()


# ---------------------------------------------------------------------------
# Sidebar: jump-to-question navigator
# ---------------------------------------------------------------------------

def render_navigator():
    """Render a sidebar navigator to jump to any question, with status markers."""
    questions = st.session_state.questions
    total = len(questions)
    current = st.session_state.current_question_index

    st.sidebar.header("🧭 Navigator")

    # Live counters
    answered = sum(1 for i in range(total) if is_answered(i))
    flagged = len(st.session_state.flagged_indexes)
    remaining = total - answered
    c1, c2, c3 = st.sidebar.columns(3)
    c1.metric("✅ Done", answered)
    c2.metric("🚩 Flag", flagged)
    c3.metric("⚪ Left", remaining)

    # Fast "jump to #" dropdown (labels show the question number + status).
    labels = []
    for i, q in enumerate(questions):
        labels.append(f"{question_status_icon(i)} Q{q.get('question_number', i + 1)}")
    picked = st.sidebar.selectbox(
        "Jump to question",
        options=list(range(total)),
        index=current,
        format_func=lambda i: f"{labels[i]}  ({i + 1}/{total})",
        key="nav_jump_select",
    )
    if picked != current:
        goto_question(picked)

    # Optional filter to declutter long sets.
    view = st.sidebar.radio(
        "Show", ["All", "Flagged", "Unanswered"], horizontal=True, key="nav_view"
    )

    # Compact clickable grid of question buttons.
    st.sidebar.caption("Click a number to jump:")
    per_row = 5
    row = None
    shown = 0
    for i in range(total):
        if view == "Flagged" and i not in st.session_state.flagged_indexes:
            continue
        if view == "Unanswered" and is_answered(i):
            continue
        if shown % per_row == 0:
            row = st.sidebar.columns(per_row)
        col = row[shown % per_row]
        icon = question_status_icon(i)
        label = f"{icon}{i + 1}"
        # Highlight the current question.
        btn_type = "primary" if i == current else "secondary"
        if col.button(label, key=f"nav_btn_{i}", type=btn_type, use_container_width=True):
            goto_question(i)
        shown += 1

    if shown == 0:
        st.sidebar.info("No questions match this filter.")

    st.sidebar.caption("✅ answered · 🚩 flagged · ⚪ not attempted")


# ---------------------------------------------------------------------------
# Home / upload
# ---------------------------------------------------------------------------

def show_home_page():
    st.title("📘 CertPrep Coach")
    st.subheader("PDF to Practice Quiz Tool — Version 3")
    st.info(
        "Upload a practice-question PDF. The app extracts questions and images, "
        "detects question types, groups case studies, and provides interactive "
        "drag-and-drop and dropdown widgets."
    )

    uploaded_file = st.file_uploader("Upload your PDF file", type=["pdf"])

    if uploaded_file is not None:
        if st.session_state.image_dir is None:
            st.session_state.image_dir = tempfile.mkdtemp(prefix="certprep_img_")

        with st.spinner("Reading PDF, extracting images, and parsing questions..."):
            file_bytes = uploaded_file.read()
            full_text, page_images = extract_pdf_content(
                file_bytes, st.session_state.image_dir
            )
            questions = parse_questions(full_text, page_images)

        if len(questions) == 0:
            st.error("No questions could be parsed from this PDF.")
            with st.expander("Show extracted raw text for troubleshooting"):
                st.text_area("Extracted Text", full_text[:20000], height=400)
        else:
            st.success(f"Parsed {len(questions)} questions.")
            st.session_state.all_questions = questions
            reset_quiz_progress()
            st.session_state.show_setup = True

            counts = {}
            for q in questions:
                counts[q["type"]] = counts.get(q["type"], 0) + 1
            cols = st.columns(len(counts))
            for col, (t, c) in zip(cols, counts.items()):
                col.metric(TYPE_LABELS.get(t, t), c)

            n_case = sum(1 for q in questions if q["is_case_study"])
            n_img = sum(1 for q in questions if q["images"])
            st.caption(f"📁 {n_case} case-study question(s) · 🖼️ {n_img} with images")
            st.rerun()


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def show_setup_page():
    st.title("⚙️ Configure Your Practice Session")
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
                    sess = shuffle_questions(sess)
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
        if st.button("📄 Upload a different PDF"):
            full_reset()
            st.rerun()


# ---------------------------------------------------------------------------
# Shared renderers
# ---------------------------------------------------------------------------

def show_images(images, caption="🖼️ Exhibit / image", expanded=True):
    imgs = [p for p in images if os.path.exists(p)]
    if not imgs:
        return
    with st.expander(f"{caption} ({len(imgs)})", expanded=expanded):
        for p in imgs:
            st.image(p, use_container_width=True)


def render_self_assess(idx):
    st.markdown("**Self-assessment** (check your answer against the exhibit):")
    current = st.session_state.self_assessed.get(idx)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ I got it right", key=f"sa_r_{idx}",
                     type="primary" if current == "correct" else "secondary"):
            st.session_state.self_assessed[idx] = "correct"
            st.rerun()
    with c2:
        if st.button("❌ I got it wrong", key=f"sa_w_{idx}",
                     type="primary" if current == "incorrect" else "secondary"):
            st.session_state.self_assessed[idx] = "incorrect"
            st.rerun()
    if current:
        st.info(f"Marked as: **{current}**")


def render_choice(question, idx, multi):
    options = question["options"]
    labels = [f"{k}. {v}" for k, v in options.items()]

    if multi:
        st.caption("Select all that apply.")
        chosen = []
        prev = st.session_state.user_answers.get(idx, "") or ""
        for k, v in options.items():
            if st.checkbox(f"{k}. {v}", value=(k in prev), key=f"c_{idx}_{k}"):
                chosen.append(k)
        st.session_state.user_answers[idx] = "".join(sorted(chosen))
    else:
        prev = st.session_state.user_answers.get(idx)
        di = None
        if prev:
            for i, lab in enumerate(labels):
                if lab.startswith(prev + "."):
                    di = i
                    break
        pick = st.radio("Select your answer:", labels, index=di, key=f"r_{idx}")
        if pick:
            st.session_state.user_answers[idx] = pick.split(".")[0]

    if question["answer_available"]:
        if st.button("Check Answer", key=f"chk_{idx}"):
            sel = "".join(sorted((st.session_state.user_answers.get(idx) or "")))
            cor = "".join(sorted(question["correct_answer"]))
            if not sel:
                st.warning("Please select an answer first.")
            elif sel == cor:
                st.success(f"✅ Correct. Answer: {cor}")
            else:
                st.error(f"❌ Incorrect. You chose {sel}. Correct answer: {cor}")
    else:
        st.caption("ℹ️ No answer key in this PDF for this question — self-assess after reasoning.")
        render_self_assess(idx)


# ---- Interactive DRAG DROP -------------------------------------------------

def render_dragdrop(question, idx):
    st.caption("↕️ **Drag and drop** — the items and answer area are in the exhibit "
               "below. Enter the items and slots once, then assign each slot.")
    show_images(question["images"], "🖼️ Exhibit (items + answer key)")

    key = qid(question)
    stem = (question.get("question_text") or "").lower()
    seq = "sequence" in stem or "arrange" in stem or "in the correct order" in stem
    default_slots = "Step 1\nStep 2\nStep 3\nStep 4" if seq else "Answer slot 1\nAnswer slot 2"

    with st.expander("🧩 Set up the answer area (one entry per line)", expanded=True):
        cA, cB = st.columns(2)
        with cA:
            items_raw = st.text_area(
                "Draggable items", value=st.session_state.get(f"ddi_{key}", ""),
                key=f"ddi_{key}", height=160,
                placeholder="Delete\nFresh Start\nRetire\nSync\nWipe",
            )
        with cB:
            slots_raw = st.text_area(
                "Answer slots", value=st.session_state.get(f"dds_{key}", default_slots),
                key=f"dds_{key}", height=160,
                placeholder="Device1\nDevice2",
            )

    items = [x.strip() for x in items_raw.splitlines() if x.strip()]
    slots = [x.strip() for x in slots_raw.splitlines() if x.strip()]

    if not items:
        st.warning("Enter the draggable items (from the exhibit) to build the drag-and-drop.")
    else:
        st.markdown("**Assign an item to each slot:**")
        pool = ["(choose)"] + items
        assignments = {}
        for n, slot in enumerate(slots):
            choice = st.selectbox(f"➡️ {slot}", pool, key=f"dd_{key}_{n}")
            assignments[slot] = choice
        chosen = {s: v for s, v in assignments.items() if v != "(choose)"}
        if chosen:
            st.caption("Your sequence: " + " → ".join(f"**{s}** = {v}" for s, v in chosen.items()))

    render_self_assess(idx)


# ---- Interactive HOTSPOT ---------------------------------------------------

def parse_hotspot_lines(raw):
    """Parse 'Label = opt1 | opt2 | opt3' lines into [(label, [opts]), ...]."""
    groups = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" in line:
            label, opts = line.split("=", 1)
            options = [o.strip() for o in opts.split("|") if o.strip()]
        else:
            label, options = line, []
        groups.append((label.strip(), options))
    return groups


def render_hotspot(question, idx):
    st.caption("🔽 **Hotspot** — the dropdowns and answer key are in the exhibit "
               "below. Enter each dropdown once, then make your selections.")
    show_images(question["images"], "🖼️ Exhibit (dropdowns + answer key)")

    key = qid(question)
    stem = (question.get("question_text") or "").lower()
    yesno = "select yes" in stem or "otherwise, select no" in stem or "select no" in stem
    if yesno:
        default = "Statement 1 = Yes | No\nStatement 2 = Yes | No\nStatement 3 = Yes | No"
    else:
        default = "Windows build = Cpu | OSVersion | SystemInfo | WindowsService\nFolder = DiskDrive | FileInfo | MemoryInfo | SystemInfo"

    with st.expander("🧩 Set up the dropdowns (one per line — `Label = opt1 | opt2 | opt3`)",
                     expanded=True):
        config_raw = st.text_area(
            "Dropdowns", value=st.session_state.get(f"hs_{key}", default),
            key=f"hs_{key}", height=140,
        )

    groups = parse_hotspot_lines(config_raw)
    if not groups:
        st.warning("Enter at least one dropdown (from the exhibit) to build the hotspot.")
    else:
        st.markdown("**Make a selection for each dropdown:**")
        selections = {}
        for n, (label, options) in enumerate(groups):
            opts = ["(select)"] + (options if options else ["Yes", "No"])
            selections[label] = st.selectbox(f"🔽 {label}", opts, key=f"hsopt_{key}_{n}")
        picked = {l: v for l, v in selections.items() if v != "(select)"}
        if picked:
            st.caption("Your selections: " + " · ".join(f"**{l}** → {v}" for l, v in picked.items()))

    render_self_assess(idx)


def render_simulation(question, idx):
    st.caption("🧪 **Simulation task** — attempt it in a lab, then check the exhibit.")
    show_images(question["images"], "🖼️ Task solution / exhibit")
    st.text_area("📝 Your working / notes (optional)", key=f"notes_{qid(question)}")
    render_self_assess(idx)


def render_question_body(question, idx, show_choice_images=True):
    qtype = question["type"]
    if qtype == "SINGLE":
        if show_choice_images:
            show_images(question["images"], "🖼️ Exhibit / image")
        render_choice(question, idx, multi=False)
    elif qtype == "MULTI":
        if show_choice_images:
            show_images(question["images"], "🖼️ Exhibit / image")
        render_choice(question, idx, multi=True)
    elif qtype == "HOTSPOT":
        render_hotspot(question, idx)
    elif qtype == "DRAG DROP":
        render_dragdrop(question, idx)
    elif qtype == "SIMULATION":
        render_simulation(question, idx)


# ---------------------------------------------------------------------------
# Quiz page
# ---------------------------------------------------------------------------

def render_timer():
    if not st.session_state.timed_mode or st.session_state.start_time is None:
        return False
    remaining = get_time_remaining(st.session_state.start_time,
                                   st.session_state.time_limit_minutes * 60)
    if remaining <= 0:
        st.error("⏰ Time is up! Submitting your quiz.")
        return True
    if remaining <= 60:
        st.error(f"⏱️ Time remaining: **{format_seconds(remaining)}**")
    elif remaining <= 300:
        st.warning(f"⏱️ Time remaining: **{format_seconds(remaining)}**")
    else:
        st.info(f"⏱️ Time remaining: **{format_seconds(remaining)}**")
    return False


def show_quiz_page():
    questions = st.session_state.questions
    idx = st.session_state.current_question_index
    total = len(questions)
    q = questions[idx]

    # Sidebar navigator (jump to any question).
    render_navigator()

    st.title("📝 Practice Quiz")

    if render_timer():
        st.session_state.quiz_completed = True
        st.rerun()

    st.progress((idx + 1) / total)
    h1, h2, h3 = st.columns(3)
    h1.caption(f"Question {idx + 1} of {total}")
    h2.caption(f"🏷️ {q.get('topic')} · 🧩 {TYPE_LABELS.get(q['type'])}")
    h3.caption(f"✅ {len(st.session_state.user_answers) + len(st.session_state.self_assessed)} done | "
               f"🚩 {len(st.session_state.flagged_indexes)} flagged")

    # Question-type banner (mirrors 'DRAG DROP' / 'HOTSPOT' shown at top of PDF).
    if q["type"] in ("HOTSPOT", "DRAG DROP", "SIMULATION"):
        st.markdown(f"#### 🧩 {TYPE_LABELS.get(q['type']).upper()}")

    # Case-study scenario panel (text only; exhibits shown in the body).
    if q.get("is_case_study") and q.get("case_scenario"):
        label = q.get("case_label") or "Case study"
        pos, size = q.get("case_position"), q.get("case_size")
        badge = f" — part {pos} of {size}" if pos and size else ""
        st.markdown(f"### 📁 Case Study: {label}{badge}")
        with st.expander("📖 Case study scenario", expanded=False):
            st.markdown(q["case_scenario"])
        st.markdown("### ❓ Question")
        st.write(q["question_text"] or "_(See exhibit image.)_")
        render_question_body(q, idx, show_choice_images=True)
    else:
        st.markdown("### Question")
        st.write(q["question_text"] or "_(See exhibit image below.)_")
        render_question_body(q, idx, show_choice_images=True)

    # Flag
    st.markdown("---")
    flagged = idx in st.session_state.flagged_indexes
    if st.button("🚩 Unflag" if flagged else "🚩 Flag as difficult", key=f"flag_{idx}"):
        if flagged:
            st.session_state.flagged_indexes.discard(idx)
        else:
            st.session_state.flagged_indexes.add(idx)
        st.rerun()

    c1, _c2, c3 = st.columns(3)
    with c1:
        if st.button("⬅️ Previous", disabled=idx == 0):
            st.session_state.current_question_index -= 1
            st.rerun()
    with c3:
        if idx < total - 1:
            if st.button("Next ➡️"):
                st.session_state.current_question_index += 1
                st.rerun()
        else:
            if st.button("🏁 Finish Quiz", type="primary"):
                st.session_state.quiz_completed = True
                st.rerun()

    if st.session_state.timed_mode:
        time.sleep(1)
        st.rerun()


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
    st.caption(f"🧪 {score['non_gradable_total']} question(s) were self-assessed "
               "(hotspot/drag-drop/simulation or no answer key in the PDF).")

    if st.session_state.timed_mode and st.session_state.start_time:
        st.caption(f"⏱️ Time taken: {format_seconds(time.time() - st.session_state.start_time)}")

    st.markdown("---")
    st.subheader("Review")
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
            "Q#": q["question_number"],
            "Case": q.get("case_label") or "",
            "Type": TYPE_LABELS.get(q["type"]),
            "Your Answer": sel,
            "Correct": cor,
            "Result": res,
            "Flag": "🚩" if i in flagged else "",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🔁 Practice Again")
    ci, cf = st.columns(2)
    with ci:
        inc = st.checkbox(f"Include incorrect ({score['incorrect_count']})", value=True)
    with cf:
        incf = st.checkbox(f"Include flagged ({len(flagged)})", value=len(flagged) > 0)

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


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def main():
    initialise_session_state()
    if not st.session_state.all_questions:
        show_home_page()
    elif st.session_state.quiz_completed:
        show_results_page()
    elif st.session_state.quiz_started:
        show_quiz_page()
    elif st.session_state.show_setup:
        show_setup_page()
    else:
        show_home_page()


if __name__ == "__main__":
    main()
