"""Tests for stable content-derived chunk_id derivation (Plan 01-01, D-10)."""
import re

from app.services.chunker.ids import make_chunk_id, CHUNKER_VERSION, ID_LEN_HEX


_HEX_RE = re.compile(r"^[0-9a-f]+$")


def test_stable_hash():
    doc_id = "doc-abc-123"
    section_path = "Chapter 1 > Section A"
    chunk_text = "The quick brown fox jumps over the lazy dog."

    # Deterministic: same inputs → same id across 100 calls.
    first = make_chunk_id(doc_id, section_path, chunk_text)
    for _ in range(100):
        assert make_chunk_id(doc_id, section_path, chunk_text) == first

    # Format: 12 lowercase hex chars.
    assert len(first) == ID_LEN_HEX == 12
    assert _HEX_RE.match(first), f"id {first!r} contains non-hex or uppercase chars"

    # Differing in ANY one of the three inputs produces a different id.
    assert make_chunk_id("doc-different", section_path, chunk_text) != first
    assert make_chunk_id(doc_id, "Chapter 1 > Section B", chunk_text) != first
    assert make_chunk_id(doc_id, section_path, chunk_text + " ") != first

    # CHUNKER_VERSION is exported but MUST NOT be part of the hash input (D-10).
    # We verify by recomputing the hash by hand without the version and confirming
    # it equals make_chunk_id's output.
    import hashlib
    expected = hashlib.sha256(
        (doc_id + "\x1f" + section_path + "\x1f" + chunk_text).encode("utf-8")
    ).hexdigest()[:ID_LEN_HEX]
    assert first == expected
    # CHUNKER_VERSION is still importable and non-empty.
    assert isinstance(CHUNKER_VERSION, str) and CHUNKER_VERSION


def test_no_collision_10k():
    doc_id = "doc-collision-test"
    section_path = "Section/Path"
    ids = {make_chunk_id(doc_id, section_path, f"chunk {i}") for i in range(10_000)}
    assert len(ids) == 10_000
