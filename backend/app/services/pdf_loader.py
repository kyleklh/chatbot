import re
from pypdf import PdfReader


def normalize_text(text: str) -> str:
    # Rejoin hyphenated line breaks (e.g. "infor-\nmation" → "information")
    text = re.sub(r'-\n(\S)', r'\1', text)

    # Join lines that are mid-sentence: if a line doesn't end with sentence
    # punctuation, join it with the next line using a space
    lines = text.split('\n')
    joined: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            joined.append('')
            continue
        if joined and joined[-1] and not re.search(r'[.!?:;]\s*$', joined[-1]):
            joined[-1] += ' ' + line
        else:
            joined.append(line)

    # Collapse multiple blank lines into one paragraph break
    text = '\n\n'.join(filter(None, '\n'.join(joined).split('\n\n')))

    # Normalize multiple spaces
    text = re.sub(r'  +', ' ', text)

    return text.strip()


def extract_pdf_pages(file_path: str) -> list[dict]:
    reader = PdfReader(file_path)
    pages = []

    for index, page in enumerate(reader.pages):
        raw = page.extract_text() or ""
        text = normalize_text(raw)

        if text:
            pages.append({
                "page": index + 1,
                "text": text
            })

    return pages
