"""Question rendering: practice widgets, reading view, and controls."""

import os

import streamlit as st

from ui.state import qid, reset_answer, goto_question, format_question_text

# Real browser drag-and-drop (optional).
try:
    from streamlit_sortables import sort_items
    HAS_SORTABLES = True
except Exception:  # noqa
    HAS_SORTABLES = False

# AI vision layer (optional — only used if OPENAI_API_KEY is configured).
try:
    from src import ai_extractor as ai
    HAS_AI_MODULE = True
except Exception:  # noqa
    HAS_AI_MODULE = False


def _ai_cfg():
    if not HAS_AI_MODULE:
        return None
    cfg = ai.get_config()
    return cfg if ai.is_configured(cfg) else None


def show_images(images, caption="🖼️ Exhibit / image", expanded=True):
    imgs = [p for p in images if os.path.exists(p)]
    if not imgs:
        return False
    with st.expander(f"{caption} ({len(imgs)})", expanded=expanded):
        for p in imgs:
            st.image(p, use_container_width=True)
    return True


def _has_images(question):
    return any(os.path.exists(p) for p in question.get("images", []))


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
# AI extraction helper (cached in session so we don't re-call per rerun)
# ---------------------------------------------------------------------------

def _get_ai_extraction(question, idx):
    """Return the AI extraction dict for this question, or None. Cached in
    session state + on disk (via ai_extractor) so it's a one-time cost."""
    cfg = _ai_cfg()
    if not cfg:
        return None
    cache = st.session_state.setdefault("_ai_ext", {})
    k = qid(question)
    if k in cache:
        return cache[k]
    # Auto-extract button so the user controls when a call is made.
    if st.button("🤖 Auto-extract with AI", key=f"ai_{idx}"):
        with st.spinner("Reading the exhibit with AI..."):
            res = ai.extract_from_images(question, cfg)
        cache[k] = res
        st.rerun()
    return cache.get(k)


# ---------------------------------------------------------------------------
# Choice
# ---------------------------------------------------------------------------

def render_choice(question, idx, multi, ai_answer=None):
    options = question["options"]
    labels = [f"{k}. {v}" for k, v in options.items()]
    answer = question["correct_answer"] or (ai_answer or "")
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

    if answer:
        src = "PDF key" if question["correct_answer"] else "AI"
        if st.button("Check Answer", key=f"chk_{idx}"):
            sel = "".join(sorted((st.session_state.user_answers.get(idx) or "")))
            cor = "".join(sorted(answer))
            if not sel:
                st.warning("Please select an answer first.")
            elif sel == cor:
                st.success(f"✅ Correct. Answer: {cor}  ·  _(key from {src})_")
            else:
                st.error(f"❌ Incorrect. You chose {sel}. Correct: {cor}  ·  _(key from {src})_")
    else:
        st.caption("ℹ️ No answer key in this PDF — self-assess after reasoning.")
        render_self_assess(idx)


# ---------------------------------------------------------------------------
# Reveal helper (hotspot / simulation, and drag-drop check)
# ---------------------------------------------------------------------------

def _reveal_exhibit(question, idx, label):
    if not _has_images(question):
        st.warning("No exhibit image was captured for this question. "
                   "Try **🔄 Re-parse** on the home page.")
        return
    reveal_key = f"reveal_{idx}"
    if not st.session_state.get(reveal_key, False):
        st.caption("🔒 The exhibit contains the answer. Attempt first, then reveal to check.")
        if st.button("👁️ Reveal exhibit & answer", key=f"revbtn_{idx}"):
            st.session_state[reveal_key] = True
            st.rerun()
    else:
        show_images(question["images"], label, expanded=True)
        if st.button("🙈 Hide exhibit", key=f"hidebtn_{idx}"):
            st.session_state[reveal_key] = False
            st.rerun()


# ---------------------------------------------------------------------------
# Drag and drop
# ---------------------------------------------------------------------------

