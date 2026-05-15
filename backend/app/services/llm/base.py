"""LLMProvider Protocol — the 3-method provider seam (D-05, D-06).

Decision D-06: providers expose a minimal surface — `stream`, `generate`,
`token_count`. Tokenization is per-provider because the LLM-call tokenizer must
match the provider's actual encoding (Groq/Llama uses cl100k_base via tiktoken;
Anthropic would use its own count_tokens endpoint). This is intentionally
distinct from the ingest-time chunker tokenizer in
`app/services/chunker/tokens.py`, which is provider-agnostic.
"""
from __future__ import annotations

from typing import Iterator, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal 3-method surface every LLM provider must implement (D-06)."""

    def stream(self, messages: list[dict]) -> Iterator[str]:
        """Yield response tokens as they arrive from the provider."""
        ...

    def generate(self, messages: list[dict]) -> str:
        """Return the full completion string (non-streaming)."""
        ...

    def token_count(self, text: str) -> int:
        """Return the number of tokens in `text` per the provider's tokenizer."""
        ...
