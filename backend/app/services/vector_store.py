import chromadb
from typing import Any, TypedDict, cast
from app.config import CHROMA_DIR, CHROMA_COLLECTION_NAME

client = chromadb.PersistentClient(path=CHROMA_DIR)

collection = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
_parents_collection = client.get_or_create_collection(name="docurag_parents")


class Chunk(TypedDict, total=False):
    text: str
    page: int | str
    embed_text: str
    chunk_id: str
    parent_ref: str
    kind: str
    metadata: dict[str, Any]


def add_chunks(
    document_id: str,
    file_name: str,
    children: list[Chunk],
    parents: list[Chunk],
    child_embeddings: list[list[float]],
    *,
    skip_bm25_rebuild: bool = False,
) -> None:
    """Persist a hierarchical chunk batch.

    Children → main collection, keyed by `chunk_id` (replaces legacy positional
    `{document_id}_{index}` ids). Parents → `docurag_parents` collection with
    zero-vector embeddings (parents are fetched by id, never queried by
    similarity — RESEARCH Open Question #3).

    `skip_bm25_rebuild=True` is used by the startup re-index migration (Plan 06)
    to avoid rebuilding the BM25 index once per document during a bulk replay.
    """
    if not children and not parents:
        return

    # Children: pull metadata off each chunk; ensure file_name is recorded so
    # downstream consumers (get_all_documents, search_chunks) keep working.
    child_ids: list[str] = []
    child_docs: list[str] = []
    child_metas: list[dict[str, Any]] = []
    for chunk in children:
        meta = dict(chunk.get("metadata") or {})
        meta.setdefault("file_name", file_name)
        cid = meta.get("chunk_id")
        if not cid:
            raise ValueError("Child chunk missing chunk_id in metadata")
        child_ids.append(str(cid))
        child_docs.append(chunk.get("text") or "")
        child_metas.append(meta)

    if child_ids:
        collection.add(
            ids=child_ids,
            documents=child_docs,
            metadatas=cast(Any, child_metas),
            embeddings=cast(Any, child_embeddings),
        )

    # Parents: write to the parent collection with placeholder zero-vectors.
    parent_ids: list[str] = []
    parent_docs: list[str] = []
    parent_metas: list[dict[str, Any]] = []
    for chunk in parents:
        meta = dict(chunk.get("metadata") or {})
        meta.setdefault("file_name", file_name)
        pid = meta.get("chunk_id")
        if not pid:
            raise ValueError("Parent chunk missing chunk_id in metadata")
        parent_ids.append(str(pid))
        parent_docs.append(chunk.get("text") or "")
        parent_metas.append(meta)

    if parent_ids:
        dim = len(child_embeddings[0]) if child_embeddings else 0
        zero_vec = [0.0] * dim
        _parents_collection.add(
            ids=parent_ids,
            documents=parent_docs,
            metadatas=cast(Any, parent_metas),
            embeddings=cast(Any, [zero_vec] * len(parent_ids)) if dim else None,
        )

    if not skip_bm25_rebuild:
        from app.services import bm25_retriever
        bm25_retriever.rebuild_index()


def parent_lookup(parent_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch parent chunks by id from `docurag_parents`.

    Returns a dict keyed by chunk_id: {"text": str, "metadata": dict}. Missing
    ids are simply absent from the returned dict.
    """
    if not parent_ids:
        return {}
    results = _parents_collection.get(ids=parent_ids, include=["documents", "metadatas"])
    out: dict[str, dict[str, Any]] = {}
    ids = cast(list, results.get("ids")) or []
    docs = cast(list, results.get("documents")) or []
    metas = cast(list, results.get("metadatas")) or []
    for i, doc, meta in zip(ids, docs, metas):
        out[str(i)] = {"text": doc or "", "metadata": cast(dict, meta) or {}}
    return out


def search_chunks(
    query_embedding: list[float],
    top_k: int = 5,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = {
        "query_embeddings": cast(Any, [query_embedding]),
        "n_results": top_k,
    }
    if document_id:
        kwargs["where"] = {"document_id": document_id}
    elif document_ids:
        kwargs["where"] = {"document_id": {"$in": document_ids}}
    results = collection.query(**kwargs)

    sources: list[dict[str, Any]] = []

    documents = cast(list, results.get("documents")) or [[]]
    metadatas = cast(list, results.get("metadatas")) or [[]]
    distances = cast(list, results.get("distances")) or [[]]

    if not documents or not metadatas or not distances:
        return sources

    documents = documents[0]
    metadatas = metadatas[0]
    distances = distances[0]

    for text, metadata, distance in zip(documents, metadatas, distances):
        sources.append({
            "text": text,
            "metadata": metadata,
            "filename": metadata["file_name"],
            "page": metadata["page"],
            "chunk_id": metadata.get("chunk_id"),
            "distance": distance
        })

    return sources


def get_all_documents() -> list[dict[str, Any]]:
    """Document inventory derived from the CHILD collection only.

    Parents do NOT contribute to `chunk_count` — that count reflects the
    retrieval-visible child chunks (RESEARCH Open Question #2).
    """
    results = collection.get()

    documents: dict[str, dict[str, Any]] = {}

    metadatas_list = cast(list, results.get("metadatas")) or []
    for metadata in metadatas_list:
        metadata = cast(dict[str, Any], metadata)
        document_id = metadata.get("document_id")
        if not document_id:
            continue
        key = str(document_id)
        entry = documents.get(key)
        if entry is None:
            documents[key] = {
                "document_id": document_id,
                "file_name": metadata.get("file_name"),
                "chunk_count": 1,
                "indexed_at": metadata.get("indexed_at"),
            }
        else:
            entry["chunk_count"] += 1
            existing_ts = entry.get("indexed_at")
            new_ts = metadata.get("indexed_at")
            if existing_ts is None and new_ts is not None:
                entry["indexed_at"] = new_ts

    return list(documents.values())


def find_document_by_filename(file_name: str) -> dict[str, Any] | None:
    results = collection.get(where={"file_name": file_name}, include=["metadatas"])
    metadatas_list = cast(list, results.get("metadatas")) or []
    if not metadatas_list:
        return None
    meta = cast(dict[str, Any], metadatas_list[0])
    return {"document_id": meta.get("document_id"), "file_name": meta.get("file_name")}


def delete_document(document_id: str) -> None:
    collection.delete(where={"document_id": document_id})
    _parents_collection.delete(where={"document_id": document_id})

    from app.services import bm25_retriever
    bm25_retriever.rebuild_index()
