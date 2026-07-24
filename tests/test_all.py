"""
CertPrep Coach — automated test suite.

Run from the project root:

    python tests/test_all.py          # plain run, clear PASS/FAIL summary
    python -m pytest tests/           # also works if you have pytest

It checks, without any manual clicking:
  1. Every module imports (no syntax / import errors)
  2. Text formatting produces clean, multi-line output (no run-on blobs)
  3. Case-study section grouping (dedupe + nest Environment/Requirements)
  4. Parser: options, answer key, community capture, noise stripping
  5. Exam builder: set size + guaranteed case-study/Yes-No per set
  6. Progress: save/load round-trips correctly
  7. Score report scaling (70% == 700 pass line)
  8. (Optional) Real PDFs under 'Sample Inputs/' parse sanely

Exit code is 0 if everything passes, 1 otherwise — so it can gate a commit
or run in CI.
"""

import os
import sys
import traceback

# Make the project root importable when run as `python tests/test_all.py`.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ---------------------------------------------------------------------------
# Tiny test framework (no dependencies)
# ---------------------------------------------------------------------------

_RESULTS = []


def check(name, condition, detail=""):
    _RESULTS.append((name, bool(condition), detail))
    icon = "✅" if condition else "❌"
    line = f"  {icon} {name}"
    if detail and not condition:
        line += f"  →  {detail}"
    print(line)
    return bool(condition)


def section(title):
    print(f"\n=== {title} ===")


def run(test_fn):
    """Run a test function, catching exceptions as failures."""
    try:
        test_fn()
    except Exception as e:  # noqa
        check(f"{test_fn.__name__} (crashed)", False,
              f"{e.__class__.__name__}: {e}")
        traceback.print_exc()


# ---------------------------------------------------------------------------
# 1. Imports / compile
# ---------------------------------------------------------------------------

def test_imports():
    section("1. Module imports")
    modules = [
        "src.pdf_reader", "src.question_parser", "src.quiz_engine",
        "src.library", "src.exam_builder", "src.progress",
        "ui.state", "ui.styles", "ui.header", "ui.navigator",
        "ui.questions", "ui.pages", "ui.report",
    ]
    for m in modules:
        try:
            __import__(m)
            check(f"import {m}", True)
        except Exception as e:  # noqa
            check(f"import {m}", False, f"{e.__class__.__name__}: {e}")


# ---------------------------------------------------------------------------
# 2. Formatting
# ---------------------------------------------------------------------------

def test_formatting():
    section("2. Text formatting")
    from ui.state import format_body, format_question_text

    # ExamTopics key/value blob with trailing ' -' separators (the bug case).
    blob = ("ADatum plans to implement the following changes: Name: Boundary1 - "
            "Network boundary: 192.168.1.0/24 Scope tags: Tag1 - Assignments: "
            "Included groups: Group1, Group2 - Name: Connection1 - Connection "
            "type: L2TP - Excluded groups: GroupB -")
    out = format_body(blob)
    lines = [l for l in out.split("\n") if l.strip()]
    check("format_body splits into multiple lines", len(lines) >= 6,
          f"only {len(lines)} lines")
    check("format_body has no giant run-on line",
          max((len(l) for l in lines), default=0) < 250)
    check("format_body surfaces key labels as bullets",
          any(l.lstrip().startswith("- ") and "Name:" in l for l in lines))

    # Question stem with leading dash + inline bullets + trailing question.
    stem = ("- You have a Microsoft 365 subscription. It contains: • Policy1 "
            "• Policy2 • Policy3 Which policy should you configure?")
    fq = format_question_text(stem)
    check("format_question_text strips leading dash", not fq.lstrip().startswith("-  You"))
    check("format_question_text bolds the question", "**Which policy should you configure?**" in fq)
    check("format_question_text bullets the inline list", fq.count("\n- ") >= 3)
    check("format_question_text leaves no raw bullet char", "\u2022" not in fq)


# ---------------------------------------------------------------------------
# 3. Grouped navigation
# ---------------------------------------------------------------------------

def test_grouping():
    section("3. Case-study nav grouping")
    from ui.state import group_sections

    sections = [
        ("Overview", "ov"),
        ("Existing Environment", "existing"),
        ("Environment", "env one"),
        ("Environment", "env two"),          # duplicate
        ("Requirements", "general reqs"),
        ("Technical Requirements", "tech"),
        ("Problem Statements", "problems"),
    ]
    nav, content = group_sections(sections)

    env = next((i for i in nav if i.get("name") == "Environment"), None)
    req = next((i for i in nav if i.get("name") == "Requirements"), None)
    check("Environment becomes a group", env is not None)
    check("Requirements becomes a group", req is not None)
    if env:
        # 'Existing Environment' + merged 'Environment' (general) == 2 children
        check("duplicate Environment merged (<=2 children)",
              len(env["children"]) <= 2, f"{len(env['children'])} children")
    if req:
        check("Requirements has Technical child",
              any("Technical" in c["label"] for c in req["children"]))
    check("every nav key resolves to content",
          all(_all_keys_resolve(nav, content)))


