# Decisions (synthesized ADR intel)

Source ADRs:
- `c:\Users\Kyle\chatbot\DESIGN_DECISIONS.md` (LOCKED, 2026-05-10, /plan-design-review pass)

Status legend: LOCKED = cannot be auto-overridden by lower-precedence sources.

---

## DEC-per-message-sources
- **Status:** LOCKED
- **Source:** DESIGN_DECISIONS.md §1
- **Scope:** ChatPanel, assistant message data model, citation badges, sources panel
- **Decision:** Attach `sources[]` to each assistant message in chat history. Render a `[📄 N sources]` pill at the bottom of every assistant message (omit when N=0). Clicking the pill sets that message as *active*: right sources panel scrolls to its sources and the message gets a left-border indigo accent. Citation badges `[1]`, `[2]` inside an older message bind to that message's stored sources (not the global latest), so hover tooltip and PDF-viewer modal show the correct chunk.
- **Defaults:** Default active = latest assistant message on render. New question swaps active to the new message.

## DEC-conversation-history-sidebar
- **Status:** LOCKED
- **Source:** DESIGN_DECISIONS.md §2
- **Scope:** Left rail (240px), localStorage, ChatPanel
- **Decision:** Stack a chats list inside the existing 240px left rail. Order top→bottom: Brand → `+ New chat` (full-width, indigo) → Conversations list (scrollable, grouped Today / Yesterday / Older) → Thin divider → Upload zone (existing) → Documents list (existing).
- **Naming:** Auto from first 40 chars of the first user message. Manual rename via hover-revealed pencil icon. Delete = confirm-twice pattern (same as DocumentList).
- **Active chat indicator:** Filled indigo background row.
- **Persistence:** localStorage for v1. Backend persistence deferred until auth lands.

## DEC-per-document-filter-chips
- **Status:** LOCKED
- **Source:** DESIGN_DECISIONS.md §3
- **Scope:** DocumentList, routes_chat.py `/chat/stream`, Chroma query filter
- **Decision:** No separate chip UI — toggle directly on each DocumentList row via a small eye/check icon. Deselected rows drop to 40% opacity. Footer under docs list shows `Searching 3 of 5 documents` (omitted when all selected).
- **Default:** all on.
- **Backend contract:** `/chat/stream` accepts optional `document_ids: list[str]`; retriever filters Chroma queries by that whitelist.

## DEC-upload-progress-states
- **Status:** LOCKED
- **Source:** DESIGN_DECISIONS.md §4
- **Scope:** UploadZone, frontend only (v1)
- **Decision:** On file drop, insert a pending row per file immediately. Show `Uploading 67%` driven by XHR `onProgress`. After upload completes (awaiting indexing response), swap to `Indexing…` with `.animate-shimmer` indeterminate bar. On success replace pending row with real document row using existing `freshIds` pulse.
- **Deferred:** Granular backend stages (Extracting → Chunking → Embedding N/M) — requires `/upload` to become SSE. Not worth the rewrite now.

## DEC-mobile-deferred
- **Status:** LOCKED
- **Source:** DESIGN_DECISIONS.md §5
- **Scope:** Responsive layout, touch, PDF viewer at 375px
- **Decision:** Mobile / narrow viewport explicitly DEFERRED to a dedicated pass. Until then keep tightening desktop. Future scope captured: hamburger drawer for chats+docs, bottom-sheet sources panel, tap-to-show citation tooltip (no hover on touch), PDF viewer modal at 375px (toolbar wrap + page render scale), 44px min touch targets, keyboard-aware compose input.

## DEC-document-management-tooltip
- **Status:** LOCKED
- **Source:** DESIGN_DECISIONS.md §6
- **Scope:** DocumentList hover, `/documents` endpoint, Chroma metadata
- **Decision:** Hovering a doc row shows tooltip `24 chunks · indexed 3 hours ago` (relative time).
- **Backend contract:** `/documents` response extends to include `chunk_count` and `indexed_at` per document. `chunk_count` = `Chroma.count(where={document_id})`. `indexed_at` = timestamp stored in Chroma metadata at chunk-add time, read back from any one chunk of the document.

## DEC-implementation-order
- **Status:** LOCKED
- **Source:** DESIGN_DECISIONS.md "Implementation order"
- **Scope:** Sequencing of the six locked UI/UX decisions for shippable PRs
- **Decision:** Ship tight → heavy so each PR is independent: (1) Document tooltip [~30 min], (2) Upload progress [~1 hr], (3) Per-message sources [~1.5 hr], (4) Filter chips [~1.5 hr], (5) Conversation history sidebar [~3-4 hr].
