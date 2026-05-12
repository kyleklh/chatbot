import re

import fitz  # PyMuPDF
from pypdf import PdfReader

from app.services.chunker.tables import render_table_markdown


def normalize_text(text: str) -> str:
    text = re.sub(r'-\n(\S)', r'\1', text)
    lines = text.split('\n')
    joined: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            joined.append('')
            continue
        if joined and joined[-1] and not re.search(r'[.!?:;|]\s*$', joined[-1]):
            joined[-1] += ' ' + line
        else:
            joined.append(line)
    text = '\n\n'.join(filter(None, '\n'.join(joined).split('\n\n')))
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def _get_text(page: fitz.Page, clip: fitz.Rect | None = None) -> str:
    if clip is not None:
        return str(page.get_text("text", clip=clip) or "")  # type: ignore[arg-type]
    return str(page.get_text("text") or "")  # type: ignore[arg-type]


def _extract_page(page: fitz.Page) -> str:
    finder = page.find_tables()  # type: ignore[union-attr]
    tables = finder.tables if finder else []

    if not tables:
        return normalize_text(_get_text(page))

    parts: list[str] = []
    page_rect = page.rect
    bboxes = sorted([t.bbox for t in tables], key=lambda b: b[1])

    # Prose above the first table (title / description)
    if bboxes[0][1] > page_rect.y0 + 10:
        clip = fitz.Rect(page_rect.x0, page_rect.y0, page_rect.x1, bboxes[0][1])
        above = normalize_text(_get_text(page, clip))
        if above:
            parts.append(above)

    # Each table rendered via the generic markdown renderer (D-07: no layout-
    # specific heuristics, no label-gating fallback).
    for t in tables:
        md = render_table_markdown(t.extract())
        if md:
            parts.append(md)

    # Prose below the last table (footnotes)
    if bboxes[-1][3] < page_rect.y1 - 10:
        clip = fitz.Rect(page_rect.x0, bboxes[-1][3], page_rect.x1, page_rect.y1)
        below = normalize_text(_get_text(page, clip))
        if below:
            parts.append(below)

    return '\n\n'.join(p for p in parts if p)


def extract_pdf_pages(file_path: str) -> list[dict]:
    pages = []

    try:
        doc = fitz.open(file_path)
        for index, page in enumerate(doc):  # type: ignore[arg-type]
            text = _extract_page(page)
            if text:
                pages.append({"page": index + 1, "text": text})
    except Exception as e:
        print(f"PyMuPDF failed ({e}), falling back to pypdf")
        reader = PdfReader(file_path)
        for index, page in enumerate(reader.pages):
            text = normalize_text(page.extract_text() or "")
            if text:
                pages.append({"page": index + 1, "text": text})

    return pages
