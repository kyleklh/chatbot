# Requirements: DocuRAG

**Defined:** 2026-05-11
**Core Value:** Every assistant claim has a clickable inline citation that jumps to the correct page with the correct supporting quote.

## v1 Requirements

Requirements for the 1–2 week v1 milestone. IDs are kebab-case slugs (matching intel synthesis) to preserve traceability back to `.planning/intel/requirements.md`.

### Chunking (foundation for citations)

- [ ] **REQ-context-preserving-chunking**: Replace current chunker with a layout-aware + hierarchical strategy.
  - Layout-aware: respects headers, lists, and table boundaries. Never splits a table row. Never separates a header from its first paragraph.
  - Hierarchical: small chunks (~256 tok) retrieved for precision; expand to parent section (~1–2k tok) when feeding the LLM. Citations point to the small chunk.
  - Demonstrably preserves table rows + header→section relationships on 3 sample PDFs the user provides.
  - Hard constraint: MUST NOT use `pdfplumber` or `docling`.

### Citations (Pillar A — highest priority)

- [ ] **REQ-grounded-citations**: Grounded, inline citations tied to specific chunks during streamed answers.
  - Inline `[1][2]` markers emitted DURING the streamed answer (not appended at the end).
  - Markers tie to specific chunks (chunk identity, not just document).
  - Hovering shows tooltip/popover with the exact supporting quote snippet.
  - Clicking opens PDF viewer at that page with the cited region highlighted.
  - Citations survive markdown rendering (existing `MarkdownBoundary.jsx`).
  - Every claim in the answer has a clickable inline citation that resolves to the right page + supporting quote.

### Document-forward UI

- [ ] **REQ-document-forward-ui-polish**: Visual polish pass — PDF is the hero surface, chat a quieter accent column.
  - Paper-like reading canvas; tight readable typography; generous margins; restrained palette.
  - Polished conversation list, upload affordance, empty states, loading/streaming states.
  - Consumes the 7 LOCKED ADR decisions (per-message sources pill, conversation sidebar, per-document filter toggle, upload progress states, document tooltip, mobile deferred, implementation order).
  - Passes a `/design-review` pass for typography, spacing, hierarchy, calm palette.
  - Mobile is NOT a v1 requirement.

### Deployment & privacy

- [ ] **REQ-public-deployment-with-privacy-disclosure**: Deploy v1 to a publicly reachable URL with a documented no-train guarantee surfaced in the UI.
  - App reachable on the public internet (waitlist wall acceptable).
  - No-train / privacy guarantee visible in the UI.
  - All LLM calls go through no-train endpoints only (Anthropic, OpenAI zero-retention, Groq per ToS).
  - Platform decision (Vercel+Fly/Render split vs single VPS+Docker vs Render full-stack) made and recorded during this phase.

### Cross-cutting (must hold across all phases)

- [ ] **REQ-no-happy-path-regressions**: Existing upload → chunk → embed → ask → streamed-answer-with-sources flow must continue to work end-to-end after v1 changes.
- [ ] **REQ-forward-compatible-multitenancy-schema**: Any new persistent state added during v1 must include (or be trivially migrate-able to include) `user_id` / workspace scoping. No design choice blocks adding Google-only or Google+Microsoft SSO later.
- [ ] **REQ-provider-flexible-llm**: LLM provider is callable through a thin abstraction layer. Switching providers does not require changes to `langgraph_rag.py` graph nodes beyond the LLM call site. v1 ships on Groq; abstraction must permit later swap (Gemini, OpenRouter, Anthropic).

### Stretch (only if Pillars A/B/C are clean)

- [ ] **REQ-stretch-google-drive-oauth**: Google Drive OAuth as the first external source.
  - OAuth flow works.
  - Picked files ingested via the same chunk/embed pipeline.
  - Picked files appear in the user's document library.
  - Only attempted after REQ-context-preserving-chunking, REQ-grounded-citations, and REQ-document-forward-ui-polish are clean.

## v2 Requirements

Deferred to future milestones. Tracked but NOT in current roadmap.

### Auth / multi-tenancy
- **AUTH-V2-01**: SSO via Google (or Google+Microsoft) using Clerk or Supabase Auth.
- **AUTH-V2-02**: JWT verification middleware; every Chroma query and uploaded file scoped by `user_id` / `workspace_id`.
- **AUTH-V2-03**: Migration: existing docs attribute to a default workspace; new uploads go to authenticated user's workspace.
- **AUTH-V2-04**: Backend persistence of conversation history (replacing localStorage).

