import re
import hashlib


PAGE_MARKER_RE = re.compile(r"\[\[\[PAGE\s+(\d+)\]\]\]")
IMG_MARKER_RE = re.compile(r"\[\[\[IMG:([0-9a-fA-F]+)\]\]\]")
QUESTION_TYPES = ["DRAG DROP", "HOTSPOT", "SIMULATION"]
COMMENT_MARKERS = ["Highly Voted", "Most Recent", "Selected Answer:",
                   "Community vote distribution", "upvoted"]

QUESTION_LEADS = [
    r"For each of the following statements", r"To answer,", r"Use the drop-down menus",
    r"Which \w", r"What \w", r"How many ", r"To which ", r"You need to ",
    r"You implement ", r"You are evaluating", r"You are preparing", r"You install ",
    r"What is the maximum", r"What should you",
]
QUESTION_LEAD_RE = re.compile("|".join(QUESTION_LEADS), re.IGNORECASE)


def strip_examtopics_noise(text):
    """
    Remove ExamTopics page headers/footers WITHOUT crossing into question text.

    IMPORTANT: every rule here is LINE-SCOPED (anchored to a single line). We do
    NOT use a greedy 'datetime ... examtopics.com' span, because some exports
    (e.g. SC-100) put the datetime at the TOP of a page and the URL at the
    BOTTOM — a greedy match would swallow the whole page's questions in between.
    """
    # Datetime stamp line: "5/6/25, 8:31 AM"
    text = re.sub(r"(?m)^\s*\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}\s*[AP]M\s*$",
                  " ", text)
    # Title line: "... Free Actual Q&As, Page N | ExamTopics"
    text = re.sub(r"(?im)^.*Free Actual Q&As.*ExamTopics.*$", " ", text)
    # URL line (optionally followed by a page fraction like 9/230)
    text = re.sub(r"(?im)^\s*https?://\S*examtopics\.com\S*(?:\s+\d{1,4}/\d{1,4})?\s*$",
                  " ", text)
    # A bare page fraction on its own line: "9/230"
    text = re.sub(r"(?m)^\s*\d{1,4}/\d{2,4}\s*$", " ", text)
    # Any leftover inline URL fragment (rare).
    text = re.sub(r"https?://\S*examtopics\.com\S*", " ", text, flags=re.IGNORECASE)
    return text


def clean_text(text):
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_comments(text):
    cut = len(text)
    for marker in COMMENT_MARKERS:
        idx = text.find(marker)
        if idx != -1 and idx < cut:
            cut = idx
    m = re.search(r"\b\d+\s+(?:year|month|week|day|hour)s?,?\s+.*?ago\b", text)
    if m and m.start() < cut:
        cut = m.start()
    return text[:cut].strip(), text[cut:].strip()


def clean_community(text):
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    for mk in ["Highly Voted", "Most Recent", "Selected Answer:",
               "Community vote distribution"]:
        text = text.replace(mk, "\n\n**" + mk + "**")
    return text.strip()


def extract_suggested_answer(community):
    if not community:
        return ""
    picks = re.findall(r"Selected\s*Answer\s*:?\s*([A-F]{1,6})", community, re.IGNORECASE)
    if not picks:
        return ""
    picks = ["".join(sorted(p.upper())) for p in picks]
    return max(set(picks), key=picks.count)


def detect_type(block):
    head = block[:140].upper()
    for qtype in QUESTION_TYPES:
        if qtype in head:
            return qtype
    return "CHOICE"


def parse_options(region):
    matches = list(re.finditer(r"(?:^|\n)\s*-?\s*([A-F])\.\s+", region))
    options = {}
    for i, m in enumerate(matches):
        letter = m.group(1).upper()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(region)
        txt = re.sub(r"\s*\n\s*", " ", region[start:end]).strip()
        if txt:
            options[letter] = txt
    return options, matches


def split_scenario_and_question(stem):
    leads = list(QUESTION_LEAD_RE.finditer(stem))
    if not leads:
        return "", stem
    last = leads[-1]
    if last.start() < 40:
        return "", stem
    return stem[:last.start()].strip(), stem[last.start():].strip()


def extract_case_label(scenario):
    m = re.search(r"Overview\s*-?\s*([A-Za-z][A-Za-z0-9]+)", scenario)
    if m and m.group(1).lower() != "overview":
        return m.group(1)
    return "Case study"


def scenario_key(scenario):
    norm = re.sub(r"\s+", " ", scenario.lower()).strip()[:200]
    return hashlib.md5(norm.encode("utf-8")).hexdigest()[:12]


