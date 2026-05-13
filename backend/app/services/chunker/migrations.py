"""Startup re-index migration for the Phase 1 chunker rebuild (D-09).

On first boot after the chunker version bump, every document in Chroma whose
chunks lack the new `chunker_version` metadata is re-extracted via the new
pipeline and re-added with the full new metadata schema (chunk_id, parent_ref,
page, chunker_version, indexed_at).

Wired into FastAPI's lifespan (see `app.main`) so the scan runs BEFORE the
upload route binds — that's the only way to avoid a concurrent-ingestion race
where a fresh /upload could land mid-rescan (Pitfall 4).

Idempotent: subsequent boots find no stale docs and return early.

`UPLOAD_DIR` is read lazily inside the function so tests can monkeypatch
`app.config.UPLOAD_DIR` (or the symbol bound in this module) without paying
the price of an import-time capture.
"""
from __future__ import annotations

import os
from typing import Any

from app.config import UPLOAD_DIR  # noqa: F401  (bound here so tests can monkeypatch this module)
from app.services import bm25_retriever, vector_store
from app.services.chunker import chunk_pages
from app.services.chunker.ids import CHUNKER_VERSION
from app.services.embeddings import embed_texts
from app.services.pdf_loader import extract_pdf_pages


def _expected_file_path(document_id: str, file_name: str) -> str:
    safe = (file_name or "").replace(" ", "_")
    return os.path.join(UPLOAD_DIR, f"{document_id}_{safe}")


def run_migration_scan_on_boot() -> dict[str, Any]:
    """Re-index any document whose chunks lack the current CHUNKER_VERSION.

    Returns a summary dict:
      {scanned: int, reindexed: int, skipped_missing_file: int, errors: list[str]}
    """
    summary: dict[str, Any] = {
        "scanned": 0,
        "reindexed": 0,
        "skipped_missing_file": 0,
        "errors": [],
    }

    try:
        all_meta = vector_store.collection.get(include=["metadatas"])
    except Exception as exc:
        summary["errors"].append(f"collection.get failed: {exc!r}")
        return summary

    metas_list = all_meta.get("metadatas") or []

    # Group: document_id -> (latest seen chunker_version, file_name).
    by_doc: dict[str, dict[str, Any]] = {}
    for m in metas_list:
        if not isinstance(m, dict):
            continue
        doc_id = m.get("document_id")
        if not doc_id:
            continue
        doc_id = str(doc_id)
        entry = by_doc.setdefault(
            doc_id,
            {"version": None, "file_name": None},
        )
        # Prefer a non-empty file_name when we encounter one.
        if not entry["file_name"]:
            entry["file_name"] = m.get("file_name")
        v = m.get("chunker_version")
        # Keep the highest-priority observation; current version wins.
        if v == CHUNKER_VERSION:
            entry["version"] = CHUNKER_VERSION
        elif entry["version"] is None:
            entry["version"] = v

    stale: list[tuple[str, str]] = [
        (doc_id, info["file_name"] or "")
        for doc_id, info in by_doc.items()
        if info["version"] != CHUNKER_VERSION
    ]
    summary["scanned"] = len(by_doc)

    if not stale:
        return summary

    for doc_id, file_name in stale:
        path = _expected_file_path(doc_id, file_name)
        if not file_name or not os.path.isfile(path):
            summary["skipped_missing_file"] += 1
            continue

        try:
            pages = extract_pdf_pages(path)
            children, parents = chunk_pages(
                pages,
                document_id=doc_id,
                source_path=path,
                file_name=file_name,
            )
            if not children:
                summary["errors"].append(f"{doc_id}: no children extracted; left as-is")
                continue

            # Wipe legacy rows for this document from both collections before
            # re-adding under the new schema (text shape changed; embeddings
            # must be regenerated — `update()` won't cut it).
            try:
                vector_store.collection.delete(where={"document_id": doc_id})
            except Exception as exc:
                summary["errors"].append(f"{doc_id}: child delete failed: {exc!r}")
                continue
            try:
                vector_store._parents_collection.delete(where={"document_id": doc_id})
            except Exception:
                # Parents collection may legitimately have no rows for this doc on first migration.
                pass

            embed_source = [c.get("embed_text") or c.get("text", "") for c in children]
            embeddings = embed_texts(embed_source)
            vector_store.add_chunks(
                document_id=doc_id,
                file_name=file_name,
                children=children,
                parents=parents,
                child_embeddings=embeddings,
                skip_bm25_rebuild=True,
            )
            summary["reindexed"] += 1
        except Exception as exc:
            summary["errors"].append(f"{doc_id}: re-index failed: {exc!r}")

    # Single rebuild for the whole scan (Pitfall 5).
    try:
        bm25_retriever.rebuild_index()
    except Exception as exc:
        summary["errors"].append(f"bm25 rebuild failed: {exc!r}")

    return summary
