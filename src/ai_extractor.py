"""
AI vision layer for CertPrep Coach (OpenAI) — holistic question understanding.

The main entry point is `analyze_question(question, cfg)`. It sends the AI the
question text PLUS every image at once (each image explicitly numbered), and
asks for ONE complete, self-consistent understanding:

  - image_roles : for each image index, one of
        "question"    -> the exhibit/answer-area the user must respond to (show)
        "answer_key"  -> the correct answer (green/highlighted) — HIDE in practice
        "table"       -> a data table the scenario refers to (show)
        "exhibit"     -> config screenshot/diagram (show)
        "other"       -> avatar/decoration (ignore)
  - type        : DRAG_DROP | HOTSPOT | CHOICE | SIMULATION
  - items/answer/answer_map : for DRAG_DROP
  - dropdowns   : for HOTSPOT [{label, options, correct}]
  - correct_answer : for CHOICE
  - explanation : short "why" for study/reading

Because it's a single call, the image roles and the extracted answer can't
disagree (the old failure mode). Results are cached to a SHARED, committable
folder (ai_cache/) keyed by content hash, so an exam is analysed once for the
whole team.

Shared team cache
-----------------
  ai_cache/            <- committed to Git (extracted data only, NO secrets)
Lookup: ai_cache/  ->  .cache/ai/ (legacy/local)  ->  live API (then writes
ai_cache/). Teammates who pull the repo get instant AI with no key.

Config (never hard-code):
    OPENAI_API_KEY, OPENAI_MODEL (default gpt-4o-mini)
    OPENAI_CA_BUNDLE -> corporate root CA for SSL-inspection proxies (NCS)
"""

import os
import json
import base64
import hashlib
import re

import requests


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARED_CACHE_DIR = os.path.join(PROJECT_ROOT, "ai_cache")
LOCAL_CACHE_DIR = os.path.join(PROJECT_ROOT, ".cache", "ai")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

VALID_ROLES = {"question", "answer_key", "table", "exhibit", "other"}


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
        "timeout": int(os.getenv("AI_TIMEOUT", "90")),
        "ca_bundle": os.getenv("OPENAI_CA_BUNDLE", "")
                     or os.getenv("REQUESTS_CA_BUNDLE", ""),
    }
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if v})
    return cfg


def _verify(cfg):
    ca = cfg.get("ca_bundle")
    return ca if (ca and os.path.exists(ca)) else True


def is_configured(cfg):
    return bool(cfg.get("api_key"))


def cache_count():
    n = 0
    for d in (SHARED_CACHE_DIR, LOCAL_CACHE_DIR):
        if os.path.isdir(d):
            n += len([f for f in os.listdir(d) if f.endswith(".json")])
    return n


def config_status():
    cfg = get_config()
    if not cfg.get("api_key"):
        cached = cache_count()
        base = "No OPENAI_API_KEY set"
        if cached:
            return True, f"{base} — but {cached} cached AI result(s) available."
        return False, base + ". Add OPENAI_API_KEY to .env (or pull a repo with ai_cache/)."
    ca = cfg.get("ca_bundle")
    if ca and not os.path.exists(ca):
        return True, f"AI key found, but OPENAI_CA_BUNDLE path missing: {ca}"
    return True, f"AI ready (model: {cfg['model']}{', corporate CA' if ca else ''})."


# ---------------------------------------------------------------------------
# Low-level
# ---------------------------------------------------------------------------

def _b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _img_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return hashlib.md5(path.encode()).hexdigest()


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


