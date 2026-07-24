"""Shared state, constants, and helper functions for the CertPrep Coach UI."""

import re

import streamlit as st


TYPE_LABELS = {
    "SINGLE": "Single choice",
    "MULTI": "Multiple choice",
    "HOTSPOT": "Hotspot / dropdown",
    "DRAG DROP": "Drag and drop",
    "SIMULATION": "Simulation",
}

SCENARIO_SECTIONS = [
    "Windows Autopilot Configuration",
    "Microsoft Intune Configuration",
    "Intune Configuration",
    "Active Directory Environment",
    "System Center 2012 Infrastructure",
    "Existing Environment",
    "Network Environment",
    "Cloud Environment",
    "Technical Requirements",
    "Security Requirements",
    "General Requirements",
    "Business Requirements",
    "Compliance Requirements",
    "Business Goals",
    "App1 Requirements",
    "Users and Groups",
    "Planned Changes",
    "Planned changes",
    "Problem Statements",
    "Requirements",
    "Environment",
    "Overview",
    "Devices",
    "App1",
]

# Suffixes used to nest sections under a parent group in the case-study nav.
GROUP_SUFFIXES = ["Environment", "Requirements", "Configuration", "Infrastructure"]


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
        "feedback_indexes": set(),
        "quiz_started": False,
        "quiz_completed": False,
        "show_setup": False,
        "show_mode": False,
        "timed_mode": False,
        "time_limit_minutes": 30,
        "start_time": None,
        "image_dir": None,
        "source_label": "",
        "exam_name": "",
        "exam_mode": "full",
        "exam_sets": [],
        "app_mode": "practice",         # "practice" or "reading"
        "cs_view": "__question__",
        "nav_collapsed": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_quiz_progress():
    st.session_state.current_question_index = 0
    st.session_state.user_answers = {}
    st.session_state.self_assessed = {}
    st.session_state.flagged_indexes = set()
    st.session_state.feedback_indexes = set()
    st.session_state.quiz_started = False
    st.session_state.quiz_completed = False
    st.session_state.start_time = None
    st.session_state.cs_view = "__question__"
    st.session_state.pop("nav_jump_select", None)


def full_reset():
    reset_quiz_progress()
    st.session_state.all_questions = []
    st.session_state.questions = []
    st.session_state.show_setup = False
    st.session_state.show_mode = False
    st.session_state.source_label = ""
    st.session_state.exam_name = ""
    st.session_state.exam_sets = []


def go_home():
    full_reset()
    st.rerun()


def qid(question):
    return (f"{question.get('topic','G')}__{question.get('question_number','?')}"
            f"__{question.get('type','?')}")


def load_questions_into_state(questions, source_label, exam_name=""):
    st.session_state.all_questions = questions
    st.session_state.source_label = source_label
    st.session_state.exam_name = exam_name or source_label
    reset_quiz_progress()
    st.session_state.show_mode = True
    st.session_state.show_setup = False


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def goto_question(i):
    total = len(st.session_state.questions)
    i = max(0, min(i, total - 1)) if total else 0
    st.session_state.current_question_index = i
    st.session_state.cs_view = "__question__"
    st.rerun()


def is_answered(i):
    if st.session_state.user_answers.get(i):
        return True
    if i in st.session_state.self_assessed:
        return True
    return False


def question_status_icon(i):
    if i in st.session_state.flagged_indexes:
        return "🚩"
    if is_answered(i):
        return "✅"
    return "⚪"


def reset_answer(idx, question):
    st.session_state.user_answers.pop(idx, None)
    st.session_state.self_assessed.pop(idx, None)
    prefixes = (f"r_{idx}", f"c_{idx}_", f"dd_{qid(question)}_", f"hsopt_{qid(question)}_")
    for k in list(st.session_state.keys()):
        if any(k.startswith(p) for p in prefixes):
            del st.session_state[k]
    st.rerun()


# ---------------------------------------------------------------------------
# Section categorisation
# ---------------------------------------------------------------------------

def section_of(q):
    if q.get("type") == "SIMULATION":
        return "Lab"
    if q.get("is_case_study"):
        return "Case Study"
    return "Standalone"


def compute_sections():
    questions = st.session_state.questions
    cur = st.session_state.current_question_index
    stats = {"Standalone": {"total": 0, "done": 0, "pos": None},
             "Case Study": {"total": 0, "done": 0, "pos": None},
             "Lab": {"total": 0, "done": 0, "pos": None}}
    counter = {"Standalone": 0, "Case Study": 0, "Lab": 0}
    for i, q in enumerate(questions):
        sec = section_of(q)
        stats[sec]["total"] += 1
        counter[sec] += 1
        if is_answered(i):
            stats[sec]["done"] += 1
        if i == cur:
            stats[sec]["pos"] = counter[sec]
    return stats


# ---------------------------------------------------------------------------
# Text formatting
# ---------------------------------------------------------------------------

