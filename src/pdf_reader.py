import os
import hashlib

import fitz


# Images smaller than this pixel area are treated as UI noise (avatars, icons).
MIN_IMAGE_AREA = 12000

PAGE_MARKER = "[[[PAGE {n}]]]"


def extract_text_from_pdf(uploaded_file):
    """Simple text-only extraction (kept for compatibility)."""
    text = ""
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for i in range(len(doc)):
        text += doc.load_page(i).get_text() + "\n"
    doc.close()
    return text


def extract_pdf_content(file_bytes, image_dir):
    """
    Extract text and images from a PDF.

    Returns (full_text, page_images):
      - full_text: page text joined, with "[[[PAGE n]]]" markers before each page.
      - page_images: dict {page_number: [image_paths]}.

    Filtering:
      - Tiny images (icons/avatars) are skipped.
      - Only images repeated on a very large fraction of pages (site logo /
        watermark) are treated as UI noise and skipped. Case-study exhibits that
        repeat across a handful of pages are KEPT.
      - Identical images are de-duplicated on disk but still associated with
        every page they appear on.
    """
    os.makedirs(image_dir, exist_ok=True)
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = len(doc)

    # A logo/watermark appears on most pages; use a high threshold so real
    # exhibits (which repeat only within a case study) are preserved.
    ui_repeat_threshold = max(20, int(total_pages * 0.5))

    text_parts = []
    raw_images = {}          # page_number -> [(hash, bytes)]
    hash_pages = {}          # hash -> set(pages)

    for page_index in range(total_pages):
        page = doc.load_page(page_index)
        page_number = page_index + 1

        text_parts.append(PAGE_MARKER.format(n=page_number))
        text_parts.append(page.get_text())

        entries = []
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
            except Exception:
                continue

            if pix.width * pix.height < MIN_IMAGE_AREA:
                pix = None
                continue

            if pix.n - pix.alpha >= 4:  # CMYK -> RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)

            img_bytes = pix.tobytes("png")
            img_hash = hashlib.md5(img_bytes).hexdigest()
            entries.append((img_hash, img_bytes))
            hash_pages.setdefault(img_hash, set()).add(page_number)
            pix = None

        raw_images[page_number] = entries

    # Save non-UI images (deduped), associating each with all its pages.
    page_images = {}
    saved = {}  # hash -> path

    for page_number, entries in raw_images.items():
        for img_hash, img_bytes in entries:
            if len(hash_pages.get(img_hash, set())) > ui_repeat_threshold:
                continue  # site logo / watermark
            if img_hash not in saved:
                path = os.path.join(image_dir, f"img_{img_hash[:12]}.png")
                with open(path, "wb") as f:
                    f.write(img_bytes)
                saved[img_hash] = path
            page_images.setdefault(page_number, [])
            if saved[img_hash] not in page_images[page_number]:
                page_images[page_number].append(saved[img_hash])

    doc.close()
    return "\n".join(text_parts), page_images
