import random
import time


def _norm(ans):
    if not ans:
        return ""
    return "".join(sorted(ans.upper()))


def calculate_score(user_answers, questions):
    """Only auto-gradable questions count toward the score."""
    correct = 0
    gradable = 0
    non_gradable = 0
    for i, q in enumerate(questions):
        if not q.get("gradable"):
            non_gradable += 1
            continue
        gradable += 1
        if _norm(user_answers.get(i)) and _norm(user_answers.get(i)) == _norm(q.get("correct_answer")):
            correct += 1
    pct = round((correct / gradable) * 100, 2) if gradable else 0
    return {
        "total_questions": len(questions),
        "gradable_total": gradable,
        "non_gradable_total": non_gradable,
        "correct_count": correct,
        "incorrect_count": gradable - correct,
        "score_percentage": pct,
    }


def shuffle_questions(questions):
    out = questions.copy()
    random.shuffle(out)
    return out


def shuffle_options(question):
    if question.get("type") not in ("SINGLE", "MULTI"):
        return question.copy()
    options = question.get("options", {})
    correct = question.get("correct_answer", "")
    if not options or not correct:
        return question.copy()
    correct_texts = {options.get(l) for l in correct}
    items = list(options.items())
    random.shuffle(items)
    letters = ["A", "B", "C", "D", "E", "F", "G"]
    new_opts, new_correct = {}, []
    for idx, (_old, txt) in enumerate(items):
        nl = letters[idx]
        new_opts[nl] = txt
        if txt in correct_texts:
            new_correct.append(nl)
    q = question.copy()
    q["options"] = new_opts
    q["correct_answer"] = "".join(sorted(new_correct))
    return q


def filter_by_topics(questions, selected):
    if not selected:
        return questions.copy()
    return [q for q in questions if q.get("topic", "General") in selected]


def filter_by_types(questions, selected):
    if not selected:
        return questions.copy()
    return [q for q in questions if q.get("type") in selected]


def build_review_set(user_answers, questions, flagged, include_incorrect, include_flagged):
    out, seen = [], set()
    for i, q in enumerate(questions):
        inc = False
        if include_incorrect and q.get("gradable"):
            if _norm(user_answers.get(i)) != _norm(q.get("correct_answer")):
                inc = True
        if include_flagged and i in flagged:
            inc = True
        if inc and i not in seen:
            out.append(q)
            seen.add(i)
    return out


def format_seconds(total):
    if total < 0:
        total = 0
    return f"{int(total)//60:02d}:{int(total)%60:02d}"


def get_time_remaining(start_time, limit_seconds):
    return max(limit_seconds - (time.time() - start_time), 0)
