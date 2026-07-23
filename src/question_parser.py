import re
import hashlib


PAGE_MARKER_RE = re.compile(r"\[\[\[PAGE\s+(\d+)\]\]\]")

QUESTION_TYPES = ["DRAG DROP", "HOTSPOT", "SIMULATION"]

# Markers that indicate the community-discussion / noise section starts.
COMMENT_MARKERS = [
    "Highly Voted", "Most Recent", "Selected Answer:",
    "Community vote distribution", "upvoted",
]

# Phrases that typically begin the actual question inside a long case study.
QUESTION_LEADS = [
    r"For each of the following statements",
    r"To answer,",
    r"Use the drop-down menus",
    r"Which \w",
    r"What \w",
    r"How many ",
    r"To which ",
    r"You need to ",
    r"You implement ",
    r"You are evaluating",
    r"You are preparing",
    r"You install ",
    r"What is the maximum",
    r"What should you",
]
QUESTION_LEAD_RE = re.compile("|".join(QUESTION_LEADS), re.IGNORECASE)


# ---------------------------------------------------------------------------
# Noise removal
# ---------------------------------------------------------------------------

def strip_examtopics_noise(text):
    """Remove ExamTopics page footers, URLs, and page-number fragments."""
    # Full footer: datetime -> "... | ExamTopics" -> URL -> optional "N/NNN".
    text = re.sub(
        r"\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}\s*[AP]M.*?examtopics\.com/\S*"
        r"(?:\s*\n?\s*\d{1,4}/\d{1,4})?",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Leftover footer title lines.
    text = re.sub(r"(?im)^.*Free Actual Q&As.*ExamTopics.*$", " ", text)
    # Leftover bare URLs.
    text = re.sub(r"https?://\S*examtopics\.com\S*", " ", text, flags=re.IGNORECASE)
    # Leftover standalone page fractions like "9/230" on their own line.
    text = re.sub(r"(?m)^\s*\d{1,4}/\d{2,4}\s*$", " ", text)
    # Leftover standalone datetime stamps.
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}\s*[AP]M", " ", text)
    return text


def clean_text(text):
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def cut_comments(text):
    """Return only the portion before the community discussion begins."""
    cut = len(text)
    for marker in COMMENT_MARKERS:
        idx = text.find(marker)
        if idx != -1 and idx < cut:
            cut = idx
    m = re.search(r"\b\d+\s+(?:year|month|week|day|hour)s?,?\s+.*?ago\b", text)
    if m and m.start() < cut:
        cut = m.start()
    return text[:cut].strip()


# ---------------------------------------------------------------------------
# Type + option parsing
# ---------------------------------------------------------------------------

def detect_type(block):
    head = block[:140].upper()
    for qtype in QUESTION_TYPES:
        if qtype in head:
            return qtype
    return "CHOICE"


def parse_options(region):
    """Extract answer options A-F. Returns (options_dict, match_list)."""
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


# ---------------------------------------------------------------------------
# Case study handling
# ---------------------------------------------------------------------------

def split_scenario_and_question(stem):
    """
    For a case-study stem (long scenario + trailing question), split into
    (scenario, question) using the LAST question-lead phrase found.
    """
    leads = list(QUESTION_LEAD_RE.finditer(stem))
    if not leads:
        return "", stem
    # Use the last lead that is not extremely early in the text.
    last = leads[-1]
    pos = last.start()
    if pos < 40:  # whole thing is basically the question
        return "", stem
    scenario = stem[:pos].strip()
    question = stem[pos:].strip()
    return scenario, question


def extract_case_label(scenario):
    # Handles "Overview ADatum...", "- Overview - ADatum...", "Overview Contoso, Ltd."
    m = re.search(r"Overview\s*-?\s*([A-Za-z][A-Za-z0-9]+)", scenario)
    if m and m.group(1).lower() != "overview":
        return m.group(1)
    return "Case study"


