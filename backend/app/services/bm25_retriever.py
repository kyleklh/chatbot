import re
from typing import Any

from rank_bm25 import BM25Okapi

from app.services.vector_store import collection

_bm25: BM25Okapi | None = None
_chunks: list[dict[str, Any]] = []


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def rebuild_index() -> None:
    global _bm25, _chunks
    results = collection.get()
    ids = results.get("ids") or []
    documents = results.get("documents") or []
    metadatas = results.get("metadatas") or []
    _chunks = [
        {"id": i, "text": d, "tokens": _tokenize(d), "metadata": m}
        for i, d, m in zip(ids, documents, metadatas)
    ]
    _bm25 = BM25Okapi([c["tokens"] for c in _chunks]) if _chunks else None


def search_bm25(query: str, top_k: int, document_id: str | None = None) -> list[dict[str, Any]]:
    if _bm25 is None or not _chunks:
        return []
    scores = _bm25.get_scores(_tokenize(query))
    candidates = [
        (chunk, float(score))
        for chunk, score in zip(_chunks, scores)
        if score > 0
        and (document_id is None or chunk["metadata"].get("document_id") == document_id)
    ]
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [
        {
            "text": c["text"],
            "metadata": c["metadata"],
            "filename": c["metadata"]["file_name"],
            "page": c["metadata"]["page"],
            "distance": None,
        }
        for c, _ in candidates[:top_k]
    ]


rebuild_index()