def _cache_read(key):
    for d in (SHARED_CACHE_DIR, LOCAL_CACHE_DIR):
        path = os.path.join(d, f"{key}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return None


def _cache_write(key, data):
    os.makedirs(SHARED_CACHE_DIR, exist_ok=True)
    try:
        with open(os.path.join(SHARED_CACHE_DIR, f"{key}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _post(cfg, messages, max_tokens=1200):
    body = {"model": cfg["model"], "messages": messages, "temperature": 0,
            "max_tokens": max_tokens, "response_format": {"type": "json_object"}}
    headers = {"Authorization": f"Bearer {cfg['api_key']}",
               "Content-Type": "application/json"}
    r = requests.post(OPENAI_URL, headers=headers, json=body,
                      timeout=cfg["timeout"], verify=_verify(cfg))
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Holistic analysis
# ---------------------------------------------------------------------------

ANALYZE_SYSTEM = (
    "You are an expert at reading Microsoft certification practice questions. "
    "You are given the question text and one or more numbered images. Analyse "
    "EVERYTHING together and return a single STRICT JSON object that is fully "
    "self-consistent. Use only what is visible. Never invent options. JSON only."
)


def _analyze_prompt(question_text, qtype, n_images):
    return (
        f"Question type hint: {qtype}\n"
        f"Number of images: {n_images} (referred to as image 1..{n_images} in "
        f"the order provided)\n\n"
        f"Question text:\n{question_text}\n\n"
        "Return STRICT JSON:\n"
        "{\n"
        '  "type": "DRAG_DROP" | "HOTSPOT" | "CHOICE" | "SIMULATION",\n'
        '  "image_roles": [ {"index": 1, "role": "question|answer_key|table|exhibit|other"}, ... ],\n'
        "     // Classify EVERY image. The image that shows the BLANK answer area /\n"
        "     // exhibit the user must respond to = \"question\". The image showing the\n"
        "     // CORRECT answer (green/highlighted rows, or a 'Correct Answer' panel)\n"
        "     // = \"answer_key\". Data tables = \"table\". Config screenshots = \"exhibit\".\n"
        '  "items": [string],          // DRAG_DROP: all draggable actions\n'
        '  "answer": [string],         // DRAG_DROP: correct items, in order\n'
        '  "answer_map": {slot: item}, // DRAG_DROP match-to-target\n'
        '  "dropdowns": [ {"label": string, "options": [string], "correct": string} ],\n'
        '  "correct_answer": string,   // CHOICE: e.g. "B" or "AE"\n'
        '  "explanation": string       // one or two sentences on WHY (for study)\n'
        "}\n"
        "Rules: every image gets exactly one role. For HOTSPOT, read each dropdown\n"
        "label, its options, and the correct option from the answer-key image.\n"
        "For DRAG_DROP, 'answer' lists only the correct items in top-to-bottom order.\n"
        "Omit keys that do not apply."
    )


def _content_blocks(question_text, qtype, images):
    blocks = [{"type": "text", "text": _analyze_prompt(question_text, qtype, len(images))}]
    for i, p in enumerate(images, 1):
        blocks.append({"type": "text", "text": f"--- image {i} ---"})
        blocks.append({"type": "image_url",
                       "image_url": {"url": f"data:image/png;base64,{_b64(p)}"}})
    return blocks


def _normalise(data, images):
    data.setdefault("type", "CHOICE")
    data.setdefault("items", [])
    data.setdefault("answer", [])
    data.setdefault("answer_map", {})
    data.setdefault("dropdowns", [])
    data.setdefault("correct_answer", "")
    data.setdefault("explanation", "")

    # Build a {path: role} map from image_roles (1-based index -> path).
    roles = {}
    for entry in data.get("image_roles", []) or []:
        try:
            idx = int(entry.get("index"))
        except Exception:
            continue
        role = (entry.get("role") or "exhibit").strip().lower()
        if role not in VALID_ROLES:
            role = "exhibit"
        if 1 <= idx <= len(images):
            roles[images[idx - 1]] = role
    # Any unclassified images -> safe default (show as exhibit).
    for p in images:
        roles.setdefault(p, "exhibit")
    data["roles"] = roles

    # DRAG_DROP consistency: derive answer from answer_map if needed; ensure
    # every answer item exists in items.
    if not data["answer"] and data["answer_map"]:
        data["answer"] = [data["answer_map"][k] for k in sorted(data["answer_map"].keys())]
    for a in data["answer"]:
        if a not in data["items"]:
            data["items"].append(a)
    return data


def analyze_question(question, cfg, use_cache=True):
    """
    Holistic per-question analysis. Returns a dict with keys:
      ok, type, roles{path:role}, items, answer, answer_map, dropdowns,
      correct_answer, explanation  (and error/_cached where relevant).
    """
    images = [p for p in question.get("images", []) if os.path.exists(p)]
    qtype = question.get("type", "")
    qtext = question.get("question_text", "")

    key = "analyze_" + hashlib.md5(
        (qtype + qtext[:300] + "".join(_img_hash(p) for p in images)).encode()
    ).hexdigest()

    if use_cache:
        cached = _cache_read(key)
        if cached is not None:
            cached["ok"] = True
            cached["_cached"] = True
            # roles keys are stored by path; if the paths changed we still keep
            # the structural answer data (items/answer/dropdowns).
            return cached

    if not images:
        return {"ok": False, "error": "No images to analyse.",
                "roles": {}, "type": qtype, "items": [], "answer": [],
                "dropdowns": [], "correct_answer": ""}
    if not is_configured(cfg):
        return {"ok": False, "error": "Not cached and no OPENAI_API_KEY.",
                "roles": {p: "exhibit" for p in images}, "type": qtype,
                "items": [], "answer": [], "dropdowns": [], "correct_answer": ""}

    messages = [
        {"role": "system", "content": ANALYZE_SYSTEM},
        {"role": "user", "content": _content_blocks(qtext, qtype, images)},
    ]
    try:
        raw = _post(cfg, messages)
    except requests.HTTPError as e:
        return {"ok": False, "error": f"API error {e.response.status_code}: {e.response.text[:200]}",
                "roles": {p: "exhibit" for p in images}}
    except Exception as e:  # noqa
        return {"ok": False, "error": f"Request failed: {e}",
                "roles": {p: "exhibit" for p in images}}

    data = _parse_json(raw)
    if not data:
        return {"ok": False, "error": "Could not parse AI response.", "raw": raw[:300],
                "roles": {p: "exhibit" for p in images}}

    data = _normalise(data, images)
    data["ok"] = True
    _cache_write(key, data)
    return data
