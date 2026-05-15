# Phase 2: Citations backend - Research

**Researched:** 2026-05-14
**Domain:** RAG citation emission — streaming marker parsing, post-hoc quote extraction, LLM provider seam
**Confidence:** HIGH (all findings are direct reads of the codebase being modified + verified package state)

## Summary

The AI-SPEC.md has already locked the framework (LangGraph stays + hand-rolled `LLMProvider` Protocol/factory), the quote-extraction strategy (Strategy b: deterministic post-hoc fuzzy substring match), the module layout (`app/services/llm/` + `app/services/citations/`), the eval strategy, and the pitfalls. This research fills the **implementation-detail gaps** the planner needs: the exact current shape of every file that gets modified, a concrete buildable design for the tolerant streaming parser, the rapidfuzz-vs-difflib decision (with a correction to an AI-SPEC assumption), the D-06 tokenization reconciliation, and the SC5 regression surface.

**Primary recommendation:** Plan against the *actual* code shapes documented below — they differ from the AI-SPEC's idealized sketches in three load-bearing ways: (1) **rapidfuzz is NOT installed and NOT in `requirements.txt`** — the AI-SPEC wrongly assumes it is; the planner must add an explicit install task OR use stdlib `difflib`; (2) `stream_answer_with_graph` builds its final `sources[]` payload itself (lines 317–326), *not* inside the graph — that hand-built list is what D-04 enriches; (3) the existing streaming path's `try/except` wraps the *entire* token loop, so the tolerant parser must live inside that try-block. Use `difflib.SequenceMatcher` (stdlib, zero new dependency) for the fuzzy quote match unless the planner explicitly wants to add `rapidfuzz` — `difflib` is more than fast enough for 5 chunks × a few markers per request.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `[N]` marker emission | API/Backend (LLM call) | — | The LLM produces markers inline during generation; prompt change in `_build_answer_messages` |
| Tolerant marker parse + normalize + strip | API/Backend (streaming path) | — | Pure-Python filter between `provider.stream()` and the `{token:...}` SSE events |
| Marker → chunk_id resolution | API/Backend (streaming path) | — | Positional lookup against `filtered_sources`, already numbered `[Source 1..N]` |
| Verbatim quote extraction | API/Backend (`citations/quotes.py`) | — | Post-hoc fuzzy substring match against cited chunk text; runs at done-event assembly |
| Provider abstraction (`stream`/`generate`/`token_count`) | API/Backend (`services/llm/`) | — | Protocol + factory; the only LLM chokepoint |
| `done`-event payload assembly + validation | API/Backend (`langgraph_rag.py` + `schemas.py`) | — | Pydantic `DoneEvent`/`Source` validates the assembled payload before `json.dumps` |
| SSE transport | API/Backend (`routes_chat.py`) | — | Unchanged — already wraps the generator in `StreamingResponse` |
| Badge rendering / hover / click-to-jump | Frontend | — | **Phase 3 — explicitly out of scope** |

## Standard Stack

No new framework. The phase wraps SDKs already pinned (loosely) in `backend/requirements.txt`.

### Core
| Library | Installed Version | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| `groq` | **1.2.0** [VERIFIED: `python -c "import groq"`] | LLM SDK wrapped by `GroqProvider` | Already the project's LLM client |
| `tiktoken` | **0.12.0** [VERIFIED] | `cl100k_base` token counting | Already used by `chunker/tokens.py`; Groq/Llama share this encoder |
| `langgraph` / `langchain` / `langchain-community` | unpinned in requirements.txt [VERIFIED: file read] | Existing RAG graph — untouched | Already the backend architecture |
| `typing.Protocol` | stdlib (Python 3.13.0) [VERIFIED] | `LLMProvider` structural interface | No install; PEP 544 |
| `pydantic` | (installed, via fastapi) | `Source` / `DoneEvent` payload validation | Already the schema layer (`app/models/schemas.py`) |

### Supporting — Fuzzy quote match (Claude's discretion, Strategy b locked)
| Library | Status | Purpose | Verdict |
|---------|--------|---------|---------|
| `difflib` (`SequenceMatcher`) | stdlib — always available [VERIFIED: Python 3.13] | Post-hoc fuzzy substring match for the verbatim quote | **RECOMMENDED for v1** — zero new dependency, sufficient performance |
| `rapidfuzz` | **NOT installed, NOT in requirements.txt** [VERIFIED: `ModuleNotFoundError`; requirements.txt read] | Faster fuzzy matching with `partial_ratio` / alignment | Only if planner adds an explicit install + pin task — see correction below |

> **CORRECTION to AI-SPEC.md:** Section 5 ("Setup") and Section 4 both state *"rapidfuzz already in backend/requirements.txt"* and *"confirm pinned in backend/requirements.txt"*. **This is false.** `backend/requirements.txt` (full contents read) is: fastapi, uvicorn, python-multipart, python-dotenv, pypdf, pymupdf4llm, chromadb, sentence-transformers, rank-bm25, groq, langgraph, langchain, langchain-community, langchain-chroma, langchain-huggingface, langchain-text-splitters, tiktoken. **No rapidfuzz.** `import rapidfuzz` raises `ModuleNotFoundError`. The planner MUST either (a) add `rapidfuzz` to `requirements.txt` + install as an explicit task, or (b) use stdlib `difflib` and require no dependency change. Recommendation: **(b) difflib** — the matching workload is tiny (≤5 chunks, a handful of markers per request, ~1–2 KB chunk text each), `difflib.SequenceMatcher.find_longest_match` / `get_matching_blocks` handles it in well under the 1–5 ms/marker budget the AI-SPEC cites, and it keeps the dependency surface flat (consistent with the "no new framework" posture).