def _all_keys_resolve(nav, content):
    ok = []
    for item in nav:
        if item["type"] == "single":
            ok.append(item["key"] in content)
        else:
            for c in item["children"]:
                ok.append(c["key"] in content)
    return ok or [True]


# ---------------------------------------------------------------------------
# 4. Parser
# ---------------------------------------------------------------------------

def test_parser():
    section("4. Question parser")
    from src.question_parser import parse_questions

    raw = ("[[[PAGE 1]]] 1/23/26, 10:14 AM MD-102 Exam - Free Actual Q&As | ExamTopics "
           "https://www.examtopics.com/exams/microsoft/md-102/custom-view/ 8/230 "
           "Topic 1 Question #5 You have a Microsoft 365 subscription.\n"
           "Which policy should you use?\n"
           "A. Policy1\nB. Policy2\nC. Policy3\nD. Policy4\n"
           "Correct Answer: B "
           "Highly Voted user123 9 months ago Selected Answer: B Correct because reasons. "
           "upvoted 15 times Most Recent user456 Selected Answer: B I agree.")
    qs = parse_questions(raw, {})
    check("parsed exactly 1 question", len(qs) == 1, f"got {len(qs)}")
    if qs:
        q = qs[0]
        check("options A-D parsed", list(q["options"].keys()) == ["A", "B", "C", "D"],
              str(list(q["options"].keys())))
        check("correct answer = B", q["correct_answer"] == "B", q["correct_answer"])
        check("community discussion captured", bool(q["community"]))
        check("community voted answer = B", q["suggested_answer"] == "B", q["suggested_answer"])
        check("footer noise stripped from stem",
              "examtopics" not in q["question_text"].lower() and "/230" not in q["question_text"])
        check("comments not leaking into stem", "upvoted" not in q["question_text"])

    # Yes/No hotspot detection + case-study grouping (realistic-length scenario)
    scenario = ("Overview Contoso, Ltd. is a consulting company that has a main office "
                "in Montreal and two branch offices in Seattle and New York. "
                "Existing Environment - The network contains an Active Directory "
                "domain named contoso.com. ")
    raw2 = ("[[[PAGE 1]]] Topic 1 Question #1 HOTSPOT Case study " + scenario +
            "For each of the following statements, select Yes if true. "
            "Otherwise, select No. Correct Answer: "
            "[[[PAGE 2]]] Topic 1 Question #2 Case study " + scenario +
            "Which tool should you use to manage the devices in the domain?\n"
            "A. Tool1\nB. Tool2\nCorrect Answer: A")
    qs2 = parse_questions(raw2, {})
    check("case-study questions grouped by case_id",
          len({q["case_id"] for q in qs2 if q["case_id"]}) == 1, "expected 1 shared case_id")
    check("case_size reflects group",
          all(q.get("case_size") == 2 for q in qs2 if q["case_id"]))


# ---------------------------------------------------------------------------
# 5. Exam builder
# ---------------------------------------------------------------------------

def _make_bank(n_case_studies=4, qs_per_case=3, n_yesno=15, n_single=150):
    qs = []
    qn = 1
    for c in range(n_case_studies):
        for _ in range(qs_per_case):
            qs.append({"question_number": qn, "type": "SINGLE", "is_case_study": True,
                       "case_id": f"C{c}", "question_text": "x", "gradable": True,
                       "correct_answer": "A"})
            qn += 1
    for _ in range(n_yesno):
        qs.append({"question_number": qn, "type": "HOTSPOT", "is_case_study": False,
                   "case_id": None, "question_text": "For each statement select yes. "
                   "Otherwise, select No.", "gradable": False, "correct_answer": ""})
        qn += 1
    for _ in range(n_single):
        qs.append({"question_number": qn, "type": "SINGLE", "is_case_study": False,
                   "case_id": None, "question_text": "x", "gradable": True,
                   "correct_answer": "A"})
        qn += 1
    return qs


def test_exam_builder():
    section("5. Exam builder (sets)")
    from src import exam_builder as eb

    qs = _make_bank()
    sets = eb.build_sets(qs)
    check("produces at least one set", len(sets) >= 1)
    check("all questions preserved", sum(len(s) for s in sets) == len(qs),
          f"{sum(len(s) for s in sets)} vs {len(qs)}")

    # Case blocks stay intact within a single set.
    def case_intact():
        for cid in {q["case_id"] for q in qs if q["case_id"]}:
            in_sets = [i for i, s in enumerate(sets) if any(q["case_id"] == cid for q in s)]
            if len(in_sets) != 1:
                return False
        return True
    check("case-study blocks stay in ONE set", case_intact())
    check("every set has >=1 case study",
          all(eb.set_summary(s)["case_studies"] >= 1 for s in sets))
    check("every set has >=2 Yes/No",
          all(eb.set_summary(s)["yesno"] >= 2 for s in sets))

    full = eb.build_full(qs)
    check("full mode returns single set of all", len(full) == 1 and len(full[0]) == len(qs))


