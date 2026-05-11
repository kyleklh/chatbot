# DocuRAG

## What This Is

A document-forward RAG SaaS for individual knowledge workers and prosumers. Users upload PDFs (with future Google Drive / SharePoint / Dropbox / Notion connectors), read them in a paper-like canvas, and chat with them with grounded, page-cited answers. v1 is desktop-only, single-user, BYO-documents.

## Core Value

Every assistant claim has a clickable inline citation that jumps to the correct page with the correct supporting quote. If everything else fails, citation accuracy on the user's own PDFs must work.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- Upload → chunk → embed → ask → streamed answer with sources happy path (existing pipeline; must not regress)
- Hybrid retrieval: vector + BM25 via RRF + cross-encoder reranker
- React 19 + Vite + Tailwind v4 frontend with chat panel, document list, PDF viewer, upload zone, conversations list, sources panel
- Conversation history persisted in `localStorage` (`frontend/src/storage.js`)

### Active

<!-- v1 scope. Building toward these. See REQUIREMENTS.md for full list and IDs. -->

- [ ] Grounded inline citations during streamed answers (Pillar A — highest priority)
- [ ] Layout-aware + hierarchical chunking (Pillar B — citations depend on chunk identity)
- [ ] Document-forward UI polish pass (Pillar C — consumes 7 LOCKED ADR decisions)
- [ ] Public deployment with no-train privacy disclosure surfaced in UI
- [ ] No happy-path regressions (upload → chat must keep working)
- [ ] Forward-compatible multi-tenancy schema (every new persistent row carries or can trivially carry `user_id`)
- [ ] Provider-flexible LLM (thin abstraction so Groq → Gemini / OpenRouter / Anthropic is a one-file swap)
- [ ] (Stretch) Google Drive OAuth as first external source

### Out of Scope

<!-- Locked v1 exclusions. -->

