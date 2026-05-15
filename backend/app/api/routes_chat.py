from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.services.langgraph_rag import answer_question_with_graph, stream_answer_with_graph

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in request.history]
    # 503 translation moved here from the deleted groq_client.py shim (Plan 02-03
    # handoff). Graph nodes now call get_provider() directly, which raises native
    # SDK exceptions per D-08; the /chat handler translates those to a graceful
    # 503 so the existing route contract is preserved. The streaming path keeps
    # its own try/except inside the SSE generator (no HTTPException there — that
    # would break the SSE contract).
    try:
        return answer_question_with_graph(
            document_id=request.document_id or None,
            document_ids=request.document_ids or None,
            question=request.question,
            history=history,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Try again in a moment.",
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
