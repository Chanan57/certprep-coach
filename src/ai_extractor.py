"""
AI vision layer for CertPrep Coach (OpenAI).

Two jobs:

1) extract_from_images(question, cfg)
   Reads an exhibit image and returns structured answer data so drag-drop /
   hotspot boards can auto-populate and be auto-graded.

2) categorize_images(question, cfg)
   Classifies EACH image attached to a question as one of:
       "table"       – a data table the scenario refers to (Users, Devices…)
       "answer_area" – the question's answer area / answer key (drag-drop
                       actions+order, hotspot dropdowns, Correct Answer boxes)
       "exhibit"     – a configuration screenshot / diagram used as reference
       "other"       – anything else (avatars, decoration)
   This lets the UI route images correctly — e.g. keep answer-area images OUT
   of the "Tables & exhibits" panel and show them with the answer instead.

Config (never hard-code the key):
    OPENAI_API_KEY, OPENAI_MODEL (default gpt-4o-mini)

Everything is cached to .cache/ai/ so each image is only sent once.
"""

import os
import json
import base64
import hashlib
import re

import requests


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_CACHE_DIR = os.path.join(PROJECT_ROOT, ".cache", "ai")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

VALID_CATEGORIES = {"table", "answer_area", "exhibit", "other"}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_dotenv():
    path = os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_config(overrides=None):
    _load_dotenv()
    cfg = {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "timeout": int(os.getenv("AI_TIMEOUT", "60")),
    }
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if v})
    return cfg


def is_configured(cfg):
    return bool(cfg.get("api_key"))


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _image_block(path):
    return {"type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{_encode_image(path)}"}}


def _image_blocks(image_paths, max_images=4):
    return [_image_block(p) for p in image_paths[:max_images] if os.path.exists(p)]


def _parse_json(raw):
    if not raw:
        return {}
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {}
    return {}


def _img_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return hashlib.md5(path.encode()).hexdigest()


