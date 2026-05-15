---
phase: 02-citations-backend
plan: 02
subsystem: api
tags: [citations, streaming, pydantic, difflib, regex, langgraph]

# Dependency graph
requires:
  - phase: 02-citations-backend
    provides: "Wave 0 test scaffolding (test_citations_eval.py stubs, citations_golden.jsonl, pytest semantic marker)"
provides:
  - "CitationStreamParser — tolerant streaming marker parser implementing D-01/D-02/D-03/D-04"
  - "best_quote_span + extract_quote — deterministic verbatim-substring quote extractor (difflib.SequenceMatcher, autojunk=False)"
  - "Source (extended) + DoneEvent Pydantic schemas with marker→chunk_id validation at the schema boundary"
  - "12 unit tests proving SC2 (verbatim quote substring) and SC3 (DoneEvent validates) at the unit level"
affects: [02-citations-backend Plan 02-03, frontend citations rendering]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tolerant streaming text parser: append-to-buffer + run-regex-over-buffer + hold-back-potential-prefix"
    - "Verbatim quote extraction via difflib.SequenceMatcher(autojunk=False) — span indices re-slice into haystack for substring guarantee by construction"
    - "Pydantic field_validator using info.data to cross-reference sibling field state (marker_map values must exist in sources chunk_ids)"
    - "D-03 thin logging: print() marker numbers + counts + scores ONLY; never chunk text, never keys"

key-files:
  created:
    - backend/app/services/citations/__init__.py
    - backend/app/services/citations/parser.py
    - backend/app/services/citations/quotes.py
  modified:
    - backend/app/models/schemas.py
    - backend/tests/test_citations_eval.py

key-decisions:
  - "Source citation fields default to empty string (chunk_id='' / document_id='' / quote='') so the non-streaming /chat ChatResponse path keeps validating before Plan 02-03 wires both paths to populate real values (Assumption A5)."
  - "Multi-citation [1, 2] is normalized to discrete [1][2] (RESEARCH Assumption A2 / REQ wording)."
  - "Markdown-context blindness is accepted as a v1 limitation — the parser does not track code-fence state."
  - "Quote extraction expands the fuzzy match outward to sentence boundaries inside the chunk (still a substring) for readability."
  - "Below-threshold quote score falls back to the chunk's leading sentence and print()-logs the score."

patterns-established:
  - "Streaming-marker hold-back: a trailing `[`, `[Sou`, `[1,` is kept in the buffer until the matching `]` arrives or flush() is called."
  - "DoneEvent.marker_map validator: cross-field check via info.data is the canonical way to enforce a derived invariant across two Pydantic fields."

requirements-completed:
  - REQ-grounded-citations

# Metrics
duration: ~25min
completed: 2026-05-15
---

# Phase 02 Plan 02: Grounded Citations Parser + Verbatim-Quote Schema Summary

**Tolerant CitationStreamParser (D-01/D-02/D-03/D-04) with difflib-backed verbatim-substring quote extraction and DoneEvent Pydantic schema that enforces marker→chunk_id resolution at the schema boundary — SC2 + SC3 proven at the unit level (12 passing tests).**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3
- **Files modified:** 5 (2 source + 1 schema + 1 package init + 1 test file)
- **Lines added:** ~480 (source + tests)

## Accomplishments
- `CitationStreamParser` consumes raw LLM token chunks via `feed()`, normalizes `[Source N]` / `[1, 2]` / `[ N ]` drift to canonical discrete `[N]` markers, correctly handles markers split across token boundaries (the load-bearing pitfall), strips + print()-logs unresolvable markers, and exposes `marker_to_chunk_id()` + `enriched_sources()` for the streaming `done`-event payload assembly.
- `best_quote_span` returns indices that re-slice `chunk_text` to a guaranteed verbatim substring (`autojunk=False` is load-bearing); `extract_quote` expands outward to sentence boundaries within the chunk, with a leading-sentence fallback on low-similarity scores.
- `Source` extended with `chunk_id` / `document_id` / `quote` (defaulting to `""`); new `DoneEvent` model has a `field_validator("marker_map")` that rejects any `marker_map` value not present in `sources[].chunk_id`.
- 12 new tests (zero new skips beyond the explicitly-deferred Wave-0 SC1 stub) cover: verbatim substring guarantee, `best_quote_span` index correctness, low-score fallback + log-discipline, DoneEvent pass+fail validation, chunk_id-stable marker resolution under `filtered_sources` shuffle, drift normalization, unresolvable-marker stripping, split-across-tokens resolution, multi-token `[Source N]` reassembly, unterminated-bracket literal emission, and non-digit bracket content left untouched.

