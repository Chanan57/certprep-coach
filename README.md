# CertPrep Coach — Version 3 (fixed)

A Python + Streamlit exam-preparation tool. Upload a practice-question PDF and
it becomes an interactive, configurable quiz — with images, multiple question
types, and grouped case studies.

## What this version fixes

- 🧹 **Footer/noise removal** — strips repeated ExamTopics page footers
  (`1/23/26, 10:14 AM ... ExamTopics ... 9/230`) that were being glued onto the
  last answer option.
- 🖼️ **Images now show** — the image filter was too aggressive and dropped
  case-study exhibits; it now keeps exhibits and only skips true site logos.
- 🔽 **No more fake "Option 1/2/3"** — hotspot and drag-drop answer areas live
  inside the exhibit images, so the app shows the image + a self-assessment
  instead of fabricating meaningless dropdowns.
- 📁 **Case-study grouping** — questions that share a scenario (e.g. ADatum,
  Contoso) are grouped; the shared scenario + exhibits are shown once, with the
  specific question below.

## Question types

| Type | Interaction | Graded? |
|------|-------------|---------|
| Single choice | Radio buttons | ✅ Auto (if the PDF includes the key) |
| Multiple choice | Checkboxes | ✅ Auto (set match) |
| Hotspot / dropdown | Exhibit image + self-assessment | 🔎 Self-assess |
| Drag and drop | Exhibit image + self-assessment | 🔎 Self-assess |
| Simulation | Task text + exhibit + self-assessment | 🔎 Self-assess |

If a PDF has no answer key (common in free dumps), choice questions become
self-assessed too, with a clear note.

## Features

- Session setup: topic + type filters, shuffle, timed mode
- Case-study scenario grouping with exhibits
- Flag-as-difficult, smart retake (incorrect + flagged)
- Score summary (auto-graded vs self-assessed) + CSV export

## Project structure

```text
certprep-coach/
|-- app.py
|-- requirements.txt
|-- README.md
|-- src/
    |-- __init__.py
    |-- pdf_reader.py        # text + image extraction (noise-tolerant)
    |-- question_parser.py   # footer stripping, type detection, case studies
    |-- quiz_engine.py       # scoring, shuffle, filter, review, timer
    |-- topic_tagger.py      # optional keyword topic tagging
```

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown (usually http://localhost:8501), upload a PDF, choose
your session options, and practice.

## Tested against

- **MD-102** dump (110 questions): footers stripped, ADatum & Contoso case
  studies grouped, exhibits shown, no answer key → self-assessed.
- **SC-401** dump (254 questions): single/multi/hotspot/drag-drop/simulation all
  detected, answer keys auto-graded where present, images shown.

## Notes

- Extracted images are written to a temporary folder per session.
- Hotspot/drag-drop answers are inside the exhibit images by design of these
  PDFs, so those question types use self-assessment.
