"""Stable content-derived chunk_id derivation (D-10).

`make_chunk_id` returns a 12 hex char (48-bit) id derived from
sha256(document_id + "\\x1f" + section_path + "\\x1f" + chunk_text).

CHUNKER_VERSION is exported here as a stable version label for metadata
but is intentionally NOT part of the hash input: chunk ids must survive
chunker version bumps as long as content alignment holds (D-10). This
keeps citations stored in conversation history valid across re-indexes.

Collision math (per RESEARCH § "Pattern 3"): a 48-bit truncated SHA-256
gives a ~7e-7 collision probability at v1 scale. If/when scale grows,
bump ID_LEN_HEX to 16 (64 bits) — callers that read the value via the
constant will adjust automatically.
"""
from __future__ import annotations

import hashlib

CHUNKER_VERSION: str = "v2-2026-05"
ID_LEN_HEX: int = 12  # 48-bit space; see RESEARCH § "Pattern 3"

_SEP = "\x1f"  # ASCII unit-separator; cannot appear inside any of the three fields


def make_chunk_id(
    document_id: str,
    section_path: str,
    chunk_text: str,
    *,
    occurrence: int = 0,
) -> str:
    """Return a deterministic 12-hex-char chunk id for the given content.

    The id is content-derived: identical (document_id, section_path, chunk_text,
    occurrence) always produces the same id. CHUNKER_VERSION is intentionally
    excluded so that ids survive chunker version bumps when the underlying
    content does not change.

    `occurrence` disambiguates legitimately repeated text within a single
    section (observed in Apple's 10-K: identical RSU Award Agreement clauses
    appear up to 4x under the same H1/H2 path; both auditor reports open with
    the same line). When `occurrence == 0` the hash input is unchanged for
    backward compatibility — any PDF without intra-section duplicates produces
    identical ids before and after this parameter was added. The assembler
    increments `occurrence` only for the 2nd, 3rd, ... appearance of the same
    (section_path, text) tuple within one document, so stability across
    reindexes holds whenever chunker output ordering is deterministic.
    """
    if occurrence == 0:
        payload = (document_id + _SEP + section_path + _SEP + chunk_text).encode("utf-8")
    else:
        payload = (
            document_id + _SEP + section_path + _SEP + str(occurrence) + _SEP + chunk_text
        ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:ID_LEN_HEX]
