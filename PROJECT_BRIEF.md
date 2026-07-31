# CertPrep Coach — Session Brief

> **How to use this:** Paste the "⚡ Quick brief" + "🔴 Current state" sections
> below at the START of a new AI chat so the assistant is instantly up to speed.
> Keep this file updated as the project evolves.

---

## ⚡ Quick brief (paste this into a new chat)

```
I'm working on CertPrep Coach — a Python + Streamlit exam simulator that parses
ExamTopics PDF exports into an interactive quiz. GitHub: Chanan57/certprep-coach,
local path C:\Dev\certprep-coach. Key facts:

STRUCTURE
- app.py = thin router ONLY. Strict if/elif/else, renders exactly ONE page/run.
  Order: no-questions->home, quiz_completed->results, quiz_started->quiz,
  show_mode->mode chooser. quiz_started MUST be checked before show_mode.
- src/pdf_reader.py + src/question_parser.py = a MATCHED PAIR. pdf_reader emits
  inline [[[IMG:hash]]] markers in reading order; parser binds images to the
  question whose "Question #N" tag the marker falls under. Update BOTH together.
- src/ai_extractor.py = holistic analyze_question() (OpenAI vision). ONE call
  per question returns image roles + answer + explanation (self-consistent).
  Shared committable cache in ai_cache/. Reads cache BEFORE checking the key.
- src/exam_prep.py = one-click prepare (parse + community + images + AI).
- src/exam_builder.py = full / 60-question sets / quick-test(10 mixed).
- src/library.py = SQLite-cached exam library (.cache/library.db) + add_exam.
- src/progress.py = save/resume session JSON.
- src/image_router.py = positional fallback (last of 2+ images = answer key).
- ui/ = state.py, styles.py (indigo/Poppins), header.py, navigator.py,
  questions.py, pages.py, report.py.
- tests/test_all.py = run before every commit.

HARD-WON RULES (do not reintroduce these bugs)
1. Images bind by "Question #" TAG via inline markers, NOT by page number.
   NO cross-question de-dup for inline markers (it robbed questions of images).
2. Noise-stripper must be LINE-SCOPED. A greedy datetime->URL span deletes
   whole pages of questions on SC-100 (datetime at page top, URL at bottom).
3. Answer-key / "Correct Answer" (green) images: HIDDEN in practice, shown in
   reading. Router: 1 image=question; 2+=last is the answer key (or AI roles).
4. Use holistic analyze_question(), NOT the old categorize_images()/
   extract_from_images() split (those were removed).
5. TOKEN POLICY: AI tokens spent ONLY via Prepare (real key). Practice/Reading/
   prewarm/per-question use a CACHE-ONLY config (key blanked) — reads cache,
   never calls API. Prepare is the only token spender.
6. NEVER commit .env, *.cer/*.pem, or exam PDFs (Sample Inputs/). ai_cache/ IS
   committed (shared team AI cache, no secrets). .gitignore enforces this.
7. On NCS network, OpenAI needs OPENAI_CA_BUNDLE=<corporate .cer> or SSL fails
   (CERTIFICATE_VERIFY_FAILED). Verify with: python check_ai.py
8. git: gc.auto=0 (antivirus locks .git/objects). Keep repo OUT of OneDrive
   (use C:\Dev). Commit helper: python commit.py "msg".
9. Teammates need the PDFs (via Teams/SharePoint, not git) to SEE images; the
   committed ai_cache/ then gives them free AI answers with no key.
10. My sandbox resets between turns — I can't see live files. Paste the specific
    file we're editing; commit to Git after each change.

Ask me to paste any specific file before editing it.
```

---

## 🔴 Current state (as of 21 Jul 2026, Sydney)

```
Everything is BUILT and working: Practice/Reading modes, Full/60-set/Quick test,
holistic AI (analyze_question), one-click Prepare, token policy (AI only via
Prepare), shared ai_cache/, modern indigo/Poppins UI, plus README.md,
AI_SETUP.md, TEST_CHECKLIST.md, PROJECT_BRIEF.md.

OPEN BUGS being fixed:

1. ✅ FIXED (applied): COVERAGE LEAK — the mode chooser (Coverage radio + set
   table) rendered BELOW the quiz in practice mode. Fix = strict if/elif router
   in app.py (quiz_started checked before show_mode). A fresh strict app.py was
   applied. TO CONFIRM: restart Streamlit + Ctrl+F5; Coverage should no longer
   appear under the quiz.

2. ❌ OPEN: TRIPLE CONTROLS — a case-study question showing "No options to
   select" renders the Reset Answer / Review later / Leave Feedback control
   block THREE times (stacked). Diagnosis so far:
     - app.py IS the strict router (confirmed).
     - ui/pages.py show_quiz_page: render_question_controls called once (line
       ~441 standalone) — CLEAN.
     - ui/pages.py _render_case_study: render_question_controls called once
       (line ~508, inside view=="__question__") — CLEAN.
     - Therefore the triple must originate in ui/questions.py
       render_question_body (NOT yet inspected).
   NEXT STEP: paste ui/questions.py (esp. render_question_body) to pinpoint why
   a no-options case-study question stacks the controls 3x. Likely the SINGLE/
   MULTI branch falls through to render_self_assess / controls repeatedly, or a
   type mismatch renders more than once.

QUESTIONS TO ANSWER when resuming:
- After the new app.py + hard refresh: is Coverage still shown under the quiz?
- Do the 3 control blocks appear on EVERY case-study question, or only the one
  that says "No options to select"?
```

