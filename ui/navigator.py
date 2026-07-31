"""Sidebar navigator (P2 + P3): premium all-question navigation.

Shows every question in the current set, the live progress bar + stats, a
jump-to dropdown, a click-to-jump grid, and a dedicated "Review Later" list.
Home / Save controls and the collapse toggle are preserved from the original.
"""

import streamlit as st

from src import progress as prog
from ui.state import (
    goto_question, is_answered, question_status_icon, go_home,
    build_progress_payload,
)


def _on_jump_select():
    st.session_state.current_question_index = st.session_state["nav_jump_select"]
    st.session_state.cs_view = "__question__"


def _save_now():
    """Save progress to disk."""
    payload = build_progress_payload()
    prog.save_progress(st.session_state.exam_name,
                       st.session_state.exam_mode, payload)
    st.session_state["_saved_toast"] = True


def render_navigator():
    questions = st.session_state.questions
    total = len(questions)
    current = st.session_state.current_question_index

    sb = st.sidebar

    # ---- Top controls: Home + Save ----
    top1, top2 = sb.columns(2)
    with top1:
        if st.button("🏠 Home", use_container_width=True, key="nav_home"):
            go_home()
    with top2:
        if st.button("💾 Save", use_container_width=True, key="nav_save"):
            _save_now()

    if st.session_state.pop("_saved_toast", False):
        sb.success("Progress saved ✓")

    sb.markdown("## 🧭 Exam Navigator")

    # ---- Live stats ----
    answered = sum(1 for i in range(total) if is_answered(i))
    flagged = len(st.session_state.flagged_indexes)
    remaining = max(total - answered, 0)
    pct = int((answered / total) * 100) if total else 0

    sb.markdown(
        f"""
        <div class="nav-stat-card">
            <div class="nav-stat-title">Progress</div>
            <div class="nav-stat-main">{answered} / {total}</div>
            <div class="nav-stat-sub">{pct}% completed</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    sb.progress(pct / 100 if total else 0.0)

    c1, c2, c3 = sb.columns(3)
    c1.metric("✅ Done", answered)
    c2.metric("🚩 Review", flagged)
    c3.metric("⚪ Left", remaining)

    # ---- Collapse / expand toggle ----
    st.session_state.nav_collapsed = sb.toggle(
        "Collapse question grid", value=st.session_state.nav_collapsed,
        help="Hide the question grid to focus on the current question.")

    # ---- Jump-to dropdown (synced before widget creation) ----
    st.session_state["nav_jump_select"] = current
    labels = [f"{question_status_icon(i)} Q{q.get('question_number', i + 1)}"
              for i, q in enumerate(questions)]
    sb.selectbox("Jump to question", options=list(range(total)),
                 format_func=lambda i: f"{labels[i]}  ({i + 1}/{total})",
                 key="nav_jump_select", on_change=_on_jump_select)

    if st.session_state.nav_collapsed:
        sb.caption("Grid hidden — untick *Collapse question grid* to show it.")
        return

    # ---- Filterable click-to-jump grid ----
    view = sb.radio("Show", ["All", "Review later", "Unanswered"],
                    horizontal=True, key="nav_view")
    sb.caption("Click a number to jump:")
    per_row = 4
    row = None
    shown = 0
    for i in range(total):
        if view == "Review later" and i not in st.session_state.flagged_indexes:
            continue
        if view == "Unanswered" and is_answered(i):
            continue
        if shown % per_row == 0:
            row = sb.columns(per_row)
        col = row[shown % per_row]
        btn_type = "primary" if i == current else "secondary"
        if col.button(f"{question_status_icon(i)}{i + 1}", key=f"nav_btn_{i}",
                      type=btn_type, use_container_width=True):
            goto_question(i)
        shown += 1
    if shown == 0:
        sb.info("No questions match this filter.")

    # ---- Dedicated Review Later list (P3) ----
    if st.session_state.flagged_indexes:
        sb.markdown("---")
        sb.markdown("### 🚩 Review Later")
        for i in sorted(st.session_state.flagged_indexes):
            if 0 <= i < total:
                qn = questions[i].get("question_number", i + 1)
                if sb.button(f"🚩 Q{qn}", key=f"nav_flag_{i}",
                             use_container_width=True):
                    goto_question(i)

    sb.caption("✅ answered · 🚩 review later · ⚪ not attempted")