def render_dragdrop(question, idx, show_imgs=True):
    st.caption("**Drag and Drop / Build List** — drag the actions into the "
               "**Answer Area** in the correct order.")

    key = qid(question)
    extraction = _get_ai_extraction(question, idx)

    # 1) Prefer AI-extracted items (no typing). 2) Else user-typed seed. 3) manual.
    ai_items = extraction.get("items") if extraction else []
    ai_map = extraction.get("answer_map") if extraction else {}

    if not HAS_SORTABLES:
        st.info("💡 Install **streamlit-sortables** for true drag-and-drop.")
        _dragdrop_manual(question, idx, key)
        _reveal_exhibit(question, idx, "🗝️ Exhibit — actions & correct order")
        render_self_assess(idx)
        return

    if ai_items:
        st.caption("🤖 Actions auto-extracted from the exhibit by AI.")
        actions = ai_items
    else:
        seed_key = f"ddseed_{key}"
        seed = st.text_area(
            "✏️ Actions from the exhibit (one per line) — or click "
            "**🤖 Auto-extract with AI** above to fill these automatically:",
            value=st.session_state.get(seed_key, ""), key=f"ddseedbox_{key}", height=110,
            placeholder="Create a sensitivity label.\nCreate a sensitive info type.\n"
                        "Create an auto-labeling policy.")
        st.session_state[seed_key] = seed
        actions = [x.strip() for x in seed.splitlines() if x.strip()]

    if not actions:
        st.info("⬆️ Provide the actions (type them, or use AI) to activate the board.")
    else:
        containers = [
            {"header": "📋 Actions (available)", "items": list(actions)},
            {"header": "✅ Answer Area (your order)", "items": []},
        ]
        try:
            arranged = sort_items(containers, multi_containers=True, key=f"ddsort_{key}")
        except TypeError:
            arranged = sort_items(containers, multi_containers=True)

        answer = []
        for c in arranged:
            if c["header"].startswith("✅"):
                answer = c["items"]
        if answer:
            st.markdown("**Your sequence:**")
            for i, a in enumerate(answer, 1):
                st.markdown(f"{i}. {a}")
            st.session_state.user_answers[idx] = " | ".join(answer)

            # Auto-grade if AI gave us the correct mapping.
            if ai_map:
                if st.button("Check order", key=f"ddcheck_{idx}"):
                    correct_order = [ai_map[k] for k in sorted(ai_map.keys())]
                    if answer == correct_order:
                        st.success("✅ Correct order!")
                        st.session_state.self_assessed[idx] = "correct"
                    else:
                        st.error("❌ Not quite. Correct order: "
                                 + " → ".join(correct_order))
                        st.session_state.self_assessed[idx] = "incorrect"

    if not ai_map:
        _reveal_exhibit(question, idx, "🗝️ Exhibit — actions & correct order")
        render_self_assess(idx)


def _dragdrop_manual(question, idx, key):
    with st.expander("🧩 Build your answer", expanded=True):
        cA, cB = st.columns(2)
        with cA:
            items_raw = st.text_area("Actions / source items",
                value=st.session_state.get(f"ddi_{key}", ""), key=f"ddi_{key}",
                height=150, placeholder="Type one action per line")
        with cB:
            slots_raw = st.text_area("Answer area (in order)",
                value=st.session_state.get(f"dds_{key}", "Step 1\nStep 2\nStep 3"),
                key=f"dds_{key}", height=150)
        items = [x.strip() for x in items_raw.splitlines() if x.strip()]
        slots = [x.strip() for x in slots_raw.splitlines() if x.strip()]
        if items and slots:
            pool = ["(choose)"] + items
            chosen = {}
            for n, slot in enumerate(slots):
                pick = st.selectbox(f"➡️ {slot}", pool, key=f"dd_{key}_{n}")
                if pick != "(choose)":
                    chosen[slot] = pick
            if chosen:
                st.caption("Your order: " + " → ".join(chosen.values()))


