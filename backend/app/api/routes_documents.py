import os
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.config import UPLOAD_DIR
from app.services.vector_store import get_all_documents, delete_document

router = APIRouter()

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


@router.get("/documents")
def documents():
    return {
        "documents": get_all_documents()
    }


@router.delete("/documents/{document_id}")
def remove_document(document_id: str):
    delete_document(document_id)

    return {
        "message": "Document deleted.",
        "document_id": document_id
    }


@router.get("/pdf/{document_id}")
def serve_pdf(document_id: str):
    if not _UUID_RE.match(document_id):
        raise HTTPException(status_code=400, detail="Invalid document_id.")

    prefix = f"{document_id}_"
    try:
        match = next(
            (name for name in os.listdir(UPLOAD_DIR) if name.startswith(prefix)),
            None,
        )
    except FileNotFoundError:
        match = None

    if not match:
        raise HTTPException(status_code=404, detail="PDF not found.")

    return FileResponse(
        os.path.join(UPLOAD_DIR, match),
        media_type="application/pdf",
        filename=match[len(prefix):],
    )