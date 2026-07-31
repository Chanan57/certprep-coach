"""Exam-style header: Question number, progress segments, and a study/countdown timer.

TIMER POLICY (P1):
  - Reading mode           -> "READING TIME"  (counts UP / elapsed)
  - Practice, NOT timed    -> "STUDY TIME"    (counts UP / elapsed  ← how long you've studied)
  - Practice, timed mode   -> "TIME REMAINING"(counts DOWN)
The study/reading timer is simply time since start_time, so it reflects the real
time the learner has spent on this set.
"""

import time

import streamlit as st

from src.quiz_engine import get_time_remaining
from ui.state import compute_sections, hhmmss


def render_exam_header(qnum):
    stats = compute_sections()

    reading = st.session_state.get("app_mode") == "reading"
    timed = bool(st.session_state.get("timed_mode")) and st.session_state.start_time is not None

    # ---- Decide timer label + value based on mode ----
    if timed and not reading:
        remaining = get_time_remaining(st.session_state.start_time,
                                       st.session_state.time_limit_minutes * 60)
        timer = hhmmss(remaining)
        timer_label = "TIME REMAINING"
    elif st.session_state.start_time is not None:
        elapsed = time.time() - st.session_state.start_time
        timer = hhmmss(elapsed)
        timer_label = "READING TIME" if reading else "STUDY TIME"
    else:
        timer = "00 : 00 : 00"
        timer_label = "READING TIME" if reading else "STUDY TIME"

    # ---- Progress segments (Standalone / Case Study / Lab) ----
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
          <div><div class="exam-timer-label">{timer_label}</div>
               <div class="exam-timer">{timer}</div></div>
        </div>
        {prog_html}
        """,
        unsafe_allow_html=True,
    )