### Installation
```bash
# Option (b) — RECOMMENDED: no install needed. difflib is stdlib.
# Option (a) — only if planner chooses rapidfuzz:
#   echo "rapidfuzz==3.*" >> backend/requirements.txt && pip install rapidfuzz
# Recommended regardless (Pitfall 5, AI-SPEC): tighten the loose pins —
#   groq==1.2.0
#   tiktoken==0.12.0
```

## Current-State Code Read (the files the planner writes tasks against)

### `backend/app/services/langgraph_rag.py` — exact shapes

**`RAGState` (TypedDict, lines 29–38):**
```python
document_id: str | None
document_ids: list[str] | None
original_question: str
rewritten_question: str
sources: list[dict[str, Any]]            # raw RRF-merged
filtered_sources: list[dict[str, Any]]   # reranked, the citation basis
context: str
answer: str
history: list[dict[str, str]]
```

**`filtered_sources` element shape** (produced by `search_chunks` in `vector_store.py` lines 142–150, then reranked):
```python
{
  "text": str,                  # the CHILD chunk text
  "metadata": dict,             # includes document_id, chunk_id, page, parent_ref, file_name, ...
  "filename": str,              # == metadata["file_name"]
  "page": int,                  # == metadata["page"]
  "chunk_id": str,              # == metadata.get("chunk_id")  (D-10 stable, occurrence-disambiguated)
  "distance": float | None,
}
```
So **`chunk_id`, `document_id`, `page` are ALL already present** on each `filtered_sources` element (via `s["chunk_id"]`, `s["metadata"]["document_id"]`, `s["page"]`). The parser/quote layer needs no extra retrieval — it has everything to build the enriched payload. **The only thing missing today is `quote`.**

**`_build_answer_messages(state)` (lines 179–219):** builds `[{"role":"system",...}, *history, {"role":"user", "content": f"Context:\n{state['context']}\n\nQuestion: {...}"}]`. The system prompt currently says: *"Cite every important claim using [Source 1], [Source 2], etc."* — **D-01 changes this line** to ask for compact `[N]`. Note the system prompt is large and table-heavy; the `[N]` instruction is a single line to edit, plus the AI-SPEC's recommended 1–2 few-shot examples + no-fabrication rule.

**`answer_node(state)` (lines 222–224):** `answer = generate_with_messages(_build_answer_messages(state))`. **D-05 reroutes this to `get_provider().generate(...)`.**

**`stream_answer_with_graph(...)` (lines 282–327)** — the streaming citation path. Critical structure:
- Lines 300–303: runs nodes manually (`rewrite → retrieve → filter_sources → expand_to_parents`) — NOT via `rag_graph.invoke`.
- Lines 305–308: early return if no `filtered_sources` — yields one `{token:...}` then `{"sources": [], "done": True}`.
- Lines 310–315: **`try/except` wraps the ENTIRE token loop.** `for token in stream_with_groq(_build_answer_messages(state)): yield json.dumps({"token": token})`. On exception: prints + yields a "temporarily unavailable" token. **The tolerant parser must sit inside this try-block**, wrapping `provider.stream(...)`, and `parser.flush()` must also run before the except boundary (or right after the loop).
- Lines 317–327: **the final `sources[]` is hand-built HERE, in this function** — a list comprehension over `state["filtered_sources"]` producing `{text, page, filename, document_id, distance}` dicts, then `yield json.dumps({"sources": sources, "done": True})`. **This is the exact payload D-04 enriches** — add `chunk_id` + `quote` per element, and add the `marker_map` key to the done event. It is NOT built inside the graph; it is built in this generator.

**`expand_to_parents_node` (lines 122–168):** rewrites `state["context"]` to parent-section text, re-numbering blocks `[Source 1]..[Source N]` **in `filtered_sources` order** (line 165: `f"[Source {index + 1}] (Page {page}, {filename})\n{block_text}"`). It dedupes by `parent_ref` — multiple children sharing a parent render once, but **`filtered_sources` itself is NOT reordered or deduped** (only the context string is). So the positional `N → filtered_sources[N-1]` mapping D-02 resolves against is stable and authoritative. ⚠️ Caveat: because context blocks dedupe by parent but `filtered_sources` does not, the LLM sees fewer numbered blocks than `len(filtered_sources)` when children share parents — the `[Source N]` numbering in the *prompt* still counts every child by index, so numbering stays 1:1 with `filtered_sources` indices. Confirm this holds when writing the parser (the numbering uses `enumerate(filtered)`, so it does).

**`answer_question_with_graph` (lines 256–279):** the non-streaming path — `rag_graph.invoke(...)` then returns `{"answer", "sources": result["filtered_sources"]}`. Goes through `answer_node` → `generate_with_messages`. Must keep working (REQ-no-happy-path-regressions).

**Import line to replace (line 9):** `from app.services.groq_client import generate_with_groq, generate_with_messages, stream_with_groq` — three by-name imports. `generate_with_groq` is also used by `rewrite_question_node` (line 65) — **don't forget that third call site.** D-05's "two call sites" (`answer_node`, `stream_answer_with_graph`) is incomplete: `rewrite_question_node` is a *third* LLM call site using `generate_with_groq`. The planner should route all three through the provider seam (`provider.generate`).

