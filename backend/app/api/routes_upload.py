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


async def _process_file(file: UploadFile) -> dict[str, Any]:
    filename = file.filename or "unknown"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"{filename}: only PDF files are supported.")

    document_id = str(uuid.uuid4())
    safe_filename = filename.replace(" ", "_")
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}_{safe_filename}")

    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    pages = extract_pdf_pages(file_path)
    chunks = chunk_pages(pages)

    if not chunks:
        raise HTTPException(status_code=400, detail=f"{filename}: no text could be extracted. Try a text-based PDF, not a scanned image.")

    texts = [chunk["text"] for chunk in chunks]
    embeddings = embed_texts(texts)

    add_chunks(
        document_id=document_id,
        file_name=filename,
        chunks=chunks,  # type: ignore
        embeddings=embeddings,
    )

    return {
        "document_id": document_id,
        "file_name": filename,
        "num_chunks": len(chunks),
        "num_pages": len(pages),
    }


@router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    results = []
    for file in files:
        result = await _process_file(file)
        results.append(result)

    return {
        "message": f"{len(results)} file(s) uploaded and indexed successfully.",
        "documents": results,
        # keep single-file compat fields for the first file
        "document_id": results[0]["document_id"] if results else None,
        "file_name": results[0]["file_name"] if results else None,
        "num_chunks": results[0]["num_chunks"] if results else 0,
        "num_pages": results[0]["num_pages"] if results else 0,
    }