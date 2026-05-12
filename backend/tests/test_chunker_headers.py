"""Unit tests for HeaderClassifier (Plan 01-02).

Covers:
  - pymupdf4llm.IdentifyHeaders-based font-size detection (H1, H2, body)
  - Whole-line-bold fallback (D-01 secondary signal, RESEARCH OQ #4)
  - Inline bold-emphasis rejection (no false positive on "**Note:** ...")
"""
from __future__ import annotations

import pymupdf
import pytest

from app.services.chunker.headers import HeaderClassifier


def _find_span(doc, page_index: int, text_prefix: str):
    """Locate the first span on a page whose stripped text starts with prefix.

    Returns (span_dict, page) or (None, None).
    """
    page = doc.load_page(page_index)
    for block in page.get_text("dict")["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if span["text"].strip().startswith(text_prefix):
                    return span, page
    return None, None


def test_identify_headers(synthetic_pdf):
    """H1 "Section A" → level 1; body prose → level 0."""
    doc = pymupdf.open(synthetic_pdf)
    try:
        clf = HeaderClassifier(doc, max_levels=2)

        h1_span, page1 = _find_span(doc, 0, "Section A")
        assert h1_span is not None, "fixture must render 'Section A' on page 1"
        assert clf.classify_span(h1_span, page1) == 1

        body_span, page1b = _find_span(doc, 0, "This is the opening paragraph")
        assert body_span is not None, "fixture must render body prose on page 1"
        assert clf.classify_span(body_span, page1b) == 0
    finally:
        doc.close()


def test_pending_header_crosses_page(synthetic_pdf):
    """H2 "Subsection" at bottom of page 1 classifies as level 2.

    The CARRY across pages is the section assembler's job (Plan 04). Here we
    only verify the classifier surfaces the H2 correctly.
    """
    doc = pymupdf.open(synthetic_pdf)
    try:
        clf = HeaderClassifier(doc, max_levels=2)
        h2_span, page1 = _find_span(doc, 0, "Subsection")
        assert h2_span is not None, "fixture must render 'Subsection' H2 on page 1"
        assert clf.classify_span(h2_span, page1) == 2
    finally:
        doc.close()


def test_no_bold_inline_false_positive():
    """Inline "**Note:**" emphasis within a longer body line MUST NOT be a header.

    The whole-line-bold gate requires ALL spans bold AND combined len <= 80
    AND no terminal .;: punctuation. Here span 2 is not bold and the combined
    text is >80 chars, so the gate fails → level 0.
    """
    # Synthetic line: no PDF needed. flags bit 16 == bold per PyMuPDF docs.
    line = {
        "spans": [
            {"text": "Note:", "flags": 16, "size": 12.0},
            {
                "text": " the following sentence continues for a while and is far longer than 80 chars total.",
                "flags": 0,
                "size": 12.0,
            },
        ]
    }
    # We need a classifier; build one against a trivial empty doc so the
    # font-size path returns body for every span.
    doc = pymupdf.open()
    doc.new_page(width=612, height=792)
    try:
        clf = HeaderClassifier(doc, max_levels=2)
        assert clf.classify_line(line, page=None) == 0
    finally:
        doc.close()


def test_whole_line_bold_fallback_positive():
    """ALL spans bold, combined text <= 80 chars, no terminal .;: → level 2.

    Exercises the D-01 secondary signal / bold fallback path on its own when
    pymupdf4llm.IdentifyHeaders would otherwise return body (because all
    spans are body-size).
    """
    line = {
        "spans": [
            {"text": "Important ", "flags": 16, "size": 12.0},
            {"text": "Subsection Heading", "flags": 16, "size": 12.0},
        ]
    }
    doc = pymupdf.open()
    doc.new_page(width=612, height=792)
    try:
        clf = HeaderClassifier(doc, max_levels=2)
        assert clf.classify_line(line, page=None) == 2
    finally:
        doc.close()
