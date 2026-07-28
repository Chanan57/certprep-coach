# 🤖 AI Vision Layer — Setup

The AI layer reads exhibit images with OpenAI's vision model so **drag-and-drop
and hotspot questions auto-build and auto-grade** (no typing), answer-area
images are hidden during practice, and missing answer keys are recovered.

It is **completely optional** — without a key, the app falls back to the manual
build / reveal-exhibit flow.

---

## 1. Add your API key

Copy `.env.example` to `.env` in the project root and paste your key:

```
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

`.env` is git-ignored, so your key never lands on GitHub. (Confirm `.gitignore`
contains `.env`.)

---

## 2. ⚠️ Corporate network (NCS) — the certificate step

On the NCS network, HTTPS traffic is **SSL-inspected** by a corporate proxy.
Python won't trust the proxy's certificate by default, so the AI call fails with:

```
[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate
```

If you see this, do the following **one-time** setup.

### a) Export the corporate root certificate
1. Press `Win+R` → type `certmgr.msc` → Enter
2. Open **Trusted Root Certification Authorities → Certificates**
3. Find your proxy's cert (names like **Zscaler Root CA**, **Netskope**, **NCS**,
   or your gateway vendor). *Unsure? Ask NCS IT for "the corporate root CA
   (.cer, Base-64) for our SSL-inspection proxy."*
4. Right-click → **All Tasks → Export**
5. Choose **No, do not export the private key**
6. Choose **Base-64 encoded X.509 (.CER)**
7. Save as: `C:\Dev\certprep-coach\corporate-ca.cer`

### b) Point the app at it
Add one line to your `.env`:

```
OPENAI_CA_BUNDLE=C:\Dev\certprep-coach\corporate-ca.cer
```

> If a single `.cer` isn't enough (some proxies use a chain), ask IT for the full
> bundle as a `.pem` and point `OPENAI_CA_BUNDLE` at that instead.

---

## 3. Verify it works

```bash
python check_ai.py
```

You want all steps green, ending with:

```
✅ 4. OpenAI responded: "OK"
🎉 AI is working — drag-drop/hotspot auto-fill will function.
```

The diagnostic tells you exactly what to fix if a step fails (missing key,
bad key = 401, no credit = 429, wrong model = 404, or the SSL/cert issue above).

---

## 4. Use it

Just start a Practice or Reading session. When you begin, a one-time
**🤖 Preparing questions with AI** step runs (with a progress bar) and caches
everything. After that:

- Drag-and-drop boards are **pre-filled** with the actions — just drag & drop
- Hotspot dropdowns are **pre-filled** with options + correct answers
- Answer-area images are hidden in practice, shown in reading
- Everything is cached to `.cache/ai/`, so it's a **one-time cost per exam**

---

## 5. Cost

With `gpt-4o-mini`, extraction is a fraction of a cent per question. A full
250-question exam is roughly **US$1–2 one-time**, then free from cache forever.

- `gpt-4o-mini` (default) — cheap, fast, accurate enough for these exhibits
- `gpt-4o` — higher accuracy at a bit more cost; set `OPENAI_MODEL=gpt-4o`

---

## Security notes

- The `.env` key is never printed or committed.
- The corporate-CA approach keeps SSL verification **on** — never disable
  certificate verification on a work machine.
- Exhibit images are sent to OpenAI for extraction — confirm this is acceptable
  under your team's data-handling policy before using on sensitive content.

---

## Troubleshooting quick reference

| Symptom | Fix |
|---|---|
| `OPENAI_API_KEY not found` | Add it to `.env`, restart the app |
| `CERTIFICATE_VERIFY_FAILED` | Do the corporate-CA step (section 2) |
| Still asks you to type in drag-drop | AI not reaching OpenAI — run `check_ai.py` |
| `401 Unauthorized` | Key is wrong/revoked — recheck the value in `.env` |
| `429` | No credit/quota — check OpenAI billing |
| `404 model not found` | Set `OPENAI_MODEL=gpt-4o-mini` |
| Changes not taking effect | Fully restart Streamlit (Ctrl+C → `streamlit run app.py`) |
