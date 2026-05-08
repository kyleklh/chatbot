import re

import fitz  # PyMuPDF
from pypdf import PdfReader


def normalize_text(text: str) -> str:
    text = re.sub(r'-\n(\S)', r'\1', text)
    lines = text.split('\n')
    joined: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            joined.append('')
            continue
        if joined and joined[-1] and not re.search(r'[.!?:;|]\s*$', joined[-1]):
            joined[-1] += ' ' + line
        else:
            joined.append(line)
    text = '\n\n'.join(filter(None, '\n'.join(joined).split('\n\n')))
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def _clean(text: str | None) -> str:
    return re.sub(r'\s+', ' ', (text or '').replace('\n', ' ')).strip()


def _parse_values(s: str) -> list[str]:
    """Split a multi-value cell like '$ 514,623 $ 132,502 $ – $ – $ – $ 647,125'
    into individual values ['514,623', '132,502', '–', '–', '–', '647,125']."""
    s = (s or "").strip()
    if not s:
        return []
    if "$" in s:
        parts = re.split(r"\$\s*", s)
        return [p.strip() for p in parts if p.strip()]
    return s.split()


def _fitz_table_to_markdown(rows: list[list]) -> str:
    """Reconstruct a paired-column table (e.g. current vs prior period) where
    PyMuPDF's table finder splits the two paired columns into separate rows
    because of typographic differences (bold vs regular, etc.)."""
    if not rows:
        return ""

    # Find where actual data rows begin: first row whose last column has dollar values
    data_start = 0
    for i, row in enumerate(rows):
        last = row[-1] if row else None
        if last and re.search(r'\$\s*[\d,]+', str(last)):
            data_start = i
            break

    data_rows = rows[data_start:]

    # Detect number of sub-columns by scanning all non-label cells in the first few rows.
    # We can't rely on just the last cell — the Total column often has only one value.
    n_sub = 1
    for row in data_rows[:10]:
        for cell in row[1:]:  # skip label column
            if cell and str(cell).strip():
                first_line = str(cell).split('\n')[0].strip()
                if '$' in first_line:
                    vals = _parse_values(first_line)
                    if len(vals) > n_sub:
                        n_sub = len(vals)
        if n_sub > 1:
            break

    # Try to extract sub-column names from header rows above data_start.
    # For squished tables the headers don't map cleanly to sub-columns, so
    # collect the bottom-most non-empty cell per column as a best-effort label.
    sub_names: list[str] = []
    if n_sub > 1:
        if data_start > 0:
            n_raw_cols = max((len(r) for r in rows[:data_start] if r), default=0)
            col_labels: list[str] = [""] * max(n_raw_cols, n_sub + 1)
            for hrow in rows[:data_start]:
                for ci, cell in enumerate(hrow or []):
                    if ci > 0 and cell and str(cell).strip():
                        col_labels[ci] = _clean(cell)
            candidates = [re.sub(r'\s*\(\d+\)', '', lbl).strip() for lbl in col_labels[1:] if lbl]
            if len(candidates) >= n_sub:
                sub_names = candidates[:n_sub]
        if not sub_names:
            sub_names = [f"Col {k+1}" for k in range(n_sub)]

    # Extract year labels for the two main columns from header rows.
    year_labels: list[str] = []
    for hrow in rows[:data_start]:
        for cell in (hrow or []):
            if cell:
                years = re.findall(r'\b(20\d\d)\b', str(cell))
                for y in years:
                    if y not in year_labels:
                        year_labels.append(y)
    col1_label = year_labels[0] if year_labels else "Col 1"
    col2_label = year_labels[1] if len(year_labels) > 1 else "Col 2"

    if n_sub > 1:
        headers = (
            ["Category"]
            + [f"{col1_label} {c}" for c in sub_names]
            + [f"{col2_label} {c}" for c in sub_names]
        )
    else:
        headers = ["Category", col1_label, col2_label]

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]

    def expand(raw: str) -> list[str]:
        """Parse a value string and pad/trim to n_sub cells."""
        vals = _parse_values(raw)
        return (vals + [""] * n_sub)[:n_sub]

    def make_row(label: str, d_col1: str, d_col2: str) -> str:
        if n_sub > 1:
            cells = [label] + expand(d_col1) + expand(d_col2)
        else:
            cells = [label, d_col1, d_col2]
        return "| " + " | ".join(cells) + " |"

    i = 0
    while i < len(data_rows):
        row = data_rows[i]
        label_cell = row[0] if row else None
        col1 = row[1] if len(row) > 1 else None
        col_last = row[-1] if row else None

        if label_cell is not None:
            raw_labels = [l.strip() for l in (label_cell or '').split('\n') if l.strip()]
            labels: list[str] = []
            for lbl in raw_labels:
                if labels and (lbl[0].islower() or lbl.split()[0].lower() in ('and', 'or', 'of')):
                    labels[-1] += ' ' + lbl
                else:
                    labels.append(lbl)

            data_col2 = [l.strip() for l in (col_last or '').split('\n') if l.strip()]
            col1_empty = not (col1 and str(col1).strip())

            if col1_empty:
                data_col1: list[str] = []
                j = i + 1
                while j < len(data_rows) and data_rows[j][0] is None:
                    d = _clean(data_rows[j][1] if len(data_rows[j]) > 1 else None)
                    if d:
                        data_col1.append(d)
                    j += 1
            else:
                data_col1 = [l.strip() for l in (col1 or '').split('\n') if l.strip()]
                j = i + 1

            n_data = max(len(data_col1), len(data_col2))
            n_section_headers = len(labels) - n_data

            for k in range(max(0, n_section_headers)):
                empty = " | ".join([""] * (n_sub * 2 if n_sub > 1 else 2))
                lines.append(f"| **{labels[k]}** | {empty} |")

            for k in range(n_data):
                idx = k + max(0, n_section_headers)
                label = labels[idx] if idx < len(labels) else ''
                d_col1 = data_col1[k] if k < len(data_col1) else ''
                d_col2 = data_col2[k] if k < len(data_col2) else ''
                lines.append(make_row(label, d_col1, d_col2))

            i = j
        else:
            i += 1

    return '\n'.join(lines)


