from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def mock_groq_client():
    with patch("app.services.ollama_client._client") as mock:
        yield mock


def _make_completion(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def test_success(mock_groq_client):
    from app.services.ollama_client import generate_with_ollama

    mock_groq_client.chat.completions.create.return_value = _make_completion("Here is the answer.")
    result = generate_with_ollama("What is the rent?")
    assert result == "Here is the answer."


def test_empty_response_returns_empty_string(mock_groq_client):
    from app.services.ollama_client import generate_with_ollama

    mock_groq_client.chat.completions.create.return_value = _make_completion("")
    result = generate_with_ollama("What is the rent?")
    assert result == ""


def test_auth_error_raises_503(mock_groq_client):
    from app.services.ollama_client import generate_with_ollama

    mock_groq_client.chat.completions.create.side_effect = Exception("401 Unauthorized")
    with pytest.raises(HTTPException) as exc_info:
        generate_with_ollama("What is the rent?")
    assert exc_info.value.status_code == 503


def test_rate_limit_raises_503(mock_groq_client):
    from app.services.ollama_client import generate_with_ollama

    mock_groq_client.chat.completions.create.side_effect = Exception("429 rate_limit_exceeded")
    with pytest.raises(HTTPException) as exc_info:
        generate_with_ollama("What is the rent?")
    assert exc_info.value.status_code == 503
