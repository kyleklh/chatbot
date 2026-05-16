"""End-to-end smoke test for the chunking-rebuild pipeline (Plan 01-08).

Drives upload → chunk → embed → ask through a real FastAPI app via
`fastapi.testclient.TestClient`. The LLM provider is the only mocked
service; embeddings run locally via BGE (already installed) and the
reranker uses the real CrossEncoder so we don't accidentally break the
retrieval stack.

Covers:
- SC4: happy-path upload+ask survives the rebuild.
- SC1 (Plan 02-03): canonical ``[N]`` markers stream during generation —
  appear in ``{"token": ...}`` SSE events BEFORE the ``done`` event
  (selectable via ``-k stream_marker``).
- SC2/SC3 integration (Plan 02-03): the final ``done`` event validates
  through ``DoneEvent.model_validate``; every Source carries non-empty
  ``chunk_id``, ``document_id``, ``page``, ``quote``; ``marker_map`` is
  present and every value is a chunk_id present in ``sources``.
- SC5 (Plan 02-03) / DEC-per-document-filter-chips: the ``document_ids``
  filter still excludes other documents post-rebuild AND every cited
  chunk's ``document_id`` (via ``marker_map`` → ``done.sources``) is
  inside the requested filter.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Generator, Iterator

import chromadb
import pytest
from fastapi.testclient import TestClient

from app.services import vector_store
from app.models.schemas import DoneEvent

# Cross-process module references we may need to patch.
import app.config as cfg
import app.services.langgraph_rag as lg
import app.services.chunker.migrations as mig


# The fake provider's stream() yields tokens that exercise every parser path:
# - canonical `[1]` (resolvable, kept as `[1]`)
# - drift `[Source 2]` (normalized to `[2]`)
# - compound `[1, 2]` (expanded to `[1][2]`)
# - unresolvable `[9]` (stripped + print()-logged via D-03)
_FAKE_STREAM_TOKENS: list[str] = [
    "Section A introduces the topic ",
    "[1]",
    " and the subsection elaborates ",
    "[Source 2]",
    ". Combined evidence supports the claim ",
    "[1, 2]",
    ". An invented citation ",
    "[9]",
    " should disappear from the output.",
]


class _FakeProvider:
    """Deterministic LLMProvider stand-in for the smoke test.

    Implements the 3-method surface of ``app.services.llm.base.LLMProvider``
    so it satisfies the ``@runtime_checkable`` Protocol. ``stream`` yields
    answer-text fragments containing canonical, drift, compound, and
    unresolvable markers to exercise the parser's normalize/strip paths
    (D-01/D-03).
    """

    def stream(self, messages: list[dict]) -> Iterator[str]:
        for tok in _FAKE_STREAM_TOKENS:
            yield tok

    def generate(self, messages: list[dict]) -> str:
        return "stubbed-answer referencing [1]."

    def token_count(self, text: str) -> int:
        return max(1, len(text) // 4)


def _fake_get_provider() -> _FakeProvider:
    return _FakeProvider()


@pytest.fixture
def hermetic_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Swap CHROMA_DIR, UPLOAD_DIR, and the LLM provider; yield a TestClient.

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
    # Chroma collection names must be 3-512 chars of [a-zA-Z0-9._-] and start
    # AND end with an alphanumeric. Strip trailing punctuation that pytest can
    # leave in `tmp_path.name` (e.g. "test_pipeline_smoke_") and pad if empty.
    raw_suffix = tmp_path.name.replace("-", "")[:20]
    suffix = raw_suffix.strip("._-") or "x"
    fake_children = eph_client.create_collection(name=f"smoke_children_{suffix}")
    fake_parents = eph_client.create_collection(name=f"smoke_parents_{suffix}")
    monkeypatch.setattr(vector_store, "collection", fake_children)
    monkeypatch.setattr(vector_store, "_parents_collection", fake_parents)
    # bm25_retriever holds a captured reference to the production collection;
    # repoint it too so search_bm25 doesn't query a stale handle.
    import app.services.bm25_retriever as bm25
    monkeypatch.setattr(bm25, "collection", fake_children)

    # Patch the provider seam where langgraph_rag resolves it. After Plan
    # 02-03 the graph nodes no longer reference `stream_with_groq` /
    # `generate_with_groq` by name, so the stub must target `get_provider`
    # in the `lg` namespace.
    monkeypatch.setattr(lg, "get_provider", _fake_get_provider)

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


def _has_canonical_marker(text: str) -> bool:
    """True iff `text` contains a canonical discrete `[N]` marker (digits only)."""
    import re

    return re.search(r"\[\d+\]", text) is not None


def test_pipeline_smoke_stream_marker(hermetic_app: TestClient, synthetic_pdf: Path) -> None:
    """SC1 + SC2/SC3 integration.

    Asserts:
    - Upload+ask happy path still works post-rebuild (SC4).
    - A canonical ``[N]`` marker appears in a ``token`` SSE event BEFORE
      the ``done`` event (SC1 — markers stream DURING generation, not
      stitched onto the done event).
    - The last ``done`` event validates through ``DoneEvent.model_validate``.
    - Every Source carries non-empty ``chunk_id``, ``document_id``, ``page``,
      ``quote`` (SC2/SC3 integration).
    - ``marker_map`` is present and every value is a chunk_id present in
      ``sources``.
    """
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

    # SC1: a canonical `[N]` marker must appear in a token event BEFORE the
    # done event in the SSE sequence. Locate the first done index and scan
    # only tokens preceding it.
    done_idx = next(i for i, e in enumerate(events) if e.get("done") is True)
    pre_done_token_texts = [
        e["token"] for e in events[:done_idx] if "token" in e
    ]
    joined_pre_done = "".join(pre_done_token_texts)
    assert _has_canonical_marker(joined_pre_done), (
        f"SC1: expected a canonical `[N]` marker in token events before the done "
        f"event; pre-done token text was {joined_pre_done!r}"
    )

    # The unresolvable `[9]` must have been stripped (D-03) — it should NOT
    # appear in the streamed canonical-marker text.
    assert "[9]" not in joined_pre_done, (
        f"D-03: unresolvable marker `[9]` should have been stripped from "
        f"streamed output; saw {joined_pre_done!r}"
    )

    # SC2/SC3 integration: validate the final done event through DoneEvent.
    done_payload = done_events[-1]
    done_model = DoneEvent.model_validate(done_payload)
    assert done_model.sources, "expected non-empty sources[]"
    for s in done_model.sources:
        assert s.chunk_id, f"source missing chunk_id: {s}"
        assert s.document_id, f"source missing document_id: {s}"
        assert s.page is not None, f"source missing page: {s}"
        assert s.quote, f"source missing quote: {s}"
        # Sanity: smoke fixture uploads a single file named "smoke.pdf".
        assert s.document_id == doc_id, s
        assert s.filename == "smoke.pdf", s

    # `marker_map` present and every value resolves to a chunk_id in sources.
    assert done_model.marker_map, "expected non-empty marker_map"
    known_chunk_ids = {s.chunk_id for s in done_model.sources}
    for marker, chunk_id in done_model.marker_map.items():
        assert chunk_id in known_chunk_ids, (
            f"marker_map[{marker!r}] = {chunk_id!r} not in done.sources chunk_ids "
            f"{sorted(known_chunk_ids)}"
        )


def test_document_ids_filter(hermetic_app: TestClient, synthetic_pdf: Path, tmp_path: Path) -> None:
    """DEC-per-document-filter-chips regression guard + SC5 provenance.

    Upload two PDFs; ask with ``document_ids=[first_doc_id]``;
    1) Assert no source leaks from the second doc (the original
       DEC-per-document-filter-chips invariant).
    2) Assert every cited chunk's ``document_id`` (resolved via
       ``marker_map`` → ``done.sources``) is inside the requested
       ``document_ids`` filter (SC5 citation provenance, Plan 02-03).
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

    # Validate the done payload through DoneEvent so downstream provenance
    # assertions are typed.
    done_model = DoneEvent.model_validate(done[-1])

    sources = done_model.sources
    assert sources, "expected non-empty sources[] for the filtered doc"
    # Original DEC-per-document-filter-chips invariant: no leak.
    for s in sources:
        assert s.document_id == id_a, (
            f"document_ids filter leaked: source has document_id={s.document_id!r}, "
            f"expected only {id_a!r} (DEC-per-document-filter-chips)"
        )

    # SC5 provenance: every CITED chunk (those reachable via marker_map →
    # sources) must have its document_id inside the requested filter.
    requested = {id_a}
    chunk_to_doc = {s.chunk_id: s.document_id for s in sources}
    cited_chunk_ids = set(done_model.marker_map.values())
    # The streamed answer contains resolvable markers (the fake provider
    # injects `[1]`, `[2]`, `[1, 2]`) so marker_map must be non-empty when
    # the underlying retrieval returned >=1 source.
    assert cited_chunk_ids, (
        f"expected at least one cited chunk via marker_map; got "
        f"marker_map={done_model.marker_map!r}"
    )
    for chunk_id in cited_chunk_ids:
        cited_doc = chunk_to_doc.get(chunk_id)
        assert cited_doc in requested, (
            f"SC5 provenance: cited chunk_id={chunk_id!r} has document_id="
            f"{cited_doc!r}, which is outside the requested document_ids "
            f"filter {sorted(requested)}"
        )
