"""Parent-expansion retrieval node integration test (Plan 01-05).

Verifies SC3: retrieval can fetch a small chunk and expand to its parent
section for the LLM context window, while preserving child chunk_ids as
citation identity.

Strategy: call `expand_to_parents_node` directly with a hand-built state so
we don't have to run the full LangGraph (which would require Groq). The
parent collection is seeded via the public `vector_store.add_chunks` API
with deterministic ids; the node should fetch parents via
`vector_store.parent_lookup`, dedupe by parent_ref, and produce a
parent-text context.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.services import vector_store
from app.services.langgraph_rag import expand_to_parents_node


def _child(chunk_id: str, parent_ref: str, page: int, file_name: str = "demo.pdf") -> dict[str, Any]:
    return {
        "text": f"child-text-{chunk_id}",
        "filename": file_name,
        "page": page,
        "metadata": {
            "chunk_id": chunk_id,
            "document_id": "docA",
            "parent_ref": parent_ref,
            "page": page,
            "kind": "prose",
            "chunker_version": "v2-2026-05",
            "indexed_at": 1715472000,
            "file_name": file_name,
        },
        "distance": 0.1,
    }


@pytest.fixture
def seeded_parents(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Seed two parents in the docurag_parents collection and clean up after."""
    parent_texts = {
        "p1": "Parent ONE — long section text about alpha. " * 20,
        "p2": "Parent TWO — long section text about beta. " * 20,
    }
    # Insert via the parents collection directly (zero-vec embeddings).
    dim = 1  # placeholder; parents are fetched by id, not similarity
    vector_store._parents_collection.add(
        ids=list(parent_texts.keys()),
        documents=list(parent_texts.values()),
        metadatas=[
            {"chunk_id": pid, "document_id": "docA", "kind": "parent", "file_name": "demo.pdf"}
            for pid in parent_texts
        ],
        embeddings=[[0.0] * dim for _ in parent_texts],
    )
    yield parent_texts
    # Cleanup
    vector_store._parents_collection.delete(ids=list(parent_texts.keys()))


def _state_with(filtered_sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "document_id": "docA",
        "document_ids": None,
        "original_question": "q",
        "rewritten_question": "q",
        "sources": filtered_sources,
        "filtered_sources": filtered_sources,
        "context": "child-context-fallback",
        "answer": "",
        "history": [],
    }


def test_retrieval_parent_expansion(seeded_parents: dict[str, str]) -> None:
    # Three children, two of which share parent p1 (must dedupe in context).
    c_a = _child("c-a", parent_ref="p1", page=1)
    c_b = _child("c-b", parent_ref="p1", page=1)
    c_c = _child("c-c", parent_ref="p2", page=2)

    # Count parent_lookup invocations to assert single-call batching.
    call_count = {"n": 0, "last_ids": None}
    orig = vector_store.parent_lookup

    def counting_lookup(ids: list[str]) -> dict[str, Any]:
        call_count["n"] += 1
        call_count["last_ids"] = sorted(ids)
        return orig(ids)

    import app.services.langgraph_rag as lg
    original_lookup = lg.parent_lookup  # type: ignore[attr-defined]
    lg.parent_lookup = counting_lookup  # type: ignore[attr-defined]
    try:
        new_state = expand_to_parents_node(_state_with([c_a, c_b, c_c]))
    finally:
        lg.parent_lookup = original_lookup  # type: ignore[attr-defined]

    # Context now contains parent text, NOT child text.
    assert "Parent ONE" in new_state["context"]
    assert "Parent TWO" in new_state["context"]
    assert "child-text-c-a" not in new_state["context"]

    # Dedupe: parent p1 appears exactly once even though two children cite it.
    assert new_state["context"].count("Parent ONE") == 20  # text is repeated 20x within the single parent text
    # Stricter dedupe assertion: only one Source-N block for parent p1.
    assert new_state["context"].count("[Source 1]") == 1
    assert new_state["context"].count("[Source 3]") == 1  # c-c is the 3rd child → its parent block uses index 3

    # Single batched lookup for the distinct parent_refs.
    assert call_count["n"] == 1
    assert call_count["last_ids"] == ["p1", "p2"]

    # Citation identity preserved on every filtered_source.
    cids = [s["metadata"]["chunk_id"] for s in new_state["filtered_sources"]]
    assert cids == ["c-a", "c-b", "c-c"]


def test_expand_node_with_no_parent_refs() -> None:
    """If no children have parent_ref, the node returns state unchanged."""
    bare = {**_child("c-x", parent_ref="", page=1)}
    bare["metadata"] = {k: v for k, v in bare["metadata"].items() if k != "parent_ref"}
    state = _state_with([bare])
    new_state = expand_to_parents_node(state)
    assert new_state["context"] == "child-context-fallback"


def test_expand_node_tolerates_missing_parent(seeded_parents: dict[str, str]) -> None:
    """If a parent_ref doesn't resolve, fall back to that child's own text."""
    c_missing = _child("c-m", parent_ref="p-nonexistent", page=5)
    c_ok = _child("c-ok", parent_ref="p1", page=1)
    new_state = expand_to_parents_node(_state_with([c_missing, c_ok]))
    # Missing parent → child text used as the source block.
    assert "child-text-c-m" in new_state["context"]
    # Resolved parent → parent text used.
    assert "Parent ONE" in new_state["context"]