### Mobile / responsive
- **MOB-V2-01**: Narrow-viewport (<900px) layout — sources to slide-over drawer, indexed-docs/upload to hamburger menu, tap-to-show citation tooltips, 44px touch targets, keyboard-aware compose input, PDF viewer at 375px.

### Retrieval quality & evaluation
- **EVAL-V2-01**: Golden Q&A dataset (~30–50 pairs from real PDFs) in `backend/eval/` with question + expected substring + expected source pages. Run on every retrieval change.
- **EVAL-V2-02**: Query logging to `query_log.jsonl` or sqlite — question, rewritten question, retrieved chunk IDs, distances, reranker scores, answer, latency, document_ids. Wire thumbs-up/down to log. `/admin/queries` endpoint to scan recent failures.

### Multi-format loaders
- **LOAD-V2-01**: Word (`python-docx`), PowerPoint (`python-pptx`), Excel (`openpyxl`), plaintext, Markdown — all returning the same `[{"page", "text"}]` shape.

### Cloud connectors (post-Drive)
- **CONN-V2-01**: Microsoft OneDrive / SharePoint OAuth + picker.
- **CONN-V2-02**: Dropbox OAuth + picker.
- **CONN-V2-03**: Box, Notion / Confluence connectors.
- **CONN-V2-04**: Incremental sync via webhooks (Drive Push, Graph subscriptions); source-system ACL respect on query.

### Multimodal extraction
- **MM-V2-01**: When a table is detected, render its bounding box as PNG via PyMuPDF and send to a vision LLM (Llama 4 Maverick / GPT-4o / Claude) for markdown conversion. Trigger only on suspect tables (`Col 1` placeholder heuristic). Same pipeline for embedded charts/diagrams.

### Infra
- **INFRA-V2-01**: OpenRouter fallback chain (Groq primary → Gemini secondary on 429) for streaming stability.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mobile-optimized UI | LOCKED defer (DEC-mobile-deferred); desktop reading tool for v1 |
| Team / workspace collaboration | Single-user v1; schema stays multi-tenant-compatible |
| Billing / paywall / metering | Pre-revenue v1 |
| In-PDF annotations / highlights / note-taking | Reader, not editor |
| Slack ingestion | Not a document source for v1 |
| Audio / video document types | PDF-only v1 |
| Backend persistence of conversations | Deferred until auth lands; localStorage v1 |
| `pdfplumber` PDF extractor | Already failed on real user PDFs |
| `docling` PDF extractor | Works but ~2s/page + high RAM — too heavy for constrained deploy |
| Pure-serverless deployment | Cannot handle long-running embedding / vector store ops |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-context-preserving-chunking | Phase 1 | Pending |
| REQ-grounded-citations | Phase 2 + Phase 3 (split: backend then frontend) | Pending |
| REQ-document-forward-ui-polish | Phase 4 | Pending |
| REQ-forward-compatible-multitenancy-schema | Phase 1 (cross-cuts all; checked here as new persistent state is added) | Pending |
| REQ-provider-flexible-llm | Phase 2 (verified during backend citation work, which touches the LLM call site) | Pending |
| REQ-no-happy-path-regressions | Phase 4 (final guard before deploy) | Pending |
| REQ-public-deployment-with-privacy-disclosure | Phase 5 | Pending |
| REQ-stretch-google-drive-oauth | Phase 6 (stretch) | Pending |

**Coverage:**
- v1 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

Notes on mapping:
- REQ-grounded-citations is intentionally split across Phase 2 (backend marker emission, chunk→page mapping, quote extraction) and Phase 3 (markdown-safe markers, hover preview, click-to-jump). Both phases must be complete for the requirement itself to be satisfied; status flips to Complete after Phase 3.
- REQ-forward-compatible-multitenancy-schema and REQ-provider-flexible-llm are design constraints that get enforced when new persistent state / LLM call sites are touched; they're owned by the earliest phase that touches them.
- REQ-no-happy-path-regressions is a cross-cutting guard, formally verified in Phase 4 before the deploy phase.

---
*Requirements defined: 2026-05-11*
*Last updated: 2026-05-11 after new-project ingest.*
