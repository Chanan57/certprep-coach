"""Exam-mode builder: full exam, ~60-question sets, and a quick 10-question test."""

import math
import random


SET_SIZE = 60
MIN_CASE_STUDIES = 1
MIN_YESNO = 2

QUICK_SIZE = 10   # default number of questions in a quick test


def is_yesno(q):
    if q.get("type") != "HOTSPOT":
        return False
    stem = (q.get("question_text") or "").lower()
    return ("select yes" in stem or "otherwise, select no" in stem
            or "select no" in stem)


def _case_blocks(questions):
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
    return [list(questions)]


def build_sets(questions, set_size=SET_SIZE,
               min_case=MIN_CASE_STUDIES, min_yesno=MIN_YESNO):
    if not questions:
        return []

    total = len(questions)
    num_sets = max(1, math.ceil(total / set_size))

    blocks = _case_blocks(questions)
    case_blocks = [b for b in blocks if b[0] == "case"]
    yesno_singles = [b for b in blocks if b[0] == "single" and is_yesno(b[2][0])]
    other_singles = [b for b in blocks if b[0] == "single" and not is_yesno(b[2][0])]

    if case_blocks and min_case > 0:
        max_sets_for_cases = max(1, len(case_blocks) // min_case)
        if max_sets_for_cases < num_sets and total / max_sets_for_cases <= set_size * 1.6:
            num_sets = max_sets_for_cases

    sets = [[] for _ in range(num_sets)]

    def sizes():
        return [len(s) for s in sets]

    def smallest():
        s = sizes()
        return s.index(min(s))

    ci = 0
    for _kind, _cid, qs in case_blocks:
        sets[ci % num_sets].extend(qs)
        ci += 1

    yn_queue = [b[2][0] for b in yesno_singles]
    yi = 0
    for s in sets:
        got = sum(1 for q in s if is_yesno(q))
        while got < min_yesno and yi < len(yn_queue):
            s.append(yn_queue[yi]); yi += 1; got += 1
    while yi < len(yn_queue):
        sets[smallest()].append(yn_queue[yi]); yi += 1

    for _kind, _cid, qs in other_singles:
        sets[smallest()].extend(qs)

    return [s for s in sets if s]


def build_quick_test(questions, size=QUICK_SIZE, seed=None):
    """
    Build a short quick-test set (default 10 questions) that samples across as
    many DIFFERENT question types as the bank offers.

    Strategy:
      1. Group questions by type (SINGLE, MULTI, HOTSPOT, DRAG DROP, SIMULATION).
      2. Round-robin one question from each available type until `size` is
         reached, so the mix is as varied as possible.
      3. If the bank has fewer than `size` questions, return them all.

    Case-study questions are treated as standalone here (a quick test is meant
    to be fast, not scenario-heavy), but they can still be picked to add variety.

    `seed` makes the selection reproducible for tests; leave None for random.
    """
    if not questions:
        return []

    rng = random.Random(seed)

    # Bucket by type, shuffled within each bucket.
    buckets = {}
    for q in questions:
        buckets.setdefault(q.get("type", "SINGLE"), []).append(q)
    for qs in buckets.values():
        rng.shuffle(qs)

    # Preferred type order for a nice spread; unknown types appended after.
    preferred = ["SINGLE", "MULTI", "HOTSPOT", "DRAG DROP", "SIMULATION"]
    type_order = [t for t in preferred if t in buckets]
    type_order += [t for t in buckets if t not in preferred]

    selected = []
    seen = set()

    # Round-robin across types.
    while len(selected) < size and any(buckets[t] for t in type_order):
        for t in type_order:
            if not buckets[t]:
                continue
            q = buckets[t].pop()
            key = id(q)
            if key in seen:
                continue
            selected.append(q)
            seen.add(key)
            if len(selected) >= size:
                break

    return selected[:size]


def set_summary(one_set):
    cases = {}
    yesno = 0
    for q in one_set:
        if q.get("case_id"):
            cases.setdefault(q["case_id"], 0)
            cases[q["case_id"]] += 1
        if is_yesno(q):
            yesno += 1
    return {"total": len(one_set), "case_study_questions": sum(cases.values()),
            "case_studies": len(cases), "yesno": yesno}


def type_breakdown(one_set):
    """Return {type: count} for a set — handy for showing the quick-test mix."""
    out = {}
    for q in one_set:
        out[q.get("type", "SINGLE")] = out.get(q.get("type", "SINGLE"), 0) + 1
    return out
