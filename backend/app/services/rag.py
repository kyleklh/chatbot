from typing import Any
from app.services.embeddings import embed_texts
from app.services.vector_store import search_chunks
from app.services.ollama_client import generate_with_ollama

# With normalized L2 embeddings, cos_sim = 1 - d²/2.
# A distance of 1.0 ≈ cosine similarity of 0.5 — below this the chunk is
# unlikely to be meaningfully relevant to the question.
RELEVANCE_THRESHOLD = 1.0


def build_context(sources: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"[{i + 1} | Page {s['page']}]\n{s['text']}"
        for i, s in enumerate(sources)
    )


def flatten_source(raw: dict[str, Any]) -> dict[str, Any]:
    metadata = raw.get("metadata", {})
    return {
        "text": raw["text"],
        "page": metadata.get("page"),
        "filename": raw.get("filename") or metadata.get("file_name"),
        "distance": raw.get("distance"),
    }


def filter_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        s for s in sources
        if s.get("distance") is None or s["distance"] <= RELEVANCE_THRESHOLD
    ]


NOT_FOUND_PHRASES = [
    "couldn't find",
    "could not find",
    "not in the",
    "not found in",
    "no information",
    "does not contain",
    "not mentioned",
    "not provided",
]


def answer_question(document_id: str, question: str) -> dict[str, Any]:
    query_embedding = embed_texts([question])[0]

    # Fetch extra candidates so filtering still leaves enough good sources
    raw_sources = search_chunks(
        document_id=document_id,
        query_embedding=query_embedding,
        top_k=8
    )

    all_sources = [flatten_source(s) for s in raw_sources]
    relevant_sources = filter_sources(all_sources)
    context_sources = relevant_sources if relevant_sources else all_sources[:3]

    context = build_context(context_sources)

    prompt = f"""
You are DocuRAG, a document question-answering assistant.

Use only the provided context to answer the question.

Rules:
- Answer clearly and directly.
- When you use information from a source, cite it inline as [1], [2], [3], etc.
- Only cite sources you actually used.
- If the answer is not in the context, say exactly: "I couldn't find that in the uploaded document."
- Do not use outside knowledge.
- Do not make up details.

Context:
{context}

Question:
{question}

Answer:
"""

    answer = generate_with_ollama(prompt)

    answer_lower = answer.lower()
    model_found_nothing = any(phrase in answer_lower for phrase in NOT_FOUND_PHRASES)

    return {
        "answer": answer,
        "sources": [] if model_found_nothing else context_sources,
    }
