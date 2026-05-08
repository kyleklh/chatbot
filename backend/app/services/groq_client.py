from typing import Generator

from groq import Groq
from fastapi import HTTPException

from app.config import GROQ_API_KEY, GROQ_MODEL, MAX_TOKENS

_client = Groq(api_key=GROQ_API_KEY)


def generate_with_groq(prompt: str) -> str:
    return _call_groq([{"role": "user", "content": prompt}])


def generate_with_messages(messages: list[dict]) -> str:
    return _call_groq(messages)


def stream_with_groq(messages: list[dict]) -> Generator[str, None, None]:
    try:
        stream = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=MAX_TOKENS,
            stream=True,
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token
    except Exception as e:
        print(f"Groq streaming error: {type(e).__name__}: {e}")
        raise


def _call_groq(messages: list[dict]) -> str:
    try:
        completion = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=MAX_TOKENS,
        )
        return completion.choices[0].message.content or ""
    except Exception as e:
        print(f"Groq error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable. Try again in a moment.")