def _table_has_proper_labels(md: str) -> bool:
    """Return True if the reconstructed markdown is a properly labelled table.

    The reliable signal for a failed reconstruction is that col 1 is almost
    entirely empty — PyMuPDF collapsed everything into col 0 and left the rest
    blank. For a good table (Table 41 style) col 1 has actual numeric values in
    most data rows.
    """
    lines = [l for l in md.split('\n') if l.startswith('|') and '---' not in l]
    if len(lines) < 3:
        return False
    data_lines = lines[1:]  # skip the header row
    empty_col1 = sum(
        1 for line in data_lines
        if len(line.split('|')) >= 3 and not line.split('|')[2].strip()
    )
    return empty_col1 < len(data_lines) * 0.7


def _get_text(page: fitz.Page, clip: fitz.Rect | None = None) -> str:
    if clip is not None:
        return str(page.get_text("text", clip=clip) or "")  # type: ignore[arg-type]
    return str(page.get_text("text") or "")  # type: ignore[arg-type]


def _extract_page(page: fitz.Page) -> str:
    finder = page.find_tables()  # type: ignore[union-attr]
    tables = finder.tables if finder else []

    if not tables:
        return normalize_text(_get_text(page))

    parts: list[str] = []
    page_rect = page.rect
    bboxes = sorted([t.bbox for t in tables], key=lambda b: b[1])

    # Prose above the first table (title / description)
    if bboxes[0][1] > page_rect.y0 + 10:
        clip = fitz.Rect(page_rect.x0, page_rect.y0, page_rect.x1, bboxes[0][1])
        above = normalize_text(_get_text(page, clip))
        if above:
            parts.append(above)

    # Each table reconstructed; fall back to raw text if row labels are missing
    for t in tables:
        md = _fitz_table_to_markdown(t.extract())
        if md and _table_has_proper_labels(md):
            parts.append(md)
        else:
            # Row labels were not captured inside the table bbox. Use raw text
            # from the full page width at this table's vertical extent so that
            # labels printed to the left of the table grid are included.
            clip = fitz.Rect(page_rect.x0, t.bbox[1], page_rect.x1, t.bbox[3])
            raw = normalize_text(_get_text(page, clip))
            if raw:
                parts.append(raw)

    # Prose below the last table (footnotes)
    if bboxes[-1][3] < page_rect.y1 - 10:
        clip = fitz.Rect(page_rect.x0, bboxes[-1][3], page_rect.x1, page_rect.y1)
        below = normalize_text(_get_text(page, clip))
        if below:
            parts.append(below)

    return '\n\n'.join(p for p in parts if p)


def extract_pdf_pages(file_path: str) -> list[dict]:
    pages = []

    try:
        doc = fitz.open(file_path)
        for index, page in enumerate(doc):  # type: ignore[arg-type]
            text = _extract_page(page)
            if text:
                pages.append({"page": index + 1, "text": text})
    except Exception as e:
        print(f"PyMuPDF failed ({e}), falling back to pypdf")
        reader = PdfReader(file_path)
        for index, page in enumerate(reader.pages):
            text = normalize_text(page.extract_text() or "")
            if text:
                pages.append({"page": index + 1, "text": text})

    return pages
