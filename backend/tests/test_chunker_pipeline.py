"""Full chunker pipeline tests (Plan 01-04).

Validates:
- D-11 metadata schema (all 7 required keys on every child chunk)
- D-04 pending-header carry across pages (synthetic_pdf H2 at end of page 1
  must show up in first page-2 child chunk)
- D-12 user_id seam: present only when explicitly passed
"""
from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from app.services.chunker import chunk_pages
from app.services.chunker.assembler import build_chunk_metadata  # noqa: F401  (imported for re-export contract)
from app.services.pdf_loader import extract_pdf_pages


_REQUIRED_CHILD_KEYS = {
    "chunk_id",
    "document_id",
    "parent_ref",
    "page",
    "chunker_version",
    "indexed_at",
    "kind",
}


def _run(pdf_path: Path, **kwargs):
    pages = extract_pdf_pages(str(pdf_path))
    return chunk_pages(
        pages,
        document_id=kwargs.pop("document_id", "doc1"),
        source_path=str(pdf_path),
        **kwargs,
    )


def test_metadata_schema(synthetic_pdf: Path) -> None:
    children, parents = _run(synthetic_pdf)

    assert isinstance(children, list) and isinstance(parents, list)
    assert children, "expected at least one child chunk"
    assert parents, "expected at least one parent chunk"

    for c in children:
        meta = c["metadata"]
        missing = _REQUIRED_CHILD_KEYS - set(meta.keys())
        assert not missing, f"child metadata missing keys: {missing}"
        assert meta["kind"] in {"prose", "table_row_group"}, meta["kind"]
        assert isinstance(meta["parent_ref"], str) and meta["parent_ref"], "parent_ref must be non-empty str"
        assert isinstance(meta["indexed_at"], int)
        assert meta["chunker_version"] == "v2-2026-05"
        assert meta["document_id"] == "doc1"

    for p in parents:
        assert p["metadata"]["kind"] == "parent"
        assert isinstance(p["metadata"]["chunk_id"], str) and p["metadata"]["chunk_id"]

    # D-04 pending-header carry: H2 "Subsection" lives at the bottom of page 1
    # with no body on page 1; the synthetic body that follows is on page 2.
    # The first page-2 child chunk text MUST contain "Subsection".
    page2_children = [c for c in children if c["metadata"].get("page") == 2 or
                      (isinstance(c["metadata"].get("page"), str) and c["metadata"]["page"].startswith("2"))]
    assert page2_children, "expected at least one child on page 2"
    assert "Subsection" in page2_children[0]["text"], (
        f"page-2 first chunk should carry the pending H2 'Subsection'; got: "
        f"{page2_children[0]['text'][:200]!r}"
    )


def test_user_id_seam(synthetic_pdf: Path) -> None:
    children_none, _ = _run(synthetic_pdf, user_id=None)
    for c in children_none:
        assert "user_id" not in c["metadata"], "user_id must be absent when not provided"

    children_u1, _ = _run(synthetic_pdf, user_id="u1")
    for c in children_u1:
        assert c["metadata"].get("user_id") == "u1", c["metadata"]


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — implemented in plan 01-07")
def test_no_split_rows():
    assert False, "Wave 0 stub"


@pytest.mark.xfail(strict=True, reason="Wave 0 stub — implemented in plan 01-07")
def test_header_attached_to_body():
    assert False, "Wave 0 stub"
