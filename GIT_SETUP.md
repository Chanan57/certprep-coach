# Getting CertPrep Coach into Git (one-time setup)

This ends the "file reset" problem for good: the repo becomes the single source
of truth in **your** environment, and Copilot only ever hands you one changed
file at a time to commit.

## 0. Prerequisites
- Git installed (`git --version`)
- A GitHub or Azure DevOps account
- The project folder locally (from the last downloaded zip), e.g. `certprep-coach/`

## 1. Put the starter files in the project
Copy `.gitignore` into the root of `certprep-coach/` so it sits next to `app.py`:

```text
certprep-coach/
├── .gitignore        <-- add this
├── app.py
├── requirements.txt
├── README.md
└── src/
    ├── __init__.py
    ├── pdf_reader.py
    ├── question_parser.py
    ├── quiz_engine.py
    ├── topic_tagger.py
    └── ai_extractor.py
```

## 2. Initialise and make the first commit

```bash
cd path/to/certprep-coach

git init
git add .
git commit -m "Initial commit: CertPrep Coach AI version"
```

## 3a. Push to GitHub
Create an empty repo on github.com (no README/gitignore — you already have them),
then:

```bash
git branch -M main
git remote add origin https://github.com/<you>/certprep-coach.git
git push -u origin main
```

## 3b. OR push to Azure DevOps
Create an empty repo in your project, then:

```bash
git branch -M main
git remote add origin https://dev.azure.com/<org>/<project>/_git/certprep-coach
git push -u origin main
```

## 4. The ongoing workflow with Copilot

```text
You:  "update ai_extractor.py to add disk caching"
Copilot: [gives you just the updated ai_extractor.py]
You:  save over the file, then:
        git add src/ai_extractor.py
        git commit -m "AI: cache extractions to disk"
        git push
```

One small edit = one small file = minimal tokens, full history, team-shareable.

## Security reminders (baked into .gitignore)
- **Never commit API keys.** Put them in a local `.env` (git-ignored) or use
  Streamlit secrets / environment variables.
- Runtime image folders (`certprep_img_*`) and results CSVs are git-ignored.

## Optional: a .env for local AI keys (not committed)
Create `certprep-coach/.env` (already ignored) — load it however you prefer, or
just export the vars in your shell:

```bash
AI_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-06-01
```
