"""
One-click exam preparation for CertPrep Coach.

prepare_exam() runs the WHOLE pipeline up front so an exam is fully ready the
moment the user starts practising:

  1. Parse all PDFs (force re-parse) -> questions, community discussions, images
     (via library.load_exam, which caches to the SQLite library cache).
  2. AI-analyse every image question (holistic analyze_question) so drag-drop /
     hotspot widgets, image roles, and answers are pre-built and cached to the
     shared ai_cache/ folder.

It reports progress via a callback so the UI can show a live progress bar, and
returns a summary dict describing what was prepared.

Designed to be UI-agnostic: pass in the already-loaded `library` and
`ai_extractor` modules (or let it import them), plus a `progress` callback
    progress(fraction: float, message: str)
"""

import os


def _default_progress(_fraction, _message):
    pass


def prepare_exam(exam_name, cfg=None, progress=None,
                 lib=None, ai=None, library_dir=None):
    """
    Fully prepare an exam. Returns a summary dict:
        {
          "exam": str,
          "questions": int,
          "with_images": int,
          "with_community": int,
          "ai_analysed": int,      # questions successfully analysed by AI
          "ai_skipped": int,       # image questions AI couldn't analyse
          "ai_available": bool,    # whether AI was configured/reachable
          "types": {type: count},
        }
    `progress(fraction, message)` is called throughout (fraction in 0..1).
    """
    progress = progress or _default_progress

    # Lazy imports so this module is easy to unit-test with stubs.
    if lib is None:
        from src import library as lib  # noqa
    if ai is None:
        try:
            from src import ai_extractor as ai  # noqa
        except Exception:  # noqa
            ai = None

    # ---- Step 1: parse everything (force, to capture community + images) ---
    progress(0.02, f"Parsing {exam_name} (questions, images, discussions)...")

    def parse_cb(done, total, fname):
        frac = 0.02 + 0.33 * (done / max(total, 1))
        progress(frac, f"Parsing {fname} ({done}/{total})...")

    kwargs = {"force": True, "progress": parse_cb}
    if library_dir:
        kwargs["library_dir"] = library_dir
    questions = lib.load_exam(exam_name, **kwargs)

    total_q = len(questions)
    with_images = [q for q in questions if q.get("images")]
    with_community = sum(1 for q in questions if q.get("community"))
    types = {}
    for q in questions:
        types[q.get("type", "SINGLE")] = types.get(q.get("type", "SINGLE"), 0) + 1

    summary = {
        "exam": exam_name, "questions": total_q,
        "with_images": len(with_images), "with_community": with_community,
        "ai_analysed": 0, "ai_skipped": 0, "ai_available": False, "types": types,
    }

    if total_q == 0:
        progress(1.0, "No questions were parsed.")
        return summary

    # ---- Step 2: AI-analyse every image question -------------------------
    cfg = cfg or (ai.get_config() if ai else None)
    ai_ready = bool(ai and cfg and (ai.is_configured(cfg) or ai.cache_count()))
    summary["ai_available"] = bool(ai and cfg and ai.is_configured(cfg))

    if not ai or not ai_ready or not with_images:
        progress(1.0, "Parsing complete. (AI not configured — questions still "
                      "work with manual/fallback rendering.)")
        return summary

    analysed = skipped = 0
    n = len(with_images)
    for i, q in enumerate(with_images):
        progress(0.35 + 0.63 * (i / n),
                 f"AI analysing image question {i + 1} of {n}...")
        try:
            res = ai.analyze_question(q, cfg)
            if res.get("ok"):
                analysed += 1
            else:
                skipped += 1
        except Exception:  # noqa
            skipped += 1

    summary["ai_analysed"] = analysed
    summary["ai_skipped"] = skipped
    progress(1.0, f"Ready! {total_q} questions, {analysed} AI-analysed.")
    return summary