# ---------------------------------------------------------------------------
# 6. Progress save/load
# ---------------------------------------------------------------------------

def test_progress():
    section("6. Progress save/load")
    from src import progress as prog

    payload = {"question_numbers": [1, 2, 3], "current_index": 2,
               "user_answers": {0: "A", 1: "BC"}, "self_assessed": {2: "correct"},
               "flagged": {1}, "feedback": set(), "elapsed_seconds": 42,
               "timed_mode": True, "time_limit_minutes": 120}
    prog.save_progress("__TEST__", "full", payload)
    loaded = prog.load_progress("__TEST__", "full")
    check("progress file round-trips", loaded is not None)
    if loaded:
        check("int keys restored", loaded["user_answers"].get(0) == "A")
        check("multi-answer preserved", loaded["user_answers"].get(1) == "BC")
        check("flagged restored as set", loaded["flagged"] == {1})
        summ = prog.progress_summary("__TEST__", "full")
        check("summary answered count", summ and summ["answered"] == 3, str(summ))
    prog.delete_progress("__TEST__", "full")
    check("progress deletes cleanly", not prog.has_progress("__TEST__", "full"))


# ---------------------------------------------------------------------------
# 7. Score report scaling
# ---------------------------------------------------------------------------

def test_scoring():
    section("7. Score report scaling")
    from ui.report import _scaled_score, PASS_SCALED, PASS_PERCENT
    check("0% -> 100", _scaled_score(0) == 100, str(_scaled_score(0)))
    check("100% -> 1000", _scaled_score(100) == 1000, str(_scaled_score(100)))
    check(f"{PASS_PERCENT:.0f}% -> {PASS_SCALED} pass line",
          _scaled_score(PASS_PERCENT) == PASS_SCALED, str(_scaled_score(PASS_PERCENT)))
    check("monotonic increasing",
          _scaled_score(40) < _scaled_score(60) < _scaled_score(90))


# ---------------------------------------------------------------------------
# 8. Real PDFs (optional)
# ---------------------------------------------------------------------------

def test_real_pdfs():
    section("8. Real PDFs (optional — Sample Inputs/)")
    lib_dir = os.path.join(ROOT, "Sample Inputs")
    if not os.path.isdir(lib_dir):
        print("  ⏭️  No 'Sample Inputs/' folder — skipping real-PDF checks.")
        return
    from src import library as lib
    exams = lib.list_exams(lib_dir)
    if not exams:
        print("  ⏭️  No exams found — skipping.")
        return
    import tempfile
    for exam in exams:
        try:
            qs = lib.load_exam(exam, library_dir=lib_dir, force=False)
            check(f"'{exam}': parsed >0 questions", len(qs) > 0, f"{len(qs)}")
            leak = sum(1 for q in qs for v in q.get("options", {}).values()
                       if "examtopics" in v.lower() or "/230" in v)
            check(f"'{exam}': no footer noise in options", leak == 0, f"{leak} leaks")
            with_img = sum(1 for q in qs if q.get("images"))
            print(f"     ℹ️  {exam}: {len(qs)} questions, {with_img} with images")
        except Exception as e:  # noqa
            check(f"'{exam}': load", False, str(e))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print(" CertPrep Coach — automated checks")
    print("=" * 60)

    for t in [test_imports, test_formatting, test_grouping, test_parser,
              test_exam_builder, test_progress, test_scoring, test_real_pdfs]:
        run(t)

    passed = sum(1 for _, ok, _ in _RESULTS if ok)
    failed = [n for n, ok, _ in _RESULTS if not ok]
    print("\n" + "=" * 60)
    print(f" RESULT: {passed}/{len(_RESULTS)} checks passed")
    if failed:
        print(" FAILED:")
        for n in failed:
            print(f"   - {n}")
        print("=" * 60)
        sys.exit(1)
    print(" ALL CHECKS PASSED ✅")
    print("=" * 60)
    sys.exit(0)


# ---- pytest compatibility: expose each as a test_* function -----------------
def test_suite_imports(): test_imports()
def test_suite_formatting(): test_formatting()
def test_suite_grouping(): test_grouping()
def test_suite_parser(): test_parser()
def test_suite_exam_builder(): test_exam_builder()
def test_suite_progress(): test_progress()
def test_suite_scoring(): test_scoring()


if __name__ == "__main__":
    main()
