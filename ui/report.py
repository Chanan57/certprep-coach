"""
Microsoft-style exam score report (feature #8).

Microsoft scales exam scores to a 100–1000 range with 700 as the pass mark.
We don't know the exact (secret) scaling, so we present a transparent
*estimate*: the percentage of gradable questions answered correctly is mapped
onto the 100–1000 scale, with 70% correct aligned to the 700 pass line.
"""

import time

import streamlit as st
import pandas as pd

from src.quiz_engine import calculate_score, format_seconds
from ui.state import section_of, TYPE_LABELS


PASS_SCALED = 700
PASS_PERCENT = 70.0


def _scaled_score(percent):
    """
    Map a raw percent to Microsoft's 100–1000 scale such that:
      0%   -> 100
      70%  -> 700  (pass line)
      100% -> 1000
    Two linear segments so the 700 pass mark lines up with 70%.
    """
    if percent <= 0:
        return 100
    if percent >= 100:
        return 1000
    if percent <= PASS_PERCENT:
        # 0..70%  -> 100..700
        return round(100 + (percent / PASS_PERCENT) * (PASS_SCALED - 100))
    # 70..100% -> 700..1000
    return round(PASS_SCALED + ((percent - PASS_PERCENT) / (100 - PASS_PERCENT))
                 * (1000 - PASS_SCALED))


def render_report():
    questions = st.session_state.questions
    ua = st.session_state.user_answers
    sa = st.session_state.self_assessed
    flagged = st.session_state.flagged_indexes
    score = calculate_score(ua, questions)

    percent = score["score_percentage"]
    scaled = _scaled_score(percent)
    passed = scaled >= PASS_SCALED

    st.title("📋 Exam Score Report")

    # Headline pass/fail banner
    if passed:
        st.success(f"### ✅ PASS — Scaled score: {scaled} / 1000  (pass mark {PASS_SCALED})")
    else:
        st.error(f"### ❌ Below pass — Scaled score: {scaled} / 1000  (pass mark {PASS_SCALED})")

    st.caption("⚠️ Scaled score is an **estimate**. Microsoft's exact scaling is "
               "confidential; here 70% correct is aligned to the 700 pass line.")

    # Key metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scaled score", f"{scaled}")
    c2.metric("Raw correct", f"{score['correct_count']}/{score['gradable_total']}")
    c3.metric("Percent", f"{percent}%")
    c4.metric("Result", "PASS" if passed else "FAIL")

    if st.session_state.start_time:
        elapsed = time.time() - st.session_state.start_time
        st.caption(f"⏱️ Time taken: {format_seconds(elapsed)}  ·  "
                   f"🧪 {score['non_gradable_total']} self-assessed question(s) "
                   "(hotspot/drag-drop/simulation) are excluded from the scaled score.")

    # Progress toward pass (visual)
    st.progress(min(scaled / 1000, 1.0))

    st.markdown("---")

    # ---- Performance by skill area (topic) ----
    st.subheader("📊 Performance by skill area")
    topic_stats = {}
    for i, q in enumerate(questions):
        if not q.get("gradable"):
            continue
        topic = q.get("topic", "General")
        d = topic_stats.setdefault(topic, {"correct": 0, "total": 0})
        d["total"] += 1
        if "".join(sorted(ua.get(i, "") or "")) == "".join(sorted(q["correct_answer"])):
            d["correct"] += 1

    if topic_stats:
        rows = []
        for topic, d in topic_stats.items():
            pct = round(d["correct"] / d["total"] * 100, 1) if d["total"] else 0
            rows.append({"Skill area": topic, "Correct": d["correct"],
                         "Total": d["total"], "Score %": pct,
                         "": "✅" if pct >= PASS_PERCENT else "⚠️"})
        tdf = pd.DataFrame(rows).sort_values("Score %")
        st.dataframe(tdf, use_container_width=True, hide_index=True)
        weak = [r["Skill area"] for r in rows if r["Score %"] < PASS_PERCENT]
        if weak:
            st.warning("**Focus areas (below 70%):** " + ", ".join(weak))
        else:
            st.success("Solid across all skill areas — nice work! 🎯")
    else:
        st.caption("No auto-graded questions to break down by skill area.")

    st.markdown("---")

    # ---- Section breakdown (Standalone / Case Study / Lab) ----
    st.subheader("🗂️ By section")
    sec_stats = {}
    for i, q in enumerate(questions):
        sec = section_of(q)
        d = sec_stats.setdefault(sec, {"correct": 0, "gradable": 0, "total": 0})
        d["total"] += 1
        if q.get("gradable"):
            d["gradable"] += 1
            if "".join(sorted(ua.get(i, "") or "")) == "".join(sorted(q["correct_answer"])):
                d["correct"] += 1
    sec_rows = []
    for sec, d in sec_stats.items():
        pct = round(d["correct"] / d["gradable"] * 100, 1) if d["gradable"] else None
        sec_rows.append({"Section": sec, "Questions": d["total"],
                         "Auto-graded": d["gradable"], "Correct": d["correct"],
                         "Score %": pct if pct is not None else "—"})
    st.dataframe(pd.DataFrame(sec_rows), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---- Full answer review ----
    with st.expander("🔍 Full answer review", expanded=False):
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
            rows.append({"Q#": q["question_number"], "Section": section_of(q),
                         "Type": TYPE_LABELS.get(q["type"]), "Your answer": sel,
                         "Correct": cor, "Result": res,
                         "Review": "🚩" if i in flagged else ""})
        rdf = pd.DataFrame(rows)
        st.dataframe(rdf, use_container_width=True, hide_index=True)
        csv = rdf.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download report as CSV", data=csv,
                           file_name="certprep_score_report.csv", mime="text/csv")

    return passed, scaled
