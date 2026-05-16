# Roadmap: DocuRAG

## Overview

v1 is a 1–2 week milestone that turns the current working-but-loose RAG chatbot into a document-forward SaaS where every claim is cited to a clickable page + supporting quote. We start at the foundation (chunking — citations depend on chunk identity), then build citations backend-up, then citations frontend-down, then polish the document-forward UI (consuming 7 LOCKED ADR decisions), then deploy publicly with a no-train privacy disclosure. Google Drive OAuth is a stretch sixth phase, attempted only if the first five are clean.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Chunking rebuild** - Layout-aware + hierarchical chunker on a non-blacklisted extractor; foundation for chunk-identity citations
- [ ] **Phase 2: Citations backend** - Inline marker emission during streaming, chunk→page mapping, supporting-quote extraction
- [ ] **Phase 3: Citations frontend** - Markdown-safe `[1][2]` markers, hover quote preview, click-to-jump in PdfViewer
- [ ] **Phase 4: Document-forward UI polish** - Paper-like canvas, calm palette, and the 7 LOCKED ADR decisions land as independent PRs
- [ ] **Phase 5: Public deployment + privacy disclosure** - Pick platform, ship publicly, surface no-train guarantee in UI
- [ ] **Phase 6: Google Drive OAuth (stretch)** - First external document source, only if Phases 1–5 are clean

## Phase Details

### Phase 1: Chunking rebuild
**Goal**: A layout-aware, hierarchical chunker that produces stable, citable chunk identities and preserves tables + header→section relationships on real PDFs — without using `pdfplumber` or `docling`.
**Depends on**: Nothing (first phase)
**Requirements**: REQ-context-preserving-chunking, REQ-forward-compatible-multitenancy-schema
**Success Criteria** (what must be TRUE):
  1. On 3 user-provided sample PDFs, no table row is split across chunks and no header is separated from its first paragraph.
  2. Each small chunk (~256 tok) carries a stable `chunk_id`, parent section reference, `page` (or page range), and `indexed_at` in Chroma metadata.
  3. Retrieval can fetch a small chunk and expand to its parent section (~1–2k tok) for the LLM context window.
  4. The existing upload → chunk → embed → ask pipeline still works end-to-end (no happy-path regression).
  5. Any new persistent fields added to chunk metadata are either `user_id`-scoped or trivially migrate-able to be.
**Plans**: 9 plans
- [x] 01-00-PLAN.md — Wave 0 test scaffolding + tiktoken dependency
- [x] 01-01-PLAN.md — Stable chunk_id derivation + token-length helper
- [x] 01-02-PLAN.md — Header detection via pymupdf4llm.IdentifyHeaders + bold fallback
- [x] 01-03-PLAN.md — Generic table chunking; delete _fitz_table_to_markdown
- [x] 01-04-PLAN.md — Hierarchical assembler + metadata schema + retrieval-key migration
- [x] 01-05-PLAN.md — Parent expansion node in LangGraph retrieval
- [x] 01-06-PLAN.md — Startup re-index migration via FastAPI lifespan
- [x] 01-07-PLAN.md — SC1 integration tests on 3 user-provided sample PDFs
- [x] 01-08-PLAN.md — End-to-end smoke + document_ids filter regression
**UI hint**: no

### Phase 2: Citations backend
**Goal**: The backend can emit grounded `[N]` markers inside the streamed answer, each resolving to a specific chunk, its page, and a supporting quote — through a provider-agnostic LLM call site.
**Depends on**: Phase 1
**Requirements**: REQ-grounded-citations (backend half), REQ-provider-flexible-llm
**Success Criteria** (what must be TRUE):
  1. The streaming response includes inline `[N]` markers emitted DURING generation (not stitched on at the end).
  2. Each marker resolves server-side to a specific chunk_id, document_id, page, and a verbatim supporting quote substring.
  3. The per-message `sources[]` payload (LOCKED schema) carries chunk_id + page + quote per source.
  4. The LLM call site is behind a thin abstraction so switching from Groq to Gemini/OpenRouter/Anthropic doesn't require touching `langgraph_rag.py` graph nodes.
  5. `/chat/stream` continues to accept the LOCKED `document_ids: list[str]` filter parameter without regression.
**Plans**: 4 plans
- [x] 02-00-PLAN.md — Wave 0 test scaffolding: stub test files, semantic marker, requirements-dev.txt, golden eval seed
- [x] 02-01-PLAN.md — LLMProvider Protocol + GroqProvider + get_provider() factory; groq_client shrink + test migration
- [x] 02-02-PLAN.md — CitationStreamParser + difflib verbatim-quote extractor + Source/DoneEvent schemas
- [x] 02-03-PLAN.md — Wire provider seam + parser into langgraph_rag; compact [N] prompt; SC1/SC5 integration tests
**UI hint**: no

