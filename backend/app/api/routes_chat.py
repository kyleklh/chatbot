from fastapi import APIRouter
from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag import answer_question

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest): 
    return answer_question(
        document_id=request.document_id,
        question=request.question
    )