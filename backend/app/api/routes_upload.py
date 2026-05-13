import os
import uuid
from typing import Any
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import UPLOAD_DIR
from app.services.pdf_loader import extract_pdf_pages
from app.services.chunker import chunk_pages
from app.services.embeddings import embed_texts
from app.services.vector_store import add_chunks, find_document_by_filename

router = APIRouter()


async def _process_file(file: UploadFile) -> dict[str, Any]:
    filename = file.filename or "unknown"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"{filename}: only PDF files are supported.")

    existing = find_document_by_filename(filename)
    if existing:
        return {**existing, "num_chunks": 0, "num_pages": 0, "already_exists": True}

    document_id = str(uuid.uuid4())
    safe_filename = filename.replace(" ", "_")
    file_path = os.path.join(UPLOAD_DIR, f"{document_id}_{safe_filename}")

    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    pages = extract_pdf_pages(file_path)
    children, parents = chunk_pages(
        pages,
        document_id=document_id,
        source_path=file_path,
        file_name=filename,
    )

    if not children:
        raise HTTPException(status_code=400, detail=f"{filename}: no text could be extracted. Try a text-based PDF, not a scanned image.")

    embed_source = [chunk.get("embed_text") or chunk["text"] for chunk in children]
    child_embeddings = embed_texts(embed_source)

    add_chunks(
        document_id=document_id,
        file_name=filename,
        children=children,  # type: ignore
        parents=parents,  # type: ignore
        child_embeddings=child_embeddings,
    )

    return {
        "document_id": document_id,
        "file_name": filename,
        "num_chunks": len(children),
        "num_pages": len(pages),
    }


@router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    results = []
    for file in files:
        try:
            result = await _process_file(file)
            status = "already_exists" if result.get("already_exists") else "ok"
            results.append({**result, "status": status})
        except HTTPException as e:
            results.append({
                "file_name": file.filename or "unknown",
                "status": "error",
                "error": e.detail,
            })
        except Exception as e:
            print(f"Unexpected error processing {file.filename}: {type(e).__name__}: {e}")
            results.append({
                "file_name": file.filename or "unknown",
                "status": "error",
                "error": "Unexpected error processing this file.",
            })

    succeeded = [r for r in results if r["status"] in ("ok", "already_exists")]

    return {
        "message": f"{len(succeeded)}/{len(results)} file(s) indexed successfully.",
        "documents": results,
        "document_id": succeeded[0]["document_id"] if succeeded else None,
        "file_name": succeeded[0]["file_name"] if succeeded else None,
        "num_chunks": succeeded[0].get("num_chunks", 0) if succeeded else 0,
        "num_pages": succeeded[0].get("num_pages", 0) if succeeded else 0,
    }