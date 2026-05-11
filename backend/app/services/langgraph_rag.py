import json
from typing import Any, Generator, TypedDict

from langgraph.graph import END, StateGraph

from app.services.embeddings import embed_texts
from app.services.vector_store import search_chunks
from app.services.bm25_retriever import search_bm25
from app.services.groq_client import generate_with_groq, generate_with_messages, stream_with_groq
from app.services.reranker import rerank
from app.config import RAG_TOP_K, RAG_MAX_DISTANCE


def _rrf_merge(*rankings: list[dict[str, Any]], k: int = 60) -> list[dict[str, Any]]:
    scores: dict[tuple, float] = {}
    sources: dict[tuple, dict[str, Any]] = {}
    for ranking in rankings:
        for rank, source in enumerate(ranking):
            key = (source["metadata"]["document_id"], source["metadata"]["chunk_index"])
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            sources[key] = source
    return sorted(
        sources.values(),
        key=lambda s: scores[(s["metadata"]["document_id"], s["metadata"]["chunk_index"])],
        reverse=True,
    )


class RAGState(TypedDict):
    document_id: str | None
    original_question: str
    rewritten_question: str
    sources: list[dict[str, Any]]
    filtered_sources: list[dict[str, Any]]
    context: str
    answer: str
    history: list[dict[str, str]]


def rewrite_question_node(state: RAGState) -> RAGState:
    history = state.get("history", [])
    history_section = ""
    if history:
        recent = history[-4:]
        lines = [f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in recent]
        history_section = "\n\nRecent conversation:\n" + "\n".join(lines) + "\n"

    prompt = f"""Rewrite the user's question into a clear standalone search query.
{history_section}
Rules:
- Resolve any references (it, that, this, the previous topic) using the conversation history if present.
- Keep the original meaning.
- Do not answer the question.
- Do not add facts.
- Make it short and specific.

Original question:
{state["original_question"]}

Rewritten search query:
"""

    try:
        rewritten = generate_with_groq(prompt).strip()
    except Exception:
        rewritten = ""
    if not rewritten:
        rewritten = state["original_question"]

    return {**state, "rewritten_question": rewritten}


def retrieve_node(state: RAGState) -> RAGState:
    rewritten = state["rewritten_question"]
    original = state["original_question"]

    query_embedding = embed_texts([rewritten])[0]
    vector_sources = search_chunks(
        query_embedding=query_embedding,
        top_k=RAG_TOP_K,
        document_id=state["document_id"],
    )
    bm25_sources = search_bm25(
        query=original,
        top_k=RAG_TOP_K,
        document_id=state["document_id"],
    )

    sources = _rrf_merge(vector_sources, bm25_sources)
    return {**state, "sources": sources}


