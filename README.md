# 📘 CertPrep Coach

**An exam simulator for Microsoft certification practice.** Upload exam-question
PDFs and CertPrep Coach turns them into an interactive, Microsoft-style practice
experience — with case-study navigation, timed sessions, scoring, an AI vision
layer that auto-builds drag-and-drop / hotspot questions, and a study-focused
reading mode.

Built with **Python + Streamlit**. Internal team tool for certification prep.

---

## ✨ Features

### Study modes
- **Practice mode** — answer questions, check answers, get a scored report
- **Reading mode** — reveal the correct answer, highlight the right options, and
  read the captured community discussion & voted answers for each question

### Coverage options
- **Full exam** — every question in one sitting
- **60-question sets** — each set guaranteed to include at least one case study
  and two Yes/No questions
- **⚡ Quick test** — 10 mixed-type questions for a fast check

### Exam experience
- **Microsoft-style UI** — Segoe UI font, Fluent palette, progress header
  (Standalone / Case Study / Lab) and an `HH:MM:SS` countdown timer
- **All question types** — single choice, multiple choice, hotspot/dropdown,
  drag-and-drop, and lab/simulation
- **Case studies** — grouped left-nav (Overview, Environment ▸ Existing/Network,
  Requirements ▸ Technical, etc.) with the question and exhibits on the right
- **Clean formatting** — run-on stems are split into readable sentences and
  bulleted lists, with the actual question bolded
- **Navigator** — jump-to-question grid (collapsible) with status markers
  (✅ answered · 🚩 review later · ⚪ not attempted)
- **Save & resume**, **End exam**, and a **score report** using Microsoft-style
  100–1000 scaling (700 pass line) with per-skill-area and per-section breakdowns

### 🤖 AI vision layer (optional)
With an OpenAI key configured, the app reads exhibit images and:
- **Auto-builds drag-and-drop** — the actions appear as draggable cards and the
  Answer Area has the right number of slots; your order is auto-graded
- **Auto-builds hotspot dropdowns** — options + correct answers filled in
- **Routes images** — keeps answer-area images out of the tables/exhibits panel
  and hidden during practice
- **Recovers missing answer keys** for choice questions

Without AI, everything falls back to a manual build / reveal-exhibit flow.

### Library
- **Question library** — pre-loaded exams parsed once and cached in SQLite for
  instant loading thereafter
- **Add new exam** from the home page — create a folder and upload PDFs directly
- **Quick upload** for one-off PDFs

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
Create a `Sample Inputs` folder in the project root, one subfolder per exam with
the PDF(s) inside — or use **➕ Add New Exam** in the app:

```text
Sample Inputs/
├── MD 102/
│   └── md-102.pdf
└── SC 401/
    └── sc-401.pdf
```

### 4. (Optional) Enable AI
See **[AI_SETUP.md](AI_SETUP.md)** — covers the API key **and** the corporate
network (NCS) certificate fix. Skip this to use the app without AI.

### 5. Run
```bash
streamlit run app.py
```
Open the local URL shown (usually http://localhost:8501).

### 6. Practise
1. **📚 Question Library** → pick an exam → **Load this exam**
2. Choose **Practice** or **Reading**, and **Full / 60-question set / Quick test**
3. Start, resume, or take the exam — then review your score report

> 💡 **First time / Reading mode:** click **🔄 Re-parse (ignore cache)** once so
> images and community discussions are captured with the latest parser.

---

## 🗂️ Project structure

```text
certprep-coach/
├── app.py                  # thin router / entry point
├── requirements.txt
├── commit.py               # helper: git add + commit + push
├── check_ai.py             # AI diagnostic (run to verify AI setup)
├── .env.example            # template for AI config (copy to .env)
├── README.md
├── AI_SETUP.md
│
├── src/                    # data + logic layer
│   ├── pdf_reader.py       # text + inline image extraction
│   ├── question_parser.py  # question types, case studies, community, images
│   ├── quiz_engine.py      # scoring, shuffle, filter, review, timer
│   ├── exam_builder.py     # full / 60-question sets / quick test
│   ├── library.py          # SQLite-cached exam library + add-exam
│   ├── progress.py         # save/load session progress (JSON)
│   └── ai_extractor.py     # AI vision: extraction + image classification
│
├── ui/                     # presentation layer
│   ├── state.py            # session state, formatting, grouped-nav logic
│   ├── styles.py           # Fluent / Segoe CSS
│   ├── header.py           # progress header + timer
│   ├── navigator.py        # sidebar navigator
│   ├── questions.py        # practice + reading renderers, controls, footer
│   ├── pages.py            # home, mode chooser, quiz, report pages
│   └── report.py           # Microsoft-style score report
│
├── tests/
│   └── test_all.py         # automated checks (run before committing)
│
├── Sample Inputs/          # exam library (git-ignored) — one folder per exam
├── .cache/                 # SQLite parse cache + images + AI cache (git-ignored)
└── .progress/              # saved session files (git-ignored)
```

---

## 🧰 Developer notes

- **Run the tests** before committing: `python tests/test_all.py`
- **Commit helper:** `python commit.py "your message"` stages, commits, and pushes.
- **Git housekeeping:** this repo sets `gc.auto 0` to avoid an antivirus/OneDrive
  file-lock issue during automatic garbage collection. Don't run `git gc` manually.
- **Caching:** parsed questions, extracted images and AI results are cached under
  `.cache/`. Use **🔄 Re-parse** (or delete `.cache/`) to rebuild.
- **Keep it out of OneDrive:** work from a non-synced path like `C:\Dev\` to avoid
  Git/OneDrive file-lock conflicts.

---

## ⚠️ Responsible use

This is an **internal, non-commercial** study tool. Use only exam material your
team is authorised to use. Certification-exam content is the intellectual
property of the certifying vendor — keep usage within your organisation's
policies. If AI is enabled, exhibit images are sent to OpenAI for extraction —
confirm this is acceptable under your data-handling policy.

---

## 🛣️ Roadmap ideas

- Nested parent/child scenario sections with deeper grouping
- Keyboard shortcuts for faster navigation
- Team leaderboard and shared progress
- Shared AI cache so an exam is extracted once for the whole team
