from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.services.embeddings import embed_texts
from app.services.vector_store import search_chunks
from app.services.ollama_client import generate_with_ollama


class RAGState(TypedDict):
    document_id: str | None
    original_question: str
    rewritten_question: str
    sources: list[dict[str, Any]]
    filtered_sources: list[dict[str, Any]]
    context: str
    answer: str


def rewrite_question_node(state: RAGState) -> RAGState:
    prompt = f"""
Rewrite the user's question into a clear standalone search query.

Rules:
- Keep the original meaning.
- Do not answer the question.
- Do not add facts.
- Make it short and specific.

Original question:
{state["original_question"]}

Rewritten search query:
"""

    rewritten = generate_with_ollama(prompt).strip()

    if not rewritten:
        rewritten = state["original_question"]

    return {
        **state,
        "rewritten_question": rewritten,
    }


def retrieve_node(state: RAGState) -> RAGState:
    query_embedding = embed_texts([state["rewritten_question"]])[0]

    sources = search_chunks(
        query_embedding=query_embedding,
        top_k=8,
        document_id=state["document_id"],
    )

    return {
        **state,
        "sources": sources,
    }


def filter_sources_node(state: RAGState) -> RAGState:
    sources = state["sources"]

    if not sources:
        return {
            **state,
            "filtered_sources": [],
            "context": "",
        }

    # Chroma distance thresholds depend on your embedding setup.
    # Start loose, then tune after testing.
    max_distance = 1.3

    filtered_sources = [
        source for source in sources
        if source.get("distance") is None or source["distance"] <= max_distance
    ]

    # Fallback: if threshold removes everything, keep the top 3
    if not filtered_sources:
        filtered_sources = sources[:3]

    context_parts: list[str] = []

    for index, source in enumerate(filtered_sources[:5]):
        context_parts.append(
            f"[Source {index + 1} | Page {source['metadata']['page']} | File: {source['filename']}]\n"
            f"{source['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    return {
        **state,
        "filtered_sources": filtered_sources[:5],
        "context": context,
    }


def should_answer(state: RAGState) -> str:
    if not state["filtered_sources"]:
        return "no_context"

    return "answer"


def no_context_node(state: RAGState) -> RAGState:
    return {
        **state,
        "answer": "I couldn't find that in the uploaded document.",
    }


def answer_node(state: RAGState) -> RAGState:
    prompt = f"""
You are DocuRAG, a document question-answering assistant.

Answer the user's question using ONLY the context below.

Strict rules:
- Use only the provided context.
- Do not use outside knowledge.
- If the context does not contain the answer, say:
  "I couldn't find that in the uploaded document."
- Cite every important claim using [Source 1], [Source 2], etc.
- Be concise but complete.
- If sources disagree, mention that.

Context:
{state["context"]}

User question:
{state["original_question"]}

Answer:
"""

    answer = generate_with_ollama(prompt)

    return {
        **state,
        "answer": answer,
    }


def build_rag_graph():
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("filter_sources", filter_sources_node)
    graph.add_node("no_context", no_context_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("retrieve")

    graph.add_edge("retrieve", "filter_sources")

    graph.add_conditional_edges(
        "filter_sources",
        should_answer,
        {
            "answer": "answer",
            "no_context": "no_context",
        },
    )

    graph.add_edge("answer", END)
    graph.add_edge("no_context", END)

    return graph.compile()


rag_graph = build_rag_graph()


def answer_question_with_graph(document_id: str | None, question: str) -> dict[str, Any]:
    initial_state: RAGState = {
        "document_id": document_id,
        "original_question": question,
        "rewritten_question": question,
        "sources": [],
        "filtered_sources": [],
        "context": "",
        "answer": "",
    }

    result = rag_graph.invoke(initial_state)

    return {
        "answer": result["answer"],
        "sources": result["filtered_sources"],
    }