- Mobile / narrow-viewport UI — LOCKED defer per ADR DEC-mobile-deferred; desktop-first reading tool
- Team / workspace collaboration — single-user v1; schema must stay multi-tenancy-compatible though
- Billing / paywall / usage metering — pre-revenue v1
- In-PDF annotations, highlights, note-taking — reader, not editor
- Slack ingestion, audio / video document types — PDF-only v1
- Backend persistence of conversations — deferred until auth lands (localStorage only in v1)
- `pdfplumber` and `docling` PDF extractors — both already failed on real user PDFs (pdfplumber: didn't work; docling: ~2s/page + high RAM)

## Context

**Current architecture (2026-05-11):**
- Backend: FastAPI in `backend/app/`. RAG = LangGraph state machine (`langgraph_rag.py`). Hybrid retrieval (`bm25_retriever.py` + `vector_store.py` via RRF). Cross-encoder reranker (`reranker.py`). LLM via Groq (`groq_client.py`). PDF loader + chunker (`pdf_loader.py`, `chunker.py`).
- Frontend: React 19 + Vite + Tailwind v4.
- Deploy: not yet wired. Auth: none. Tenancy: implicit single-user.

**User-confirmed gaps driving v1:**
1. Citations exist but aren't tight — no inline `[1][2]` in streamed output, no hover quote, no click-to-jump-to-page.
2. Current chunker destroys context — breaks tables, headers, multi-page concepts. Canonical bug: Quebec row from RBC annual report Table 43 returned Atlantic provinces' values.
3. No auth, no multi-user, no external sources — all v2+, but v1 schema cannot block them.

**Known concerns:**
- Groq free tier rate-limits aggressively, sometimes cutting streams mid-sentence so `onDone` never fires → empty sources panel. Provider-flexible abstraction (Gemini / OpenRouter fallback) is the planned mitigation.
- Multimodal vision-LLM extraction for suspect tables is a known follow-up, not v1.
- Evaluation harness (golden Q&A dataset) and query observability are valuable but post-v1.

## Constraints

- **Tech stack (LOCKED):** FastAPI backend + React/Vite frontend. No framework migrations.
- **Tech blacklist (LOCKED):** No `pdfplumber`, no `docling`. PyMuPDF (`fitz`) is the likely base; layout pass built on top.
- **Privacy (LOCKED):** User documents must not train any model. Use no-train API endpoints only (Anthropic, OpenAI zero-retention, Groq per ToS). No-train guarantee must be visible in the UI.
- **Deployment (LOCKED):** Must handle FastAPI long-running ops (embedding, vector store). Pure-serverless likely ruled out. Platform itself is open — Vercel+Fly/Render split, single VPS+Docker, or Render full-stack. Decided in deploy phase.
- **Cost:** One-time setup + low monthly maintenance. Favor managed free tiers, cheap VPS, or open-source self-host. No VC-burn assumptions.
- **Scope (LOCKED):** Mobile, teams, billing, annotations, Slack, audio/video are all OUT for v1 (see Out of Scope).
- **API contract (LOCKED, ADR):** `/chat/stream` accepts optional `document_ids: list[str]`; retriever filters Chroma by that whitelist.
- **API contract (LOCKED, ADR):** `/documents` response includes `chunk_count: int` and `indexed_at: timestamp` per document.
- **Schema (LOCKED, ADR):** Chroma chunk metadata carries `indexed_at` timestamp written at chunk-add time.
- **Schema (LOCKED, ADR):** Each assistant message carries its own `sources[]` array. Citation badges resolve against per-message sources, not a global latest pointer.
- **Persistence (LOCKED, ADR):** v1 conversation history is `localStorage` only.
- **Timeline:** 1–2 week v1 milestone window.

## Key Decisions

<!-- LOCKED decisions from DESIGN_DECISIONS.md (/plan-design-review 2026-05-10). All immutable for v1. -->

<decisions>

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| **DEC-per-message-sources** — Each assistant message stores its own `sources[]`. `[📄 N sources]` pill at message bottom; clicking sets that message active (right panel scrolls + left-border indigo accent); citation badges `[1][2]` bind to that message's stored sources. Default active = latest message. | Citations in older messages must keep resolving correctly after new questions. Global "latest sources" pointer corrupts history. | LOCKED |
| **DEC-conversation-history-sidebar** — Chats list stacked into existing 240px left rail: Brand → `+ New chat` (indigo, full-width) → Conversations (scrollable, grouped Today/Yesterday/Older) → divider → Upload zone → Documents. Auto-name from first 40 chars of first user message; hover-pencil rename; confirm-twice delete; active row = filled indigo. `localStorage` v1; backend persistence after auth. | Single rail keeps the document-forward layout intact; auth deferred so server persistence is overkill. | LOCKED |
| **DEC-per-document-filter-chips** — No separate chip UI. Toggle directly on each DocumentList row via small eye/check icon; deselected rows drop to 40% opacity. Footer reads `Searching N of M documents` (omitted when all selected). Default: all on. Backend: `/chat/stream` accepts optional `document_ids: list[str]`; retriever filters Chroma. | Chips would duplicate the document list. Row-level toggle keeps a single source of truth and reads naturally. | LOCKED |
| **DEC-upload-progress-states** — On drop: insert pending row immediately, show `Uploading 67%` from XHR `onProgress`, swap to `Indexing…` with `.animate-shimmer` indeterminate bar, then replace with real document row via existing `freshIds` pulse. | Granular backend stages (Extracting → Chunking → Embedding N/M) require turning `/upload` into SSE — not worth the rewrite for v1. | LOCKED |
| **DEC-mobile-deferred** — Mobile / narrow viewport explicitly deferred to a dedicated pass. Keep tightening desktop until then. | v1 is a desktop reading tool. Mobile-first design at this stage would dilute Pillars A/B/C. | LOCKED |
| **DEC-document-management-tooltip** — Hovering a doc row shows `24 chunks · indexed 3 hours ago` (relative time). Backend: `/documents` returns `chunk_count` (`Chroma.count(where={document_id})`) and `indexed_at` (from any chunk's metadata). | Lightweight surface for "is this document healthy and current?" without an admin page. | LOCKED |
| **DEC-implementation-order** — Ship locked UI/UX work tight → heavy as independent PRs: (1) Document tooltip ~30 min, (2) Upload progress ~1 hr, (3) Per-message sources ~1.5 hr, (4) Filter chips ~1.5 hr, (5) Conversation history sidebar ~3–4 hr. | Each PR independently reviewable; momentum from small wins; large work last. | LOCKED |

</decisions>

**Open decisions (handoff to phase planning):**

| Decision | Notes |
|----------|-------|
| PDF extraction library | NOT pdfplumber, NOT docling. PyMuPDF base likely; possibly `unstructured` without docling backend. Decided in Phase 1. |
| Chunking algorithm | Layout-aware + hierarchical (parent-child). Specific implementation decided in Phase 1. |
| Vector store | Keep current `vector_store.py` (Chroma) or swap? Cost + portability lens. Default = keep. |
| Auth provider | Deferred to v2 auth phase. v1 schema must remain compatible (Google+Microsoft SSO leaning). |
| Deployment platform | Vercel+Fly/Render split vs. single VPS+Docker vs. Render full-stack. Decided in Phase 5. |
| LLM provider for v1 | Currently Groq. Abstraction must permit swap (Gemini AI Studio OpenAI-compatible endpoint or OpenRouter fallback chain). |

---
*Last updated: 2026-05-11 after new-project ingest of DESIGN_DECISIONS.md (ADR), PROJECT.md source (PRD), TODOS.md (DOC).*
