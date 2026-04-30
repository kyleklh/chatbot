from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_upload import router as upload_router
from app.api.routes_chat import router as chat_router
from app.api.routes_documents import router as documents_router
from app.config import CORS_ORIGINS, CORS_ORIGIN_REGEX


app = FastAPI(title="DocuRag API")

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



