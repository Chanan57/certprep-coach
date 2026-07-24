# 📘 CertPrep Coach

**An exam simulator for Microsoft certification practice.** Upload exam-question
PDFs and CertPrep Coach turns them into an interactive, Microsoft-style practice
experience — complete with case-study navigation, timed sessions, scoring, and a
study-focused reading mode.

Built with **Python + Streamlit**. Internal team tool for certification prep.

---

## ✨ Features

### Study modes
- **Practice mode** — answer questions, check answers, get a scored report
- **Reading mode** — reveal the correct answer, highlight the right options, and
  read the captured community discussion & voted answers for each question

### Exam experience
- **Microsoft-style UI** — Segoe UI font, Fluent colour palette, progress header
  (Standalone / Case Study / Lab), and an `HH:MM:SS` countdown timer
- **Question types** — single choice, multiple choice, hotspot/dropdown,
  drag-and-drop, and lab/simulation
- **Case studies** — grouped left-nav (Overview, Environment ▸ Existing/Network,
  Requirements ▸ Technical, etc.) with the question and exhibits on the right
- **Clean formatting** — run-on stems are split into readable sentences and
  bulleted lists, with the actual question bolded

### Exam modes & flow
- **Full exam** (all questions) or **~60-question sets** — each set guaranteed to
  include at least one case study and two Yes/No questions
- **Jump-to-question navigator** with a collapsible grid and status markers
  (✅ answered · 🚩 review later · ⚪ not attempted)
- **Save & resume** progress, or start fresh
- **End exam** anytime, or **Finish** at the last question
- **Score report** using Microsoft-style 100–1000 scaling (700 pass line), with
  per-skill-area and per-section breakdowns and CSV export

### Library
- **Question library** — pre-loaded exams parsed once and cached in SQLite for
  instant loading thereafter
- **Add new exam** from the home page — create a folder and upload PDFs directly
- **Quick upload** for one-off PDFs

---

## 🗂️ Project structure

```text
certprep-coach/
├── app.py                  # thin router / entry point
├── requirements.txt
├── commit.py               # helper: git add + commit + push
│
├── src/                    # data + logic layer
│   ├── pdf_reader.py       # text + image extraction
│   ├── question_parser.py  # question types, case studies, community capture
│   ├── quiz_engine.py      # scoring, shuffle, filter, review, timer
│   ├── library.py          # SQLite-cached exam library + add-exam
│   ├── exam_builder.py     # full-exam and 60-question set building
│   ├── progress.py         # save/load session progress (JSON)
│   └── topic_tagger.py     # optional keyword topic tagging
│
├── ui/                     # presentation layer
│   ├── state.py            # session state, formatting, grouped-nav logic
│   ├── styles.py           # Fluent / Segoe CSS
│   ├── header.py           # progress header + timer
│   ├── navigator.py        # sidebar navigator (collapse, home, save)
│   ├── questions.py        # practice + reading renderers, controls, footer
│   ├── pages.py            # home, mode chooser, quiz, report pages
│   └── report.py           # Microsoft-style score report
│
├── Sample Inputs/          # exam library (git-ignored) — one folder per exam
│   ├── MD 102/  *.pdf
│   └── SC 401/  *.pdf
│
├── .cache/                 # SQLite parse cache + images (git-ignored)
└── .progress/              # saved session files (git-ignored)
```

---

## 🚀 Getting started

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Add your exams
Create a `Sample Inputs` folder in the project root, with one subfolder per exam
and the exam PDF(s) inside — or use **➕ Add New Exam** in the app:

```text
Sample Inputs/
├── MD 102/
│   └── md-102.pdf
└── SC 401/
    └── sc-401.pdf
```

### 3. Run the app
```bash
streamlit run app.py
```

Open the local URL shown (usually http://localhost:8501).

### 4. Practise
1. **📚 Question Library** → pick an exam → **Load this exam**
2. Choose **Practice** or **Reading** mode, and **Full exam** or **60-question set**
3. Start, resume, or take the exam — then review your score report

> 💡 **Reading mode tip:** if an exam was loaded before community capture was
> added, click **🔄 Re-parse (ignore cache)** once so discussions are available.

---

## 🧰 Developer notes

- **Commit helper:** run `python commit.py "your message"` to stage, commit, and
  push in one step.
- **Git housekeeping:** this repo sets `gc.auto 0` to avoid an antivirus/OneDrive
  file-lock issue during automatic garbage collection. Don't run `git gc` manually.
- **Caching:** parsed questions and extracted images are cached under `.cache/`;
  delete it (or use **Re-parse**) to rebuild.

---

## ⚠️ Responsible use

This is an **internal, non-commercial** study tool. Use only exam material your
team is authorised to use. Certification-exam content is the intellectual
property of the certifying vendor — keep usage within your organisation's
policies.

---

## 🛣️ Roadmap ideas

- **AI layer** (Azure OpenAI vision) to auto-read hotspot/drag-drop answers from
  exhibit images and clean up community text
- Nested parent/child scenario sections with deeper grouping
- Keyboard shortcuts for faster navigation
- Team leaderboard and shared progress
