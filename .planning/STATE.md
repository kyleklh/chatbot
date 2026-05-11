# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-11)

**Core value:** Every assistant claim has a clickable inline citation that jumps to the correct page with the correct supporting quote.
**Current focus:** Phase 1 — Chunking rebuild

## Current Position

Phase: 1 of 6 (Chunking rebuild)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-05-11 — Roadmap created from new-project ingest of DESIGN_DECISIONS.md (ADR), PROJECT.md source (PRD), and TODOS.md (DOC).

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| — | — | — | — |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

7 LOCKED ADR decisions in PROJECT.md Key Decisions (DEC-per-message-sources, DEC-conversation-history-sidebar, DEC-per-document-filter-chips, DEC-upload-progress-states, DEC-mobile-deferred, DEC-document-management-tooltip, DEC-implementation-order). 6 open decisions deferred to phase planning (extractor, chunking algorithm, vector store keep/swap, auth provider, deploy platform, v1 LLM provider).

### Pending Todos

None yet. Backlog topics captured in `.planning/intel/context.md` (evaluation harness, query observability, multi-format loaders, cloud connectors beyond Drive, vision-LLM multimodal extraction, OpenRouter fallback chain) — surfaced as v2 in REQUIREMENTS.md.

### Blockers/Concerns

- Groq free tier rate-limits aggressively, sometimes truncating streams so `onDone` never fires → empty sources panel. Mitigation = REQ-provider-flexible-llm (verified in Phase 2). Watch during Phase 2.
- Open decision in Phase 1: which PDF extractor (PyMuPDF base is leading candidate; `pdfplumber` and `docling` are LOCKED-out).
- Open decision in Phase 5: deployment platform among Vercel+Fly/Render split, single VPS+Docker, Render full-stack.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-11
Stopped at: Roadmap + STATE created from new-project ingest. Next step is `/gsd-plan-phase 1`.
Resume file: None
