"""get_provider() — factory + lazy instance cache for LLMProvider (D-05, D-07).

Switches on the `LLM_PROVIDER` config key (sourced from the LLM_PROVIDER env var).
Adding a new provider in a future phase = a new class file + one `elif` branch
here. The cache is process-local and bounded by the tiny allow-list (T-02-01-03).

T-02-01-01: unknown LLM_PROVIDER values raise ValueError — no silent fallthrough,
no arbitrary-provider injection from env tampering.
"""
from __future__ import annotations

from app.config import LLM_PROVIDER
from app.services.llm.base import LLMProvider
from app.services.llm.groq_provider import GroqProvider

_PROVIDER_CACHE: dict[str, LLMProvider] = {}


def get_provider() -> LLMProvider:
    """Return the LLMProvider implementation for the configured LLM_PROVIDER."""
    name = LLM_PROVIDER.lower()
    cached = _PROVIDER_CACHE.get(name)
    if cached is not None:
        return cached

    if name == "groq":
        provider: LLMProvider = GroqProvider()
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER={LLM_PROVIDER!r}. Supported providers: 'groq'."
        )

    _PROVIDER_CACHE[name] = provider
    return provider