def filter_sources_node(state: RAGState) -> RAGState:
    sources = state["sources"]

    if not sources:
        return {**state, "filtered_sources": [], "context": ""}

    max_distance = RAG_MAX_DISTANCE
    filtered_sources = [s for s in sources if s.get("distance") is None or s["distance"] <= max_distance]

    if not filtered_sources:
        filtered_sources = sources[:3]

    filtered_sources = rerank(state["original_question"], filtered_sources)

    context_parts: list[str] = []
    for index, source in enumerate(filtered_sources):
        context_parts.append(
            f"[Source {index + 1}] (Page {source['metadata']['page']}, {source['filename']})\n"
            f"{source['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    return {**state, "filtered_sources": filtered_sources, "context": context}


def should_answer(state: RAGState) -> str:
    return "no_context" if not state["filtered_sources"] else "answer"


def no_context_node(state: RAGState) -> RAGState:
    return {**state, "answer": "I couldn't find that in the uploaded document."}


def _build_answer_messages(state: RAGState) -> list[dict]:
    system_prompt = (
        "You are DocuRAG, a document question-answering assistant.\n\n"
        "Strict rules:\n"
        "- Use only the provided context.\n"
        "- Do not use outside knowledge.\n"
        "- If the context does not contain the answer, say: \"I couldn't find that in the uploaded document.\"\n"
        "- Cite every important claim using [Source 1], [Source 2], etc.\n"
        "\n"
        "Table rules (CRITICAL — follow exactly):\n"
        "- NEVER embed pipe-separated table data inline in a paragraph. If you write `|`, you MUST be on a new "
        "line and producing a proper markdown table.\n"
        "- If the user asks to show, display, list, or reproduce a table, output the FULL table using markdown "
        "table syntax — header row, separator row of dashes, then one data row per line. Each row on its OWN line.\n"
        "- If the context contains a markdown table (lines starting with |), reproduce it EXACTLY — same columns, "
        "same rows, same order, on separate lines. Do not collapse, merge, or summarize.\n"
        "- If you need to reference data from a table while answering a different question, paraphrase the relevant "
        "value(s) in plain English. Do NOT paste raw pipe-separated rows into your prose.\n"
        "- For tables, include ALL rows and ALL columns. Do not truncate with '...' or 'and so on'.\n"
        "- DETECT CORRUPTED HEADERS: if a column header in the source table is unusually long (more than ~6 words), "
        "contains run-on concatenated topics (e.g. 'Credit risk Counterparty credit risk Off-balance sheet On-balance "
        "amount Repo-style Total'), or contains placeholders like 'Col 1', 'Col 2', the source table extraction "
        "was imperfect. In that case: do NOT print the corrupted header verbatim. Instead say 'The original "
        "table\\'s column headers couldn\\'t be cleanly extracted' and present only the clearly-labelled columns "
        "you can identify (e.g., row labels and a Total column). Offer to look up specific values if the user asks.\n"
        "\n"
        "Other:\n"
        "- If sources disagree, mention that."
    )

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    for msg in state.get("history", []):
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": f"Context:\n{state['context']}\n\nQuestion: {state['original_question']}",
    })

    return messages


def answer_node(state: RAGState) -> RAGState:
    answer = generate_with_messages(_build_answer_messages(state))
    return {**state, "answer": answer}


def build_rag_graph():
    graph = StateGraph(RAGState)

    graph.add_node("rewrite_question", rewrite_question_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("filter_sources", filter_sources_node)
    graph.add_node("no_context", no_context_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("rewrite_question")

    graph.add_edge("rewrite_question", "retrieve")
    graph.add_edge("retrieve", "filter_sources")
    graph.add_conditional_edges(
        "filter_sources",
        should_answer,
        {"answer": "answer", "no_context": "no_context"},
    )
    graph.add_edge("answer", END)
    graph.add_edge("no_context", END)

    return graph.compile()


rag_graph = build_rag_graph()


def answer_question_with_graph(
    document_id: str | None,
    question: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    initial_state: RAGState = {
        "document_id": document_id,
        "original_question": question,
        "rewritten_question": question,
        "sources": [],
        "filtered_sources": [],
        "context": "",
        "answer": "",
        "history": history or [],
    }

    result = rag_graph.invoke(initial_state)

    return {
        "answer": result["answer"],
        "sources": result["filtered_sources"],
    }


def stream_answer_with_graph(
    document_id: str | None,
    question: str,
    history: list[dict[str, str]],
) -> Generator[str, None, None]:
    state: RAGState = {
        "document_id": document_id,
        "original_question": question,
        "rewritten_question": question,
        "sources": [],
        "filtered_sources": [],
        "context": "",
        "answer": "",
        "history": history,
    }

    state = rewrite_question_node(state)
    state = retrieve_node(state)
    state = filter_sources_node(state)

    if not state["filtered_sources"]:
        yield json.dumps({"token": "I couldn't find that in the uploaded document."})
        yield json.dumps({"sources": [], "done": True})
        return

    try:
        for token in stream_with_groq(_build_answer_messages(state)):
            yield json.dumps({"token": token})
    except Exception as e:
        print(f"Streaming error: {type(e).__name__}: {e}")
        yield json.dumps({"token": "Sorry, the AI service is temporarily unavailable. Please try again in a moment."})

    sources = [
        {
            "text": s["text"],
            "page": s["page"],
            "filename": s["filename"],
            "document_id": s["metadata"]["document_id"],
            "distance": s.get("distance"),
        }
        for s in state["filtered_sources"]
    ]
    yield json.dumps({"sources": sources, "done": True})
