"""Exam-style header: Question number, progress segments, and countdown timer."""

import time

import streamlit as st

from src.quiz_engine import get_time_remaining
from ui.state import compute_sections, hhmmss


def render_exam_header(qnum):
    stats = compute_sections()

    if st.session_state.timed_mode and st.session_state.start_time is not None:
        remaining = get_time_remaining(st.session_state.start_time,
                                       st.session_state.time_limit_minutes * 60)
        timer = hhmmss(remaining)
    elif st.session_state.start_time is not None:
        timer = hhmmss(time.time() - st.session_state.start_time)
    else:
        timer = "00 : 00 : 00"

    segs = []
    order = [("Standalone Questions", "Standalone"),
             ("Case Study", "Case Study"),
             ("Lab", "Lab")]
    for label, key in order:
        s = stats[key]
        if s["total"] == 0:
            continue
        pct = int((s["done"] / s["total"]) * 100) if s["total"] else 0
        count = f"({s['done']}/{s['total']})"
        segs.append(
            f"<div class='prog-item'><div class='prog-label'>{label} {count}</div>"
            f"<div class='prog-bar'><div class='prog-fill' style='width:{pct}%'></div></div></div>"
        )
    prog_html = "<div class='prog-wrap'>" + "".join(segs) + "</div>"

    st.markdown(
        f"""
        <div class="exam-topbar">
          <div class="exam-qnum">Question {qnum}</div>
          <div><div class="exam-timer-label">TIME REMAINING</div>
               <div class="exam-timer">{timer}</div></div>
        </div>
        {prog_html}
        """,
        unsafe_allow_html=True,
    )
