"""
check_images.py — diagnose why a question shows "No exhibit image was captured".

Run from the project root:

    python check_images.py "SC 100"        # exam folder name under Sample Inputs
    python check_images.py "SC 100" 4      # focus on a specific question number

It reports, for the given exam:
  A) whether pdf_reader + question_parser are the matched (inline-marker) pair
  B) how many RASTER images PyMuPDF can actually extract from the PDF(s)
  C) how many parsed questions ended up with images
  D) for a focused question: does its page contain raster images at all?

This distinguishes the three causes:
  - version mismatch / stale cache  -> B > 0 but C == 0
  - genuine vector-only answer area -> B == 0 (nothing to extract)
  - all good                        -> B > 0 and C > 0
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_images.py \"<Exam folder>\" [question_number]")
        sys.exit(1)
    exam = sys.argv[1]
    focus = int(sys.argv[2]) if len(sys.argv) > 2 else None

    print("=" * 60)
    print(f" Image diagnostic — exam: {exam}")
    print("=" * 60)

    # --- A) Are pdf_reader / parser the matched inline-marker pair? --------
    import inspect
    from src import pdf_reader, question_parser
    reader_src = inspect.getsource(pdf_reader)
    parser_src = inspect.getsource(question_parser)
    reader_inline = "IMG_MARKER" in reader_src or "[[[IMG" in reader_src
    parser_inline = "IMG_MARKER_RE" in parser_src or "[[[IMG" in parser_src
    print("\nA) Module versions:")
    print(f"   pdf_reader emits inline image markers : {'YES' if reader_inline else 'NO (OLD)'}")
    print(f"   question_parser reads inline markers  : {'YES' if parser_inline else 'NO (OLD)'}")
    if reader_inline != parser_inline:
        print("   ❌ MISMATCH — update BOTH files to the latest matched pair.")
    elif reader_inline and parser_inline:
        print("   ✅ Matched pair.")
    else:
        print("   ⚠️  Both are the OLD page-based version.")

    # --- Locate the exam PDFs ---------------------------------------------
    folder = os.path.join(ROOT, "Sample Inputs", exam)
    if not os.path.isdir(folder):
        print(f"\n❌ Folder not found: {folder}")
        sys.exit(1)
    pdfs = [os.path.join(folder, f) for f in sorted(os.listdir(folder))
            if f.lower().endswith(".pdf")]
    if not pdfs:
        print(f"\n❌ No PDFs in {folder}")
        sys.exit(1)
    print(f"\n   PDFs: {[os.path.basename(p) for p in pdfs]}")

    # --- B) Raw raster-image count straight from PyMuPDF -------------------
    import fitz
    total_raster = 0
    pages_with_raster = 0
    for path in pdfs:
        doc = fitz.open(path)
        for pi in range(len(doc)):
            imgs = doc[pi].get_images(full=True)
            if imgs:
                pages_with_raster += 1
            total_raster += len(imgs)
        doc.close()
    print("\nB) Raw raster images PyMuPDF can see:")
    print(f"   total raster images across PDF(s): {total_raster}")
    print(f"   pages containing >=1 raster image : {pages_with_raster}")
    if total_raster == 0:
        print("   🟠 ZERO raster images — this PDF likely draws answer areas as")
        print("      TEXT + VECTOR graphics. PyMuPDF cannot extract those as images.")
        print("      (This is a genuine limitation; the AI needs a raster image.)")

    # --- C) Run the real pipeline and count images per question -----------
    import tempfile
    tmp = tempfile.mkdtemp()
    all_q = []
    for path in pdfs:
        with open(path, "rb") as f:
            data = f.read()
        full_text, image_data = pdf_reader.extract_pdf_content(data, tmp)
        qs = question_parser.parse_questions(full_text, image_data)
        all_q.extend(qs)
    with_img = sum(1 for q in all_q if q.get("images"))
    print("\nC) After parsing:")
    print(f"   questions parsed        : {len(all_q)}")
    print(f"   questions WITH image(s) : {with_img}")
    if total_raster > 0 and with_img == 0:
        print("   ❌ Images exist in the PDF but NONE attached to questions →")
        print("      version mismatch or stale cache. Update both files + Re-parse.")
    elif with_img > 0:
        print("   ✅ Images are being attached to questions.")

    # --- D) Focus on one question -----------------------------------------
    if focus is not None:
        q = next((x for x in all_q if x.get("question_number") == focus), None)
        print(f"\nD) Question #{focus}:")
        if not q:
            print("   (not found)")
        else:
            print(f"   type   : {q.get('type')}")
            print(f"   images : {len(q.get('images', []))}")
            for p in q.get("images", []):
                print(f"            - {os.path.basename(p)}")
            if not q.get("images"):
                print("   → no image attached. See B) and C) above for the reason.")

    print("\n" + "=" * 60)
    print(" Summary")
    print("=" * 60)
    if total_raster == 0:
        print(" 🟠 This PDF has no raster images to extract (vector/text answer")
        print("    areas). Fix: re-export the PDF from ExamTopics as one that")
        print("    embeds screenshots, or accept manual entry for these.")
    elif with_img == 0:
        print(" 🔴 Images exist but aren't attaching. Fix: ensure pdf_reader.py")
        print("    AND question_parser.py are the latest matched pair, then click")
        print("    '🔄 Re-parse (ignore cache)' on the home page.")
    else:
        print(" ✅ Pipeline is healthy. If a single question still lacks an image,")
        print("    it's specific to that question's layout — Re-parse to refresh.")


if __name__ == "__main__":
    main()
