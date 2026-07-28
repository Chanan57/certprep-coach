"""
AI vision layer for CertPrep Coach (OpenAI).

Reads an exhibit image with a vision-capable model (gpt-4o / gpt-4o-mini) and
returns structured data so drag-drop / hotspot boards can auto-populate and be
auto-graded:

    DRAG_DROP -> items, slots, answer_map (correct item per slot)
    HOTSPOT   -> dropdowns [{label, options, correct}]
    CHOICE    -> correct_answer (letters)

Configuration (NEVER hard-code the key):
    OPENAI_API_KEY   – your key (env var or a git-ignored .env)
    OPENAI_MODEL     – default "gpt-4o-mini" (vision-capable, cheap)

Results are cached to .cache/ai/<image-hash>.json so each question is only
sent to the model once — one-time cost per exam for the whole team.

No third-party SDK required; uses the REST API via `requests`.
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


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_dotenv():
    """Minimal .env loader (no dependency). Loads KEY=VALUE lines if present."""
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
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You read screenshots of Microsoft certification practice questions and "
    "return STRICT JSON describing the interactive answer area and the correct "
    "answer. Use only what is visible in the image and the provided question "
    "text. Never invent options. Respond with JSON only, no prose."
)


def _user_prompt(question_text, qtype):
    schema = (
        'Return JSON:\n'
        '{\n'
        '  "type": "DRAG_DROP" | "HOTSPOT" | "CHOICE",\n'
        '  "items": [string],           // DRAG_DROP: source actions\n'
        '  "slots": [string],           // DRAG_DROP: answer-area positions/targets\n'
        '  "answer_map": {slot: item},  // DRAG_DROP: correct item per slot\n'
        '  "dropdowns": [               // HOTSPOT\n'
        '     {"label": string, "options": [string], "correct": string}\n'
        '  ],\n'
        '  "correct_answer": string,    // CHOICE: e.g. "B" or "AE"\n'
        '  "notes": string\n'
        '}\n'
        'Omit keys that do not apply. Use exact wording from the image. '
        'If the image shows a "Correct Answer" / answer area, use it to fill '
        'answer_map / dropdowns[].correct / correct_answer.'
    )
    return f"Question type: {qtype}\nQuestion text:\n{question_text}\n\n{schema}"


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _cache_key(image_paths, qtype, question_text):
    h = hashlib.md5()
    h.update((qtype or "").encode())
    h.update((question_text or "")[:200].encode())
    for p in image_paths:
        try:
            with open(p, "rb") as f:
                h.update(hashlib.md5(f.read()).digest())
        except Exception:
            h.update(p.encode())
    return h.hexdigest()


def _cache_path(key):
    os.makedirs(AI_CACHE_DIR, exist_ok=True)
    return os.path.join(AI_CACHE_DIR, f"{key}.json")


def _read_cache(key):
    path = _cache_path(key)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _write_cache(key, data):
    try:
        with open(_cache_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def _encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _image_blocks(image_paths, max_images=4):
    blocks = []
    for p in image_paths[:max_images]:
        if os.path.exists(p):
            b64 = _encode_image(p)
            blocks.append({"type": "image_url",
                           "image_url": {"url": f"data:image/png;base64,{b64}"}})
    return blocks


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


def extract_from_images(question, cfg, use_cache=True):
    """
    Return a normalised dict:
      {ok, type, items, slots, answer_map, dropdowns, correct_answer, notes,
       error?}
    Cached per image so repeat views cost nothing.
    """
    if not is_configured(cfg):
        return {"ok": False, "error": "AI is not configured (no OPENAI_API_KEY)."}

    images = [p for p in question.get("images", []) if os.path.exists(p)]
    if not images:
        return {"ok": False, "error": "No exhibit images for this question."}

    qtype = question.get("type", "")
    qtext = question.get("question_text", "")
    key = _cache_key(images, qtype, qtext)

    if use_cache:
        cached = _read_cache(key)
        if cached is not None:
            cached["ok"] = True
            cached["_cached"] = True
            return cached

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [{"type": "text", "text": _user_prompt(qtext, qtype)}]
                                     + _image_blocks(images)},
    ]
    body = {"model": cfg["model"], "messages": messages, "temperature": 0,
            "max_tokens": 900, "response_format": {"type": "json_object"}}
    headers = {"Authorization": f"Bearer {cfg['api_key']}",
               "Content-Type": "application/json"}

    try:
        r = requests.post(OPENAI_URL, headers=headers, json=body, timeout=cfg["timeout"])
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"]
    except requests.HTTPError as e:
        return {"ok": False, "error": f"API error {e.response.status_code}: "
                f"{e.response.text[:200]}"}
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
    _write_cache(key, data)
    return data
