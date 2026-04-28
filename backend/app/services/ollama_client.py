import requests
from app.config import OLLAMA_URL, OLLAMA_MODEL

def generate_with_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "max_tokens": 2048,
        "stream": False
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout = 120)

    response.raise_for_status()

    data = response.json()
    return data.get("response", "").strip()