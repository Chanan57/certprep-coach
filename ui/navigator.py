"""Sidebar navigator: jump-to-question dropdown + clickable number grid."""

import streamlit as st

from ui.state import goto_question, is_answered, question_status_icon


def _on_jump_select():
    st.session_state.current_question_index = st.session_state["nav_jump_select"]


def render_navigator():
    questions = st.session_state.questions
    total = len(questions)
    current = st.session_state.current_question_index

    st.sidebar.header("🧭 Navigator")
    answered = sum(1 for i in range(total) if is_answered(i))
    flagged = len(st.session_state.flagged_indexes)
    c1, c2, c3 = st.sidebar.columns(3)
    c1.metric("✅ Done", answered)
    c2.metric("🚩 Review", flagged)
    c3.metric("⚪ Left", total - answered)

    # Sync the dropdown value BEFORE the widget is instantiated (allowed).
    # goto_question() only sets current_question_index, so we mirror it here.
    st.session_state["nav_jump_select"] = current

    labels = [f"{question_status_icon(i)} Q{q.get('question_number', i + 1)}"
              for i, q in enumerate(questions)]
    st.sidebar.selectbox(
        "Jump to question",
        options=list(range(total)),
        format_func=lambda i: f"{labels[i]}  ({i + 1}/{total})",
        key="nav_jump_select",
        on_change=_on_jump_select,
    )

    view = st.sidebar.radio("Show", ["All", "Review later", "Unanswered"],
                            horizontal=True, key="nav_view")
    st.sidebar.caption("Click a number to jump:")
    per_row = 5
    row = None
    shown = 0
    for i in range(total):
        if view == "Review later" and i not in st.session_state.flagged_indexes:
            continue
        if view == "Unanswered" and is_answered(i):
            continue
        if shown % per_row == 0:
            row = st.sidebar.columns(per_row)
        col = row[shown % per_row]
        btn_type = "primary" if i == current else "secondary"
        if col.button(f"{question_status_icon(i)}{i + 1}", key=f"nav_btn_{i}",
                      type=btn_type, use_container_width=True):
            goto_question(i)
        shown += 1
    if shown == 0:
        st.sidebar.info("No questions match this filter.")
    st.sidebar.caption("✅ answered · 🚩 review later · ⚪ not attempted")
