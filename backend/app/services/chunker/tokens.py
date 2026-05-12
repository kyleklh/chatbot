"""Token-length measurement via tiktoken cl100k_base (D-12).

The encoder is constructed once at module import and reused — `tiktoken.get_encoding`
performs disk I/O on first call, so a module-level singleton keeps chunking hot
paths cheap.
"""
from __future__ import annotations

import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def token_len(text: str) -> int:
    """Return the number of cl100k_base tokens in `text`."""
    return len(_enc.encode(text))
