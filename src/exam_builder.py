"""
Exam-mode builder for CertPrep Coach.

Two modes:
  * "full"  -> every question in one sitting (kept in original order).
  * "sets"  -> split the bank into ~SET_SIZE (default 60) question sets, each
               guaranteed to contain at least MIN_CASE_STUDIES case-study
               question(s) and MIN_YESNO yes/no question(s) where the bank
               allows.

Case-study questions that share a scenario (same case_id) are kept together in
the same set and in order, mirroring the real exam.
"""

import math


SET_SIZE = 60
MIN_CASE_STUDIES = 1     # per set (case-study *questions*)
MIN_YESNO = 2            # per set


def is_yesno(q):
    """A hotspot question whose stem uses the Yes/No answer format."""
    if q.get("type") != "HOTSPOT":
        return False
    stem = (q.get("question_text") or "").lower()
    return ("select yes" in stem or "otherwise, select no" in stem
            or "select no" in stem)


def _case_blocks(questions):
    """
    Group questions into ordered blocks. Case-study questions sharing a
    case_id form one block (kept together); every other question is its own
    single-item block.
    """
    blocks = []
    case_map = {}
    for q in questions:
        cid = q.get("case_id")
        if cid:
            if cid not in case_map:
                case_map[cid] = []
                blocks.append(("case", cid, case_map[cid]))
            case_map[cid].append(q)
        else:
            blocks.append(("single", None, [q]))
    return blocks


def build_full(questions):
    """Return a single set containing all questions (original order)."""
    return [list(questions)]


def build_sets(questions, set_size=SET_SIZE,
               min_case=MIN_CASE_STUDIES, min_yesno=MIN_YESNO):
    """
    Partition questions into sets of ~set_size, each containing at least
    `min_case` case-study questions and `min_yesno` yes/no questions where
    the overall bank permits. Returns a list of lists.
    """
    if not questions:
        return []

    total = len(questions)
    num_sets = max(1, math.ceil(total / set_size))

    # Categorise blocks.
    blocks = _case_blocks(questions)
    case_blocks = [b for b in blocks if b[0] == "case"]
    yesno_singles = [b for b in blocks if b[0] == "single" and is_yesno(b[2][0])]
    other_singles = [b for b in blocks if b[0] == "single" and not is_yesno(b[2][0])]

    # Guarantee each set can hold >= min_case case studies: if there aren't
    # enough case-study blocks for that many sets, reduce the set count so long
    # as the resulting sets don't get unreasonably large (<= 1.6x set_size).
    if case_blocks and min_case > 0:
        max_sets_for_cases = max(1, len(case_blocks) // min_case)
        if max_sets_for_cases < num_sets and total / max_sets_for_cases <= set_size * 1.6:
            num_sets = max_sets_for_cases

    # Initialise empty sets.
    sets = [[] for _ in range(num_sets)]

    def sizes():
        return [len(s) for s in sets]

    def smallest_set_index():
        s = sizes()
        return s.index(min(s))

    # 1) Distribute case-study blocks round-robin (whole block per set).
    ci = 0
    for _kind, _cid, qs in case_blocks:
        target = ci % num_sets
        sets[target].extend(qs)
        ci += 1

    # 2) Distribute yes/no questions so each set gets at least min_yesno.
    yn_queue = [b[2][0] for b in yesno_singles]
    yi = 0
    # First pass: guarantee minimum where possible.
    for s in sets:
        got = sum(1 for q in s if is_yesno(q))
        while got < min_yesno and yi < len(yn_queue):
            s.append(yn_queue[yi]); yi += 1; got += 1
    # Remaining yes/no go to smallest sets.
    while yi < len(yn_queue):
        sets[smallest_set_index()].append(yn_queue[yi]); yi += 1

    # 3) Distribute the rest, always filling the smallest set (balances sizes).
    for _kind, _cid, qs in other_singles:
        sets[smallest_set_index()].extend(qs)

    # Drop any empty trailing sets (can happen with tiny banks).
    sets = [s for s in sets if s]
    return sets


def set_summary(one_set):
    """Return counts describing a single set for display."""
    cases = {}
    yesno = 0
    for q in one_set:
        if q.get("case_id"):
            cases.setdefault(q["case_id"], 0)
            cases[q["case_id"]] += 1
        if is_yesno(q):
            yesno += 1
    return {
        "total": len(one_set),
        "case_study_questions": sum(cases.values()),
        "case_studies": len(cases),
        "yesno": yesno,
    }
