from groq import Groq
from fastapi import HTTPException

from app.config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def generate_with_ollama(prompt: str) -> str:
    try:
        completion = _client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return completion.choices[0].message.content or ""
    except Exception as e:
        print(f"Groq error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable. Try again in a moment.")
