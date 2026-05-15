"""GroqProvider — wraps the Groq SDK behind the LLMProvider Protocol (D-05, D-08).

D-06 cross-reference: this module is the LLM-boundary tiktoken consumer. The
`self._enc` encoder here counts tokens for messages being sent to the Groq
chat-completions endpoint. This is intentionally separate from the ingest-time
tokenizer in `app/services/chunker/tokens.py`, which is provider-agnostic and
runs during document chunking. The two consumers must NOT be unified — a future
non-Llama provider may use a different encoding here while the chunker stays put.

D-08: this provider raises NATIVE Groq SDK exceptions on failure. The
`HTTPException(503)` translation is the caller's responsibility — it lives in
`app/services/groq_client.py` (the temporary shim) for now, and will relocate to
`routes_chat.py` in Plan 02-03 when the graph nodes are rewired.

Pitfall 4 (Research): client is built LAZILY in __init__, NOT at module scope —
so `from app.services.llm import get_provider` succeeds even with no GROQ_API_KEY,
and tests can patch the client instance.
"""
from __future__ import annotations

from typing import Iterator

import tiktoken
from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE, MAX_TOKENS


class GroqProvider:
    """Concrete LLMProvider for Groq's chat-completions API."""

    def __init__(self) -> None:
        # Lazy client construction — never at module scope (Pitfall 4).
        self._client = Groq(api_key=GROQ_API_KEY)
        # D-06: LLM-boundary tokenizer instance; see module docstring.
        self._enc = tiktoken.get_encoding("cl100k_base")

    def stream(self, messages: list[dict]) -> Iterator[str]:
        try:
            stream = self._client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
                stream=True,
            )
            for chunk in stream:
                token = chunk.choices[0].delta.content
                if token:
                    yield token
        except Exception as e:
            print(f"Groq streaming error: {type(e).__name__}: {e}")
            raise  # native exception — no HTTPException here (D-08).

    def generate(self, messages: list[dict]) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
            )
            return completion.choices[0].message.content or ""
        except Exception as e:
            print(f"Groq error: {type(e).__name__}: {e}")
            raise  # native exception — D-08 / Pitfall 6.

    def token_count(self, text: str) -> int:
        return len(self._enc.encode(text))
