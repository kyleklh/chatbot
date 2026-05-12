"""Shared pytest fixtures for the chunking-rebuild test suite.

Provides:
  - `synthetic_pdf`: builds a 3-page in-memory PDF via pymupdf with a known
    layout (H1 on page 1, H2 at bottom of page 1 with no body on page 1,
    prose body on page 2, 5-row table on page 3). Used to validate D-04
    pending-header cross-page carry and table-row-no-split behaviors.
  - `chroma_in_memory`: returns a freshly-created collection on an ephemeral
    Chroma client for isolation between tests.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def synthetic_pdf(tmp_path: Path) -> Path:
    """Build a deterministic 3-page PDF and return its filesystem path.

    Layout:
      - Page 1: H1 "Section A" (18pt bold) near top, ~12pt prose body in the
        middle, H2 "Subsection" (14pt bold) at the bottom — NO body text
        after the H2 on page 1 (this exercises D-04 pending_header carry).
      - Page 2: ~12pt prose body that logically continues from the page-1 H2.
      - Page 3: a 5-row table rendered as a simple grid (lines + text cells)
        so PyMuPDF's `find_tables()` can detect row boundaries.
    """
    import pymupdf

    pdf_path = tmp_path / "synthetic.pdf"
    doc = pymupdf.open()

    # ---- Page 1: H1 + prose + trailing H2 (no body after) -----------------
    page1 = doc.new_page(width=612, height=792)  # US Letter
    page1.insert_text(
        (72, 90),
        "Section A",
        fontsize=18,
        fontname="helv",
        render_mode=0,
    )
    # Simulate bold via a second overlay pass (PyMuPDF's base14 "helv" has no
    # synthesized bold; using "hebo" — Helvetica-Bold — for the heading).
    page1.insert_text((72, 90), "Section A", fontsize=18, fontname="hebo")

    body_p1 = (
        "This is the opening paragraph of Section A. It contains ordinary "
        "prose body text at roughly twelve point that downstream chunker "
        "logic should treat as body content attached to the Section A "
        "heading above. The paragraph continues with several more clauses "
        "to ensure the chunker observes meaningful text on this page."
    )
    page1.insert_textbox(
        pymupdf.Rect(72, 120, 540, 360),
        body_p1,
        fontsize=12,
        fontname="helv",
    )

    # H2 at the bottom of page 1, deliberately with no body text after it on
    # this page. Plan 02's chunker must carry it forward to page 2.
    page1.insert_text((72, 740), "Subsection", fontsize=14, fontname="hebo")

    # ---- Page 2: body that follows the carried H2 -------------------------
    page2 = doc.new_page(width=612, height=792)
    body_p2 = (
        "This is the first paragraph of the Subsection. It begins on page "
        "two even though its heading appeared at the foot of page one. The "
        "chunker must attach this body to the Subsection heading per D-04. "
        "Several more sentences follow so that the body is non-trivial and "
        "the chunker has enough content to emit at least one small chunk."
    )
    page2.insert_textbox(
        pymupdf.Rect(72, 90, 540, 360),
        body_p2,
        fontsize=12,
        fontname="helv",
    )

    # ---- Page 3: 5-row table ---------------------------------------------
    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((72, 90), "Results Table", fontsize=14, fontname="hebo")

    rows = [
        ("ID", "Name", "Value"),
        ("1", "Alpha", "10"),
        ("2", "Beta", "20"),
        ("3", "Gamma", "30"),
        ("4", "Delta", "40"),
    ]
    x0, y0 = 72, 120
    col_w = 140
    row_h = 24
    n_cols = 3
    n_rows = len(rows)

    # Draw grid lines so PyMuPDF's find_tables() can detect cell structure.
    for r in range(n_rows + 1):
        y = y0 + r * row_h
        page3.draw_line((x0, y), (x0 + col_w * n_cols, y))
    for c in range(n_cols + 1):
        x = x0 + c * col_w
        page3.draw_line((x, y0), (x, y0 + row_h * n_rows))

    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            page3.insert_text(
                (x0 + c * col_w + 4, y0 + r * row_h + 16),
                str(cell),
                fontsize=11,
                fontname="helv",
            )

    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture
def chroma_in_memory():
    """Yield a fresh ephemeral Chroma collection (no on-disk persistence).

    Each test gets an isolated client + collection. Test code can call
    `collection.add(...)` / `.query(...)` directly.
    """
    import chromadb

    client = chromadb.EphemeralClient()
    collection = client.create_collection(name="test_collection")
    try:
        yield collection
    finally:
        try:
            client.delete_collection(name="test_collection")
        except Exception:
            pass
