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


# ---------------------------------------------------------------------------
# SC1 parametrized integration over backend/tests/fixtures/pdfs/ (Plan 01-07)
#
# When the fixtures dir is empty, each test calls pytest.skip(...) inside its
# body so collection still succeeds (collection-time skip would otherwise
# xpass and confuse the CI signal). Drop ≥3 PDFs into the fixtures dir to
# light up SC1 per D-13.
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pdfs"
_USER_PDFS = sorted(_FIXTURES_DIR.glob("*.pdf"))


@pytest.mark.parametrize("pdf_path", _USER_PDFS or [None], ids=lambda p: p.name if p else "no-pdfs")
def test_no_split_rows(pdf_path):
    if pdf_path is None:
        pytest.skip("no user PDFs dropped into backend/tests/fixtures/pdfs/ yet — see README")
    children, _parents = chunk_pages(
        extract_pdf_pages(str(pdf_path)),
        document_id=f"sc1-{pdf_path.stem}",
        source_path=str(pdf_path),
    )
    for child in children:
        if child["metadata"].get("kind") != "table_row_group":
            continue
        text = child["text"]
        # Every line starting with `|` must have ≥ 2 unescaped pipes (balanced cells).
        for line in text.split("\n"):
            if not line.startswith("|"):
                continue
            # Count un-escaped pipes only.
            stripped = line.replace("\\|", "")
            assert stripped.count("|") >= 2, (
                f"unbalanced table row in {pdf_path.name} chunk "
                f"{child['metadata']['chunk_id']}: {line!r}"
            )
        # Pitfall 2 guard: a table_row_group chunk that begins immediately with
        # a `| value |` row (no header above) suggests a row was orphaned. Every
        # row_group_split output starts with title + header + separator, so the
        # first non-empty line should NOT match a pure-data row before a `---`
        # separator appears.
        lines = [ln for ln in text.split("\n") if ln.strip()]
        if lines:
            saw_sep = any("---" in ln for ln in lines[:3])
            assert saw_sep, (
                f"table chunk in {pdf_path.name} appears to lack header/separator "
                f"(chunk_id={child['metadata']['chunk_id']}): first lines={lines[:3]!r}"
            )


@pytest.mark.parametrize("pdf_path", _USER_PDFS or [None], ids=lambda p: p.name if p else "no-pdfs")
def test_header_attached_to_body(pdf_path):
    if pdf_path is None:
        pytest.skip("no user PDFs dropped into backend/tests/fixtures/pdfs/ yet — see README")
    children, _parents = chunk_pages(
        extract_pdf_pages(str(pdf_path)),
        document_id=f"sc1-{pdf_path.stem}",
        source_path=str(pdf_path),
    )

    # No orphan prose chunks (a 1-2 word chunk usually means a header floated alone).
    for child in children:
        if child["metadata"].get("kind") != "prose":
            continue
        word_count = len(child["text"].split())
        assert word_count > 5, (
            f"orphan/tiny prose chunk in {pdf_path.name} "
            f"(chunk_id={child['metadata']['chunk_id']}, words={word_count}): "
            f"{child['text']!r}"
        )

    # Every non-`page-*` parent_ref must own at least 100 chars of text across
    # its children — proves the header→body relationship survives chunking.
    by_parent: dict[str, int] = {}
    for child in children:
        ref = child["metadata"].get("parent_ref")
        if not ref or ref.startswith("page-"):
            continue
        by_parent[ref] = by_parent.get(ref, 0) + len(child["text"])
    for ref, total_chars in by_parent.items():
        assert total_chars > 100, (
            f"parent {ref} in {pdf_path.name} has only {total_chars} chars across its "
            f"children — header likely orphaned from its body (SC1 / D-04 violation)"
        )
