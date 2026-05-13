"""Startup re-index migration test (Plan 01-06).

Seeds the `vector_store.collection` with legacy-format chunks (no chunk_id /
parent_ref / chunker_version) for a synthetic PDF, then calls
`run_migration_scan_on_boot()` and asserts:

- All chunks for the document end up at the new CHUNKER_VERSION.
- The legacy positional ids are gone.
- The second invocation is a no-op (idempotent).
- BM25 rebuild was invoked exactly ONCE across the whole migration
  (Pitfall 5 — never N+1 in the scan loop).
- A missing source file does not crash; it increments `skipped_missing_file`.

The test monkeypatches `vector_store.collection`, `vector_store._parents_collection`,
and `UPLOAD_DIR` so the real on-disk Chroma + uploads directory are not touched.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

import chromadb
import pytest

from app.services import vector_store
from app.services.chunker.ids import CHUNKER_VERSION


def _legacy_metadata(document_id: str, file_name: str, page: int, index: int) -> dict[str, Any]:
    """Build a metadata dict shaped like the pre-Phase-1 chunker emitted."""
    return {
        "document_id": document_id,
        "file_name": file_name,
        "page": page,
        "chunk_index": index,
        "indexed_at": 1700000000,
    }


def _seed_legacy(coll, document_id: str, file_name: str, n_chunks: int = 3, dim: int = 8) -> list[str]:
    ids = [f"{document_id}_{i}" for i in range(n_chunks)]
    docs = [f"legacy chunk {i} body text" for i in range(n_chunks)]
    metas = [_legacy_metadata(document_id, file_name, page=1, index=i) for i in range(n_chunks)]
    embs = [[0.1] * dim for _ in range(n_chunks)]
    coll.add(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
    return ids


@pytest.fixture
def migration_env(tmp_path: Path, synthetic_pdf: Path, monkeypatch: pytest.MonkeyPatch):
    """Swap vector_store collections for ephemeral ones and redirect UPLOAD_DIR.

    Yields (collection, parents_collection, upload_dir, document_id, file_name).
    """
    client = chromadb.EphemeralClient()
    fake_children = client.create_collection(name="test_children")
    fake_parents = client.create_collection(name="test_parents")

    monkeypatch.setattr(vector_store, "collection", fake_children)
    monkeypatch.setattr(vector_store, "_parents_collection", fake_parents)

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    # Copy synthetic_pdf into UPLOAD_DIR using the route's naming convention.
    document_id = "doc-mig-1"
    file_name = "synthetic.pdf"
    safe = file_name.replace(" ", "_")
    target = upload_dir / f"{document_id}_{safe}"
    shutil.copy(synthetic_pdf, target)

    # migrations.py reads UPLOAD_DIR from app.config; redirect that.
    import app.config as cfg
    monkeypatch.setattr(cfg, "UPLOAD_DIR", str(upload_dir))
    # migrations.py may import the symbol directly — patch there too if present.
    try:
        import app.services.chunker.migrations as mig
        monkeypatch.setattr(mig, "UPLOAD_DIR", str(upload_dir), raising=False)
    except ImportError:
        pass

    yield fake_children, fake_parents, upload_dir, document_id, file_name


def test_migration_reindex(migration_env, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_children, fake_parents, upload_dir, document_id, file_name = migration_env
    legacy_ids = _seed_legacy(fake_children, document_id, file_name, n_chunks=3)

    # Count bm25 rebuilds — must be exactly once across the whole scan.
    rebuild_calls = {"n": 0}

    def _counting_rebuild():
        rebuild_calls["n"] += 1

    import app.services.bm25_retriever as bm25_mod
    monkeypatch.setattr(bm25_mod, "rebuild_index", _counting_rebuild)
    # Some callers import via 'from ... import bm25_retriever' — patch the
    # module reference inside migrations on demand.
    import app.services.chunker.migrations as mig
    monkeypatch.setattr(mig.bm25_retriever, "rebuild_index", _counting_rebuild)

    # Patch embed_texts to a deterministic zero-cost stub so we don't load the
    # real embedding model during this test.
    def _fake_embed(texts: list[str]) -> list[list[float]]:
        return [[0.0] * 8 for _ in texts]
    monkeypatch.setattr(mig, "embed_texts", _fake_embed)

    from app.services.chunker.migrations import run_migration_scan_on_boot

    summary = run_migration_scan_on_boot()
    assert summary["scanned"] >= 1
    assert summary["reindexed"] >= 1
    assert summary["skipped_missing_file"] == 0
    # Single rebuild for the whole scan, not per-document.
    assert rebuild_calls["n"] == 1, f"BM25 rebuild called {rebuild_calls['n']}x, expected 1"

    # All children now carry the new schema.
    post = fake_children.get(where={"document_id": document_id}, include=["metadatas"])
    metas = post.get("metadatas") or []
    assert metas, "expected re-indexed children to be present"
    for m in metas:
        assert m.get("chunker_version") == CHUNKER_VERSION, m
        assert m.get("chunk_id"), m
        assert m.get("parent_ref"), m

    # Legacy positional ids are gone.
    new_ids = set(post.get("ids") or [])
    assert not (set(legacy_ids) & new_ids), "legacy positional ids should have been deleted"

    # Idempotent: second call re-scans, finds nothing stale, reindexes nothing.
    rebuild_calls["n"] = 0
    summary2 = run_migration_scan_on_boot()
    assert summary2["reindexed"] == 0
    # Idempotent run still calls rebuild ONCE at the end (or zero — both valid).
    assert rebuild_calls["n"] <= 1


def test_migration_skips_missing_file(migration_env, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_children, _, upload_dir, document_id, file_name = migration_env
    _seed_legacy(fake_children, document_id, file_name, n_chunks=2)
    # Remove the source file so the migration must handle the gap.
    safe = file_name.replace(" ", "_")
    (upload_dir / f"{document_id}_{safe}").unlink()

    import app.services.bm25_retriever as bm25_mod
    monkeypatch.setattr(bm25_mod, "rebuild_index", lambda: None)
    import app.services.chunker.migrations as mig
    monkeypatch.setattr(mig.bm25_retriever, "rebuild_index", lambda: None)
    monkeypatch.setattr(mig, "embed_texts", lambda texts: [[0.0] * 8 for _ in texts])

    summary = mig.run_migration_scan_on_boot()
    assert summary["skipped_missing_file"] == 1
    assert summary["reindexed"] == 0
