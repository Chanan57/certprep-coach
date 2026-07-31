"""
check_img_assign.py — pin down WHY an image bleeds into the wrong question.

Run:  python check_img_assign.py "SC 100" 3 4
      (exam folder, then the question numbers to inspect)

Reports:
  A) Is pdf_reader the inline-marker version? (emits [[[IMG:hash]]])
  B) For each PDF: the raw text stream around the given question headers,
     showing where PAGE / IMG markers and 'Question #N' headers actually sit.
  C) Which image(s) the parser assigns to each of those questions.
"""

import os
import re
import sys
import inspect
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def main():
    if len(sys.argv) < 2:
        print('Usage: python check_img_assign.py "<Exam>" [qnum ...]'); sys.exit(1)
    exam = sys.argv[1]
    qnums = [int(x) for x in sys.argv[2:]] or [3, 4]

    from src import pdf_reader, question_parser

    # A) version check
    reader_src = inspect.getsource(pdf_reader)
    inline = "IMG_MARKER" in reader_src or "[[[IMG" in reader_src
    print("A) pdf_reader emits inline image markers:",
          "YES ✅" if inline else "NO ❌  (page-based → prone to bleed)")

    folder = os.path.join(ROOT, "Sample Inputs", exam)
    pdfs = [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(".pdf")]
    if not pdfs:
        print("No PDFs found."); sys.exit(1)

    header_re = re.compile(r"Question\s*#?\s*(\d+)", re.IGNORECASE)
    img_re = re.compile(r"\[\[\[IMG:([0-9a-fA-F]+)\]\]\]")
    page_re = re.compile(r"\[\[\[PAGE\s+(\d+)\]\]\]")

    tmp = tempfile.mkdtemp()
    for path in pdfs:
        with open(path, "rb") as f:
            data = f.read()
        full_text, image_data = pdf_reader.extract_pdf_content(data, tmp)

        hits = {int(m.group(1)): m.start() for m in header_re.finditer(full_text)}
        if not any(qn in hits for qn in qnums):
            continue

        print("\n" + "=" * 60)
        print(f" {os.path.basename(path)}")
        print("=" * 60)
        print(f"   image_data: {type(image_data).__name__} with {len(image_data)} entries")

        for qn in qnums:
            if qn not in hits:
                continue
            start = hits[qn]
            # window from this header to the next header (or +1500 chars)
            later = [p for n, p in hits.items() if p > start]
            end = min(later) if later else start + 1500
            window = full_text[start:end]

            # Show a compact view: strip long prose, keep markers + first words.
            markers = []
            for m in re.finditer(r"\[\[\[(?:PAGE|IMG)[^\]]*\]\]\]|Question\s*#?\s*\d+", window):
                markers.append(m.group(0))
            print(f"\n   --- Q#{qn} block: marker sequence ---")
            print("   " + "  ".join(markers[:20]))

            # Parser's actual assignment
            qs = question_parser.parse_questions(full_text, image_data)
            q = next((x for x in qs if x.get("question_number") == qn), None)
            imgs = [os.path.basename(p) for p in (q.get("images") if q else [])]
            print(f"   Parser assigned images to Q#{qn}: {imgs}")

    print("\n" + "-" * 60)
    print(" If a Q#4 IMG marker appears INSIDE the Q#3 block above, that is the")
    print(" bleed. Paste this output back and I'll pin the exact fix.")


if __name__ == "__main__":
    main()