### `backend/app/services/groq_client.py` — exact shapes
- Module-level `_client = Groq(api_key=GROQ_API_KEY)` at **import time** (line 8) — Pitfall 4: this crashes import if the key is unset. `GroqProvider` must build the client **lazily inside `get_provider()`**, not at module scope.
- `generate_with_groq(prompt: str) -> str` — wraps a single user message.
- `generate_with_messages(messages: list[dict]) -> str` — passes messages through.
- `stream_with_groq(messages: list[dict]) -> Generator[str, None, None]` — yields `chunk.choices[0].delta.content` when truthy; catches + re-raises (so the caller's try/except sees it).
- `_call_groq(messages)` — the shared non-streaming call; **raises `fastapi.HTTPException(503)` on any exception** (line 46). Pitfall 6: keep `HTTPException` OUT of `GroqProvider` (D-08 — provider raises native SDK exceptions; callers translate). The non-streaming `/chat` route currently relies on this 503 surfacing — the planner must decide where the 503 translation moves (likely `routes_chat.py` or kept as a thin wrapper).
- **Existing test** `backend/tests/test_groq_client.py` patches `app.services.groq_client._client` and asserts `generate_with_groq` raises `HTTPException(503)` on 401/429. If `groq_client.py` shrinks/changes per the AI-SPEC's "keep thin or delete", **these 4 tests break** — the planner must update or migrate them to test `GroqProvider` + the new error-translation point.

### `backend/app/models/schemas.py` — exact shapes
```python
class Source(BaseModel):          # current — lines 16–20
    text: str
    page: int
    filename: str
    distance: float | None = None

class ChatResponse(BaseModel):    # lines 23–25
    answer: str
    sources: list[Source]
```
`Source` needs `chunk_id: str` + `document_id: str` + `quote: str` added (D-04/SC3). ⚠️ Note: today's hand-built streaming `sources[]` (langgraph_rag.py lines 318–325) already includes `document_id` even though the `Source` Pydantic model does NOT — the streaming path doesn't validate against `Source` currently. Adding fields is backward-compatible for `/chat` (non-streaming `ChatResponse`) **only if** the non-streaming path also populates them — it currently builds sources from `result["filtered_sources"]` which are raw dicts, so `ChatResponse` validation would need those dicts to carry the new keys, OR the new fields get defaults. **Recommend:** add `chunk_id`, `document_id`, `quote` with no defaults to `Source`, and ensure BOTH paths populate them; add `DoneEvent` as a new model per AI-SPEC §4b. There are **no streaming-event Pydantic models today** — `{token:...}` and `{sources,done}` are bare `json.dumps(dict)`. `DoneEvent` would be the first.

### `backend/app/config.py` — exact shapes
Flat module-level constants from env. Relevant: `GROQ_API_KEY`, `GROQ_MODEL` (default `llama-3.3-70b-versatile`), `MAX_TOKENS` (4096), `RAG_TOP_K` (30), `RERANKER_TOP_N` (5), `CHILD_CHUNK_TOKENS` (256), `PARENT_CHUNK_TOKENS` (1024), `CHUNKER_VERSION` (`"v2-2026-05"`). **Add `LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")`** (D-07) — same flat style. Consider `LLM_TEMPERATURE` (AI-SPEC §4 recommends 0.0–0.2 for grounded citations; not currently set anywhere).

### `backend/app/api/routes_chat.py` — exact shapes
- `/chat` (POST, `response_model=ChatResponse`) → `answer_question_with_graph(document_id, document_ids, question, history)`.
- `/chat/stream` (POST) → `event_generator()` wraps `stream_answer_with_graph(...)`, prefixes each yielded chunk with `data: ` + `\n\n`, returns `StreamingResponse(media_type="text/event-stream")`.
- **`document_ids` flow:** `ChatRequest.document_ids: list[str] | None` → `request.document_ids or None` → `stream_answer_with_graph(... document_ids=...)` → `retrieve_node` → `search_chunks(document_ids=...)` / `search_bm25(document_ids=...)` → Chroma `where={"document_id": {"$in": document_ids}}` (vector_store.py lines 125–126). This path is **untouched by Phase 2** — the regression risk is purely that the provider-seam refactor or parser insertion accidentally drops the parameter. SC5 = keep this wiring intact.

### `backend/app/services/chunker/tokens.py` — exact shapes (D-06 reconciliation point)
Entire file is 17 lines: a module-level `_enc = tiktoken.get_encoding("cl100k_base")` singleton + `token_len(text: str) -> int`. Docstring already cites D-12. It is an **ingest-time, provider-agnostic** consumer used by the chunker.

## D-06 Tokenization Reconciliation — Recommendation

**Recommendation: the chunker KEEPS its own `chunker/tokens.py` tiktoken path. Do NOT route it through `get_provider()`.** [Confidence: HIGH — matches AI-SPEC Pitfall 1 and the architectural reasoning.]

Rationale:
- Chunking is an **ingest-time concern** that must stay **stable across provider swaps**. If the chunker's token budget changed every time `LLM_PROVIDER` flipped, the same PDF would re-chunk differently — breaking `chunk_id` stability (D-10) and triggering spurious re-index migrations (D-09). Chunk identity must be provider-invariant.
- `GroqProvider.token_count` and `chunker/tokens.token_len` both use `cl100k_base` *today* — they agree by coincidence, not contract. That coincidence is fine: they serve different masters (ingest vs. LLM-call-boundary budget checks).
- **Concrete action for the planner:** add a cross-reference comment in BOTH `chunker/tokens.py` and `llm/groq_provider.py` (or `llm/base.py`) stating: "Two intentional tiktoken consumers — chunker tokenization is provider-agnostic ingest-time and must NOT route through the LLM provider seam; see D-06." This satisfies "do not silently leave two divergent tokenizers" — they're not silent, they're documented-and-intentional. No code unification.
- The Protocol's `token_count(text)` method still gets built (D-06 locks the 3-method surface) — it's used for the *optional* future pre-call context-budget guard on the LLM side, a different use case from chunk sizing.

## The Tolerant Streaming Parser — Concrete Buildable Design

Lives in `app/services/citations/parser.py`. Constructed per-request from `filtered_sources`. Wraps `provider.stream(...)` inside `stream_answer_with_graph`'s try-block.

### Interface (matches AI-SPEC §4 core pattern)
```python
class CitationStreamParser:
    def __init__(self, filtered_sources: list[dict]): ...
    def feed(self, raw_token: str) -> Iterator[str]:   # yields cleaned tokens
        ...
    def flush(self) -> Iterator[str]:                   # emit buffered tail at stream end
        ...
    def enriched_sources(self) -> list[dict]:           # [{chunk_id, document_id, page, quote, text, filename, distance}]
        ...
    def marker_to_chunk_id(self) -> dict[str, str]:     # {"1": "chunk_abc", ...}
        ...
```

### Buffered-regex hybrid (recommended over a pure state machine)

**Token shape confirmed:** `provider.stream()` yields arbitrary-length string fragments (`chunk.choices[0].delta.content`) — a `[2]` marker CAN arrive split as `"["` then `"2]"`, or `" [Source"` then `" 2]"`. The `_read_stream` helper in `test_pipeline_smoke.py` confirms each SSE `data:` line is one JSON `{token:...}` — so the parser's job is purely on the *text*, across `feed()` calls.

**Algorithm:**
1. Maintain `self._buffer: str`. Each `feed(raw_token)` appends to buffer.
2. **Normalization regex** (run over the buffer): `r"\[\s*(?:Source\s+)?(\d+(?:\s*,\s*\d+)*)\s*\]"` — captures `[N]`, `[Source N]`, `[1, 2]`, `[ 3 ]`.
3. For each *complete* match in the buffer:
   - Split the captured group on `,` → list of integers.
   - For each `N`: resolvable if `1 <= N <= len(filtered_sources)`.
   - **Resolvable** → rewrite to canonical `[N]` (for a multi-citation `[1, 2]`, emit `[1][2]` — confirm desired form with planner; frontend Phase 3 expects discrete badges per REQ "[1][2] markers"). Record `marker_map[str(N)] = filtered_sources[N-1]["chunk_id"]`.
   - **Unresolvable** (`[5]` vs 4 sources) → **drop from output text + `print()`-log** (D-03). e.g. `print(f"[citation] stripped unresolvable marker [{N}] (have {len(filtered_sources)} sources)")`.
4. **Safe-flush boundary:** only emit buffer content up to the last index that *cannot* be the prefix of an in-progress marker. Hold back a trailing `[`, `[S`, `[Sou`, `[1,`, `[ 2` — anything matching `r"\[\s*(?:S(?:o(?:u(?:r(?:c(?:e)?)?)?)?)?)?\s*\d*\s*,?\s*\d*\s*$"` (a "could still become a marker" partial). Practical simplification: hold back from the **last unmatched `[` to end-of-buffer** if no `]` follows it yet; flush everything before that `[`.
5. `flush()` at stream end: run the regex one final time on the remaining buffer; an unterminated `[...` with no closing `]` is emitted as **literal text** (it was never a marker).

### Edge cases (all must be planned for)
| Edge case | Handling |
|-----------|----------|
| Marker split mid-stream (`"["` then `"2]"`) | Buffer + hold-back boundary — never `re.sub` per token. This is **Pitfall 2**, the load-bearing one. |
| Unresolvable marker (`[5]` vs 4 sources) | Strip from user-facing text + `print()`-log (D-03). |
| `[Source N]` / `[1, 2]` drift | Normalization regex captures all three forms → canonical `[N]` (D-01). |
| Markers inside a code block / markdown table | **Known risk.** The model may emit `[1]` inside a fenced ```code``` block or a `|table cell|`. v1 simplest: the parser does NOT track markdown context — it normalizes/strips everywhere. Document this as an accepted v1 limitation (Phase 3 frontend's `MarkdownBoundary.jsx` is where markdown-safety is really solved). If the planner wants minimal protection: skip normalization inside a ` ``` ` fence by tracking a `in_code_fence` toggle on triple-backtick — cheap, but optional for v1. Flag for the planner as a discretion call. |
| `[` that never closes (literal bracket in prose) | `flush()` emits it as literal text. |
| Model emits zero markers | `marker_map` is empty `{}`; `enriched_sources()` still returns all `filtered_sources` with quotes (quote = best-effort or leading sentence). Valid `DoneEvent`. |
| Same `N` cited multiple times | `marker_map["N"]` is idempotent (same chunk_id); fine. |

## Supporting-Quote Extraction — Concrete Approach (Strategy b, locked)

Lives in `app/services/citations/quotes.py`. Input: `(chunk_text: str, answer_span: str)` → output: `(start: int, end: int)` char span into `chunk_text`, or a low-score signal. The "answer_span" is the sentence(s) of the answer immediately preceding/around the `[N]` marker — the parser can capture this since it sees the full token stream.

### Use `difflib.SequenceMatcher` (stdlib) — recommended
```python
from difflib import SequenceMatcher

def best_quote_span(chunk_text: str, answer_span: str) -> tuple[int, int, float]:
    # SequenceMatcher over characters; find the longest contiguous matching block,
    # then expand to the largest high-ratio window. For v1, the longest matching
    # block snapped to chunk_text char offsets IS a guaranteed real substring.
    sm = SequenceMatcher(None, chunk_text, answer_span, autojunk=False)
    match = sm.find_longest_match(0, len(chunk_text), 0, len(answer_span))
    # match.a, match.size -> a real (start, end) span in chunk_text BY CONSTRUCTION
    start, end = match.a, match.a + match.size
    score = match.size / max(len(answer_span), 1)
    return start, end, score
```
**Why this satisfies SC2 deterministically:** the returned span is `chunk_text[start:end]` — by construction a verbatim substring of the cited chunk. No paraphrase risk. The "quote" shipped in `Source.quote` is literally `chunk_text[start:end]`.

**Concrete matching approach:** sliding-window is unnecessary — `SequenceMatcher.find_longest_match` already finds the best contiguous block in one pass. For a richer quote (a full sentence rather than the longest common run), expand `[start, end]` outward to the nearest sentence boundaries *within* `chunk_text` (still a verbatim substring). `get_matching_blocks()` can stitch context if the answer paraphrases mid-sentence — but keep v1 simple: longest block + sentence-boundary expansion.

**Snapping fuzzy → exact char span:** not needed with `find_longest_match` — it returns indices *into `chunk_text` directly*. (This is the advantage over `rapidfuzz.fuzz.partial_ratio`, which returns only a *score*, not offsets — you'd need `rapidfuzz.fuzz.partial_ratio_alignment` to get offsets. `difflib` gives offsets natively. Another reason to prefer `difflib`.)

**Grounding-strictness corollary (Claude's discretion):** if `score` is below a threshold (start with ~0.4–0.5, calibrate against the golden dataset), the quote is genuinely weak/unsupported. **v1 behavior:** fall back to the chunk's leading sentence as the quote and `print()`-log the low score (consistent with D-03's thin-logging posture). Hard rejection of unsupported markers is a v2 eval-surface candidate, NOT this phase.

**Performance:** `difflib` on ~1–2 KB `chunk_text` × ~200-char `answer_span`, ≤5 chunks, a few markers per request — single-digit milliseconds total, well inside budget. `autojunk=False` is important (default `autojunk` heuristic can skip "popular" characters and hurt accuracy on short strings).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy substring matching | A custom Levenshtein / sliding-window matcher | `difflib.SequenceMatcher` (stdlib) | Returns char offsets natively; edge-case-tested; zero dependency |
| Token counting | A custom tokenizer | `tiktoken` `cl100k_base` (already used) | Already the project standard |
| Provider interface | A custom ABC hierarchy | `typing.Protocol` + `@runtime_checkable` | Structural typing — zero shared base class needed (AI-SPEC locked) |
| Done-event validation | Manual dict key-checking | `pydantic` `DoneEvent` + `field_validator` | Already the schema layer; validator catches parser bugs (marker→unknown chunk) |
| SSE transport | Custom chunked-response code | `fastapi.StreamingResponse` (already in `routes_chat.py`) | Untouched — already works |

**Key insight:** the parser and quote-matcher are the only genuinely new logic; everything else is rewiring existing, working components. Resist the urge to build a "marker resolution engine" — it's a dict lookup against `filtered_sources` indices.

## Common Pitfalls

### Pitfall 1: rapidfuzz assumed-present (NEW — not in AI-SPEC's pitfall list)
**What goes wrong:** AI-SPEC says rapidfuzz is in `requirements.txt`; it is not. A task written as "use rapidfuzz" will `ModuleNotFoundError` at runtime/test.
**How to avoid:** use stdlib `difflib` (recommended), OR add an explicit `pip install rapidfuzz` + requirements.txt task.
**Warning sign:** `ModuleNotFoundError: No module named 'rapidfuzz'`.

### Pitfall 2: Markers split across token boundaries
**What goes wrong:** `re.sub` per token never matches a `[2]` that arrived as `"["` + `"2]"`.
**How to avoid:** buffered parser with a hold-back boundary (design above). This is the single highest-risk piece of new code.
**Warning sign:** dead `[` or stray `2]` fragments in streamed output during UAT.

### Pitfall 3: Forgetting `rewrite_question_node` is a third LLM call site
**What goes wrong:** D-05/AI-SPEC name only `answer_node` + `stream_answer_with_graph`. `rewrite_question_node` (line 65) also calls `generate_with_groq`. Leaving it on the old import means the provider seam is incomplete — swapping `LLM_PROVIDER` wouldn't swap the query-rewrite call.
**How to avoid:** route all three call sites through `get_provider()`.

### Pitfall 4: `Groq()` at import time crashes tests
**What goes wrong:** `groq_client.py` line 8 builds `_client` at module scope — import fails if `GROQ_API_KEY` unset.
**How to avoid:** `GroqProvider` builds its client lazily inside `get_provider()` (factory-cached, not import-time).

### Pitfall 5: Existing `test_groq_client.py` breaks when `groq_client.py` shrinks
**What goes wrong:** 4 tests patch `app.services.groq_client._client` and assert `HTTPException(503)`. If logic moves to `GroqProvider` and `groq_client.py` is gutted, these tests fail.
**How to avoid:** plan a task to migrate/rewrite these tests against `GroqProvider` + the new error-translation point.

### Pitfall 6: The streaming `try/except` boundary
**What goes wrong:** `stream_answer_with_graph`'s try wraps the whole token loop. If the parser is inserted *outside* the try, a parser exception 500s the stream instead of degrading.
**How to avoid:** parser `feed()`/`flush()` calls go *inside* the existing try-block; `DoneEvent` validation failure → drop offending marker + `print()`-log, never 500 (AI-SPEC §4b).

### Pitfall 7: `done`-event `sources[]` is built in the generator, not the graph
**What goes wrong:** a planner expecting to enrich sources "in the graph" will look in the wrong place.
**How to avoid:** the list comprehension at `langgraph_rag.py` lines 317–326 is the enrichment target.

## Code Examples

### Provider seam wiring (replaces line 9 import + 3 call sites)
```python
# langgraph_rag.py — was: from app.services.groq_client import ...
from app.services.llm import get_provider

# rewrite_question_node:   rewritten = get_provider().generate([{"role":"user","content":prompt}]).strip()
# answer_node:             answer = get_provider().generate(_build_answer_messages(state))
# stream_answer_with_graph: for raw in get_provider().stream(_build_answer_messages(state)): ...
```

### Streaming path with parser (the load-bearing change)
```python
# stream_answer_with_graph — inside the existing try/except
provider = get_provider()
parser = CitationStreamParser(state["filtered_sources"])
try:
    for raw_token in provider.stream(_build_answer_messages(state)):
        for clean in parser.feed(raw_token):
            yield json.dumps({"token": clean})
    for clean in parser.flush():
        yield json.dumps({"token": clean})
except Exception as e:
    print(f"Streaming error: {type(e).__name__}: {e}")
    yield json.dumps({"token": "Sorry, the AI service is temporarily unavailable. Please try again in a moment."})

# enriched done event (replaces lines 317-327)
done = DoneEvent(
    sources=parser.enriched_sources(),       # adds chunk_id + document_id + quote
    marker_map=parser.marker_to_chunk_id(),
)
yield json.dumps(done.model_dump())
```

## Runtime State Inventory

Phase 2 is a **code/config change** — not a rename or migration. No stored data, OS-registered state, or build artifacts carry phase-specific strings.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `chunk_id`/`page`/`document_id` already in Chroma metadata (Phase 1); Phase 2 only *reads* them | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | New `LLM_PROVIDER` env var (default `"groq"` — code provides default, no `.env` change required to ship). Optional `LLM_TEMPERATURE`. `GROQ_API_KEY` unchanged. | Document new env keys; no migration |
| Build artifacts | None | None |

## Validation Architecture

Test framework already in place — `pytest` with `fastapi.testclient.TestClient`, hermetic Chroma via `chromadb.EphemeralClient()`, Groq stubbed via `monkeypatch`. Phase 1 built the harness pattern.

> **TEST-FILE NAMING (reconciled with VALIDATION.md — authoritative):** This research originally sketched `test_provider_seam.py` and `test_citations_parser.py`. The final, authoritative names are **`test_llm_provider.py`** (SC4 — provider seam, supersedes `test_provider_seam.py`) and **`test_citations_eval.py`** (SC1 + SC2 + SC3 + parser edge cases, supersedes `test_citations_parser.py`). VALIDATION.md's per-task verification map is canonical for test-file names; the tables below have been updated to the final names. `test_provider_seam.py` and `test_citations_parser.py` will NOT exist on disk.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` (in use; `backend/tests/`) |
| Config | `backend/pytest.ini` (extended in Wave 0 to register the `semantic` marker) |
| Fixtures | `backend/tests/conftest.py` — `synthetic_pdf` (3-page deterministic PDF), `chroma_in_memory` |
| Quick run | `pytest backend/tests/test_citations_eval.py -v` (new, code-only, deterministic) |
| Full suite | `pytest backend/tests/ -v` |
| Semantic (gated) | `pytest backend/tests/test_citations_semantic.py -v -m semantic` (LLM-judge, costs Groq calls) |

### Phase Requirements → Test Map
| SC | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|-------------|
| SC1 | `[N]` markers emitted DURING streaming | unit (parser) + integration | `pytest backend/tests/test_citations_eval.py -k stream_marker -x` | ❌ Wave 0 (`test_citations_eval.py`) |
| SC2 | marker → chunk_id + document_id + page + verbatim quote | code (substring assert) | `pytest backend/tests/test_citations_eval.py -k verbatim -x` | ❌ Wave 0 (`test_citations_eval.py`) |
| SC3 | per-message `sources[]` carries chunk_id + page + quote | code (`DoneEvent.model_validate`) | `pytest backend/tests/test_citations_eval.py -k done_event -x` | ❌ Wave 0 (`test_citations_eval.py`) |
| SC4 | LLM call site behind thin abstraction; swap doesn't touch graph nodes | code (fake `LLMProvider`) | `pytest backend/tests/test_llm_provider.py -x` | ❌ Wave 0 (`test_llm_provider.py`) |
| SC5 | `document_ids` filter regression-free | code (extend existing) | `pytest backend/tests/test_pipeline_smoke.py::test_document_ids_filter -x` | ✅ EXISTS — extend it |
| — | parser: split markers, drift, unresolvable strip | unit | `pytest backend/tests/test_citations_eval.py -x` | ❌ Wave 0 (`test_citations_eval.py`) |
| — | non-streaming `/chat` still works | integration | `pytest backend/tests/test_pipeline_smoke.py -x` | ✅ EXISTS — `test_pipeline_smoke` (extend for citations) |
| — | `groq_client` / `GroqProvider` error translation | unit | `pytest backend/tests/test_groq_client.py -x` | ✅ EXISTS — must migrate |

### Sampling Rate
- **Per task commit:** `pytest backend/tests/test_citations_eval.py backend/tests/test_llm_provider.py -x` (fast, deterministic, no LLM calls)
- **Per wave merge:** `pytest backend/tests/ -v` (full code suite; excludes `-m semantic`)
- **Phase gate:** full suite green + `test_citations_semantic.py -m semantic` reviewed before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_llm_provider.py` — covers SC4: a deterministic fake `LLMProvider`; assert citation contract holds provider-independently; assert `get_provider()` factory branches + lazy construction (supersedes the originally-sketched `test_provider_seam.py`)
- [ ] `backend/tests/test_citations_eval.py` — covers SC1 (`stream_marker`), SC2 (`verbatim` — assert `quote in chunk_text`), SC3 (`done_event` — `DoneEvent` schema), marker→source resolution + shuffle-ordering test, AND parser edge cases (split markers, `[Source N]`/`[1,2]` drift, unresolvable strip, markdown-block behavior) (supersedes the originally-sketched `test_citations_parser.py` — both responsibilities merged into one file)
- [ ] `backend/tests/test_citations_semantic.py` — RAGAS faithfulness/abstention/coverage (gated `-m semantic`); needs `backend/eval/citations_golden.jsonl` (engineer-authored seed set per Open Question 4 RESOLVED; 16 Q&A pairs is the aspirational target)
- [ ] **Extend** `backend/tests/test_pipeline_smoke.py::test_document_ids_filter` — also assert every cited chunk's `document_id` is inside the filter (SC5 + citation provenance)
- [ ] **Migrate** `backend/tests/test_groq_client.py` — retarget at `GroqProvider` + new error-translation point
- [ ] Dependency: if planner chooses `rapidfuzz`, add to `requirements.txt`; if `difflib`, no install. RAGAS: `pip install ragas==0.2.*` → `backend/requirements-dev.txt` (no `requirements-dev.txt` exists today — planner creates it)
- [ ] Register `semantic` marker in `backend/pytest.ini` `markers` — no marker registered today

## Security Domain

> `security_enforcement` config not located in `.planning/config.json` (file not found at expected path). Treating as enabled; scope is narrow for this phase.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `ChatRequest` already Pydantic-validated; `DoneEvent`/`Source` validate the *outgoing* payload (parser-bug guard) |
| V6 Cryptography | no | No crypto in this phase |
| V2/V3/V4 Auth/Session/Access | no | Single-user v1, no auth (AUTH-V2-* deferred) |
| V7 Error Handling | yes | D-08: providers raise native exceptions; streaming path degrades gracefully (no stack-trace leak to client — current `print()` + generic token is correct) |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via uploaded PDF content (chunk text reaches the system/user prompt) | Tampering | Out of Phase 2 scope to *solve*; note: the tolerant parser stripping unresolvable `[N]` limits one injection payoff (fake citations). Flag for a future phase. |
| API-key leak in logs | Info Disclosure | `print()` logs must never include `GROQ_API_KEY`; provider exception messages should be type+message only (current `groq_client.py` pattern is safe — `f"{type(e).__name__}: {e}"`). |
| Sensitive document text in stdout logs | Info Disclosure | D-03's `print()` logging — keep it to marker numbers + scores, NOT full chunk text. Single-user desktop tool, low stakes, but worth a one-line note. |
| Privacy LOCKED constraint | — | Any provider added to the seam MUST be a no-train endpoint (Anthropic / OpenAI zero-retention / Groq per ToS). v1 ships Groq-only; the constraint binds future `get_provider()` branches. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `difflib.SequenceMatcher` performance is sufficient (single-digit ms per request) for ≤5 chunks × few markers | Quote Extraction | Low — if too slow, swap to `rapidfuzz` (the AI-SPEC's intended lib anyway); interface stays the same |
| A2 | The model emitting `[1, 2]` should normalize to discrete `[1][2]` (vs. keeping `[1, 2]`) | Parser design | Medium — REQ says "`[1][2]` markers"; confirm with planner/Phase 3 frontend contract. If wrong, trivial regex-output change. |
| A3 | Markdown-context-blind parsing (normalizing `[N]` inside code blocks/tables too) is acceptable for v1 | Parser edge cases | Medium — could mangle a literal `[1]` inside a fenced code block in an answer. Phase 3 `MarkdownBoundary.jsx` is the real fix; flagged as planner discretion. |
| A4 | `security_enforcement` defaults to enabled — `.planning/config.json` was not found at the path checked | Security Domain | Low — security scope for this phase is narrow regardless |
| A5 | The non-streaming `/chat` path can adopt the enriched `Source` model without breaking `ChatResponse` if both paths populate `chunk_id`/`document_id`/`quote` | schemas.py read | Medium — if `answer_node`'s source dicts don't carry the new keys, `ChatResponse` validation fails; planner must ensure the non-streaming path also enriches, or use field defaults |

## Open Questions (RESOLVED)

1. **Where does the `HTTPException(503)` translation move?** **(RESOLVED — Plan 02-01 Task 2 owns the decision and picks the 503 location; recommended landing is a thin try/except at the `routes_chat.py` `/chat` handler or `answer_question_with_graph` boundary. `HTTPException` stays out of `GroqProvider`. The chosen location is recorded in 02-01's SUMMARY as a handoff to 02-03.)**
   - What we know: `_call_groq` currently raises `HTTPException(503)`; D-08 says providers raise native SDK exceptions and "callers handle as today"; the streaming path already has its own try/except, but the non-streaming `/chat` route relies on the 503 propagating to FastAPI.
   - What's unclear: whether the 503 translation lands in `routes_chat.py`, a thin shim, or `answer_question_with_graph`.
   - Recommendation: planner decides; cleanest is a small translation at the `/chat` route or `answer_question_with_graph` boundary. Keep `HTTPException` out of `GroqProvider`.

2. **Discrete `[1][2]` vs. preserved `[1, 2]` canonical output** — see Assumption A2. **(RESOLVED — discrete `[1][2]` adopted as the canonical output form per Plan 02-02's parser design; matches the Phase 3 frontend "discrete badges" contract.)** Confirm against the Phase 3 frontend badge contract before locking the parser's output format.

3. **Few-shot examples in the system prompt** — AI-SPEC §4b recommends 1–2 inline static examples. **(RESOLVED — Plan 02-03 Task 1 adds 1–2 minimal inline few-shot examples to the system prompt alongside the `[N]` instruction and the no-fabrication rule.)** The current system prompt is already long and table-heavy; planner should decide placement and keep it minimal.

4. **`backend/eval/citations_golden.jsonl` ownership** — AI-SPEC §5 says domain experts (lawyer/analyst) label it, built concurrently with implementation. **(RESOLVED — Plan 02-00 Task 3 seeds a pragmatic engineer-authored 3–5 record golden seed set against the existing `backend/tests/fixtures/pdfs/`, expandable later; the 16-pair domain-expert-labeled target is aspirational, not a Phase 2 gate.)** For a solo-developer reality, the planner should decide a pragmatic v1: a smaller engineer-authored seed set against the existing `backend/tests/fixtures/pdfs/` (merger agreement + annual report PDFs are already present, plus 3 new fixture PDFs added recently per git status), expandable later.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `groq` | `GroqProvider` | ✓ | 1.2.0 | — |
| `tiktoken` | `token_count` / chunker | ✓ | 0.12.0 | — |
| `difflib` | quote extraction (recommended) | ✓ | stdlib (Python 3.13.0) | — |
| `rapidfuzz` | quote extraction (AI-SPEC's assumed choice) | ✗ | — | **Use `difflib` (stdlib) — recommended** |
| `pydantic` | `DoneEvent`/`Source` validation | ✓ | (via fastapi) | — |
| `ragas` | semantic eval tests only | ✗ | — | Code-based eval (the 4 Critical dims) runs without it; RAGAS gated `-m semantic` |
| `pytest` / `TestClient` | all tests | ✓ | in use | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:**
- `rapidfuzz` → `difflib` (stdlib) — recommended path, no install.
- `ragas` → only needed for the gated semantic test file; the 4 Critical code-based eval dimensions need nothing new. Planner: `pip install ragas==0.2.*` into a new `backend/requirements-dev.txt`.

## Project Constraints (from CLAUDE.md)

`./CLAUDE.md` is a skill-routing file only — no coding conventions, forbidden patterns, or test rules. No actionable build directives. (Skill routing: bugs → `/investigate`, code review → `/review`, etc. — not relevant to planning task content.)

From `MEMORY.md` (user auto-memory): **PDF extractors `pdfplumber` and `docling` have both failed on this user's PDFs — do not propose either.** Not relevant to Phase 2 (no PDF extraction work here) but noted for completeness.

## Sources

### Primary (HIGH confidence — direct codebase reads this session)
- `backend/app/services/langgraph_rag.py` — full file, all functions
- `backend/app/services/groq_client.py` — full file
- `backend/app/models/schemas.py` — full file
- `backend/app/config.py` — full file
- `backend/app/api/routes_chat.py` — full file
- `backend/app/services/chunker/tokens.py` — full file
- `backend/app/services/vector_store.py` — `search_chunks`, `parent_lookup`, `get_all_documents`
- `backend/tests/test_pipeline_smoke.py`, `conftest.py`, `test_groq_client.py` — full files
- `backend/requirements.txt` — full file
- `python -c "import rapidfuzz/groq/tiktoken"` — version verification (rapidfuzz absent; groq 1.2.0; tiktoken 0.12.0; Python 3.13.0)
- `.planning/phases/02-citations-backend/02-CONTEXT.md`, `02-AI-SPEC.md`
- `.planning/REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`, `.planning/phases/01-chunking-rebuild/01-CONTEXT.md`

### Secondary (MEDIUM confidence)
- AI-SPEC.md §3–5 — framework/pattern guidance (note: its rapidfuzz-in-requirements claim is CORRECTED above)

## Metadata

**Confidence breakdown:**
- Current-state code read: HIGH — every file read directly this session
- Parser design: HIGH — grounded in the confirmed token/SSE shapes
- Quote-extraction (difflib): HIGH — stdlib, verified available; rapidfuzz absence verified
- D-06 reconciliation: HIGH — matches AI-SPEC Pitfall 1 + chunk-identity reasoning
- Validation architecture: HIGH — existing harness read directly

**Research date:** 2026-05-14
**Valid until:** ~2026-06-14 (stable — internal codebase, no fast-moving external deps; re-verify if `groq` SDK is bumped)
</content>
