# 📘 CertPrep Coach

**An exam simulator for Microsoft certification practice.** Point it at
ExamTopics PDF exports and CertPrep Coach turns them into an interactive,
Microsoft-style practice experience — with case-study navigation, timed
sessions, scoring, a holistic **AI vision layer** that auto-builds drag-and-drop
and hotspot questions, and a study-focused **Reading mode** with community
discussions.

Built with **Python + Streamlit**. An internal, non-commercial team study tool.

> 🎯 Why it exists: prepping for Microsoft certs by scrolling PDF exports page by
> page is slow, passive, and gives no way to test yourself. Paid sites have a
> simulation mode but lock it behind purchased test exams. CertPrep Coach gives
> you a friendly, interactive way to actually practise — for free.

---

## ✨ Features

### Study modes
- **Practice mode** — answer questions, check answers, get a scored report.
- **Reading mode** — reveal the correct answer, highlight the right options, and
  read the captured community discussion & voted answers for each question.

### Coverage options
- **Full exam** — every question in one sitting.
- **60-question sets** — each set guaranteed ≥1 case study and ≥2 Yes/No.
- **⚡ Quick test** — 10 mixed-type questions for a fast check.

### Exam experience
- **Modern, Fluent-style UI** — Poppins/Inter fonts, indigo palette, rounded
  cards, a progress header (Standalone / Case Study / Lab) and an `HH:MM:SS`
  countdown timer.
- **All question types** — single, multiple choice, hotspot/dropdown,
  drag-and-drop (real draggable cards via `streamlit-sortables`), and lab/sim.
- **Case studies** — grouped left-nav (Overview, Environment ▸ Existing/Network,
  Requirements ▸ Technical…) with the question and exhibits on the right.
- **Clean formatting** — run-on stems split into readable sentences and bullet
  lists, with the actual question bolded.
- **Navigator** — jump-to-question grid (collapsible) with status markers
  (✅ answered · 🚩 review later · ⚪ not attempted).
- **Save & resume**, **End exam**, and a **score report** using Microsoft-style
  100–1000 scaling (700 pass line) with per-skill-area and per-section breakdowns.

### 🤖 AI vision layer (optional)
With an OpenAI key configured and an exam **Prepared**, the app reads exhibit
images with a single **holistic** call per question and:
- **Auto-builds drag-and-drop** — actions become draggable cards; the Answer
  Area has the right number of slots; your order is auto-graded.
- **Auto-builds hotspot dropdowns** — options + correct answers filled in.
- **Routes images** — keeps the green "Correct Answer" image out of the question
  during practice; shows it in reading.
- **Recovers missing answer keys** for choice questions and gives a short "why".

Without AI, everything falls back to a manual build / reveal-exhibit flow.

### ⚙️ One-click Prepare (parse + community + images + AI)
Adding an exam (**➕ Create & prepare**) — or the **⚙️ Prepare** button on the
Library tab — runs the whole pipeline up front with a live progress bar:
parse → capture community discussions → extract images → AI-analyse every image
question. After that, practice/reading is instant.

### 💰 Token policy (keeps costs tiny)
**AI tokens are spent ONCE, only during Prepare.** Load, Practice, Reading and
per-question rendering are **cache-only** — they read the prepared results for
free and never call the API. A full 250-question exam is a one-time ~US$1–2 on
`gpt-4o-mini`, then free forever.

### 🤝 Shared team cache
Prepared AI results are stored in a committable `ai_cache/` folder (extracted
data only, no secrets). One teammate Prepares an exam and commits it; everyone
else pulls the repo and gets instant AI-powered questions **with no API key**.

### Library
- **Question library** — exams parsed once and cached in SQLite for instant
  loading thereafter.
- **Add new exam** from the home page — create a folder, upload PDFs, prepare.
- **Quick upload** for one-off PDFs.

---

## 🚀 Getting started

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Clone and install
```bash
git clone https://github.com/Chanan57/certprep-coach.git
cd certprep-coach
pip install -r requirements.txt
```

### 3. Add your exams
Use **➕ Add New Exam** in the app, or create a `Sample Inputs` folder in the
project root, one subfolder per exam with the PDF(s) inside:
```text
Sample Inputs/
├── MD 102/  md-102.pdf
└── SC 100/  sc-100.pdf
```

