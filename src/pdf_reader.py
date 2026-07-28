"""
PDF text + image extraction for CertPrep Coach.

Key design: images are emitted INLINE in the text stream at their real
reading-order position (by vertical coordinate), as [[[IMG:<hash>]]] markers.
Because the parser splits the text by "Question #N" tags, each image marker
naturally falls inside the block of the question it belongs to — so images are
attached to the correct question by TAG, not merely by page number.

extract_pdf_content(file_bytes, image_dir) -> (full_text, image_map)
    full_text : page text with [[[PAGE n]]] markers and inline [[[IMG:hash]]]
    image_map : {hash: saved_path}  (only meaningful, de-duplicated images)
"""

import os
import hashlib

import fitz


MIN_IMAGE_AREA = 12000          # skip tiny icons/avatars
PAGE_MARKER = "[[[PAGE {n}]]]"
IMG_MARKER = "[[[IMG:{h}]]]"


def extract_text_from_pdf(uploaded_file):
    """Plain text only (kept for any legacy callers)."""
    text = ""
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for i in range(len(doc)):
        text += doc.load_page(i).get_text() + "\n"
    doc.close()
    return text


def _image_entries_for_page(doc, page):
    """
    Return a list of (y0, hash, png_bytes, w, h) for images on this page, using
    each image's on-page rectangle so we know its vertical position.
    """
    entries = []
    seen_xref = set()
    for img in page.get_images(full=True):
        xref = img[0]
        if xref in seen_xref:
            continue
        seen_xref.add(xref)
        # Where does this image sit on the page?
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        y0 = rects[0].y0 if rects else 1e9  # unknown -> sort to bottom
        try:
            pix = fitz.Pixmap(doc, xref)
        except Exception:
            continue
        if pix.width * pix.height < MIN_IMAGE_AREA:
            pix = None
            continue
        if pix.n - pix.alpha >= 4:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        png = pix.tobytes("png")
        h = hashlib.md5(png).hexdigest()
        entries.append((y0, h, png, pix.width, pix.height))
        pix = None
    return entries


def extract_pdf_content(file_bytes, image_dir):
    os.makedirs(image_dir, exist_ok=True)
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = len(doc)
    ui_repeat_threshold = max(20, int(total_pages * 0.5))

    # ---- Pass 1: collect image entries per page + hash frequency ----------
    page_entries = {}       # page_index -> [(y0, hash, png, w, h)]
    hash_pages = {}         # hash -> set(page_index)
    for pi in range(total_pages):
        page = doc.load_page(pi)
        entries = _image_entries_for_page(doc, page)
        page_entries[pi] = entries
        for _y, h, _png, _w, _hh in entries:
            hash_pages.setdefault(h, set()).add(pi)

    # ---- Decide which hashes to keep (skip site logos/watermarks) ---------
    def keep(h):
        return len(hash_pages.get(h, set())) <= ui_repeat_threshold

    # ---- Save kept images to disk (de-duplicated by hash) -----------------
    image_map = {}
    for pi in range(total_pages):
        for _y, h, png, _w, _hh in page_entries[pi]:
            if not keep(h) or h in image_map:
                continue
            path = os.path.join(image_dir, f"img_{h[:12]}.png")
            with open(path, "wb") as f:
                f.write(png)
            image_map[h] = path

    # ---- Pass 2: build inline reading-order text stream -------------------
    text_parts = []
    for pi in range(total_pages):
        page = doc.load_page(pi)
        text_parts.append(PAGE_MARKER.format(n=pi + 1))

        # Text + image blocks together, sorted by vertical position.
        stream = []  # (y0, kind, value)
        try:
            blocks = page.get_text("blocks")  # (x0,y0,x1,y1,text,bno,btype)
        except Exception:
            blocks = []
        for b in blocks:
            if len(b) >= 7 and b[6] == 0 and (b[4] or "").strip():
                stream.append((b[1], "text", b[4]))
        for y0, h, _png, _w, _hh in page_entries[pi]:
            if keep(h):
                stream.append((y0, "img", h))

        if stream:
            stream.sort(key=lambda e: (e[0], 0 if e[1] == "text" else 1))
            for _y, kind, val in stream:
                if kind == "text":
                    text_parts.append(val)
                else:
                    text_parts.append(IMG_MARKER.format(h=val))
        else:
            # Fallback: no block info — use plain text.
            text_parts.append(page.get_text())

    doc.close()
    return "\n".join(text_parts), image_map
