# Context (synthesized DOC intel)

Source DOCs:
- `c:\Users\Kyle\chatbot\TODOS.md` — DocuRAG backlog, grouped by area

This file captures backlog items, observations, and forward-looking notes that are not requirements (PRD) or decisions (ADR). They inform downstream planning but do not commit scope.

---

## Topic: Current architecture snapshot (as of 2026-05-11)
- **Source:** PROJECT.md §2
- Backend: FastAPI in `backend/app/`. RAG pipeline is a LangGraph state machine (`langgraph_rag.py`). Hybrid retrieval = vector + BM25 merged via RRF (`bm25_retriever.py`, `vector_store.py`). Cross-encoder reranker (`reranker.py`). LLM via Groq (`groq_client.py`). PDF loader + chunker (`pdf_loader.py`, `chunker.py`).
- Frontend: React 19 + Vite + Tailwind v4. Components: chat panel, document list, PDF viewer (react-pdf), upload zone, conversations list, sources panel. Conversation history persisted in `localStorage` (`frontend/src/storage.js`).
- Deploy: not yet decided / not yet wired for production. Auth: none. Tenancy: implicit single-user.
- What works: upload → chunk → embed → ask → streamed answer with sources.

## Topic: User-confirmed gaps (drove the v1 milestone)
- **Source:** PROJECT.md §2
1. Citations exist but are not tight: no inline `[1][2]` in streamed output, no hover quote preview, no click-to-jump-to-page.
2. Chunking destroys context — current strategy breaks tables, headers, and multi-page concepts.
3. No auth, no multi-user, no external document sources.

## Topic: Backlog — UI/UX (mobile)
- **Source:** TODOS.md "UI / UX"
- Mobile / narrow-viewport layout: at <900px the three columns (chat, sources, indexed docs) need to collapse — sources to slide-over drawer, indexed-docs/upload to hamburger menu. Tap-to-show citation tooltip. PDF viewer at 375px. 44px touch targets. Keyboard-aware compose input.
- **Status:** Deferred per LOCKED ADR DEC-mobile-deferred and PROJECT.md §3 Pillar C / §7 (mobile not v1).

## Topic: Backlog — Retrieval quality & evaluation
- **Source:** TODOS.md "Quality & evaluation"
- **Evaluation harness:** Hybrid retrieval improvements (BGE embedding, cross-encoder reranker, BM25+vector) have shipped without measurement. Build a golden dataset (~30–50 Q&A pairs from real PDFs) in `backend/eval/`. Each entry: `{question, expected_answer_substring, expected_source_pages}`. Run on every retrieval change. Candidate frameworks: Ragas (context precision/recall, faithfulness), TruLens, or a simple pytest with substring + page-membership assertions.
- **Observability / query logging:** No visibility into what users ask, which chunks retrieved badly, or which answers were unfounded. Log every query to `backend/app/storage/query_log.jsonl` or a sqlite table with: `timestamp, question, rewritten_question, retrieved_chunk_ids, retrieved_distances, reranker_scores, answer, latency_ms, document_ids`. Thumbs-up/down feedback UI already ships but only `console.log`s — wire it to append to the log. Add a small `/admin/queries` endpoint to scan recent failures. Canonical motivating bug: Quebec row from RBC annual report Table 43 returned Atlantic provinces' values.

## Topic: Backlog — Auth / multi-tenancy
- **Source:** TODOS.md "Auth / multi-tenancy"
- Prerequisite plumbing for cloud connector OAuth, ACL preservation, cross-device conversation history, multi-tenant document isolation, and future billing.
- Cheapest path candidates: Clerk or Supabase Auth on the frontend; JWT verification middleware on backend; scope every Chroma query and every uploaded file by `user_id` (or `workspace_id` for team accounts).
- Migration plan: existing docs get attributed to a default workspace; new uploads go to the authenticated user's workspace.
- Cross-reference: PROJECT.md §4.1 author preference leans Google+Microsoft SSO. v1 schema must remain compatible (see REQ-forward-compatible-multitenancy-schema).

## Topic: Backlog — Multi-format document loaders
- **Source:** TODOS.md "Data sources / integrations"
- Beyond PDF: Word (`python-docx`), PowerPoint (`python-pptx`), Excel (`openpyxl`), plaintext, Markdown. `unstructured` covers all in one dep if its weight is acceptable.
- Each loader returns the same `[{"page": int, "text": str}]` shape as `extract_pdf_pages` — chunking + embedding pipeline unchanged.
- Surface area: small dispatcher in `pdf_loader.py` (consider renaming to `loaders.py`) keyed by file extension; extension whitelist updates in `routes_upload.py`.
- Excel: each sheet ≈ a page; tables pass through to chunker as markdown to hit the table-aware embedding path.

