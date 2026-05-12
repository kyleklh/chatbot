"""Generic markdown table renderer + row-group splitter (D-05, D-06, D-07).

D-07 LOCKED CONSTRAINT: no hard-coded heuristics tied to specific table layouts.
One pipe-cell per source cell. No reordering, no merging, no label inference.
"""
from __future__ import annotations

from app.services.chunker.tokens import token_len


def render_table_markdown(cells: list[list[str | None]]) -> str:
    """Render `cells` as a GitHub-flavored markdown table.

    - Pads short rows to max width with empty cells.
    - Replaces embedded newlines with a single space.
    - Escapes `|` as `\\|`.
    - `None` cells become empty strings.
    - Emits a `---` separator row after the first row.
    - No trailing newline.
    """
    if not cells:
        return ""
    width = max(len(row) for row in cells)

    def _cell(c: str | None) -> str:
        if c is None:
            return ""
        return str(c).replace("\n", " ").replace("|", "\\|").strip()

    out: list[str] = []
    for i, row in enumerate(cells):
        padded = list(row) + [None] * (width - len(row))
        out.append("| " + " | ".join(_cell(c) for c in padded) + " |")
        if i == 0:
            out.append("| " + " | ".join(["---"] * width) + " |")
    return "\n".join(out)


def row_group_split(
    table_md: str,
    title: str,
    target_tokens: int = 256,
) -> list[str]:
    """Greedy-pack data rows into chunks ≤ target_tokens, never splitting a row.

    Each chunk is prefixed with `title + "\\n" + header_row + "\\n" + sep_row` so
    retrieval-time embeddings carry the table's column context (D-06).

    If a single row alone exceeds `target_tokens`, it still occupies its own chunk
    intact — never split, never truncated.
    """
    if not table_md:
        return []
    lines = table_md.split("\n")
    if len(lines) < 3:
        # No data rows — header only (or malformed). Emit one chunk.
        return [f"{title}\n{table_md}"]

    header, sep, data = lines[0], lines[1], lines[2:]
    prefix = f"{title}\n{header}\n{sep}"
    prefix_tokens = token_len(prefix)

    chunks: list[str] = []
    buf: list[str] = []
    buf_tokens = 0
    for row in data:
        row_tokens = token_len("\n" + row)
        if buf and prefix_tokens + buf_tokens + row_tokens > target_tokens:
            chunks.append(prefix + "\n" + "\n".join(buf))
            buf = []
            buf_tokens = 0
        buf.append(row)
        buf_tokens += row_tokens
    if buf:
        chunks.append(prefix + "\n" + "\n".join(buf))
    return chunks