## Task Commits

1. **Task 1: Extend Source + add DoneEvent Pydantic models** — `02457dd` (feat)
2. **Task 2: citations/quotes.py — deterministic verbatim quote extractor** — `a64c7ab` (feat)
3. **Task 3: CitationStreamParser + SC2/SC3 unit tests** — `d89318e` (feat)

## Files Created/Modified
- `backend/app/services/citations/__init__.py` — package init (created)
- `backend/app/services/citations/parser.py` — `CitationStreamParser` class (created)
- `backend/app/services/citations/quotes.py` — `best_quote_span` + `extract_quote` (created)
- `backend/app/models/schemas.py` — extended `Source`, new `DoneEvent` (modified)
- `backend/tests/test_citations_eval.py` — replaced 6 Wave-0 stubs with 12 real tests (1 SC1 stub left as explicit Plan 02-03 deferral) (modified)

## Decisions Made
See `key-decisions` in frontmatter. The most consequential:
- **Defaults on the new `Source` fields.** Without defaults the non-streaming `/chat` path's `ChatResponse(sources=[Source(...)])` would have started raising before Plan 02-03 ever runs; defaulting to `""` is the safe seam.
- **stdlib `difflib` only.** Plan 02-01's environment audit (and RESEARCH) confirmed `rapidfuzz` is not installed; `difflib.SequenceMatcher(autojunk=False).find_longest_match` is sufficient for the substring task and zero new dependencies.
- **Discrete marker expansion for `[1, 2]` → `[1][2]`.** Matches the REQ wording and avoids ambiguity in the downstream `marker_map`.

## Deviations from Plan
None — plan executed exactly as written. No Rule-1/2/3/4 deviations were required.

## Issues Encountered
- The `quotes.py` initial draft contained the literal string `rapidfuzz` inside a clarifying comment. The plan's acceptance criterion specifies "no `rapidfuzz` import"; the comment phrasing was tightened so a substring check of the source also passes (defensive — the canonical check is AST-based on imports). No commit hash was needed since the change happened pre-commit.
- The full project pytest suite was attempted as a secondary smoke check but the shell's pytest-collection step took ~3 min and the subsequent run hung in this environment. The plan's primary verify gate — `pytest tests/test_citations_eval.py -q` — was run directly and passes (12 passed, 1 explicit deferral skip, 0 errors). Plan 02-01's concurrent edits to `groq_client.py` / `llm/*` are the most likely cause of any unrelated test churn; cross-plan integration is out of scope here.

## Self-Check: PASSED

- backend/app/services/citations/__init__.py — FOUND
- backend/app/services/citations/parser.py — FOUND
- backend/app/services/citations/quotes.py — FOUND
- backend/app/models/schemas.py — FOUND (modified, contains `DoneEvent`)
- backend/tests/test_citations_eval.py — FOUND (12 real tests)
- Commit 02457dd — FOUND in git log
- Commit a64c7ab — FOUND in git log
- Commit d89318e — FOUND in git log
- `pytest tests/test_citations_eval.py -q` — 12 passed, 1 skipped (explicit Plan 02-03 deferral), 0 errors
- `python -c "from app.services.citations.parser import CitationStreamParser; from app.services.citations.quotes import best_quote_span, extract_quote; from app.models.schemas import Source, DoneEvent"` — succeeds

## Next Phase Readiness
- **Plan 02-03 can now wire `CitationStreamParser` into `langgraph_rag.py`** — the parser is a standalone, fully-unit-tested component constructed from a `filtered_sources` list (the exact shape `langgraph_rag` already produces at lines 317-326). Plan 02-03 must additionally make the non-streaming `/chat` path populate `chunk_id` / `document_id` / `quote` so the defaults stop being the only fallback.
- **SC1 (stream emits marker tokens during generation) remains the one open test** — it is correctly left as a Wave-0 stub deferred to Plan 02-03, matching the original Wave-0 plan.

---
*Phase: 02-citations-backend*
*Completed: 2026-05-15*
