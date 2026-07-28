"""
check_parse.py — find out WHY fresh parsing returns 0 questions.

Run:  python check_parse.py "SC 100"

It extracts one PDF's text and reports:
  - how many characters of text were extracted
  - how many "Question ..." header matches the parser's regex finds
  - a raw sample of the text (so we can see the real header format)
  - what the noise-stripper leaves behind
"""

import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def main():
    exam = sys.argv[1] if len(sys.argv) > 1 else "SC 100"
    folder = os.path.join(ROOT, "Sample Inputs", exam)
    pdfs = [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(".pdf")]
    if not pdfs:
        print("No PDFs found."); sys.exit(1)

    path = pdfs[0]
    print("=" * 60)
    print(f" Parse diagnostic — {os.path.basename(path)}")
    print("=" * 60)

    from src import pdf_reader, question_parser

    with open(path, "rb") as f:
        data = f.read()
    tmp = tempfile.mkdtemp()
    full_text, image_data = pdf_reader.extract_pdf_content(data, tmp)

    print(f"\n1) Extracted text length: {len(full_text)} chars")
    print(f"   image_data type: {type(image_data).__name__}, entries: {len(image_data)}")

    # Header regex the parser uses.
    header_re = re.compile(r"(?:Topic\s+(\d+)\s+)?Question\s*#?\s*(\d+)", re.IGNORECASE)
    raw_hits = list(header_re.finditer(full_text))
    print(f"\n2) 'Question #N' matches in RAW extracted text: {len(raw_hits)}")

    # After noise stripping (what parse_questions actually works on).
    stripped = question_parser.strip_examtopics_noise(full_text)
    stripped = question_parser.clean_text(stripped)
    strip_hits = list(header_re.finditer(stripped))
    print(f"3) 'Question #N' matches AFTER noise-strip: {len(strip_hits)}")
    if len(raw_hits) > 0 and len(strip_hits) == 0:
        print("   ❌ The noise-stripper is DELETING the question headers!")

    # How many questions the full parser returns.
    qs = question_parser.parse_questions(full_text, image_data)
    print(f"4) parse_questions() returned: {len(qs)} questions")

    # Show the first chunk of raw text so we can see the real format.
    print("\n5) First 600 chars of RAW extracted text:")
    print("-" * 60)
    print(full_text[:600])
    print("-" * 60)

    # Show text around the first 'Question' word, if any.
    idx = full_text.lower().find("question")
    if idx != -1:
        print("\n6) Text around the first 'question' occurrence:")
        print("-" * 60)
        print(repr(full_text[max(0, idx - 40): idx + 120]))
        print("-" * 60)
    else:
        print("\n6) The word 'question' does NOT appear in the extracted text at all.")
        print("   → The PDF text may be inside images (scanned) — needs OCR.")


if __name__ == "__main__":
    main()
