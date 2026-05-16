---
phase: 02-citations-backend
verified: 2026-05-15T00:00:00Z
status: passed
score: 5/5 success criteria verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 2: Citations Backend — Verification Report

**Phase Goal:** The backend can emit grounded `[N]` markers inside the streamed answer, each resolving to a specific chunk, its page, and a supporting quote — through a provider-agnostic LLM call site.

**Verified:** 2026-05-15
**Status:** PASSED
**Re-verification:** No — initial verification.

## Goal Achievement

### Observable Truths (Success Criteria)

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| SC1 | Streaming response includes inline `[N]` markers emitted DURING generation | VERIFIED | `backend/app/services/langgraph_rag.py:322-330` wraps `provider.stream()` with `CitationStreamParser.feed()/flush()` and yields `{"token": clean}` SSE frames per cleaned chunk. End-to-end asserted by `tests/test_pipeline_smoke.py::test_pipeline_smoke_stream_marker` (lines 195-213) which locates `[N]` in tokens BEFORE the `done` event. PASSED. |
| SC2 | Each marker resolves server-side to a chunk_id, document_id, page, and verbatim supporting quote | VERIFIED | `CitationStreamParser._process_markers` (parser.py:126-153) maps each canonical `[N]` to `self._sources[n-1].chunk_id`. `enriched_sources()` (parser.py:161-179) emits chunk_id+document_id+page+quote per source. Quote is verbatim-substring by construction via `difflib.SequenceMatcher(autojunk=False)` in `citations/quotes.py`. `test_pipeline_smoke_stream_marker` (lines 219-226) asserts every `done.sources[].{chunk_id, document_id, page, quote}` is non-empty. `tests/test_citations_eval.py::test_verbatim_quote_is_substring_of_chunk` proves verbatim-substring property at unit level. |
| SC3 | Per-message `sources[]` payload (LOCKED schema) carries chunk_id+page+quote per source | VERIFIED | `app/models/schemas.py:16-26` extends `Source` with `chunk_id`/`document_id`/`quote`. `DoneEvent` (schemas.py:34-60) has `field_validator("marker_map")` rejecting any marker value not in `sources[].chunk_id`. Validated end-to-end via `DoneEvent.model_validate(done_payload)` in pipeline smoke test (line 217). |
| SC4 | LLM call site behind thin abstraction (Groq→Gemini swap doesn't touch graph nodes) | VERIFIED | `langgraph_rag.py:10` imports only `from app.services.llm import get_provider`. All three call sites (`rewrite_question_node:68`, `answer_node:235`, `stream_answer_with_graph:322`) call `get_provider().generate(...)` / `.stream(...)`. `LLMProvider` Protocol (`llm/base.py:15-29`) is 3-method `@runtime_checkable`. `get_provider()` factory (`llm/factory.py:19-34`) switches on `LLM_PROVIDER` config with allow-list `ValueError`. `groq_client.py` shim DELETED (confirmed absent on disk). 16 tests in `test_llm_provider.py` exercise Protocol/factory/cache/native-exception paths. |
| SC5 | `/chat/stream` continues to accept LOCKED `document_ids: list[str]` filter without regression | VERIFIED | `ChatRequest.document_ids: list[str] \| None` (schemas.py:11). `routes_chat.py:35-52` passes through unchanged. `stream_answer_with_graph` signature accepts `document_ids` (langgraph_rag.py:298) and threads it via `retrieve_node` to `search_chunks` + `search_bm25` (lines 86, 92). `tests/test_pipeline_smoke.py::test_document_ids_filter` (lines 238-312) verifies (a) original no-leak invariant AND (b) SC5 provenance — every cited chunk's document_id ⊆ requested filter, via `marker_map → done.sources`. PASSES. |

**Score:** 5/5 success criteria verified.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `backend/app/services/llm/base.py` | LLMProvider Protocol | VERIFIED | 30-line @runtime_checkable Protocol with stream/generate/token_count. |
| `backend/app/services/llm/groq_provider.py` | GroqProvider concrete | VERIFIED | Lazy client init, instance tokenizer, native exceptions per D-08. |
| `backend/app/services/llm/factory.py` | get_provider() + cache | VERIFIED | Process-local cache, allow-list ValueError on unknown provider. |
| `backend/app/services/citations/parser.py` | CitationStreamParser | VERIFIED | feed/flush/marker_to_chunk_id/enriched_sources; tolerant streaming with hold-back. |
| `backend/app/services/citations/quotes.py` | Verbatim quote extractor | VERIFIED | `best_quote_span` + `extract_quote`; difflib autojunk=False; substring by construction. |
| `backend/app/models/schemas.py` | Source ext + DoneEvent | VERIFIED | Source.chunk_id/document_id/quote (default ""); DoneEvent.field_validator for marker_map. |
| `backend/app/services/langgraph_rag.py` | Rewired through get_provider() | VERIFIED | No `groq` imports by name; all 3 call sites use `get_provider()`; CitationStreamParser wired inside try; DoneEvent built with bounded-retry on ValidationError. |
| `backend/app/api/routes_chat.py` | 503 translation + unchanged stream signature | VERIFIED | 503 translation absorbed (lines 19-32) for non-streaming; `/chat/stream` still passes document_ids. |
| `backend/app/services/groq_client.py` | DELETED | VERIFIED | Absent on disk; no remaining importers (grep returns only doc references in routes_chat.py and groq_provider.py comments). |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `langgraph_rag.stream_answer_with_graph` | `CitationStreamParser` | `parser.feed/flush` inside try | WIRED | langgraph_rag.py:323-330. |
| `langgraph_rag.stream_answer_with_graph` | `DoneEvent` | `parser.enriched_sources()` + `parser.marker_to_chunk_id()` → `DoneEvent(...)` → bounded-retry on ValidationError | WIRED | langgraph_rag.py:335-365. |
| Graph nodes | `LLMProvider` | `get_provider().generate/stream` | WIRED | langgraph_rag.py:68, 235, 326. |
| `routes_chat.chat` | `HTTPException(503)` | try/except around `answer_question_with_graph` | WIRED | routes_chat.py:19-32. |
| `bm25_retriever.search_bm25` → `_rrf_merge` → `CitationStreamParser` | top-level chunk_id preserved | Plan 02-03 Rule-1 fix surfacing chunk_id at top level | WIRED | bm25_retriever.py change confirmed by smoke test assertion that every Source has non-empty chunk_id. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `DoneEvent.sources` | enriched sources list | `parser.enriched_sources()` reads from `filtered_sources` populated by `retrieve_node`→`filter_sources_node`→`rerank` (real Chroma + BM25 hit, real cross-encoder) | Yes — verified end-to-end in smoke test with real BGE embeddings + real CrossEncoder reranker + ephemeral Chroma + synthetic PDF | FLOWING |
| `DoneEvent.marker_map` | marker→chunk_id dict | Populated as `CitationStreamParser._process_markers` runs over real stream tokens | Yes — non-empty marker_map asserted at smoke test line 229 | FLOWING |
| SSE `token` events | parser-cleaned token strings | `provider.stream()` (real Groq in prod, _FakeProvider in test) → `parser.feed()` → yielded as `{"token": ...}` | Yes — markers normalized, unresolvable stripped, verified in test | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Provider seam imports succeed | `python -c "from app.services.llm import get_provider; from app.services.citations.parser import CitationStreamParser; from app.models.schemas import DoneEvent"` | OK | PASS |
| Provider seam: no Groq import by name in graph | `grep -E "generate_with_groq\|stream_with_groq" backend/app/services/langgraph_rag.py` | (empty) | PASS |
| groq_client.py shim deleted | `ls backend/app/services/groq_client.py` | No such file | PASS |
| End-to-end SC1 stream marker | `pytest tests/test_pipeline_smoke.py::test_pipeline_smoke_stream_marker -q` | 1 passed | PASS |
| End-to-end SC5 provenance + no leak | `pytest tests/test_pipeline_smoke.py::test_document_ids_filter -q` | 1 passed | PASS |
| SC4 provider seam unit suite | `pytest tests/test_llm_provider.py -q` | (part of 25-pass batch) | PASS |
| SC2/SC3 citations parser unit suite | `pytest tests/test_citations_eval.py -q` | 12 passed, 1 skipped (Wave-0 stub now covered by integration smoke test) | PASS |
| Full quick suite | `pytest -q -m "not semantic"` | 48 passed, 1 skipped, 2 errors (pre-existing Chroma dim 384-vs-1 in test_retrieval_parent_expansion.py — out of scope) | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
| ----------- | ----------- | ------ | -------- |
| REQ-grounded-citations | Backend emits grounded `[N]` markers with per-marker chunk/page/quote provenance | SATISFIED | SC1+SC2+SC3 all VERIFIED above. |
| REQ-provider-flexible-llm | LLM call site abstracted; switching providers does not require graph-node edits | SATISFIED | SC4 VERIFIED. Adding a new provider is one new class file + one `elif` in factory.py. |
| REQ-no-happy-path-regressions | Existing /chat + /chat/stream + document_ids filter still work | SATISFIED | SC5 VERIFIED. Pipeline smoke test (real BGE + real CrossEncoder + ephemeral Chroma) green; 48 passed in full suite. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| backend/tests/test_citations_eval.py | 57 | `pytest.skip("Wave 0 stub — implemented in Plan 02-03")` | Info | The SC1 marker-during-generation behavior is now covered by `test_pipeline_smoke_stream_marker`. This unit stub is superseded by an integration test. Cleanup nice-to-have but not blocking. |

No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers in `app/services/llm/` or `app/services/citations/`. No empty implementations. No hardcoded empty arrays reaching rendering.

### Pre-existing Out-of-Scope Failures (acknowledged)

`tests/test_retrieval_parent_expansion.py::test_retrieval_parent_expansion` and `test_expand_node_tolerates_missing_parent` ERROR with `chromadb.errors.InvalidArgumentError: Collection expecting embedding with dimension of 384, got 1`. Verified pre-existing in Plan 02-03 by stash + re-run on parent commit. Recommend a follow-up plan addressing parent-expansion test fixtures. **Not a Phase 2 gap.**

### Gaps Summary

None blocking. All 5 Success Criteria from ROADMAP.md Phase 2 are observably true in the codebase and verified by passing tests. All three declared requirements (REQ-grounded-citations, REQ-provider-flexible-llm, REQ-no-happy-path-regressions) are satisfied.

The single skipped unit test (`test_stream_marker_emitted_during_generation`) is intentional dead weight — its SC1 coverage moved to the integration smoke test. Suggested follow-up: delete the stub in a future plan; non-blocking.

---

_Verified: 2026-05-15_
_Verifier: Claude (gsd-verifier)_
