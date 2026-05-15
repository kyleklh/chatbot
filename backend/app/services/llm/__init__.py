"""LLM provider seam (Phase 02 — D-05). Barrel re-exports.

Usage:
    from app.services.llm import get_provider, LLMProvider
    provider = get_provider()
    for tok in provider.stream(messages): ...
"""
from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_provider

__all__ = ["LLMProvider", "get_provider"]
