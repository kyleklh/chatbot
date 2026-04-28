from pydantic import BaseModel


class ChatRequest(BaseModel):
    document_id: str | None = None
    question: str


class Source(BaseModel):
    text: str
    page: int
    filename: str
    distance: float | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]