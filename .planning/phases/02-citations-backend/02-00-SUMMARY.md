---
phase: 02-citations-backend
plan: 00
subsystem: testing
tags: [pytest, ragas, citations, test-scaffolding, llm-provider]

requires:
  - phase: 01-rag-backend
    provides: existing pytest suite, test_groq_client.py, test_pipeline_smoke.py, fixture PDFs
provides:
  - Wave 0 test stubs for SC1-SC4 (15 skipped, named per VALIDATION.md)
  - Registered `semantic` pytest marker for gated LLM-judge tests
  - Dev-only `ragas==0.2.*` pin in requirements-dev.txt
  - Seed golden eval dataset (5 records, includes adversarial)
  - MIGRATION TARGET docstring on test_groq_client.py
affects: [02-01-provider-seam, 02-02-citations-parser, 02-03-streaming-integration]

tech-stack:
  added: [ragas (dev-only, pinned 0.2.*)]
  patterns:
    - "Wave 0 test scaffolding before implementation (Nyquist compliance)"
    - "Gated semantic marker isolates costly LLM-judge tests from default run"
    - "Engineer-authored seed JSONL with adversarial unanswerable record"

key-files:
  created:
    - backend/tests/test_llm_provider.py
    - backend/tests/test_citations_eval.py
    - backend/requirements-dev.txt
    - backend/eval/citations_golden.jsonl
  modified:
    - backend/pytest.ini
    - backend/tests/test_groq_client.py

key-decisions:
  - "Authoritative test-file names: test_llm_provider.py + test_citations_eval.py (per VALIDATION.md, supersedes RESEARCH.md drafts)"
  - "Stub bodies use pytest.skip() with import only of pytest at file scope — collection cannot fail on not-yet-created modules"
  - "ragas is dev-only (requirements-dev.txt), never installed in production image"
  - "Seed JSONL starts at 5 records; 16-pair domain-labeled target deferred per RESEARCH Open Question 4"

patterns-established:
  - "Wave 0 scaffolding plan: test stubs land before implementation plans reference them"
  - "Migration-target docstring marks tests scheduled for retargeting in later plans (preserve, don't delete)"

requirements-completed: [REQ-grounded-citations, REQ-provider-flexible-llm]

duration: ~10 min
completed: 2026-05-15
---

# Phase 02 Plan 00: Citations Backend Test Scaffolding Summary

**Wave 0 test scaffolding for Phase 2: 15 skipped pytest stubs covering SC1-SC4, registered `semantic` marker, seeded golden JSONL, and migration-marked existing groq_client tests.**

## Performance

- **Duration:** ~10 min
- **Tasks:** 3
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments

- Every Phase 2 Success Criterion (SC1-SC4) now traces to a named, runnable pytest target that exists on disk.
- `semantic` pytest marker registered — gated LLM-judge tests no longer warn.
- Wave 2 plans 02-01 and 02-02 can now reference these test files in their `<verify>` blocks (Nyquist compliance).
- Seed golden eval dataset is JSON-valid with at least one adversarial unanswerable record.
- The 4 existing `test_groq_client.py` tests are preserved (still green) and clearly marked as migration targets for Plan 02-01.

## Task Commits

1. **Task 1: Register pytest semantic marker + create requirements-dev.txt** — `4e42fbf` (chore)
2. **Task 2: Create test_llm_provider.py and test_citations_eval.py stubs** — `5bc8744` (test)
3. **Task 3: Seed citations_golden.jsonl + migration marker on test_groq_client.py** — `25c97af` (test)

## Files Created/Modified

- `backend/pytest.ini` — Added `markers` section registering `semantic`
- `backend/requirements-dev.txt` — New; pins `ragas==0.2.*` (dev-only)
- `backend/tests/test_llm_provider.py` — 8 stubs for SC4 provider Protocol seam (Plan 02-01)
- `backend/tests/test_citations_eval.py` — 7 stubs for SC1/SC2/SC3 parser + verbatim + schema (Plans 02-02, 02-03)
- `backend/eval/citations_golden.jsonl` — 5 records (4 answerable, 1 adversarial)
- `backend/tests/test_groq_client.py` — Added MIGRATION TARGET module docstring (test bodies untouched)

## Verification Results

- `python -m pytest --markers` → lists `semantic` marker (PASS)
- `python -m pytest tests/test_llm_provider.py tests/test_citations_eval.py -q` → 15 skipped (PASS)
- `python -m pytest tests/test_citations_eval.py -k verbatim` → 1/7 collected (PASS)
- `python -m pytest tests/test_citations_eval.py -k done_event_schema` → 1/7 collected (PASS)
- `python -m pytest tests/test_citations_eval.py -k stream_marker` → 1/7 collected (PASS)
- `python -m pytest tests/test_groq_client.py -q` → 4 passed (PASS)
- JSONL parses cleanly; `has_unanswerable: True` (PASS)

Combined run of the 3 affected files: **4 passed, 15 skipped, 1 warning** (the warning is the pre-existing `asyncio_mode` config note, out of scope per scope-boundary rule).

## Decisions Made

- Resolved naming conflict between RESEARCH.md (`test_provider_seam.py`, `test_citations_parser.py`) and VALIDATION.md (`test_llm_provider.py`, `test_citations_eval.py`) by selecting VALIDATION.md names per the plan's authoritative naming note.
- Stub files import only `pytest` at module scope to prevent collection-time failure on modules that do not yet exist.
- Used existing fixture PDF filenames (`Merger Agreement Contract Form Sample.pdf`, `ar_2025_e.pdf`) as `document_id` hints in golden JSONL.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None blocking. A pre-existing `PytestConfigWarning: Unknown config option: asyncio_mode` exists because `pytest-asyncio` is not installed in this environment. This is out of scope for this plan (scope boundary rule) and predates these changes.

## User Setup Required

None — no external service configuration required. `ragas` install is gated behind `pip install -r backend/requirements-dev.txt` and only matters when running `-m semantic`.

## Next Phase Readiness

- Wave 2 plans 02-01 (provider seam) and 02-02 (citations parser) can proceed; their `<verify>` blocks now have real test targets to reference.
- Wave 3 plan 02-03 (streaming integration) has its `test_stream_marker_emitted_during_generation` stub ready.
- No blockers for Wave 2.

## Self-Check: PASSED

- All 4 created files exist on disk:
  - `backend/tests/test_llm_provider.py` FOUND
  - `backend/tests/test_citations_eval.py` FOUND
  - `backend/requirements-dev.txt` FOUND
  - `backend/eval/citations_golden.jsonl` FOUND
- All 3 task commits exist in `git log`:
  - `4e42fbf` FOUND
  - `5bc8744` FOUND
  - `25c97af` FOUND
- All `<acceptance_criteria>` re-verified (see Verification Results above).
- Plan `<verification>` re-run on affected files: 4 passed, 15 skipped, zero ImportErrors, zero marker warnings.

---
*Phase: 02-citations-backend*
*Completed: 2026-05-15*
