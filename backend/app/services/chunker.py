from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_pages(
    pages: list[dict[str, Any]],
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[dict[str, Any]]:
    docs: list[Document] = []

    for page in pages:
        docs.append(
            Document(
                page_content=page["text"],
                metadata={"page": page["page"]},
            )
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    split_docs = splitter.split_documents(docs)

    chunks: list[dict[str, Any]] = []

    for doc in split_docs:
        text = doc.page_content.strip()

        if text:
            chunks.append(
                {
                    "text": text,
                    "page": doc.metadata["page"],
                }
            )

    return chunks