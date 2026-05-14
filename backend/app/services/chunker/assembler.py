"""Hierarchical section walker + chunk assembler (Plan 01-04).

Wires together:
- HeaderClassifier (Plan 01-02) for per-line H1/H2 detection
- render_table_markdown + row_group_split (Plan 01-03) for tables
- make_chunk_id + CHUNKER_VERSION (Plan 01-01) for stable content-derived ids
- token_len (Plan 01-01) for token-budget-aware splitting

Emits hierarchical chunks per D-01..D-12:
- Children (kind="prose" or "table_row_group") target CHILD_CHUNK_TOKENS.
- Parents (kind="parent") target PARENT_CHUNK_TOKENS, hold the concatenated
  section text; each child carries `parent_ref` = parent chunk_id.
- Section path capped at depth 2 (D-02); fallback to `f"page-{N}"` when no
  H1/H2 has been seen (D-03).
- D-04: an H2 at the very bottom of a page with no following body is carried
  forward as `pending_header` and prepended to the first body chunk on the
  next page that has body content.
- D-12: `user_id` metadata key is included ONLY when explicitly passed.
"""
from __future__ import annotations

import time
from typing import Any

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import (
    CHILD_CHUNK_OVERLAP_TOKENS,
    CHILD_CHUNK_TOKENS,
    PARENT_CHUNK_TOKENS,
)
from app.services.chunker.headers import HeaderClassifier
from app.services.chunker.ids import CHUNKER_VERSION, make_chunk_id
from app.services.chunker.tables import render_table_markdown, row_group_split
from app.services.chunker.tokens import token_len


def build_chunk_metadata(
    *,
    chunk_id: str,
    document_id: str,
    parent_ref: str,
    page: int | str,
    kind: str,
    indexed_at: int,
    user_id: str | None = None,
    file_name: str | None = None,
) -> dict[str, Any]:
    """Build the canonical chunk metadata dict (D-11, D-12 seam).

    `user_id` is included ONLY when not None — keeps the v1 schema clean while
    reserving the multi-tenant seam (D-12).
    `file_name` is an optional convenience field used by the upload path; it
    is not part of the required schema.
    """
    meta: dict[str, Any] = {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "parent_ref": parent_ref,
        "page": page,
        "kind": kind,
        "chunker_version": CHUNKER_VERSION,
        "indexed_at": indexed_at,
    }
    if user_id is not None:
        meta["user_id"] = user_id
    if file_name is not None:
        meta["file_name"] = file_name
    return meta


# ---------------------------------------------------------------------------
# Section walker
# ---------------------------------------------------------------------------

def _line_text(line: dict) -> str:
    return "".join(s.get("text", "") for s in line.get("spans", [])).strip()


def _line_bbox_overlaps(line: dict, table_bboxes: list[tuple[float, float, float, float]]) -> bool:
    """Return True if the line's bbox intersects any table bbox.

    Used to skip text lines that are part of a detected table region — the
    table is rendered separately via render_table_markdown.
    """
    lb = line.get("bbox")
    if not lb:
        return False
    lx0, ly0, lx1, ly1 = lb
    for tx0, ty0, tx1, ty1 in table_bboxes:
        # Standard 2D AABB overlap test.
        if lx0 < tx1 and lx1 > tx0 and ly0 < ty1 and ly1 > ty0:
            return True
    return False


def _section_path(h1: str | None, h2: str | None, page_num: int) -> str:
    """Compute the section_path string, capped at depth 2 (D-02).

    Fallback to `page-N` when neither H1 nor H2 has been seen (D-03).
    """
    if h1 and h2:
        return f"{h1} > {h2}"
    if h1:
        return h1
    if h2:
        return h2
    return f"page-{page_num}"


def _split_prose(text: str) -> list[str]:
    """Split a section's accumulated prose into ~CHILD_CHUNK_TOKENS chunks.

    Per D-01: RCTS is only ever invoked on prose runs, never on table
    markdown. RCTS is configured with token_len so the size/overlap budgets
    are interpreted as cl100k_base tokens, not characters.
    """
    if not text.strip():
        return []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHILD_CHUNK_TOKENS,
        chunk_overlap=CHILD_CHUNK_OVERLAP_TOKENS,
        length_function=token_len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    out = [s.strip() for s in splitter.split_text(text) if s and s.strip()]
    return out


