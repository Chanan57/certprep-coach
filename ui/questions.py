"""Question rendering: practice widgets, reading view, and controls."""

import os

import streamlit as st

from ui.state import qid, reset_answer, goto_question, format_question_text


def show_images(images, caption="🖼️ Exhibit / image", expanded=True):
    imgs = [p for p in images if os.path.exists(p)]
    if not imgs:
        return
    with st.expander(f"{caption} ({len(imgs)})", expanded=expanded):
        for p in imgs:
            st.image(p, use_container_width=True)


def render_stem(question):
    st.markdown(format_question_text(question.get("question_text", "")))
    st.markdown("")


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


# ---------------------------------------------------------------------------
# Practice-mode renderers
# ---------------------------------------------------------------------------

def render_choice(question, idx, multi):
    options = question["options"]
    labels = [f"{k}. {v}" for k, v in options.items()]
    if multi:
        st.caption("This question has multiple correct answers. Select all that apply.")
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
        pick = st.radio("Select your answer:", labels, index=di, key=f"r_{idx}",
                        label_visibility="collapsed")
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
        st.caption("ℹ️ No answer key in this PDF — self-assess after reasoning.")
        render_self_assess(idx)


def render_dragdrop(question, idx, show_imgs=True):
    st.caption("**Drag and Drop / Build List** — assign a source item to each target.")
    if show_imgs:
        show_images(question["images"], "🖼️ Exhibit (items + answer key)")
    key = qid(question)
    stem = (question.get("question_text") or "").lower()
    seq = "sequence" in stem or "arrange" in stem or "in the correct order" in stem
    default_slots = "Step 1\nStep 2\nStep 3\nStep 4" if seq else "Target 1\nTarget 2"
    with st.expander("🧩 Set up the answer area (one entry per line)", expanded=True):
        cA, cB = st.columns(2)
        with cA:
            items_raw = st.text_area("Actions / source items",
                value=st.session_state.get(f"ddi_{key}", ""), key=f"ddi_{key}",
                height=150, placeholder="Delete\nFresh Start\nRetire\nSync\nWipe")
        with cB:
            slots_raw = st.text_area("Answer area targets",
                value=st.session_state.get(f"dds_{key}", default_slots),
                key=f"dds_{key}", height=150)
    items = [x.strip() for x in items_raw.splitlines() if x.strip()]
    slots = [x.strip() for x in slots_raw.splitlines() if x.strip()]
    if not items:
        st.warning("Enter the source items (from the exhibit) to build the drag-and-drop.")
    else:
        st.markdown("**Answer Area — assign an item to each target:**")
        pool = ["(choose)"] + items
        chosen = {}
        for n, slot in enumerate(slots):
            pick = st.selectbox(f"➡️ {slot}", pool, key=f"dd_{key}_{n}")
            if pick != "(choose)":
                chosen[slot] = pick
        if chosen:
            st.caption("Your answer: " + " · ".join(f"**{s}** = {v}" for s, v in chosen.items()))
    render_self_assess(idx)


def parse_hotspot_lines(raw):
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


def render_hotspot(question, idx, show_imgs=True):
    st.caption("**Hotspot / Active Screen** — make a selection for each dropdown.")
    if show_imgs:
        show_images(question["images"], "🖼️ Exhibit (dropdowns + answer key)")
    key = qid(question)
    stem = (question.get("question_text") or "").lower()
    yesno = "select yes" in stem or "otherwise, select no" in stem or "select no" in stem
    if yesno:
        default = "Statement 1 = Yes | No\nStatement 2 = Yes | No\nStatement 3 = Yes | No"
    else:
        default = ("Dropdown 1 = Option A | Option B | Option C\n"
                   "Dropdown 2 = Option A | Option B | Option C")
    with st.expander("🧩 Set up the dropdowns (`Label = opt1 | opt2 | opt3`)", expanded=True):
        config_raw = st.text_area("Dropdowns",
            value=st.session_state.get(f"hs_{key}", default), key=f"hs_{key}", height=130)
    groups = parse_hotspot_lines(config_raw)
    if not groups:
        st.warning("Enter at least one dropdown (from the exhibit).")
    else:
        st.markdown("**Answer Area:**")
        selections = {}
        for n, (label, options) in enumerate(groups):
            opts = ["(select)"] + (options if options else ["Yes", "No"])
            selections[label] = st.selectbox(f"🔽 {label}", opts, key=f"hsopt_{key}_{n}")
        picked = {l: v for l, v in selections.items() if v != "(select)"}
        if picked:
            st.caption("Your selections: " + " · ".join(f"**{l}** → {v}" for l, v in picked.items()))
    render_self_assess(idx)


