from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.langgraph_rag import answer_question_with_graph, stream_answer_with_graph

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in request.history]
    return answer_question_with_graph(
        document_id=request.document_id or None,
        document_ids=request.document_ids or None,
        question=request.question,
        history=history,
    )


@router.post("/chat/stream")
def chat_stream(request: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in request.history]

    def event_generator():
        for chunk in stream_answer_with_graph(
            document_id=request.document_id or None,
            document_ids=request.document_ids or None,
            question=request.question,
            history=history,
        ):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