def chunk_pages(
    pages: list[dict[str, Any]] | None = None,
    document_id: str = "",
    user_id: str | None = None,
    source_path: str | None = None,
    file_name: str | None = None,
    *,
    chunk_size: int | None = None,  # legacy kwarg, ignored
    overlap: int | None = None,  # legacy kwarg, ignored
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Walk a PDF and emit (children, parents) chunks.

    `pages` is retained for backward-compat but is no longer the source of
    truth; the assembler always re-opens the PDF via `pymupdf.open(source_path)`
    to access block/line/span font info and table regions.

    If `source_path` is None we fall back to text-only chunking using the
    `pages` argument — no table detection, no header detection. This path
    exists only for tests that pre-supply page text without a backing file.
    """
    if source_path is None:
        return _chunk_text_only(pages or [], document_id, user_id, file_name)

    doc = pymupdf.open(source_path)
    try:
        classifier = HeaderClassifier(doc, max_levels=2)
        return _walk_document(
            doc=doc,
            classifier=classifier,
            document_id=document_id,
            user_id=user_id,
            file_name=file_name,
        )
    finally:
        doc.close()


def _walk_document(
    *,
    doc: pymupdf.Document,
    classifier: HeaderClassifier,
    document_id: str,
    user_id: str | None,
    file_name: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    indexed_at = int(time.time())

    # Section state — persists across pages.
    current_h1: str | None = None
    current_h2: str | None = None
    pending_header: str | None = None  # D-04 carry

    # Sections accumulated for parent emission. Keyed by (section_path, first_page);
    # value: {"text_parts": [...], "child_indices": [...], "pages": set}.
    # We materialize children eagerly but defer parent emission until after we
    # know each section is "closed".
    sections: list[dict[str, Any]] = []

    def _open_section(path: str, page_num: int) -> dict[str, Any]:
        sec = {
            "path": path,
            "first_page": page_num,
            "pages": {page_num},
            "prose_buffer": "",
            "table_chunks": [],  # list[(text, page_num)]
        }
        sections.append(sec)
        return sec

    def _current_section(path: str, page_num: int) -> dict[str, Any]:
        # Reuse the most recently-opened section if path matches; else open new.
        if sections and sections[-1]["path"] == path:
            sections[-1]["pages"].add(page_num)
            return sections[-1]
        return _open_section(path, page_num)

    for page in doc:  # type: ignore[assignment]
        page_num = page.number + 1  # 1-indexed for downstream consumers

        # ---- Detect table regions ------------------------------------------------
        # PyMuPDF's find_tables() can return Table objects with empty cells that
        # blow up on `.bbox` access (see RBC ar_2025 fixture). Treat each table's
        # bbox/extract as best-effort and skip the offending one — Phase 1.5
        # will handle hard-table failures via the multimodal path.
        try:
            finder = page.find_tables()
            raw_tables = list(finder.tables) if finder else []
        except Exception:
            raw_tables = []
        tables: list[Any] = []
        table_bboxes: list[tuple[float, float, float, float]] = []
        for t in raw_tables:
            try:
                bbox = tuple(t.bbox)
            except Exception:
                continue
            tables.append(t)
            table_bboxes.append(bbox)  # type: ignore[arg-type]

        # ---- Walk text blocks/lines, skipping anything inside a table ------------
        td = page.get_text("dict")
        page_had_body = False  # used to decide whether a trailing header becomes pending

        # Track the last header seen on this page in case it has no body following.
        last_header_text_this_page: str | None = None
        last_header_was_h2: bool = False

        for block in td.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                if _line_bbox_overlaps(line, table_bboxes):
                    continue
                text = _line_text(line)
                if not text:
                    continue

                level = classifier.classify_line(line, page)
                if level == 1:
                    current_h1 = text
                    current_h2 = None
                    last_header_text_this_page = text
                    last_header_was_h2 = False
                    # Opening a new H1 — close any pending_header (it didn't get a body).
                    pending_header = None
                    continue
                if level == 2:
                    current_h2 = text
                    last_header_text_this_page = text
                    last_header_was_h2 = True
                    pending_header = None
                    continue

                # Body line. If there's a pending_header carried from prior page,
                # prepend its text to this body line so it shows up in the first
                # emitted chunk for the new section.
                path = _section_path(current_h1, current_h2, page_num)
                sec = _current_section(path, page_num)
                # If the section's prose_buffer is empty AND we have a pending header,
                # prepend it once.
                if not sec["prose_buffer"] and pending_header:
                    sec["prose_buffer"] = pending_header + "\n\n"
                    pending_header = None
                sec["prose_buffer"] += text + "\n"
                last_header_text_this_page = None
                page_had_body = True

        # ---- Handle a trailing header that got no body on this page (D-04) -------
        # If the last classified line on the page was a header and no body followed
        # it on this page, carry it forward as pending_header. Only H2 carries —
        # an H1 with no body is an empty section and we just keep current_h1 set.
        if last_header_text_this_page and last_header_was_h2:
            pending_header = last_header_text_this_page

        # ---- Emit table chunks for this page ------------------------------------
        for t in tables:
            try:
                cells = t.extract()
            except Exception:
                cells = []
            if not cells:
                continue
            md = render_table_markdown(cells)
            if not md:
                continue
            path = _section_path(current_h1, current_h2, page_num)
            sec = _current_section(path, page_num)
            title = current_h2 or current_h1 or "Table"
            for piece in row_group_split(md, title=title, target_tokens=CHILD_CHUNK_TOKENS):
                sec["table_chunks"].append((piece, page_num))

    # -------------------------------------------------------------------------
    # Materialize children + parents.
    # -------------------------------------------------------------------------
    children: list[dict[str, Any]] = []
    parents: list[dict[str, Any]] = []

    for sec in sections:
        path = sec["path"]
        pages_set = sec["pages"]
        # Per-section "page" for metadata: int if single page; "lo-hi" string for ranges.
        if len(pages_set) == 1:
            section_page: int | str = next(iter(pages_set))
        else:
            lo, hi = min(pages_set), max(pages_set)
            section_page = f"{lo}-{hi}"

        # Build prose children.
        prose_parts: list[str] = []
        for piece in _split_prose(sec["prose_buffer"]):
            prose_parts.append(piece)

        # Build table children.
        table_parts: list[tuple[str, int]] = list(sec["table_chunks"])

        if not prose_parts and not table_parts:
            continue

        # Build parent text first so children can reference the parent's chunk_id.
        parent_text = sec["prose_buffer"].strip()
        if table_parts:
            # Append table markdown to the parent text for retrieval coverage.
            parent_text = (parent_text + "\n\n" + "\n\n".join(p for p, _ in table_parts)).strip()
        if not parent_text:
            continue
        parent_chunk_id = make_chunk_id(document_id, path, parent_text)
        parent_meta = build_chunk_metadata(
            chunk_id=parent_chunk_id,
            document_id=document_id,
            parent_ref="self",
            page=section_page,
            kind="parent",
            indexed_at=indexed_at,
            user_id=user_id,
            file_name=file_name,
        )
        parents.append({
            "text": parent_text,
            "page": section_page,
            "metadata": parent_meta,
        })

        # Determine per-chunk page values. For prose we don't have a per-piece page
        # tracker (RCTS re-segmented across the buffer); use the section_page.
        # Improvement candidate: track piece→page mapping; not required by D-11.
        for piece in prose_parts:
            cid = make_chunk_id(document_id, path, piece)
            meta = build_chunk_metadata(
                chunk_id=cid,
                document_id=document_id,
                parent_ref=parent_chunk_id,
                page=section_page,
                kind="prose",
                indexed_at=indexed_at,
                user_id=user_id,
                file_name=file_name,
            )
            children.append({
                "text": piece,
                "page": section_page,
                "metadata": meta,
            })

        for piece, page_num in table_parts:
            cid = make_chunk_id(document_id, path, piece)
            # D-06: embed_text is a natural-language summary of the table for
            # better recall — for now use the title + first-column labels.
            embed_text = _table_embed_text(piece)
            meta = build_chunk_metadata(
                chunk_id=cid,
                document_id=document_id,
                parent_ref=parent_chunk_id,
                page=page_num,
                kind="table_row_group",
                indexed_at=indexed_at,
                user_id=user_id,
                file_name=file_name,
            )
            children.append({
                "text": piece,
                "page": page_num,
                "embed_text": embed_text,
                "metadata": meta,
            })

    return children, parents


def _table_embed_text(table_md: str) -> str:
    """Build a natural-language embed surrogate for a table chunk (D-06).

    Strategy: take the first non-pipe line (title), header row, and first-column
    labels — typically a category list. Pipe-heavy markdown embeds poorly.
    """
    lines = table_md.split("\n")
    title = lines[0] if lines and not lines[0].startswith("|") else ""
    labels: list[str] = []
    for line in lines:
        if not line.startswith("|") or "---" in line:
            continue
        parts = line.split("|")
        if len(parts) < 2:
            continue
        label = parts[1].replace("*", "").strip()
        if label:
            labels.append(label)
    summary = title.strip()
    if labels:
        summary = (summary + " " if summary else "") + "Categories: " + ", ".join(labels[:40])
    return summary or table_md[:200]


# ---------------------------------------------------------------------------
# Fallback: text-only path for callers that don't have a source_path.
# ---------------------------------------------------------------------------

def _chunk_text_only(
    pages: list[dict[str, Any]],
    document_id: str,
    user_id: str | None,
    file_name: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    indexed_at = int(time.time())
    children: list[dict[str, Any]] = []
    parents: list[dict[str, Any]] = []

    for p in pages:
        page_num = p.get("page")
        text = (p.get("text") or "").strip()
        if not text:
            continue
        path = f"page-{page_num}"
        parent_id = make_chunk_id(document_id, path, text)
        parents.append({
            "text": text,
            "page": page_num,
            "metadata": build_chunk_metadata(
                chunk_id=parent_id,
                document_id=document_id,
                parent_ref="self",
                page=page_num,
                kind="parent",
                indexed_at=indexed_at,
                user_id=user_id,
                file_name=file_name,
            ),
        })
        for piece in _split_prose(text):
            cid = make_chunk_id(document_id, path, piece)
            children.append({
                "text": piece,
                "page": page_num,
                "metadata": build_chunk_metadata(
                    chunk_id=cid,
                    document_id=document_id,
                    parent_ref=parent_id,
                    page=page_num,
                    kind="prose",
                    indexed_at=indexed_at,
                    user_id=user_id,
                    file_name=file_name,
                ),
            })

    return children, parents


__all__ = ["chunk_pages", "build_chunk_metadata"]
