from fastapi import APIRouter

from app.models.schemas import ChatRequest, ChatResponse
from app.services.langgraph_rag import answer_question_with_graph

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return answer_question_with_graph(
        document_id=request.document_id,
        question=request.question,
    )