### Phase 3: Citations frontend
**Goal**: Users see inline citation badges in streamed answers, hover to read the supporting quote, and click to jump to the cited page in the PDF viewer.
**Depends on**: Phase 2
**Requirements**: REQ-grounded-citations (frontend half)
**Success Criteria** (what must be TRUE):
  1. `[1][2]` badges render inside the streamed answer and survive markdown rendering via `MarkdownBoundary.jsx`.
  2. Hovering a badge shows a tooltip/popover with the exact supporting quote.
  3. Clicking a badge opens the PDF viewer at the correct page with the cited region visually highlighted.
  4. Badges inside an older assistant message resolve against THAT message's stored `sources[]` (LOCKED per-message-sources schema), not a global latest pointer.
  5. Every claim in a sampled answer on the 3 user-provided PDFs has a clickable citation that lands on the correct page.
**Plans**: TBD
**UI hint**: yes

### Phase 4: Document-forward UI polish
**Goal**: The app reads as a paper-like document tool with a quieter chat companion column, and the 7 LOCKED ADR UI/UX decisions are all shipped as independent PRs in the locked tight-to-heavy order.
**Depends on**: Phase 3
**Requirements**: REQ-document-forward-ui-polish, REQ-no-happy-path-regressions
**Success Criteria** (what must be TRUE):
  1. PDF/document is the hero surface; chat is a calmer accent column. Typography, spacing, and palette pass a `/design-review` pass.
  2. Document tooltip shows `N chunks · indexed X ago` on hover (LOCKED DEC-document-management-tooltip; `/documents` returns `chunk_count` + `indexed_at`).
  3. Upload zone shows per-file `Uploading 67%` then `Indexing…` shimmer, then swaps to the real document row (LOCKED DEC-upload-progress-states).
  4. Each assistant message shows a `[📄 N sources]` pill that, when clicked, sets the message active (left-border indigo accent + right panel scrolls to its sources); citation badges in older messages still resolve correctly (LOCKED DEC-per-message-sources).
  5. DocumentList rows have a per-row eye/check toggle; deselected rows dim to 40% opacity; footer reads `Searching N of M documents`; `/chat/stream` honors the filter (LOCKED DEC-per-document-filter-chips).
  6. Left rail stacks: brand → `+ New chat` indigo button → grouped conversations list (Today/Yesterday/Older) → divider → upload zone → documents; auto-name from first 40 chars; hover-pencil rename; confirm-twice delete; localStorage-only persistence (LOCKED DEC-conversation-history-sidebar).
  7. Existing upload → ask → cited-answer happy path still works end-to-end (regression guard before deploy).
**Plans**: TBD
**UI hint**: yes

### Phase 5: Public deployment + privacy disclosure
**Goal**: v1 is reachable on a public URL on a cost-sensitive platform that handles long-running FastAPI ops, and the no-train privacy guarantee is visible in the UI.
**Depends on**: Phase 4
**Requirements**: REQ-public-deployment-with-privacy-disclosure
**Success Criteria** (what must be TRUE):
  1. The app is reachable at a public URL (waitlist wall acceptable).
  2. The chosen platform handles FastAPI long-running ops (embedding, vector store) — pure-serverless is explicitly ruled out and the platform choice (Vercel+Fly/Render split vs single VPS+Docker vs Render full-stack) is recorded in PROJECT.md Key Decisions.
  3. The UI surfaces a privacy / no-train statement that names the no-train endpoints in use (Anthropic / OpenAI zero-retention / Groq per ToS).
  4. All LLM calls in production hit no-train endpoints only — verified by inspecting the live config.
  5. Monthly cost projection is bounded and documented; no surprise paid tiers required to keep the site up.
**Plans**: TBD
**UI hint**: yes

### Phase 6: Google Drive OAuth (stretch)
**Goal**: A user can authenticate Google Drive, pick a PDF, and have it ingest through the same chunk/embed pipeline so it appears in their document library with working citations. Only attempted if Phases 1–5 are clean.
**Depends on**: Phase 5 (and Phases 1–3 must be clean — gating condition from PRD)
**Requirements**: REQ-stretch-google-drive-oauth
**Success Criteria** (what must be TRUE):
  1. Google OAuth flow completes successfully against a real Google account.
  2. The Drive file picker returns a chosen PDF and the backend ingests it through the existing extract → chunk → embed pipeline (no parallel pipeline).
  3. The ingested file appears in the user's document library with `chunk_count` and `indexed_at` populated.
  4. Asking a question against the Drive-sourced PDF produces a streamed, cited answer indistinguishable in quality from a direct-upload PDF.
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Chunking rebuild | 0/TBD | Not started | - |
| 2. Citations backend | 0/TBD | Not started | - |
| 3. Citations frontend | 0/TBD | Not started | - |
| 4. Document-forward UI polish | 0/TBD | Not started | - |
| 5. Public deployment + privacy disclosure | 0/TBD | Not started | - |
| 6. Google Drive OAuth (stretch) | 0/TBD | Not started | - |
