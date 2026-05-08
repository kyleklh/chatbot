from sentence_transformers import CrossEncoder
from app.config import RERANKER_MODEL, RERANKER_TOP_N

_model = CrossEncoder(RERANKER_MODEL)


def rerank(query: str, sources: list[dict]) -> list[dict]:
    if not sources:
        return sources
    pairs = [[query, s["text"]] for s in sources]
    scores = _model.predict(pairs)
    ranked = sorted(zip(scores, sources), key=lambda x: x[0], reverse=True)
    return [s for _, s in ranked[:RERANKER_TOP_N]]
