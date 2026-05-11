import time
import chromadb
from typing import Any, TypedDict, cast
from app.config import CHROMA_DIR, CHROMA_COLLECTION_NAME

client = chromadb.PersistentClient(path=CHROMA_DIR)

collection = client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)


class Chunk(TypedDict):
    text: str
    page: int


def add_chunks(
    document_id: str,
    file_name: str,
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> None:
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    indexed_at = int(time.time())

    for index, chunk in enumerate(chunks):
        ids.append(f"{document_id}_{index}")
        documents.append(chunk["text"])
        metadatas.append({
            "document_id": document_id,
            "file_name": file_name,
            "page": chunk["page"],
            "chunk_index": index,
            "indexed_at": indexed_at,
        })
        
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=cast(Any, metadatas),
        embeddings=cast(Any, embeddings),
    )

    from app.services import bm25_retriever
    bm25_retriever.rebuild_index()

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
            "distance": distance
        })
    
    return sources

def get_all_documents() -> list[dict[str, Any]]:
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
    collection.delete(
        where={"document_id": document_id}
    )

    from app.services import bm25_retriever
    bm25_retriever.rebuild_index()
