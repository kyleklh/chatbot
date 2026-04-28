import re


def split_sentences(text: str) -> list[str]:
    # Split on sentence-ending punctuation followed by space + capital or end of string.
    # Avoids splitting on common abbreviations (single uppercase letter, digits, "et al.", etc.)
    pattern = re.compile(
        r'(?<!\b[A-Z])(?<!\b[A-Z][a-z])(?<!\d)'  # negative lookbehind: not abbreviation
        r'(?<=[.!?])'                               # preceded by sentence-ending punct
        r'(?:\s{1,2})'                              # whitespace separator
        r'(?=[A-Z"\(\[])'                           # followed by capital / opening bracket
    )
    parts = pattern.split(text)
    return [p.strip() for p in parts if p.strip()]


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 900,
    overlap: int = 150
) -> list[dict]:
    chunks = []

    for page in pages:
        page_num = page["page"]
        text = page["text"].strip()

        if not text:
            continue

        sentences = split_sentences(text)

        # If splitting produced nothing useful, fall back to the whole page as one chunk
        if not sentences:
            chunks.append({"page": page_num, "text": text})
            continue

        current: list[str] = []
        current_len = 0

        for sentence in sentences:
            sentence_len = len(sentence) + 1  # +1 for the space when joining

            # If a single sentence is already larger than chunk_size, emit it alone
            if not current and sentence_len > chunk_size:
                chunks.append({"page": page_num, "text": sentence})
                continue

            if current and current_len + sentence_len > chunk_size:
                chunks.append({"page": page_num, "text": " ".join(current)})

                # Carry overlap sentences forward
                overlap_sents: list[str] = []
                overlap_len = 0
                for s in reversed(current):
                    cost = len(s) + 1
                    if overlap_len + cost <= overlap:
                        overlap_sents.insert(0, s)
                        overlap_len += cost
                    else:
                        break
                current = overlap_sents
                current_len = overlap_len

            current.append(sentence)
            current_len += sentence_len

        if current:
            chunks.append({"page": page_num, "text": " ".join(current)})

    return chunks