# ---------------------------------------------------------------------------
# Hotspot
# ---------------------------------------------------------------------------

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
    key = qid(question)
    extraction = _get_ai_extraction(question, idx)
    ai_dropdowns = extraction.get("dropdowns") if extraction else []

    if ai_dropdowns:
        st.caption("🤖 Dropdowns auto-extracted from the exhibit by AI.")
        groups = [(d.get("label", f"Dropdown {i+1}"), d.get("options", []))
                  for i, d in enumerate(ai_dropdowns)]
        correct = {d.get("label"): d.get("correct", "") for d in ai_dropdowns}
        st.markdown("**Answer Area:**")
        selections = {}
        for n, (label, options) in enumerate(groups):
            opts = ["(select)"] + (options if options else ["Yes", "No"])
            selections[label] = st.selectbox(f"🔽 {label}", opts, key=f"hsopt_{key}_{n}")
        if any(correct.values()) and st.button("Check selections", key=f"hscheck_{idx}"):
            wrong = [l for l, _ in groups if selections.get(l) != correct.get(l)]
            picked = {l: v for l, v in selections.items() if v != "(select)"}
            if not picked:
                st.warning("Make your selections first.")
            elif not wrong:
                st.success("✅ Correct! " + " · ".join(f"**{l}** → {correct[l]}" for l, _ in groups))
                st.session_state.self_assessed[idx] = "correct"
            else:
                st.error("❌ Not quite. Correct: "
                         + " · ".join(f"**{l}** → {correct.get(l,'?')}" for l, _ in groups))
                st.session_state.self_assessed[idx] = "incorrect"
        return

    # Manual fallback + reveal.
    with st.expander("🧩 Optional: build your answer", expanded=False):
        st.caption("Type each dropdown as `Label = opt1 | opt2 | opt3`, or click "
                   "**🤖 Auto-extract with AI** above.")
        stem = (question.get("question_text") or "").lower()
        yesno = "select yes" in stem or "otherwise, select no" in stem or "select no" in stem
        default = ("Statement 1 = Yes | No\nStatement 2 = Yes | No\nStatement 3 = Yes | No"
                   if yesno else "Dropdown 1 = Option A | Option B | Option C")
        config_raw = st.text_area("Dropdowns",
            value=st.session_state.get(f"hs_{key}", default), key=f"hs_{key}", height=120)
        groups = parse_hotspot_lines(config_raw)
        if groups:
            selections = {}
            for n, (label, options) in enumerate(groups):
                opts = ["(select)"] + (options if options else ["Yes", "No"])
                selections[label] = st.selectbox(f"🔽 {label}", opts, key=f"hsopt_{key}_{n}")
            picked = {l: v for l, v in selections.items() if v != "(select)"}
            if picked:
                st.caption("Your selections: "
                           + " · ".join(f"**{l}** → {v}" for l, v in picked.items()))

    _reveal_exhibit(question, idx, "🗝️ Exhibit — dropdowns & correct selections")
    render_self_assess(idx)


def render_simulation(question, idx, show_imgs=True):
    st.caption("**Lab / Simulation** task — attempt it in a lab, then reveal the "
               "solution to check.")
    st.text_area("📝 Your working / notes (optional)", key=f"notes_{qid(question)}")
    _reveal_exhibit(question, idx, "🗝️ Task solution / exhibit")
    render_self_assess(idx)


def render_question_body(question, idx, show_images_in_body=True):
    qtype = question["type"]
    if qtype in ("SINGLE", "MULTI"):
        if show_images_in_body:
            show_images(question["images"], "🖼️ Exhibit / image")
        # If no PDF key, offer AI to recover the answer.
        ai_answer = None
        if not question.get("correct_answer"):
            ext = _get_ai_extraction(question, idx)
            ai_answer = (ext or {}).get("correct_answer")
        render_choice(question, idx, multi=(qtype == "MULTI"), ai_answer=ai_answer)
    elif qtype == "HOTSPOT":
        render_hotspot(question, idx)
    elif qtype == "DRAG DROP":
        render_dragdrop(question, idx)
    elif qtype == "SIMULATION":
        render_simulation(question, idx)


# ---------------------------------------------------------------------------
# Reading mode
# ---------------------------------------------------------------------------

def render_reading_body(question, idx, show_images_in_body=True):
    qtype = question.get("type")
    is_visual = qtype in ("HOTSPOT", "DRAG DROP", "SIMULATION")

    if is_visual or show_images_in_body:
        cap = "🗝️ Exhibit & answer key" if is_visual else "🖼️ Exhibit / image"
        shown = show_images(question.get("images", []), cap, expanded=True)
    else:
        shown = False

    options = question.get("options", {})
    correct = question.get("correct_answer", "")
    suggested = question.get("suggested_answer", "")

    if options:
        st.markdown("**Options:**")
        for k, v in options.items():
            if k in correct:
                st.markdown(f"- **{k}. {v}  ✅**")
            else:
                st.markdown(f"- {k}. {v}")

    ans = correct or suggested
    if ans:
        src = "PDF key" if correct else "community vote"
        st.success(f"**Correct answer: {ans}**  ·  _({src})_")
    elif is_visual:
        if shown:
            st.info("🗝️ This is a hotspot/drag-drop/lab question — the correct "
                    "answer is shown in the **exhibit & answer key** image above.")
        else:
            st.warning("🗝️ Answer is in the exhibit image, but no image was captured. "
                       "Try **🔄 Re-parse** on the home page.")
    else:
        st.info("No explicit answer key in this PDF — see the community discussion below.")

    community = question.get("community", "")
    if community:
        with st.expander("💬 Community discussion & answers", expanded=True):
            st.markdown(community)
    else:
        st.caption("💬 No community discussion was captured for this question.")


# ---------------------------------------------------------------------------
# Controls + footer nav
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
