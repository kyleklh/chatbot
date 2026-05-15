---
phase: 02-citations-backend
plan: 01
subsystem: api
tags: [llm, provider-pattern, groq, protocol, factory, fastapi, tiktoken]

# Dependency graph
requires:
  - phase: 02-citations-backend
    provides: "Wave 0 test stubs (test_llm_provider.py 8-test skip suite)"
provides:
  - "LLMProvider Protocol (3-method surface: stream/generate/token_count) — D-06"
  - "GroqProvider with lazy client construction (Pitfall 4) and instance tokenizer"
  - "get_provider() factory with process-local cache + allow-list ValueError (T-02-01-01)"
  - "LLM_PROVIDER + LLM_TEMPERATURE config keys (D-07, AI-SPEC §4)"
  - "groq_client.py shim that owns the HTTPException(503) translation (out of provider seam)"
  - "21 green tests covering SC4 (16 in test_llm_provider.py + 5 in test_groq_client.py)"
affects:
  - "02-03 (graph node rewiring): will replace groq_client shim imports with get_provider() and relocate 503 translation to routes_chat.py"
  - "02-02 (citation parser): can adopt get_provider() for any LLM-judge evals"
  - "any future provider (Gemini/Anthropic/OpenRouter): one new class file + one elif branch in factory.py"

# Tech tracking
tech-stack:
  added: []  # No new deps — uses existing groq, tiktoken, fastapi.
  patterns:
    - "Provider seam pattern: @runtime_checkable Protocol + concrete class + factory"
    - "Lazy client construction in __init__ (never module-scope) — Pitfall 4"
    - "Process-local instance cache keyed on provider name"
    - "Native-exception boundary (D-08): provider raises SDK exceptions; framework translation lives at the caller boundary"

key-files:
  created:
    - "backend/app/services/llm/__init__.py"
    - "backend/app/services/llm/base.py"
    - "backend/app/services/llm/groq_provider.py"
    - "backend/app/services/llm/factory.py"
  modified:
    - "backend/app/config.py"
    - "backend/app/services/groq_client.py"
    - "backend/app/services/chunker/tokens.py"
    - "backend/tests/test_llm_provider.py"
    - "backend/tests/test_groq_client.py"

key-decisions:
  - "Kept groq_client.py as a thin shim (NOT deleted) so langgraph_rag.py imports still resolve until Plan 02-03 rewires graph nodes. Shim owns the HTTPException(503) translation for the non-streaming path."
  - "Relocated 503 translation to groq_client.py (the shim), not to routes_chat.py — chosen because the graph nodes call generate_with_messages directly, so translating at the shim preserves /chat behavior without modifying graph nodes (out of scope for 02-01). Plan 02-03 will move the translation to routes_chat.py when it rewires the nodes."
  - "Streaming path passes native exceptions through (no HTTPException wrap) — preserves the SSE 'temporarily unavailable' fallback token rendered by stream_answer_with_graph."
  - "Provider tokenizer kept as instance attribute (self._enc) per D-06 — distinct from chunker/tokens.py module singleton; both annotated with cross-reference comments."

patterns-established:
  - "Protocol-based provider seam: adding a new LLM = new class + one elif branch in factory.py"
  - "Lazy client construction lets `from app.services.llm import ...` succeed with no API key (tests, dev bootstrap)"
  - "Native-exception boundary: the llm/ package is FastAPI-free; framework translation is the caller's job"

requirements-completed:
  - "REQ-provider-flexible-llm"

# Metrics
duration: ~75min
completed: 2026-05-15
---

# Phase 02-01: LLM Provider Seam Summary

**LLMProvider Protocol + GroqProvider + get_provider() factory, with lazy client construction, native-exception boundary (D-08), and the HTTPException(503) translation relocated to a transitional groq_client.py shim.**

## Performance

- **Duration:** ~75 min (includes Windows-pytest contention debugging with parallel plan 02-02)
- **Started:** 2026-05-15T12:00:00Z
- **Completed:** 2026-05-15T13:15:00Z
- **Tasks:** 3
- **Files modified:** 9 (4 created, 5 modified)