def render_simulation(question, idx, show_imgs=True):
    st.caption("**Lab / Simulation** task — attempt it in a lab, then check the exhibit.")
    if show_imgs:
        show_images(question["images"], "🖼️ Task solution / exhibit")
    st.text_area("📝 Your working / notes (optional)", key=f"notes_{qid(question)}")
    render_self_assess(idx)


def render_question_body(question, idx, show_images_in_body=True):
    qtype = question["type"]
    if qtype == "SINGLE":
        if show_images_in_body:
            show_images(question["images"], "🖼️ Exhibit / image")
        render_choice(question, idx, multi=False)
    elif qtype == "MULTI":
        if show_images_in_body:
            show_images(question["images"], "🖼️ Exhibit / image")
        render_choice(question, idx, multi=True)
    elif qtype == "HOTSPOT":
        render_hotspot(question, idx, show_imgs=show_images_in_body)
    elif qtype == "DRAG DROP":
        render_dragdrop(question, idx, show_imgs=show_images_in_body)
    elif qtype == "SIMULATION":
        render_simulation(question, idx, show_imgs=show_images_in_body)


# ---------------------------------------------------------------------------
# Reading-mode renderer (correct answer + community discussion)
# ---------------------------------------------------------------------------

def render_reading_body(question, idx, show_images_in_body=True):
    """Study view: reveal answer, highlight correct options, show community."""
    if show_images_in_body:
        show_images(question["images"], "🖼️ Exhibit / image")

    options = question.get("options", {})
    correct = question.get("correct_answer", "")
    suggested = question.get("suggested_answer", "")

    if options:
        st.markdown("**Options:**")
        for k, v in options.items():
            mark = " ✅" if k in correct else ""
            style = "**" if k in correct else ""
            st.markdown(f"{style}{k}. {v}{style}{mark}")

    # Answer banner
    ans = correct or suggested
    if ans:
        src = "PDF key" if correct else "community vote"
        st.success(f"**Correct answer: {ans}**  ·  _({src})_")
    else:
        st.info("No explicit answer key in this PDF — see the community discussion below.")

    if question.get("type") in ("HOTSPOT", "DRAG DROP", "SIMULATION"):
        st.caption("🔎 This is a hotspot/drag-drop/lab question — the answer is in "
                   "the exhibit image above.")

    # Community discussion
    community = question.get("community", "")
    if community:
        with st.expander("💬 Community discussion & answers", expanded=True):
            st.markdown(community)
    else:
        st.caption("💬 No community discussion was captured for this question. "
                   "(Re-parse the exam with **🔄 Re-parse** on the home page to "
                   "capture discussions from the PDF.)")


# ---------------------------------------------------------------------------
# Per-question controls + footer nav
# ---------------------------------------------------------------------------

def render_question_controls(question, idx):
    st.markdown("")
    r1, r2, r3 = st.columns([1.4, 1.4, 6])
    with r1:
        st.markdown("<div class='reset-note'>", unsafe_allow_html=True)
        if st.button("↺ Reset Answer", key=f"reset_{idx}"):
            reset_answer(idx, question)
        st.markdown("</div>", unsafe_allow_html=True)
    with r2:
        review = idx in st.session_state.flagged_indexes
        if st.checkbox("Review later", value=review, key=f"revlater_{idx}"):
            st.session_state.flagged_indexes.add(idx)
        else:
            st.session_state.flagged_indexes.discard(idx)
    with r3:
        fb = idx in st.session_state.feedback_indexes
        if st.checkbox("Leave Feedback", value=fb, key=f"fb_{idx}"):
            st.session_state.feedback_indexes.add(idx)
        else:
            st.session_state.feedback_indexes.discard(idx)


def render_footer_nav(idx, total):
    st.markdown("---")
    left, mid, right = st.columns([1.3, 5.4, 1.3])
    with left:
        if st.button("‹  Previous", key=f"prev_{idx}", disabled=idx == 0,
                     type="primary", use_container_width=True):
            goto_question(idx - 1)
    with mid:
        with st.popover("⏹ End Exam", use_container_width=True):
            st.write("End the exam now and see your score report?")
            st.caption("Unanswered questions will be marked incorrect.")
            if st.button("Yes, end exam & score", type="primary", key=f"endexam_{idx}"):
                st.session_state.quiz_completed = True
                st.rerun()
    with right:
        if idx < total - 1:
            if st.button("Next  ›", key=f"next_{idx}", type="primary",
                         use_container_width=True):
                goto_question(idx + 1)
        else:
            if st.button("🏁 Finish", key=f"finish_{idx}", type="primary",
                         use_container_width=True):
                st.session_state.quiz_completed = True
                st.rerun()