def format_question_text(text):
    if not text:
        return "_(See exhibit.)_"
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[\-\u2022:]\s*", "", text).strip()
    text = re.sub(r"\s*[\u2022]\s*", "\n\u2022 ", text)
    text = re.sub(r"\s+-\s+(?=[A-Z0-9])", "\n\u2022 ", text)

    lines = []
    for chunk in text.split("\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.startswith("\u2022 "):
            lines.append("- " + chunk[2:].strip())
        else:
            for s in re.split(r"(?<=[.?!])\s+", chunk):
                s = s.strip()
                if not s:
                    continue
                lines.append(f"**{s}**" if s.endswith("?") else s)

    out = []
    prev_bullet = False
    for ln in lines:
        is_bullet = ln.startswith("- ")
        if out and not (is_bullet and prev_bullet):
            out.append("")
        out.append(ln)
        prev_bullet = is_bullet
    return "\n".join(out)


def split_scenario_sections(text):
    if not text:
        return []
    alts = "|".join(re.escape(s) for s in sorted(SCENARIO_SECTIONS, key=len, reverse=True))
    pattern = re.compile(r"(?<![A-Za-z])(" + alts + r")\s*[-:]\s*")
    parts = []
    matches = list(pattern.finditer(text))
    if not matches:
        return [("Scenario", text.strip())]
    for i, m in enumerate(matches):
        if i == 0 and m.start() > 0:
            pre = text[:m.start()].strip()
            if pre:
                parts.append(("Background", pre))
        title = m.group(1)
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        parts.append((title, text[body_start:body_end].strip()))
    return parts


def group_sections(sections):
    """
    Turn a flat [(title, body)] list into a grouped nav structure.

    Returns (nav, content) where:
      nav = ordered list of items:
          {"type": "single", "key": str, "label": str}
        | {"type": "group",  "name": str, "children": [{"key","label"}]}
      content = {key: (display_title, body)}

    Grouping rules:
      - Titles ending in a GROUP_SUFFIX (e.g. "Existing Environment",
        "Technical Requirements") nest under that suffix as the parent group.
      - A bare parent title (e.g. "Environment") becomes a child labelled
        "General" within its group.
      - Duplicate labels within a group are merged (bodies concatenated) so we
        don't get two identical "Environment" entries.
    """
    def parent_of(title):
        for suf in GROUP_SUFFIXES:
            if title == suf:
                return suf          # bare parent
            if title.endswith(" " + suf) or title.endswith(suf):
                return suf
        return None

    nav = []
    content = {}
    group_lookup = {}     # suffix -> nav group dict
    key_counter = 0

    def new_key():
        nonlocal key_counter
        key_counter += 1
        return f"sec_{key_counter}"

    # First pass: collect merged bodies per (group, label).
    merged = {}   # (group, label) -> [bodies], preserve order
    order = []    # list of ("single", title) or ("group", suffix, label)

    for title, body in sections:
        suf = parent_of(title)
        if suf:
            label = "General" if title == suf else title
            slot = (suf, label)
            if slot not in merged:
                merged[slot] = []
                order.append(("group", suf, label))
            merged[slot].append(body)
        else:
            slot = ("__single__", title)
            if slot not in merged:
                merged[slot] = []
                order.append(("single", title, None))
            merged[slot].append(body)

    for entry in order:
        if entry[0] == "single":
            title = entry[1]
            body = "\n\n".join(merged[("__single__", title)]).strip()
            key = new_key()
            content[key] = (title, body)
            nav.append({"type": "single", "key": key, "label": title})
        else:
            _kind, suf, label = entry
            body = "\n\n".join(merged[(suf, label)]).strip()
            key = new_key()
            content[key] = (label if label != "General" else suf, body)
            if suf not in group_lookup:
                g = {"type": "group", "name": suf, "children": []}
                group_lookup[suf] = g
                nav.append(g)
            display = label if label != "General" else f"{suf} (general)"
            group_lookup[suf]["children"].append({"key": key, "label": display})

    # Flatten single-child groups back into a single item (cleaner nav).
    cleaned = []
    for item in nav:
        if item.get("type") == "group" and len(item["children"]) == 1:
            child = item["children"][0]
            cleaned.append({"type": "single", "key": child["key"],
                            "label": item["name"]})
            # relabel content to the group name for clarity
            title, body = content[child["key"]]
            content[child["key"]] = (item["name"], body)
        else:
            cleaned.append(item)
    return cleaned, content


def format_body(text):
    if not text:
        return text
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*\u2022\s*", "\n- ", text)
    text = re.sub(r"(?<=[.?!])\s+(?=[A-Z])", "\n\n", text)
    return text.strip()


def hhmmss(total_seconds):
    total_seconds = max(int(total_seconds), 0)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d} : {m:02d} : {s:02d}"


# ---------------------------------------------------------------------------
# Progress payload helpers
# ---------------------------------------------------------------------------

def build_progress_payload():
    import time
    elapsed = (time.time() - st.session_state.start_time) if st.session_state.start_time else 0
    return {
        "question_numbers": [q.get("question_number") for q in st.session_state.questions],
        "current_index": st.session_state.current_question_index,
        "user_answers": st.session_state.user_answers,
        "self_assessed": st.session_state.self_assessed,
        "flagged": st.session_state.flagged_indexes,
        "feedback": st.session_state.feedback_indexes,
        "elapsed_seconds": elapsed,
        "timed_mode": st.session_state.timed_mode,
        "time_limit_minutes": st.session_state.time_limit_minutes,
    }


def apply_progress_payload(data):
    import time
    st.session_state.user_answers = data.get("user_answers", {})
    st.session_state.self_assessed = data.get("self_assessed", {})
    st.session_state.flagged_indexes = data.get("flagged", set())
    st.session_state.feedback_indexes = data.get("feedback", set())
    st.session_state.current_question_index = data.get("current_index", 0)
    st.session_state.timed_mode = data.get("timed_mode", False)
    st.session_state.time_limit_minutes = data.get("time_limit_minutes", 30)
    elapsed = data.get("elapsed_seconds", 0)
    st.session_state.start_time = time.time() - elapsed
