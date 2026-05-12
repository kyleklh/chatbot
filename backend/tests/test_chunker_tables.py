"""Tests for chunker/tables.py — generic table renderer + row-group splitter.

Per Plan 01-03 (D-05, D-06, D-07 LOCKED CONSTRAINT).
"""
from app.services.chunker.tables import render_table_markdown, row_group_split
from app.services.chunker.tokens import token_len


def test_embed_text_shape():
    # Exact 2-row render — header + sep + data, no trailing newline.
    out = render_table_markdown([["a", "b"], ["1", "2"]])
    assert out == "| a | b |\n| --- | --- |\n| 1 | 2 |"

    # Pipe inside a cell must be escaped to \|.
    out_pipe = render_table_markdown([["h1", "h2"], ["a|b", "c"]])
    data_line = out_pipe.split("\n")[-1]
    assert data_line == "| a\\|b | c |"

    # Newline inside a cell becomes a single space.
    out_nl = render_table_markdown([["h1", "h2"], ["a\nb", "c"]])
    data_line = out_nl.split("\n")[-1]
    assert data_line == "| a b | c |"

    # None cells become empty strings.
    out_none = render_table_markdown([["h1", "h2"], [None, "v"]])
    data_line = out_none.split("\n")[-1]
    assert data_line == "|  | v |"

    # Padding: shorter rows pad to max width with empty cells.
    out_pad = render_table_markdown([["a", "b", "c"], ["x"]])
    lines = out_pad.split("\n")
    assert lines[0] == "| a | b | c |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| x |  |  |"


def _balanced_pipes(line: str) -> bool:
    """A markdown table line must start and end with `|` and have N+1 unescaped pipes
    for N cells. We test that every `|` line has at least 2 unescaped pipes and the
    line starts/ends with `|`."""
    if not line.startswith("|") or not line.endswith("|"):
        return False
    # Count unescaped pipes (not preceded by backslash).
    count = 0
    i = 0
    while i < len(line):
        if line[i] == "|" and (i == 0 or line[i - 1] != "\\"):
            count += 1
        i += 1
    return count >= 2


def test_no_row_split():
    # 20 data rows + header.
    cells = [["col1", "col2", "col3"]] + [
        [f"r{i}c1", f"r{i}c2", f"r{i}c3"] for i in range(20)
    ]
    table_md = render_table_markdown(cells)
    chunks = row_group_split(table_md, title="Demo Table", target_tokens=64)

    # Must produce more than 1 chunk at this token budget.
    assert len(chunks) > 1, f"expected >1 chunk, got {len(chunks)}"

    expected_prefix = "Demo Table\n| col1 | col2 | col3 |\n| --- | --- | --- |"
    seen_rows: list[str] = []
    for chunk in chunks:
        assert chunk.startswith(expected_prefix), f"chunk missing prefix: {chunk!r}"
        for line in chunk.split("\n"):
            if line.startswith("|"):
                assert _balanced_pipes(line), f"unbalanced pipes: {line!r}"
        # Collect data rows (lines after the prefix).
        body = chunk[len(expected_prefix):].lstrip("\n")
        for line in body.split("\n"):
            if line.startswith("|") and "---" not in line:
                seen_rows.append(line)

    # Build expected data rows from the original render.
    original_data_rows = table_md.split("\n")[2:]  # skip header + sep
    assert sorted(seen_rows) == sorted(original_data_rows), (
        "data rows lost or duplicated across chunks"
    )
    # No duplication.
    assert len(seen_rows) == len(original_data_rows)

    # Oversize-row case: a single row whose token_len alone exceeds target.
    big_cell = "word " * 200  # well over 64 tokens
    big_cells = [["h1", "h2"], [big_cell, "x"]]
    big_md = render_table_markdown(big_cells)
    big_chunks = row_group_split(big_md, title="Big", target_tokens=64)
    big_data_row = big_md.split("\n")[2]
    # The oversize row appears intact in exactly one chunk.
    occurrences = sum(1 for c in big_chunks if big_data_row in c)
    assert occurrences == 1, (
        f"oversize row should appear intact in exactly one chunk, got {occurrences}"
    )
    # And token_len of that row alone > target — proves we didn't split it.
    assert token_len(big_data_row) > 64
