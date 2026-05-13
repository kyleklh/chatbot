from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_upload import router as upload_router
from app.api.routes_chat import router as chat_router
from app.api.routes_documents import router as documents_router
from app.config import CORS_ORIGINS, CORS_ORIGIN_REGEX
from app.services.chunker.migrations import run_migration_scan_on_boot


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Force re-index any pre-v2 documents BEFORE the upload route binds, so a
    # concurrent /upload can never land mid-scan (D-09 + Pitfall 4).
    try:
        summary = run_migration_scan_on_boot()
        if summary.get("reindexed"):
            print(
                f"[startup-migration] re-indexed {summary['reindexed']}/{summary['scanned']} docs"
                f" (skipped_missing_file={summary['skipped_missing_file']})"
            )
        if summary.get("errors"):
            for err in summary["errors"]:
                print(f"[startup-migration] WARN: {err}")
    except Exception as exc:  # pragma: no cover — never block startup on migration crash
        print(f"[startup-migration] FATAL: {type(exc).__name__}: {exc}")
    yield


app = FastAPI(title="DocuRag API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, tags = ["Upload"])
app.include_router(chat_router, tags = ["Chat"])
app.include_router(documents_router, tags = ["Documents"])

@app.get("/")
def read_root():
    return {"message": "Welcome to DocuRag API!"}
