import os
import uuid
from typing import Any
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import UPLOAD_DIR
from app.services.pdf_loader import extract_pdf_pages
from app.services.chunker import chunk_pages
from app.services.embeddings import embed_texts
from app.services.vector_store import add_chunks

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = file.filename or "unknown"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    document_id = str(uuid.uuid4())
    safe_filename = filename.replace(" ", "_")
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}_{safe_filename}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    pages = extract_pdf_pages(file_path)
    chunks = chunk_pages(pages)

    if not chunks:
        raise HTTPException(status_code = 400, detail="No text could be extracted from this PDF. Try a normal text-based PDF, not a scanned image PDF")
    
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embed_texts(texts)

    add_chunks(
        document_id=document_id,
        file_name=filename,
        chunks=chunks, # type: ignore
        embeddings=embeddings
    )

    return {
        "message": "File uploaded and indexed successfully.",
        "document_id": document_id,
        "file_name": filename,
        "num_chunks": len(chunks),
        "num_pages": len(pages)
    }