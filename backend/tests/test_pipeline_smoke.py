"""End-to-end smoke test for the chunking-rebuild pipeline (Plan 01-08).

Drives upload → chunk → embed → ask through a real FastAPI app via
`fastapi.testclient.TestClient`. Groq is the only mocked service; embeddings
run locally via BGE (already installed) and the reranker uses the real
CrossEncoder so we don't accidentally break the retrieval stack.

Covers:
- SC4: happy-path upload+ask survives the rebuild.
- DEC-per-document-filter-chips (LOCKED): the `document_ids: list[str]`
  filter on /chat/stream still excludes other documents post-rebuild.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Generator

import chromadb
import pytest
from fastapi.testclient import TestClient

from app.services import vector_store

# Cross-process module references we may need to patch.
import app.config as cfg
import app.services.langgraph_rag as lg
import app.services.chunker.migrations as mig


def _stub_token_stream(messages):
    """Replacement for stream_with_groq that yields deterministic tokens."""
    yield "Stubbed answer referencing [Source 1] from the uploaded document."


def _stub_generate(*args, **kwargs) -> str:
    return "stubbed-answer"


@pytest.fixture
def hermetic_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Swap CHROMA_DIR, UPLOAD_DIR, and Groq calls; yield a TestClient.

    The lifespan migration runs against an empty ephemeral Chroma — this also
    exercises the "no stale docs" idempotent branch of the migration.
    """
    # Redirect uploads to tmp.
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(cfg, "UPLOAD_DIR", str(upload_dir))
    monkeypatch.setattr(mig, "UPLOAD_DIR", str(upload_dir), raising=False)
    # routes_upload binds UPLOAD_DIR at import time; patch the in-module name.
    import app.api.routes_upload as ru
    monkeypatch.setattr(ru, "UPLOAD_DIR", str(upload_dir), raising=False)

    # Swap Chroma collections to ephemeral copies for full isolation.
    eph_client = chromadb.EphemeralClient()
    suffix = tmp_path.name.replace("-", "")[:20]
    fake_children = eph_client.create_collection(name=f"smoke_children_{suffix}")
    fake_parents = eph_client.create_collection(name=f"smoke_parents_{suffix}")
    monkeypatch.setattr(vector_store, "collection", fake_children)
    monkeypatch.setattr(vector_store, "_parents_collection", fake_parents)
    # bm25_retriever holds a captured reference to the production collection;
    # repoint it too so search_bm25 doesn't query a stale handle.
    import app.services.bm25_retriever as bm25
    monkeypatch.setattr(bm25, "collection", fake_children)

    # Mock Groq. langgraph_rag imported these names — patch them there.
    monkeypatch.setattr(lg, "generate_with_groq", _stub_generate)
    monkeypatch.setattr(lg, "generate_with_messages", _stub_generate)
    monkeypatch.setattr(lg, "stream_with_groq", _stub_token_stream)

    from app.main import app
    with TestClient(app) as client:
        yield client


def _read_stream(resp_iter) -> list[dict]:
    """Parse a streaming SSE body into a list of decoded JSON dicts."""
    events: list[dict] = []
    for raw in resp_iter:
        if not raw:
            continue
        text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
        for line in text.split("\n"):
            line = line.strip()
            if not line.startswith("data: "):
                continue
            payload = line[len("data: "):]
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                continue
    return events


def test_pipeline_smoke(hermetic_app: TestClient, synthetic_pdf: Path) -> None:
    # ---- upload ----------------------------------------------------------
    with synthetic_pdf.open("rb") as fh:
        r = hermetic_app.post(
            "/upload",
            files=[("files", ("smoke.pdf", fh, "application/pdf"))],
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["document_id"], body
    assert body["num_chunks"] >= 1
    doc_id = body["document_id"]

    # ---- ask -------------------------------------------------------------
    with hermetic_app.stream(
        "POST",
        "/chat/stream",
        json={"question": "what is in section A?", "document_id": doc_id, "history": []},
    ) as stream_resp:
        assert stream_resp.status_code == 200
        events = _read_stream(stream_resp.iter_bytes())

    token_events = [e for e in events if "token" in e]
    done_events = [e for e in events if e.get("done") is True]
    assert token_events, f"no streamed tokens; events={events}"
    assert done_events, f"no done event; events={events}"

    sources = done_events[-1].get("sources") or []
    assert sources, "expected non-empty sources[]"
    for s in sources:
        assert s.get("document_id") == doc_id, s
        assert s.get("filename") == "smoke.pdf", s
        assert "page" in s, s


def test_document_ids_filter(hermetic_app: TestClient, synthetic_pdf: Path, tmp_path: Path) -> None:
    """DEC-per-document-filter-chips regression guard.

    Upload two PDFs; ask with `document_ids=[first_doc_id]`; assert no source
    leaks from the second doc.
    """
    pdf_a = tmp_path / "doc_a.pdf"
    pdf_b = tmp_path / "doc_b.pdf"
    shutil.copy(synthetic_pdf, pdf_a)
    shutil.copy(synthetic_pdf, pdf_b)

    def _upload(p: Path) -> str:
        with p.open("rb") as fh:
            r = hermetic_app.post(
                "/upload",
                files=[("files", (p.name, fh, "application/pdf"))],
            )
        assert r.status_code == 200, r.text
        return r.json()["document_id"]

    id_a = _upload(pdf_a)
    id_b = _upload(pdf_b)
    assert id_a != id_b

    with hermetic_app.stream(
        "POST",
        "/chat/stream",
        json={
            "question": "what is in section A?",
            "document_ids": [id_a],
            "history": [],
        },
    ) as stream_resp:
        assert stream_resp.status_code == 200
        events = _read_stream(stream_resp.iter_bytes())

    done = [e for e in events if e.get("done") is True]
    assert done, f"no done event; events={events}"
    sources = done[-1].get("sources") or []
    assert sources, "expected non-empty sources[] for the filtered doc"
    for s in sources:
        assert s["document_id"] == id_a, (
            f"document_ids filter leaked: source has document_id={s['document_id']!r}, "
            f"expected only {id_a!r} (DEC-per-document-filter-chips)"
        )
