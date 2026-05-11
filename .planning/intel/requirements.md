# Requirements (synthesized PRD intel)

Source PRDs:
- `c:\Users\Kyle\chatbot\PROJECT.md` — Document Q&A SaaS brief (1-2 week v1 milestone)

---

## REQ-grounded-citations
- **Source:** PROJECT.md §3 Pillar A, §8.1
- **Scope:** Citations (highest priority pillar)
- **Description:** Provide grounded, inline citations during streamed answers tied to specific chunks (not just a sources list at the end).
- **Acceptance criteria:**
  - Inline `[1][2]` markers emitted **during** the streamed answer (not appended at the end).
  - Markers tie to specific chunks (chunk identity, not just document).
  - Hovering a citation shows a tooltip/popover with the exact supporting quote snippet.
  - Clicking a citation opens the PDF viewer at that page with the cited region highlighted.
  - Citations survive markdown rendering (existing `MarkdownBoundary.jsx`).
  - Every claim in the answer has a clickable inline citation that resolves to the right page + supporting quote.

## REQ-context-preserving-chunking
- **Source:** PROJECT.md §3 Pillar B, §8.2
- **Scope:** PDF chunking / extraction
- **Description:** Replace current chunker with a layout-aware + hierarchical strategy.
- **Acceptance criteria:**
  - **Layout-aware:** respects headers, lists, and table boundaries. Never splits a table row. Never separates a header from its first paragraph.
  - **Hierarchical (parent-child):** retrieves small chunks (~256 tok) for precision; expands to parent section (~1–2k tok) when feeding the LLM. Citations point to the small chunk.
  - Demonstrably preserves table rows and header→section relationships on at least 3 sample PDFs the user provides during verification.
- **Hard constraint (see also CON-blacklisted-extractors):** Must NOT use `pdfplumber` or `docling`.

## REQ-document-forward-ui-polish
- **Source:** PROJECT.md §3 Pillar C, §8.3
- **Scope:** UI/UX, document-forward aesthetic
- **Description:** Visual polish pass making the PDF/document the hero surface and chat a companion column.
- **Acceptance criteria:**
  - Paper-like reading canvas; PDF is the hero surface, chat is a quieter accent column (not whole screen).
  - Tight, readable typography; generous margins; restrained palette.
  - Polished conversation list, upload affordance, empty states, and loading/streaming states.
  - Passes a `/design-review` pass for typography, spacing, hierarchy, calm palette.
  - Mobile is **not** a v1 requirement (desktop reading tool).

## REQ-public-deployment-with-privacy-disclosure
- **Source:** PROJECT.md §5, §8.4
- **Scope:** Deployment, privacy
- **Description:** Deploy v1 to a publicly reachable URL with a documented privacy / no-train guarantee surfaced in the UI.
- **Acceptance criteria:**
  - App is deployed somewhere publicly reachable (waitlist wall acceptable).
  - Privacy / no-train guarantee is displayed in the UI.
  - User documents are not used to train any model (no-train API endpoints only: Anthropic, OpenAI zero-retention, Groq per ToS).
- **Open decision:** Deployment platform — Vercel+Fly/Render split vs. all-Vercel serverless vs. single-VPS Docker. GSD to propose. Pure-serverless likely ruled out by long-running embedding + vector store.

## REQ-no-happy-path-regressions
- **Source:** PROJECT.md §8.5
- **Scope:** Regression guard for v1
- **Description:** Existing upload → chat happy path must continue to work end-to-end after the v1 changes.
- **Acceptance criteria:** No regressions in current upload → chunk → embed → ask → streamed answer with sources flow.

## REQ-stretch-google-drive-oauth
- **Source:** PROJECT.md §3 Stretch, §4.2
- **Scope:** External document sources (stretch goal)
- **Description:** Google Drive OAuth as the first external source — user picks a file, it ingests, it appears in library.
- **Acceptance criteria:**
  - Google Drive OAuth flow works.
  - Picked files are ingested via the same chunk/embed pipeline.
  - Picked files appear in the user's document library.
  - Only attempted if Pillars A/B/C (REQ-grounded-citations, REQ-context-preserving-chunking, REQ-document-forward-ui-polish) are clean.

## REQ-forward-compatible-multitenancy-schema
- **Source:** PROJECT.md §4.1
- **Scope:** Schema design (not a v1 deliverable, but a v1 design constraint)
- **Description:** v1 schema must not paint future auth + multi-tenancy into a corner. Every new table/row must carry `user_id` (or be trivially migrate-able).
- **Acceptance criteria:**
  - Any new persistent state added during v1 includes (or can trivially be migrated to include) `user_id` / workspace scoping.
  - No design choices block adding Google-only SSO or Google+Microsoft auth later (author leans Google+Microsoft).

## REQ-provider-flexible-llm
- **Source:** PROJECT.md §4.4, §6 row 6
- **Scope:** LLM provider abstraction
- **Description:** Keep `groq_client.py`-style abstraction so the LLM can be swapped (Anthropic / OpenAI / Gemini / local) without rewriting the LangGraph state machine.
- **Acceptance criteria:**
  - LLM provider is callable through a thin abstraction layer.
  - Switching providers does not require changes to `langgraph_rag.py` graph nodes beyond the LLM call site.
  - v1 ships on Groq (open decision per §6 row 6); abstraction must permit later swap.