---

## 📋 Full reference

### What it is
A Streamlit exam-prep tool. Parses ExamTopics PDF exports into questions (all
types), and offers **Practice mode** (answer + scored report) and **Reading
mode** (answers + community discussion). An optional **AI vision layer** (OpenAI)
reads exhibit images to auto-build drag-drop / hotspot widgets, route images, and
recover answers.

### Folder structure
```
certprep-coach/
├── app.py                  # thin router (ONE page per run, strict if/elif)
├── requirements.txt        # streamlit, pymupdf, pandas, requests, streamlit-sortables
├── commit.py               # git add + commit + push helper
├── check_ai.py             # AI/OpenAI + corporate-CA diagnostic
├── check_images.py         # image-pipeline diagnostic
├── check_img_assign.py     # image-assignment (bleed) diagnostic  (v2: by list order)
├── .env.example            # AI config template (copy to .env)
├── .gitignore              # secrets/PDFs out; ai_cache/ in
├── README.md, AI_SETUP.md, TEST_CHECKLIST.md, PROJECT_BRIEF.md
├── src/
│   ├── pdf_reader.py       # text + inline [[[IMG:hash]]] extraction  (matched)
│   ├── question_parser.py  # types, case studies, community, image binding (matched)
│   ├── quiz_engine.py      # scoring, shuffle, filter, review, timer
│   ├── exam_builder.py     # full / 60-sets / quick-test(10)
│   ├── exam_prep.py        # one-click prepare pipeline (parse + community + AI)
│   ├── library.py          # SQLite-cached exam library + add_exam
│   ├── progress.py         # save/load session progress
│   ├── ai_extractor.py     # holistic analyze_question() + shared ai_cache/
│   └── image_router.py     # positional fallback (last of 2+ = answer key)
├── ui/
│   ├── state.py            # session state, qid, formatting, grouped-nav
│   ├── styles.py           # Fluent / Poppins-Inter CSS (indigo theme)
│   ├── header.py           # progress header + HH:MM:SS timer
│   ├── navigator.py        # sidebar jump-to-question (collapsible)
│   ├── questions.py        # practice + reading renderers, controls, footer
│   ├── pages.py            # home/library/add-exam, mode chooser, quiz, report
│   └── report.py           # Microsoft-style 100–1000 score report (700 pass)
├── tests/test_all.py       # automated checks — run before committing
├── Sample Inputs/<Exam>/   # exam PDFs (GIT-IGNORED, local only)
├── ai_cache/               # shared AI results (COMMITTED, no secrets)
├── .cache/                 # SQLite parse cache + images (git-ignored)
└── .progress/              # saved sessions (git-ignored)
```

### Features
- Practice / Reading modes
- Full exam / 60-question sets (≥1 case study + ≥2 Yes/No each) / Quick test (10)
- All question types: single, multi, hotspot, drag-drop (real streamlit-sortables), lab
- Case studies: grouped left-nav (Environment ▸ Existing/Network, etc.)
- Jump-to navigator, save/resume, end exam, Microsoft-style score report
- Holistic AI vision; one-click Prepare; shared team cache; token policy
- Modern indigo/Poppins UI

### Known limitations / honest notes
- PyMuPDF only extracts RASTER images; vector-drawn answer areas can't be pulled.
- Multi-topic exams RESTART question numbers — never key logic by question
  number alone; use list position.
- Streamlit can't do true native drag-drop beyond streamlit-sortables lists.
- Teammates need the PDFs locally to SEE images; ai_cache/ only supplies answers.

### Timeline of bugs fixed (so we don't repeat them)
- Footer noise glued onto options → line-scoped stripper.
- SC-100 returned 0 questions → greedy stripper ate headers → line-scoped fix.
- Image bleed (Q4 img on Q3) → bind by tag + drop cross-question de-dup.
- Green answer image showing in practice → image_router + role-based hiding.
- Mode-chooser rendering under the quiz → strict single-page router in app.py.
- categorize_images AttributeError → switched to holistic analyze_question().
- SSL CERTIFICATE_VERIFY_FAILED (NCS proxy) → OPENAI_CA_BUNDLE support.
- Secret in .env pushed → rotate key, gitignore .env/certs/PDFs.
- AI re-spending tokens on Reading → cache-only config; Prepare is sole spender.

### Setup recap
```
pip install -r requirements.txt
# copy .env.example -> .env, add OPENAI_API_KEY (+ OPENAI_CA_BUNDLE on NCS net)
python check_ai.py            # verify AI
streamlit run app.py
python tests/test_all.py      # before committing
python commit.py "message"    # add + commit + push
```

_Last updated: 21 Jul 2026, 14:26 · Sydney, NSW._
