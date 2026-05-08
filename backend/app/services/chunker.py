import re
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import CHUNK_SIZE, CHUNK_OVERLAP


def _table_embed_text(table_text: str, preceding_title: str) -> str:
    """Build a natural language summary for embedding a table chunk.

    Raw markdown (pipes + numbers) produces a poor vector. Embedding the section
    title + row labels instead closes the semantic gap between natural language
    queries and table content.
    """
    labels: list[str] = []
    for line in table_text.split("\n"):
        if not line.startswith("|") or "---" in line:
            continue
        parts = line.split("|")
        if len(parts) < 2:
            continue
        label = re.sub(r"\*+", "", parts[1]).strip()
        if label and label.lower() not in ("category", ""):
            labels.append(label)

    summary = preceding_title.strip()
    if labels:
        summary += " Categories: " + ", ".join(labels[:40])
    return summary


def _split_sections(text: str) -> list[dict[str, str]]:
    """Split page text into alternating prose and table sections."""
    sections: list[dict[str, str]] = []
    current_type: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        section_type = "table" if line.startswith("|") else "prose"
        if section_type != current_type:
            if current_lines:
                sections.append({"type": current_type or "prose", "text": "\n".join(current_lines)})
            current_type = section_type
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({"type": current_type or "prose", "text": "\n".join(current_lines)})

    return sections


def chunk_pages(
    pages: list[dict[str, Any]],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict[str, Any]] = []

    for page in pages:
        page_num = page["page"]
        sections = _split_sections(page["text"])
        preceding_title = ""

        for section in sections:
            if section["type"] == "prose":
                doc = Document(page_content=section["text"], metadata={"page": page_num})
                for split in splitter.split_documents([doc]):
                    text = split.page_content.strip()
                    if text:
                        chunks.append({"text": text, "page": page_num})
                # Keep up to 500 chars of trailing prose as context for the next table.
                # Using just the last paragraph gave "As at" — not enough for a good embedding.
                preceding_title = section["text"].strip()[-500:]
            else:
                table_text = section["text"].strip()
                if not table_text:
                    continue
                combined = (preceding_title + "\n\n" + table_text).strip() if preceding_title else table_text
                embed_text = _table_embed_text(table_text, preceding_title) if preceding_title else ""
                chunk: dict[str, Any] = {"text": combined, "page": page_num}
                if embed_text:
                    chunk["embed_text"] = embed_text
                chunks.append(chunk)
                preceding_title = ""

    return chunks