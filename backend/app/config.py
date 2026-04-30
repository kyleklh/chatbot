import os
from dotenv import load_dotenv

# Resolve .env relative to this file so it works regardless of working directory
_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(_ENV_PATH)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_STORAGE_DIR = os.path.join(BASE_DIR, "storage")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(_DEFAULT_STORAGE_DIR, "uploads"))
CHROMA_DIR = os.getenv("CHROMA_DIR", os.path.join(_DEFAULT_STORAGE_DIR, "chroma"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

_cors_env = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS: list[str] = (
    [o.strip() for o in _cors_env.split(",") if o.strip()]
    if _cors_env
    else ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]
)

# Allow Vercel preview and production domains without requiring a manual Railway env update.
CORS_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)
