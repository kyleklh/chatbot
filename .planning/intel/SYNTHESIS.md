# Synthesis summary

Entry point for downstream consumers (`gsd-roadmapper`, etc.). All counts below are derived from the per-type intel files in this directory.

Generated: ingest of 3 classified planning docs, mode = `new`.

---

## Doc counts by type

| Type | Count | Sources |
|---|---|---|
| ADR | 1 (LOCKED) | DESIGN_DECISIONS.md |
| PRD | 1 | PROJECT.md |
| SPEC | 0 | — |
| DOC | 1 | TODOS.md |
| **Total** | **3** | |

## Decisions

- **Locked decisions:** 7 (all from DESIGN_DECISIONS.md, /plan-design-review pass 2026-05-10)
  - DEC-per-message-sources
  - DEC-conversation-history-sidebar
  - DEC-per-document-filter-chips
  - DEC-upload-progress-states
  - DEC-mobile-deferred
  - DEC-document-management-tooltip
  - DEC-implementation-order
- **Proposed / open decisions:** 6 (from PROJECT.md §6, surfaced as open decisions for the roadmapper — see context.md "Topic: Open decisions")

See: `decisions.md`

## Requirements

- **Total:** 8
  - REQ-grounded-citations (Pillar A, highest priority)
  - REQ-context-preserving-chunking (Pillar B)
  - REQ-document-forward-ui-polish (Pillar C)
  - REQ-public-deployment-with-privacy-disclosure
  - REQ-no-happy-path-regressions
  - REQ-stretch-google-drive-oauth (stretch)
  - REQ-forward-compatible-multitenancy-schema (design constraint, not deliverable)
  - REQ-provider-flexible-llm
- All sourced from PROJECT.md.

See: `requirements.md`

## Constraints

- **Total:** 11
  - **nfr:** 5 (CON-blacklisted-pdf-extractors, CON-framework-lockin, CON-cost-sensitive, CON-no-train-privacy, CON-deployment-not-pure-serverless)
  - **scope-fence:** 1 (CON-out-of-scope-v1)
  - **api-contract (LOCKED via ADR):** 2 (CON-chat-stream-document-ids-param, CON-documents-endpoint-shape)
  - **schema (LOCKED via ADR):** 3 (CON-chroma-metadata-indexed-at, CON-message-sources-data-model, CON-conversation-history-localstorage-v1)

No formal SPEC docs were ingested; constraints are extracted from the LOCKED ADR (backend contracts) and PROJECT.md §5 non-negotiables.

See: `constraints.md`

## Context topics

- **Total topics:** 10
  - Current architecture snapshot (as of 2026-05-11)
  - User-confirmed gaps (drove the v1 milestone)
  - Backlog — UI/UX (mobile)
  - Backlog — Retrieval quality & evaluation
  - Backlog — Auth / multi-tenancy
  - Backlog — Multi-format document loaders
  - Backlog — Cloud storage connectors
  - Backlog — Infra / LLM provider swap
  - Backlog — Multimodal extraction (vision for tables + images)
  - GSD phase breakdown (author's suggested sequence)
  - Open decisions (handoff to roadmapper)

See: `context.md`

## Conflicts

- **BLOCKERS:** 0
- **WARNINGS (competing variants):** 0
- **INFO (auto-resolved / noted alignments):** 3

See: `../INGEST-CONFLICTS.md`

## Status

**READY** — no blockers, no competing variants. Safe to route to `gsd-roadmapper`.

## Pointers

- Decisions: `c:\Users\Kyle\chatbot\.planning\intel\decisions.md`
- Requirements: `c:\Users\Kyle\chatbot\.planning\intel\requirements.md`
- Constraints: `c:\Users\Kyle\chatbot\.planning\intel\constraints.md`
- Context: `c:\Users\Kyle\chatbot\.planning\intel\context.md`
- Conflicts report: `c:\Users\Kyle\chatbot\.planning\INGEST-CONFLICTS.md`
- Source classifications: `c:\Users\Kyle\chatbot\.planning\intel\classifications\`