### 4. (Optional) Enable AI
See **[AI_SETUP.md](AI_SETUP.md)** — covers the API key **and** the corporate
network (NCS) certificate fix. Skip this to use the app without AI.

### 5. Run
```bash
streamlit run app.py
```
Open the local URL (usually http://localhost:8501).

### 6. Practise
1. **📚 Question Library** → pick an exam → **⚙️ Prepare** (one-time) → **Load**.
2. Choose **Practice** or **Reading**, and **Full / 60-set / ⚡ Quick test**.
3. Start, resume, or take the exam — then review your score report.

---

## 🗂️ Project structure

```text
certprep-coach/
├── app.py                  # thin router — renders exactly ONE page per run
├── requirements.txt        # streamlit, pymupdf, pandas, requests, streamlit-sortables
├── commit.py               # git add + commit + push helper
├── check_ai.py             # AI/OpenAI + corporate-CA diagnostic
├── check_images.py         # image-pipeline diagnostic
├── check_img_assign.py     # image-assignment (bleed) diagnostic
├── .env.example            # AI config template (copy to .env)
├── README.md, AI_SETUP.md, PROJECT_BRIEF.md
│
├── src/                    # data + logic
│   ├── pdf_reader.py       # text + inline [[[IMG:hash]]] extraction  (matched pair)
│   ├── question_parser.py  # types, case studies, community, image binding (matched)
│   ├── quiz_engine.py      # scoring, shuffle, filter, review, timer
│   ├── exam_builder.py     # full / 60-sets / quick-test(10)
│   ├── exam_prep.py        # one-click prepare pipeline (parse + community + AI)
│   ├── library.py          # SQLite-cached exam library + add_exam
│   ├── progress.py         # save/load session progress
│   ├── ai_extractor.py     # holistic analyze_question() + shared ai_cache/
│   └── image_router.py     # positional fallback (last of 2+ = answer key)
│
├── ui/                     # presentation
│   ├── state.py            # session state, qid, formatting, grouped-nav
│   ├── styles.py           # Fluent / Poppins-Inter CSS (indigo theme)
│   ├── header.py           # progress header + timer
│   ├── navigator.py        # sidebar jump-to-question
│   ├── questions.py        # practice + reading renderers, controls, footer
│   ├── pages.py            # home/library/add-exam, mode chooser, quiz, report
│   └── report.py           # Microsoft-style score report
│
├── tests/test_all.py       # automated checks — run before committing
├── Sample Inputs/          # exam PDFs (GIT-IGNORED, local only)
├── ai_cache/               # shared AI results (COMMITTED, no secrets)
├── .cache/                 # SQLite parse cache + images (git-ignored)
└── .progress/              # saved sessions (git-ignored)
```

---

## 🧰 Developer notes

- **Run the tests** before committing: `python tests/test_all.py`.
- **Commit helper:** `python commit.py "your message"` stages, commits, pushes.
- **Matched pair:** `src/pdf_reader.py` and `src/question_parser.py` must be
  updated together — pdf_reader emits inline `[[[IMG:hash]]]` markers and the
  parser binds images to the question whose `Question #` tag they fall under.
- **Diagnostics:** `check_ai.py`, `check_images.py`, `check_img_assign.py` pin
  down AI/SSL and image-assignment issues quickly.
- **Git housekeeping:** repo sets `gc.auto 0` (antivirus/OneDrive lock `.git`).
  Keep the repo out of OneDrive — work from `C:\Dev`. Don't run `git gc` manually.
- **Caching:** parsed questions, images and AI results are cached. Use
  **🔄 Re-parse** / **⚙️ Prepare** (or delete `.cache/`) to rebuild.

---

## ⚠️ Responsible use

Internal, **non-commercial** study tool. Use only exam material your team is
authorised to use — certification content is the vendor's intellectual property.
If AI is enabled, exhibit images are sent to OpenAI for extraction; confirm this
is acceptable under your data-handling policy. **Never commit secrets** — `.env`,
`*.cer`/`*.pem`, and exam PDFs are git-ignored by design.

---

## 🛣️ Roadmap ideas

- "AI ready ✓ / not prepared" indicator on the mode page.
- Nested parent/child scenario sections.
- Keyboard shortcuts for navigation.
- Team leaderboard and shared progress.

---

_Last updated: 21 Jul 2026 · Sydney._
