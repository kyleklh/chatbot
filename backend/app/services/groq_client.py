"""Thin shim over the LLM provider seam (Phase 02-01 transitional).

Why this file still exists: `langgraph_rag.py` still imports
`generate_with_groq`, `generate_with_messages`, and `stream_with_groq` from
here. Plan 02-03 rewires those graph nodes to call `get_provider()` directly and
will DELETE this shim. Until then, this module forwards to the provider seam.

Where the 503 translation lives now: in this shim's non-streaming helpers
(`generate_with_groq`, `generate_with_messages`). The provider itself
(`app.services.llm.groq_provider.GroqProvider`) is FastAPI-free and raises
native SDK exceptions per D-08. We translate the native exception to
`HTTPException(503)` HERE — outside the `llm/` package — so the existing
`/chat` route behavior (503 on provider failure) is preserved without
modifying graph nodes in this plan.

Plan 02-03 handoff: when graph nodes are rewired to call `get_provider()`, the
503 translation will move to `routes_chat.py` (`/chat` handler `try/except`),
and this file will be deleted.

Streaming path: `stream_with_groq` is a passthrough that raises native
exceptions; `langgraph_rag.stream_answer_with_graph` already catches and yields
a "temporarily unavailable" token, so we do NOT translate to HTTPException on
the streaming path (that would break the SSE contract).
"""
from typing import Generator

from fastapi import HTTPException

from app.services.llm import get_provider


def generate_with_groq(prompt: str) -> str:
    return generate_with_messages([{"role": "user", "content": prompt}])


def generate_with_messages(messages: list[dict]) -> str:
    try:
        return get_provider().generate(messages)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Try again in a moment.",
        )


def stream_with_groq(messages: list[dict]) -> Generator[str, None, None]:
    # Streaming: passthrough native exceptions; SSE handler upstream renders a
    # graceful fallback token. Do NOT raise HTTPException here.
    yield from get_provider().stream(messages)
