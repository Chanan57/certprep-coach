"""
Progress persistence for CertPrep Coach.

Saves/loads a practice session (answers, self-assessments, flags, position,
elapsed time) to a JSON file so users can close the app and resume later.

Files live in .progress/<slug>.json where slug is derived from the exam name
and mode (e.g. "MD 102__full", "SC 401__set2").
"""

import os
import re
import json
import time
from datetime import datetime


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRESS_DIR = os.path.join(PROJECT_ROOT, ".progress")


def _slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", (text or "session")).strip("_")


def progress_path(exam, mode):
    os.makedirs(PROGRESS_DIR, exist_ok=True)
    return os.path.join(PROGRESS_DIR, f"{_slug(exam)}__{_slug(mode)}.json")


def has_progress(exam, mode):
    return os.path.exists(progress_path(exam, mode))


def save_progress(exam, mode, payload):
    """
    payload: dict with keys
      question_numbers (list[int]) -> identifies the exact question set
      current_index, user_answers, self_assessed, flagged, feedback,
      elapsed_seconds, timed_mode, time_limit_minutes
    """
    path = progress_path(exam, mode)
    data = dict(payload)
    data["exam"] = exam
    data["mode"] = mode
    data["saved_at"] = datetime.now().isoformat(timespec="seconds")
    # JSON keys must be strings; convert int-keyed dicts and sets.
    data["user_answers"] = {str(k): v for k, v in payload.get("user_answers", {}).items()}
    data["self_assessed"] = {str(k): v for k, v in payload.get("self_assessed", {}).items()}
    data["flagged"] = sorted(list(payload.get("flagged", [])))
    data["feedback"] = sorted(list(payload.get("feedback", [])))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def load_progress(exam, mode):
    path = progress_path(exam, mode)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Restore int keys / sets.
    data["user_answers"] = {int(k): v for k, v in data.get("user_answers", {}).items()}
    data["self_assessed"] = {int(k): v for k, v in data.get("self_assessed", {}).items()}
    data["flagged"] = set(data.get("flagged", []))
    data["feedback"] = set(data.get("feedback", []))
    return data


def delete_progress(exam, mode):
    path = progress_path(exam, mode)
    if os.path.exists(path):
        os.remove(path)


def progress_summary(exam, mode):
    """Short human summary for the 'resume' prompt, or None."""
    data = load_progress(exam, mode)
    if not data:
        return None
    answered = len(data.get("user_answers", {})) + len(data.get("self_assessed", {}))
    total = len(data.get("question_numbers", []))
    return {
        "answered": answered,
        "total": total,
        "saved_at": data.get("saved_at", "unknown"),
        "current_index": data.get("current_index", 0),
    }
