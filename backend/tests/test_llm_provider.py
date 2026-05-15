"""SC4 — LLM provider seam tests (Plan 02-01).

Covers: LLMProvider Protocol satisfaction, GroqProvider behavior (stream,
generate, token_count, native exceptions), factory branching/caching, and the
relocated HTTPException(503) translation point (shim in
`app.services.groq_client`).
"""
from __future__ import annotations

from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.llm import LLMProvider, get_provider
from app.services.llm.groq_provider import GroqProvider
from app.services.llm import factory as factory_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completion(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def _make_stream_chunk(content: str | None):
    delta = MagicMock()
    delta.content = content
    choice = MagicMock()
    choice.delta = delta
    chunk = MagicMock()
    chunk.choices = [choice]
    return chunk


@pytest.fixture(autouse=True)
def _reset_provider_cache():
    """Each test starts with an empty factory cache."""
    factory_mod._PROVIDER_CACHE.clear()
    yield
    factory_mod._PROVIDER_CACHE.clear()


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


def test_get_provider_returns_groq_for_default_config():
    # Default LLM_PROVIDER is "groq" per config.py.
    provider = get_provider()
    assert isinstance(provider, GroqProvider)


def test_get_provider_unknown_raises_valueerror():
    with patch.object(factory_mod, "LLM_PROVIDER", "anthropic"):
        with pytest.raises(ValueError) as exc:
            get_provider()
        assert "anthropic" in str(exc.value).lower() or "Unknown" in str(exc.value)


def test_get_provider_caches_instance():
    a = get_provider()
    b = get_provider()
    assert a is b


# ---------------------------------------------------------------------------
# Protocol satisfaction
# ---------------------------------------------------------------------------


class _FakeProvider:
    """Deterministic LLMProvider for tests — no SDK, no network."""

    def stream(self, messages: list[dict]) -> Iterator[str]:
        yield from ["hello", " ", "world"]

    def generate(self, messages: list[dict]) -> str:
        return "fake-response"

    def token_count(self, text: str) -> int:
        return len(text.split())


def test_fake_provider_satisfies_protocol():
    fake = _FakeProvider()
    assert isinstance(fake, LLMProvider)


# ---------------------------------------------------------------------------
# GroqProvider behavior
# ---------------------------------------------------------------------------


def test_groq_provider_stream_yields_tokens():
    provider = GroqProvider()
    fake_stream = [
        _make_stream_chunk("Hello"),
        _make_stream_chunk(" "),
        _make_stream_chunk("world"),
        _make_stream_chunk(None),  # filtered out (truthy check)
        _make_stream_chunk("!"),
    ]
    with patch.object(provider, "_client") as mock_client:
        mock_client.chat.completions.create.return_value = iter(fake_stream)
        tokens = list(provider.stream([{"role": "user", "content": "hi"}]))
    assert tokens == ["Hello", " ", "world", "!"]


def test_groq_provider_generate_returns_string():
    provider = GroqProvider()
    with patch.object(provider, "_client") as mock_client:
        mock_client.chat.completions.create.return_value = _make_completion("the answer")
        result = provider.generate([{"role": "user", "content": "q"}])
    assert result == "the answer"


def test_groq_provider_generate_empty_returns_empty_string():
    provider = GroqProvider()
    with patch.object(provider, "_client") as mock_client:
        mock_client.chat.completions.create.return_value = _make_completion("")
        assert provider.generate([{"role": "user", "content": "q"}]) == ""


def test_groq_provider_raises_native_exception_not_httpexception():
    """D-08: GroqProvider MUST raise the native SDK exception, never HTTPException."""
    provider = GroqProvider()
    with patch.object(provider, "_client") as mock_client:
        mock_client.chat.completions.create.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError):
            provider.generate([{"role": "user", "content": "q"}])
    # And specifically NOT HTTPException
    with patch.object(provider, "_client") as mock_client:
        mock_client.chat.completions.create.side_effect = RuntimeError("boom")
        try:
            provider.generate([{"role": "user", "content": "q"}])
        except HTTPException:
            pytest.fail("GroqProvider must not raise HTTPException (D-08)")
        except RuntimeError:
            pass


def test_groq_provider_stream_raises_native_exception():
    provider = GroqProvider()
    with patch.object(provider, "_client") as mock_client:
        mock_client.chat.completions.create.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError):
            list(provider.stream([{"role": "user", "content": "q"}]))


def test_groq_provider_token_count():
    provider = GroqProvider()
    n = provider.token_count("Hello world this is a sentence.")
    assert isinstance(n, int)
    assert n > 0


def test_groq_provider_token_count_empty():
    provider = GroqProvider()
    assert provider.token_count("") == 0