def _images_from_block(block, image_map):
    if not image_map:
        return []
    paths = []
    for h in IMG_MARKER_RE.findall(block):
        path = image_map.get(h.lower()) or image_map.get(h)
        if path and path not in paths:
            paths.append(path)
    return paths


def parse_questions(raw_text, image_map=None):
    if image_map is None:
        image_map = {}
    # Ignore a legacy {page:int -> [paths]} dict (old callers/tests).
    if image_map and all(isinstance(k, int) for k in image_map.keys()):
        image_map = {}

    raw_text = strip_examtopics_noise(raw_text)
    text = clean_text(raw_text)

    header_re = re.compile(r"(?:Topic\s+(\d+)\s+)?Question\s*#?\s*(\d+)", re.IGNORECASE)
    matches = list(header_re.finditer(text))
    parsed = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        topic_num = match.group(1)
        q_num = match.group(2)

        images = _images_from_block(block, image_map)

        block_clean = PAGE_MARKER_RE.sub(" ", block)
        block_clean = IMG_MARKER_RE.sub(" ", block_clean)
        block_clean = header_re.sub(" ", block_clean, count=1).strip()
        block_clean = re.sub(r"^\s*QUESTION\s*NO:?\s*\d+", " ", block_clean,
                             flags=re.IGNORECASE).strip()
        # Remove a leading "Question Set N" label if present (SC-100 style).
        block_clean = re.sub(r"^\s*Question\s*Set\s*\d+", " ", block_clean,
                             flags=re.IGNORECASE).strip()

        qtype = detect_type(block_clean)
        is_case_study = bool(re.search(r"Case\s*study", block_clean, re.IGNORECASE))

        correct = ""
        ans = re.search(r"Correct\s*Answer\s*:?\**\s*([A-F]{1,6})", block_clean, re.IGNORECASE)
        if ans:
            correct = ans.group(1).upper()

        after_parts = re.split(r"Correct\s*Answer\s*:", block_clean, flags=re.IGNORECASE)
        region = after_parts[0]
        after = after_parts[1] if len(after_parts) > 1 else ""

        community_raw = re.sub(r"^\s*\**\s*[A-F]{1,6}\s*", "", after).strip()
        suggested = extract_suggested_answer(community_raw)
        community = clean_community(community_raw)

        region, _ = split_comments(region)
        for kw in QUESTION_TYPES:
            region = re.sub(r"^\s*" + re.escape(kw), " ", region, flags=re.IGNORECASE).strip()
        region = re.sub(r"^\s*Case\s*study", " ", region, flags=re.IGNORECASE).strip()

        options, opt_matches = parse_options(region)
        stem = region[:opt_matches[0].start()].strip() if opt_matches else region.strip()
        stem = re.sub(r"\s*\n\s*", " ", stem).strip()
        stem = re.sub(r"\s*NOTE:\s*Each correct selection.*$", "", stem, flags=re.IGNORECASE).strip()

        scenario = ""
        case_label = None
        case_id = None
        if is_case_study:
            scenario, question_part = split_scenario_and_question(stem)
            if scenario:
                stem = question_part
                case_label = extract_case_label(scenario)
                if case_label and case_label != "Case study":
                    case_id = f"{topic_num or '0'}:{case_label.lower()}"
                else:
                    case_id = scenario_key(scenario)

        if qtype in QUESTION_TYPES:
            final_type = qtype
            gradable = False
            is_multi = False
        else:
            is_multi = len(correct) > 1
            final_type = "MULTI" if is_multi else "SINGLE"
            gradable = bool(options) and bool(correct)

        if not stem and not options and not images and not scenario:
            continue

        parsed.append({
            "question_number": int(q_num),
            "topic": f"Topic {topic_num}" if topic_num else "General",
            "type": final_type,
            "question_text": stem,
            "options": options,
            "correct_answer": correct,
            "is_multi": is_multi,
            "gradable": gradable,
            "answer_available": bool(correct),
            "images": images,
            "is_case_study": is_case_study,
            "case_label": case_label,
            "case_id": case_id,
            "case_scenario": scenario,
            "case_position": None,
            "case_size": None,
            "community": community,
            "suggested_answer": suggested,
        })

    _assign_case_groups(parsed)
    return parsed


def _assign_case_groups(parsed):
    groups = {}
    for i, q in enumerate(parsed):
        if q.get("case_id"):
            groups.setdefault(q["case_id"], []).append(i)
    for _cid, idxs in groups.items():
        for pos, i in enumerate(idxs):
            parsed[i]["case_position"] = pos + 1
            parsed[i]["case_size"] = len(idxs)
