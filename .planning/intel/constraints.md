# Constraints (synthesized SPEC + non-negotiable intel)

No formal SPEC docs were ingested. Constraints below are extracted from the LOCKED ADR (DESIGN_DECISIONS.md backend contracts) and from PROJECT.md §5 non-negotiables. ADR-sourced constraints inherit LOCKED status; PRD-sourced constraints are firm but lower-precedence than any future ADR.

---

## CON-blacklisted-pdf-extractors
- **Type:** nfr / technology blacklist
- **Source:** PROJECT.md §5, §6 row 1; corroborated by TODOS.md Multimodal section
- **Constraint:** Do NOT propose, evaluate, or use `pdfplumber` or `docling` for PDF extraction. Both have already failed on this user's real-world PDFs (pdfplumber: doesn't work; docling: works but ~2s/page and high peak RAM — too heavy).
- **Likely allowed candidates:** PyMuPDF (`fitz`), `unstructured` (without docling backend), custom layout pass on top of PyMuPDF block extraction.

## CON-framework-lockin
- **Type:** nfr / framework
- **Source:** PROJECT.md §5
- **Constraint:** Keep FastAPI (backend) + React/Vite (frontend). Do not migrate frameworks.

## CON-cost-sensitive
- **Type:** nfr / cost
- **Source:** PROJECT.md §5
- **Constraint:** One-time setup cost + low monthly maintenance. No VC-burn-rate assumptions. Favor managed free tiers, cheap VPS, or generous open-source self-host paths.

## CON-no-train-privacy
- **Type:** nfr / privacy
- **Source:** PROJECT.md §5
- **Constraint:** User documents must not be used to train any model. Use no-train API endpoints only (Anthropic, OpenAI enterprise/zero-retention, Groq per their terms). The privacy guarantee must be documented and shown in the UI.

## CON-deployment-not-pure-serverless
- **Type:** nfr / deployment
- **Source:** PROJECT.md §5, §6 row 5
- **Constraint:** Deployment must handle FastAPI long-running ops (embedding, vector store). Pure-serverless is "likely ruled out." Platform itself is an open decision — Vercel+Fly/Render split, all-Vercel serverless, or single-VPS Docker.

## CON-out-of-scope-v1
- **Type:** scope fence
- **Source:** PROJECT.md §7
- **Constraint:** v1 explicitly excludes: mobile-optimized UI, team/workspace collaboration, billing / paywall / usage metering, in-PDF annotations / highlights / note-taking, Slack ingestion, audio/video document support.

## CON-chat-stream-document-ids-param
- **Type:** api-contract (LOCKED via ADR)
- **Source:** DESIGN_DECISIONS.md §3 (DEC-per-document-filter-chips)
- **Constraint:** `routes_chat.py` `/chat/stream` MUST accept an optional `document_ids: list[str]` parameter. When present, the retriever filters Chroma queries by that whitelist. Absent or empty → behave as "all documents."

## CON-documents-endpoint-shape
- **Type:** api-contract (LOCKED via ADR)
- **Source:** DESIGN_DECISIONS.md §6 (DEC-document-management-tooltip)
- **Constraint:** `/documents` response MUST include `chunk_count: int` and `indexed_at: timestamp` per document. `chunk_count` derived from `Chroma.count(where={document_id})`. `indexed_at` derived from a timestamp written into Chroma metadata at chunk-add time and read back from any chunk.

## CON-chroma-metadata-indexed-at
- **Type:** schema (LOCKED via ADR)
- **Source:** DESIGN_DECISIONS.md §6
- **Constraint:** Chroma chunk metadata MUST carry an `indexed_at` timestamp written at chunk-add time. This is the source of truth for the documents tooltip and for any future "last indexed" surface.

## CON-message-sources-data-model
- **Type:** schema (LOCKED via ADR)
- **Source:** DESIGN_DECISIONS.md §1 (DEC-per-message-sources)
- **Constraint:** Each assistant message in the chat history MUST carry its own `sources[]` array. Citation badges within a message resolve against that message's sources, not against a global latest-sources pointer.

## CON-conversation-history-localstorage-v1
- **Type:** schema / persistence (LOCKED via ADR)
- **Source:** DESIGN_DECISIONS.md §2
- **Constraint:** v1 conversation history persists in `localStorage` only. Backend persistence is deferred until auth lands. v1 must not require server-side storage of conversations.