## Accomplishments

- **Provider seam package `app/services/llm/`** built per AI-SPEC §3 — 4 files (`base.py`, `groq_provider.py`, `factory.py`, `__init__.py`), all FastAPI-free, all importable with `GROQ_API_KEY` unset.
- **GroqProvider** wraps the Groq SDK with a lazy `self._client = Groq(...)` (Pitfall 4) and an instance-scoped `self._enc = tiktoken.get_encoding("cl100k_base")` (D-06 LLM-boundary tokenizer). `stream`/`generate` raise NATIVE SDK exceptions, not `HTTPException` (D-08).
- **`get_provider()` factory** switches on `LLM_PROVIDER.lower()` with a strict allow-list (`"groq"` → cached `GroqProvider()`, anything else → `ValueError`) per T-02-01-01 (Tampering mitigation).
- **`HTTPException(503)` translation relocated** out of the provider into `groq_client.py` (the transitional shim) — the `llm/` package stays framework-free.
- **`config.py`** gains `LLM_PROVIDER` (default `"groq"`) and `LLM_TEMPERATURE` (default `0.0`) per D-07 and AI-SPEC §4.
- **`chunker/tokens.py`** annotated with a D-06 cross-reference comment — the ingest-time tokenizer stays provider-agnostic and is NEVER routed through `get_provider()`.
- **21 green tests covering SC4**: 16 in `test_llm_provider.py` (factory branching, caching, unknown→ValueError, Protocol satisfaction via `_FakeProvider`, GroqProvider stream/generate/empty/token_count, native-exception assertions for both stream and generate); 5 in `test_groq_client.py` (migrated 4 legacy behaviors + 1 added for `generate_with_messages`).

## Task Commits

1. **Task 1: Create the llm/ provider seam package** — `8d14223` (feat)
2. **Task 2: Shrink groq_client.py + relocate the 503 translation** — `6474f03` (refactor)
3. **Task 3: Implement test_llm_provider.py + migrate test_groq_client.py** — `0d44e09` (test)

## Files Created/Modified

- `backend/app/services/llm/__init__.py` — Barrel re-export of `get_provider` and `LLMProvider`.
- `backend/app/services/llm/base.py` — `@runtime_checkable class LLMProvider(Protocol)` with `stream`, `generate`, `token_count`.
- `backend/app/services/llm/groq_provider.py` — `GroqProvider` (lazy `Groq` client, instance tokenizer, native exceptions).
- `backend/app/services/llm/factory.py` — `_PROVIDER_CACHE` + `get_provider()` (allow-list switch, ValueError on unknown).
- `backend/app/config.py` — Adds `LLM_PROVIDER` and `LLM_TEMPERATURE` env-driven constants.
- `backend/app/services/groq_client.py` — Reduced from 47 lines of SDK calls to a 53-line shim that delegates to `get_provider()` and owns the 503 translation.
- `backend/app/services/chunker/tokens.py` — D-06 cross-reference comment only (no logic change).
- `backend/tests/test_llm_provider.py` — Wave-0 skip stubs replaced with 16 real tests.
- `backend/tests/test_groq_client.py` — 4 legacy tests retargeted at the shim's `get_provider()` delegation; +1 new test for `generate_with_messages`.

## Decisions Made

