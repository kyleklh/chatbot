from fastapi import APIRouter
from app.services.vector_store import get_all_documents, delete_document

router = APIRouter()


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