def scenario_key(scenario):
    norm = re.sub(r"\s+", " ", scenario.lower()).strip()[:200]
    return hashlib.md5(norm.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_questions(raw_text, page_images=None):
    if page_images is None:
        page_images = {}

    # Strip noise first (keeps page markers and newlines intact).
    raw_text = strip_examtopics_noise(raw_text)
    text = clean_text(raw_text)

    header_re = re.compile(
        r"(?:Topic\s+(\d+)\s+)?Question\s*#?\s*(\d+)", re.IGNORECASE
    )
    matches = list(header_re.finditer(text))
    parsed = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        topic_num = match.group(1)
        q_num = match.group(2)

        pages = [int(p) for p in PAGE_MARKER_RE.findall(block)]

        block_clean = PAGE_MARKER_RE.sub(" ", block)
        block_clean = header_re.sub(" ", block_clean, count=1).strip()
        # Remove a leading "QUESTION NO: 77" restatement.
        block_clean = re.sub(r"^\s*QUESTION\s*NO:?\s*\d+", " ", block_clean,
                             flags=re.IGNORECASE).strip()

        qtype = detect_type(block_clean)
        is_case_study = bool(re.search(r"Case\s*study", block_clean, re.IGNORECASE))

        # Correct answer letters (may be absent in some dumps).
        correct = ""
        ans = re.search(r"Correct\s*Answer\s*:?\**\s*([A-F]{1,6})", block_clean,
                        re.IGNORECASE)
        if ans:
            correct = ans.group(1).upper()

        region = re.split(r"Correct\s*Answer\s*:", block_clean, flags=re.IGNORECASE)[0]
        region = cut_comments(region)

        # Strip leading type keyword and "Case study" tag.
        for kw in QUESTION_TYPES:
            region = re.sub(r"^\s*" + re.escape(kw), " ", region, flags=re.IGNORECASE).strip()
        region = re.sub(r"^\s*Case\s*study", " ", region, flags=re.IGNORECASE).strip()

        options, opt_matches = parse_options(region)

        stem = region[:opt_matches[0].start()].strip() if opt_matches else region.strip()
        stem = re.sub(r"\s*\n\s*", " ", stem).strip()
        # Drop trailing "NOTE: Each correct selection..." from stem tail noise.
        stem = re.sub(r"\s*NOTE:\s*Each correct selection.*$", "", stem,
                      flags=re.IGNORECASE).strip()

        # Case study: separate shared scenario from the actual question.
        scenario = ""
        case_label = None
        case_id = None
        if is_case_study:
            scenario, question_part = split_scenario_and_question(stem)
            if scenario:
                stem = question_part
                case_label = extract_case_label(scenario)
                # Group by company name (falls back to scenario hash) so all
                # questions in the same case study are grouped together.
                if case_label and case_label != "Case study":
                    case_id = f"{topic_num or '0'}:{case_label.lower()}"
                else:
                    case_id = scenario_key(scenario)

        # Resolve type + gradability.
        if qtype in QUESTION_TYPES:
            final_type = qtype
            gradable = False
            is_multi = False
        else:
            is_multi = len(correct) > 1
            final_type = "MULTI" if is_multi else "SINGLE"
            gradable = bool(options) and bool(correct)

        answer_available = bool(correct)

        images = []
        for p in pages:
            for path in page_images.get(p, []):
                if path not in images:
                    images.append(path)

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
            "answer_available": answer_available,
            "images": images,
            "is_case_study": is_case_study,
            "case_label": case_label,
            "case_id": case_id,
            "case_scenario": scenario,
            "case_position": None,
            "case_size": None,
        })

    _assign_case_groups(parsed)
    return parsed


def _assign_case_groups(parsed):
    """Fill case_position / case_size for questions sharing a case_id."""
    groups = {}
    for i, q in enumerate(parsed):
        if q.get("case_id"):
            groups.setdefault(q["case_id"], []).append(i)
    for _cid, idxs in groups.items():
        for pos, i in enumerate(idxs):
            parsed[i]["case_position"] = pos + 1
            parsed[i]["case_size"] = len(idxs)