- **Shim-vs-delete (Plan 02-03 handoff):** `groq_client.py` is KEPT as a thin shim, not deleted. Rationale: `langgraph_rag.py` line 9 still imports `generate_with_groq`/`generate_with_messages`/`stream_with_groq` from it. Deleting the module here would either force a 02-01 scope-creep into graph-node rewiring or leave a broken import. Plan 02-03's "groq_client.py finalized" task should now (a) rewire those graph-node imports to `from app.services.llm import get_provider`, (b) move the 503 try/except to the `/chat` handler in `routes_chat.py`, and (c) delete `groq_client.py` and `test_groq_client.py`.
- **503 translation lives in `groq_client.py` (the shim), not in `routes_chat.py`:** Chosen because `/chat` calls `answer_question_with_graph()` which calls graph nodes which call `generate_with_messages()` — translating at the shim preserves the existing 503 surfacing without modifying graph code, which is explicitly out of scope for this plan. The translation will move to `routes_chat.py` in Plan 02-03 as part of the graph-node rewiring.
- **Streaming path is HTTPException-free:** `stream_with_groq` yields native exceptions through; `stream_answer_with_graph` already catches and emits a graceful "temporarily unavailable" SSE token. Wrapping in HTTPException there would break the SSE contract.
- **Temperature default = 0.0** for deterministic eval reproducibility (AI-SPEC §4). Passed on both `create()` calls in `GroqProvider`.

## Deviations from Plan

None - plan executed exactly as written. All decisions above were explicitly enumerated as options in the plan's `<action>` block; the SUMMARY records the choices.

## Issues Encountered

- **Windows pytest contention with parallel plan 02-02:** Running the full quick suite (`pytest -m "not semantic"`) repeatedly hung at 8-11 dots due to ChromaDB filesystem lock contention with a concurrent pytest process from plan 02-02 (running in a sibling worktree/agent per the concurrency note). Resolution: ran a focused subset (`test_llm_provider.py`, `test_groq_client.py`, `test_chunker_*.py`, `test_fixtures.py`) covering 25 tests, all green — this set covers all 02-01-affected modules. The remaining tests (`test_chunker_pipeline.py`, `test_retrieval_parent_expansion.py`, `test_migration_reindex.py`) are not affected by Phase 02-01 changes (no shared modules touched). Plan 02-03 or post-phase verification should run the full quick suite once parallel work settles.

## Plan 02-03 Handoff (explicit, per Task 2 acceptance criterion)

- **Shim status:** `backend/app/services/groq_client.py` KEPT as a thin shim. Public names still importable: `generate_with_groq`, `generate_with_messages`, `stream_with_groq`.
- **503 translation home:** Currently in `backend/app/services/groq_client.py` (shim). Move to `backend/app/api/routes_chat.py` `/chat` handler `try/except` in Plan 02-03.
- **What Plan 02-03 needs to do:**
  1. Rewire `backend/app/services/langgraph_rag.py` line 9 import to `from app.services.llm import get_provider`; replace call sites with `get_provider().generate(...)` / `get_provider().stream(...)`.
  2. Add `try/except Exception` in `routes_chat.py` `/chat` that translates native provider exceptions to `HTTPException(503)`.
  3. Delete `backend/app/services/groq_client.py` and `backend/tests/test_groq_client.py`.

## Threat Flags

None — no new trust-boundary surface introduced beyond what the plan's `<threat_model>` enumerates. T-02-01-01 (factory tampering) and T-02-01-02 (API-key info disclosure) are both mitigated as planned.

## Self-Check: PASSED

Created files verified:
- `backend/app/services/llm/__init__.py` — FOUND
- `backend/app/services/llm/base.py` — FOUND
- `backend/app/services/llm/groq_provider.py` — FOUND
- `backend/app/services/llm/factory.py` — FOUND

Commits verified:
- `8d14223` — FOUND
- `6474f03` — FOUND
- `0d44e09` — FOUND

Tests verified:
- `pytest tests/test_llm_provider.py tests/test_groq_client.py -q` → 21 passed, 0 skipped, 0 errors.

## Next Phase Readiness

- **SC4 met:** `LLMProvider` Protocol + `GroqProvider` + `get_provider()` factory exist; swapping providers is a new class + one `elif` branch in `factory.py`.
- **Plan 02-03 unblocked:** Has everything it needs — provider seam ready, handoff documented above.
- **Plan 02-02 unblocked:** Can adopt `get_provider()` for any LLM-judge eval calls (citation parser unit tests are SDK-free per plan, but the eval harness can use it).

---
*Phase: 02-citations-backend*
*Completed: 2026-05-15*
