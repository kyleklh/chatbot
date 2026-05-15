"""Migrated tests for the `app.services.groq_client` shim (Plan 02-01).

Background: this shim wraps `get_provider()` and owns the HTTPException(503)
translation for the non-streaming path until Plan 02-03 rewires graph nodes.
These 4 tests preserve the original behaviors from the pre-seam era:

1. success → string returned
2. empty completion → empty string returned
3. auth error (native exception) → HTTPException(503) at the shim boundary
4. rate-limit error (native exception) → HTTPException(503) at the shim boundary
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


def _make_provider(generate_return=None, generate_side_effect=None) -> MagicMock:
    """Build a fake LLMProvider with scripted generate()."""
    provider = MagicMock()
    if generate_side_effect is not None:
        provider.generate.side_effect = generate_side_effect
    else:
        provider.generate.return_value = generate_return
    return provider


@pytest.fixture
def patch_provider():
    """Patch app.services.groq_client.get_provider with a controllable fake."""
    with patch("app.services.groq_client.get_provider") as mock_get:
        provider = MagicMock()
        mock_get.return_value = provider
        yield provider


def test_success(patch_provider):
    from app.services.groq_client import generate_with_groq

    patch_provider.generate.return_value = "Here is the answer."
    assert generate_with_groq("What is the rent?") == "Here is the answer."


def test_empty_response_returns_empty_string(patch_provider):
    from app.services.groq_client import generate_with_groq

    patch_provider.generate.return_value = ""
    assert generate_with_groq("What is the rent?") == ""


def test_auth_error_raises_503(patch_provider):
    from app.services.groq_client import generate_with_groq

    patch_provider.generate.side_effect = Exception("401 Unauthorized")
    with pytest.raises(HTTPException) as exc_info:
        generate_with_groq("What is the rent?")
    assert exc_info.value.status_code == 503


def test_rate_limit_raises_503(patch_provider):
    from app.services.groq_client import generate_with_groq

    patch_provider.generate.side_effect = Exception("429 rate_limit_exceeded")
    with pytest.raises(HTTPException) as exc_info:
        generate_with_groq("What is the rent?")
    assert exc_info.value.status_code == 503


def test_generate_with_messages_success(patch_provider):
    from app.services.groq_client import generate_with_messages

    patch_provider.generate.return_value = "ok"
    assert generate_with_messages([{"role": "user", "content": "hi"}]) == "ok"