## Topic: Backlog — Cloud storage connectors
- **Source:** TODOS.md "Data sources / integrations"
- Priority order: (1) Google Drive, (2) Microsoft OneDrive / SharePoint, (3) Dropbox, (4) Box, (5) Notion / Confluence.
- Per provider: OAuth, folder/site picker, backend pulls files through existing extraction + chunking + embedding pipeline, citations link back to source path (e.g. "Drive › Finance › Q3 Report.pdf").
- Considerations: respect source-system ACLs (only index what the authenticating user can read; re-check on query in multi-user mode); format conversion (Google Docs/Sheets/Slides export via APIs; OneNote/Word likewise); incremental sync via webhooks (Drive Push, Graph subscriptions) instead of full re-crawl; rate limits + pagination on first sync; per-user vs per-workspace credentials.
- Cross-reference: REQ-stretch-google-drive-oauth — Google Drive is the stretch v1 item; the rest are post-v1.

## Topic: Backlog — Infra / LLM provider swap
- **Source:** TODOS.md "Infra"
- Groq's free tier rate-limits aggressively, cutting streams mid-sentence so `onDone` never fires and the per-message sources panel stays empty.
- Candidate: Gemini 2.5 Flash via AI Studio (1,500 req/day free, faster first-token in practice, better at tables / structured output). Use the OpenAI-compatible endpoint `https://generativelanguage.googleapis.com/v1beta/openai/`.
- Better candidate: OpenRouter with a fallback chain (Groq primary → Gemini secondary on 429), one API, automatic failover.
- Streaming text shape is unchanged so no frontend changes needed.
- Cross-reference: REQ-provider-flexible-llm — abstraction must already permit this swap without graph rewrites.

## Topic: Backlog — Multimodal extraction (vision for tables + images)
- **Source:** TODOS.md "Multimodal extraction"
- Current PyMuPDF table reconstruction silently produces wrong output on complex layouts (multi-row headers, merged cells). Confirmed bug: Quebec row from RBC annual report Table 43 returned Atlantic provinces' values.
- Plan: when a table is detected, render its bounding box as a PNG with PyMuPDF and send to a vision LLM (Groq Llama 4 Maverick, GPT-4o, or Claude) to convert to markdown; concatenate with surrounding prose. Same pipeline doubles for general image interpretation (embedded charts/diagrams indexed alongside text).
- **Tried and rejected (DO NOT re-propose):** `pdfplumber` (didn't work on the same PDFs), `docling` (correct but ~2s/page and high peak RAM — too heavy for constrained deploy). See CON-blacklisted-pdf-extractors.
- Cost guardrail: trigger vision only on suspect tables (e.g. when `_fitz_table_to_markdown` produces `Col 1` placeholders). Fall back to refusing to answer if both rule-based and vision extraction fail.

## Topic: GSD phase breakdown (author's suggested sequence)
- **Source:** PROJECT.md §9
1. Phase 1 — Chunking rebuild (foundation; citations depend on chunk identity)
2. Phase 2 — Citations: backend (inline markers in streamed output, chunk→page mapping, quote extraction)
3. Phase 3 — Citations: frontend (markdown-safe inline markers, hover preview, click-to-jump in PdfViewer)
4. Phase 4 — UI polish pass (document-forward visual system, empty/loading states)
5. Phase 5 — Deployment + privacy disclosure
6. (Stretch) Phase 6 — Google Drive OAuth ingestion
- This is the author's preferred ordering; the roadmapper may revise.

## Topic: Open decisions (handoff to roadmapper)
- **Source:** PROJECT.md §6
1. PDF extraction library (NOT pdfplumber, NOT docling; likely PyMuPDF base)
2. Chunking implementation (layout-aware + hierarchical; specific algorithm TBD)
3. Vector store — keep current `vector_store.py` or swap? (cost + portability lens)
4. Auth provider (defer to multi-tenancy phase, but ensure v1 schema is compatible)
5. Deployment platform (cost-sensitive; must handle FastAPI long-running ops)
6. LLM provider for v1 (currently Groq; keep abstraction so it can swap)
