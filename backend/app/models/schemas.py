from pydantic import BaseModel, ValidationInfo, field_validator


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    document_id: str | None = None
    document_ids: list[str] | None = None
    question: str
    history: list[HistoryMessage] = []


class Source(BaseModel):
    text: str
    page: int
    filename: str
    distance: float | None = None
    # Citation enrichment fields (Plan 02-02). Defaults to "" so the non-streaming
    # /chat ChatResponse path keeps validating before Plan 02-03 wires both paths
    # to populate real values (RESEARCH Assumption A5 / planner decision).
    chunk_id: str = ""
    document_id: str = ""
    quote: str = ""


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


class DoneEvent(BaseModel):
    """Streaming `done`-event payload (D-04).

    Validates that every value in `marker_map` (the marker-number → chunk_id
    dictionary built by `CitationStreamParser.marker_to_chunk_id`) is a chunk_id
    that actually appears in the accompanying `sources` list. This is the
    schema-boundary enforcement of the chunk_id-based client contract (D-02).
    """

    done: bool = True
    sources: list[Source]
    marker_map: dict[str, str]

    @field_validator("marker_map")
    @classmethod
    def markers_resolve_to_known_chunks(
        cls, v: dict[str, str], info: ValidationInfo
    ) -> dict[str, str]:
        sources = info.data.get("sources") or []
        known = {s.chunk_id for s in sources if s.chunk_id}
        for marker, chunk_id in v.items():
            if chunk_id not in known:
                raise ValueError(
                    f"marker_map[{marker!r}] = {chunk_id!r} is not a chunk_id "
                    f"present in sources (known: {sorted(known)})"
                )
        return v
