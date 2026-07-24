"""
Library / database layer for CertPrep Coach.

Turns a folder of exam PDFs into an instantly-loadable question bank so users
never have to upload files repeatedly.

    Sample Inputs/
        MD 102/  *.pdf
        SC 401/  *.pdf

Each subfolder = one exam. Parsing is cached in SQLite (.cache/library.db)
keyed by each PDF's content hash; extracted images persist in .cache/images/.
"""

import os
import re
import json
import hashlib
import sqlite3

from src.pdf_reader import extract_pdf_content
from src.question_parser import parse_questions


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LIBRARY_DIR = os.path.join(PROJECT_ROOT, "Sample Inputs")
CACHE_DIR = os.path.join(PROJECT_ROOT, ".cache")
DB_PATH = os.path.join(CACHE_DIR, "library.db")
IMAGE_ROOT = os.path.join(CACHE_DIR, "images")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def _connect():
    os.makedirs(CACHE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pdf_cache (
            file_hash      TEXT PRIMARY KEY,
            exam           TEXT NOT NULL,
            filename       TEXT NOT NULL,
            questions_json TEXT NOT NULL,
            image_dir      TEXT NOT NULL,
            parsed_at      TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _file_hash(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def list_exams(library_dir=DEFAULT_LIBRARY_DIR):
    if not os.path.isdir(library_dir):
        return []
    exams = []
    for name in sorted(os.listdir(library_dir)):
        sub = os.path.join(library_dir, name)
        if os.path.isdir(sub) and _pdfs_in(sub):
            exams.append(name)
    return exams


def _pdfs_in(folder):
    return [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(".pdf")]


def library_summary(library_dir=DEFAULT_LIBRARY_DIR):
    out = []
    for exam in list_exams(library_dir):
        pdfs = _pdfs_in(os.path.join(library_dir, exam))
        out.append({"exam": exam, "pdf_count": len(pdfs),
                    "pdfs": [os.path.basename(p) for p in pdfs]})
    return out


# ---------------------------------------------------------------------------
# Add a new exam (create folder + save uploaded PDFs)
# ---------------------------------------------------------------------------

def _safe_exam_name(name):
    name = (name or "").strip()
    # Allow letters, numbers, spaces, dashes; collapse the rest.
    name = re.sub(r"[^A-Za-z0-9 \-_]+", "", name).strip()
    return name


def add_exam(exam_name, uploaded_files, library_dir=DEFAULT_LIBRARY_DIR):
    """
    Create (or reuse) an exam folder and save uploaded PDFs into it.

    exam_name: str
    uploaded_files: list of Streamlit UploadedFile objects (have .name + .read()/getbuffer())

    Returns (folder_path, saved_filenames). Raises ValueError on bad input.
    """
    clean = _safe_exam_name(exam_name)
    if not clean:
        raise ValueError("Please enter a valid exam name.")
    if not uploaded_files:
        raise ValueError("Please attach at least one PDF.")

    folder = os.path.join(library_dir, clean)
    os.makedirs(folder, exist_ok=True)

    saved = []
    for uf in uploaded_files:
        fname = os.path.basename(uf.name)
        if not fname.lower().endswith(".pdf"):
            continue
        dest = os.path.join(folder, fname)
        with open(dest, "wb") as f:
            # Streamlit UploadedFile supports getbuffer(); fall back to read().
            try:
                f.write(uf.getbuffer())
            except Exception:
                f.write(uf.read())
        saved.append(fname)

    if not saved:
        raise ValueError("No PDF files were saved.")
    return folder, saved


# ---------------------------------------------------------------------------
# Parsing with cache
# ---------------------------------------------------------------------------

def _parse_pdf_cached(path, exam, conn, force=False):
    file_hash = _file_hash(path)
    filename = os.path.basename(path)

    if not force:
        row = conn.execute(
            "SELECT questions_json, image_dir FROM pdf_cache WHERE file_hash = ?",
            (file_hash,)).fetchone()
        if row:
            questions_json, image_dir = row
            if os.path.isdir(image_dir):
                try:
                    return json.loads(questions_json)
                except Exception:
                    pass

    image_dir = os.path.join(IMAGE_ROOT, file_hash)
    os.makedirs(image_dir, exist_ok=True)
    with open(path, "rb") as f:
        file_bytes = f.read()
    full_text, page_images = extract_pdf_content(file_bytes, image_dir)
    questions = parse_questions(full_text, page_images)

    from datetime import datetime
    conn.execute(
        "REPLACE INTO pdf_cache (file_hash, exam, filename, questions_json, image_dir, parsed_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (file_hash, exam, filename, json.dumps(questions), image_dir,
         datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    return questions


def load_exam(exam, library_dir=DEFAULT_LIBRARY_DIR, force=False, progress=None):
    folder = os.path.join(library_dir, exam)
    pdfs = _pdfs_in(folder)
    if not pdfs:
        return []
    conn = _connect()
    all_questions = []
    try:
        for i, path in enumerate(pdfs):
            if progress:
                progress(i, len(pdfs), os.path.basename(path))
            all_questions.extend(_parse_pdf_cached(path, exam, conn, force=force))
        if progress:
            progress(len(pdfs), len(pdfs), "done")
    finally:
        conn.close()
    _regroup_cases(all_questions)
    return all_questions


def _regroup_cases(questions):
    groups = {}
    for i, q in enumerate(questions):
        cid = q.get("case_id")
        if cid:
            groups.setdefault(cid, []).append(i)
    for _cid, idxs in groups.items():
        for pos, i in enumerate(idxs):
            questions[i]["case_position"] = pos + 1
            questions[i]["case_size"] = len(idxs)


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def clear_cache():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


def cache_info():
    if not os.path.exists(DB_PATH):
        return 0, []
    conn = _connect()
    try:
        rows = conn.execute("SELECT COUNT(*) FROM pdf_cache").fetchone()[0]
        exams = [r[0] for r in conn.execute(
            "SELECT DISTINCT exam FROM pdf_cache ORDER BY exam").fetchall()]
    finally:
        conn.close()
    return rows, exams
