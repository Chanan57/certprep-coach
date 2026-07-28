# 🤖 AI Vision Layer — Setup

The AI layer reads exhibit images with OpenAI's vision model so **drag-and-drop
and hotspot questions auto-populate** (no typing) and can be **auto-graded**.

It's completely optional — if no key is set, the app falls back to the manual
build / reveal-exhibit flow exactly as before.

## 1. Add your key (never commit it)

Copy `.env.example` to `.env` in the project root and paste your key:

```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

`.env` is git-ignored, so your key stays off GitHub. (Double-check `.gitignore`
contains `.env`.)

Alternatively, set it as an environment variable before launching:

```powershell
$env:OPENAI_API_KEY = "sk-your-key-here"
streamlit run app.py
```

## 2. Install the dependency

```bash
pip install requests        # already required by the app
```

No SDK needed — the layer calls the REST API directly.

## 3. Use it

On a drag-drop or hotspot question you'll see a **🤖 Auto-extract with AI**
button. Click it once and the app:

- Reads the exhibit image with the vision model
- Fills the draggable Actions cards (drag-drop) or the dropdowns (hotspot)
- Reveals the correct answer so you can be auto-graded

Results are **cached to `.cache/ai/`** per image, so each question is only sent
to the model once — a one-time cost for the whole team. Delete `.cache/ai/` to
force re-extraction.

## 4. Cost

With `gpt-4o-mini`, vision extraction is roughly a fraction of a cent per
question. A full 250-question exam is about **US$1–2 one-time**, then free from
cache forever.

## 5. Model choice

- `gpt-4o-mini` (default) — cheap, fast, accurate enough for these exhibits
- `gpt-4o` — higher accuracy, a bit more cost; set `OPENAI_MODEL=gpt-4o`

## Security notes

- The `.env` key is never printed or committed.
- Exhibit images are sent to OpenAI for extraction — confirm this is acceptable
  under your team's data-handling policy before using on sensitive content.