def _cache_read(key):
    path = os.path.join(AI_CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _cache_write(key, data):
    os.makedirs(AI_CACHE_DIR, exist_ok=True)
    try:
        with open(os.path.join(AI_CACHE_DIR, f"{key}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _post(cfg, messages, max_tokens=900):
    body = {"model": cfg["model"], "messages": messages, "temperature": 0,
            "max_tokens": max_tokens, "response_format": {"type": "json_object"}}
    headers = {"Authorization": f"Bearer {cfg['api_key']}",
               "Content-Type": "application/json"}
    r = requests.post(OPENAI_URL, headers=headers, json=body, timeout=cfg["timeout"])
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# 1) Answer extraction
# ---------------------------------------------------------------------------

EXTRACT_SYSTEM = (
    "You read screenshots of Microsoft certification practice questions and "
    "return STRICT JSON describing the interactive answer area and the correct "
    "answer. Use only what is visible. Never invent options. JSON only."
)


def _extract_prompt(question_text, qtype):
    schema = (
        'Return JSON:\n'
        '{\n'
        '  "type": "DRAG_DROP" | "HOTSPOT" | "CHOICE",\n'
        '  "items": [string], "slots": [string], "answer_map": {slot: item},\n'
        '  "dropdowns": [{"label": string, "options": [string], "correct": string}],\n'
        '  "correct_answer": string, "notes": string\n'
        '}\nOmit keys that do not apply. Use exact wording from the image.'
    )
    return f"Question type: {qtype}\nQuestion text:\n{question_text}\n\n{schema}"


def extract_from_images(question, cfg, use_cache=True):
    if not is_configured(cfg):
        return {"ok": False, "error": "AI is not configured (no OPENAI_API_KEY)."}
    images = [p for p in question.get("images", []) if os.path.exists(p)]
    if not images:
        return {"ok": False, "error": "No exhibit images for this question."}

    qtype = question.get("type", "")
    qtext = question.get("question_text", "")
    key = "extract_" + hashlib.md5(
        (qtype + qtext[:200] + "".join(_img_hash(p) for p in images)).encode()
    ).hexdigest()

    if use_cache:
        cached = _cache_read(key)
        if cached is not None:
            cached["ok"] = True
            cached["_cached"] = True
            return cached

    messages = [
        {"role": "system", "content": EXTRACT_SYSTEM},
        {"role": "user", "content": [{"type": "text", "text": _extract_prompt(qtext, qtype)}]
                                     + _image_blocks(images)},
    ]
    try:
        raw = _post(cfg, messages)
    except requests.HTTPError as e:
        return {"ok": False, "error": f"API error {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:  # noqa
        return {"ok": False, "error": f"Request failed: {e}"}

    data = _parse_json(raw)
    if not data:
        return {"ok": False, "error": "Could not parse AI response.", "raw": raw[:300]}
    data.setdefault("type", qtype)
    data.setdefault("items", [])
    data.setdefault("slots", [])
    data.setdefault("answer_map", {})
    data.setdefault("dropdowns", [])
    data.setdefault("correct_answer", "")
    data.setdefault("notes", "")
    data["ok"] = True
    _cache_write(key, data)
    return data


# ---------------------------------------------------------------------------
# 2) Image classification
# ---------------------------------------------------------------------------

CLASSIFY_SYSTEM = (
    "You classify a single screenshot from a Microsoft certification practice "
    "question into exactly one category. Respond with STRICT JSON only."
)

CLASSIFY_PROMPT = (
    "Classify this image into exactly one category:\n"
    '- "table": a data table the scenario refers to (e.g. lists of users, '
    "groups, devices, policies, servers).\n"
    '- "answer_area": the question\'s answer area or answer key — drag-and-drop '
    "actions/answer boxes, hotspot dropdowns, Yes/No selection grids, or a "
    '"Correct Answer" panel.\n'
    '- "exhibit": a configuration screenshot, settings pane, or diagram shown '
    "as reference material.\n"
    '- "other": avatars, logos, decorative or irrelevant images.\n\n'
    'Return JSON: {"category": "table|answer_area|exhibit|other", '
    '"reason": "short"}'
)


def classify_image(path, cfg, use_cache=True):
    """Classify one image. Returns {'category':..., 'reason':..., 'ok':bool}."""
    if not is_configured(cfg):
        return {"ok": False, "category": "exhibit", "error": "AI not configured."}
    if not os.path.exists(path):
        return {"ok": False, "category": "other", "error": "missing file"}

    key = "classify_" + _img_hash(path)
    if use_cache:
        cached = _cache_read(key)
        if cached is not None:
            cached["ok"] = True
            cached["_cached"] = True
            return cached

    messages = [
        {"role": "system", "content": CLASSIFY_SYSTEM},
        {"role": "user", "content": [{"type": "text", "text": CLASSIFY_PROMPT},
                                     _image_block(path)]},
    ]
    try:
        raw = _post(cfg, messages, max_tokens=120)
    except requests.HTTPError as e:
        return {"ok": False, "category": "exhibit",
                "error": f"API error {e.response.status_code}"}
    except Exception as e:  # noqa
        return {"ok": False, "category": "exhibit", "error": f"Request failed: {e}"}

    data = _parse_json(raw)
    cat = (data.get("category") or "exhibit").strip().lower()
    if cat not in VALID_CATEGORIES:
        cat = "exhibit"
    result = {"ok": True, "category": cat, "reason": data.get("reason", "")}
    _cache_write(key, result)
    return result


def categorize_images(question, cfg, use_cache=True):
    """
    Classify every image on a question and return buckets:
        {"table": [...], "answer_area": [...], "exhibit": [...], "other": [...]}
    Paths that don't exist are skipped.
    """
    buckets = {c: [] for c in VALID_CATEGORIES}
    for p in question.get("images", []):
        if not os.path.exists(p):
            continue
        res = classify_image(p, cfg, use_cache=use_cache)
        buckets[res.get("category", "exhibit")].append(p)
    return buckets
