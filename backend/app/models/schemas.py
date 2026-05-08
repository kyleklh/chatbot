from pydantic import BaseModel


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    document_id: str | None = None
    question: str
    history: list[HistoryMessage] = []


class Source(BaseModel):
    text: str
    page: int
    filename: str
    distance: float | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]