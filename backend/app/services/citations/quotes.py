"""Deterministic verbatim quote extraction (SC2's verbatim guarantee).

Uses stdlib `difflib.SequenceMatcher` with `autojunk=False` (load-bearing —
`autojunk=True` will silently drop common short tokens from the haystack and
break exact-substring matching on chunks longer than 200 chars). The returned
span indexes directly into the chunk text, so `chunk_text[start:end]` is a
verbatim substring by construction.

Locked design choice (RESEARCH §"Supporting-Quote Extraction", PATTERNS
§quotes.py): stdlib `difflib` only — no third-party fuzzy-match dependency is
installed in this project's environment.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# Sentence-boundary characters used to expand a fuzzy match outward to a more
# readable quote while remaining a verbatim substring of the chunk.
_SENTENCE_END = re.compile(r"[.!?]\s+|\n+")


def best_quote_span(chunk_text: str, answer_span: str) -> tuple[int, int, float]:
    """Return ``(start, end, score)`` for the longest verbatim substring of
    ``chunk_text`` that overlaps ``answer_span``.

    ``score`` is ``match.size / max(len(answer_span), 1)`` — a rough fraction of
    the answer span covered by the longest common substring. ``chunk_text[start:end]``
    is guaranteed to be a substring of ``chunk_text`` (SC2).
    """
    if not chunk_text or not answer_span:
        return 0, 0, 0.0
    sm = SequenceMatcher(None, chunk_text, answer_span, autojunk=False)
    match = sm.find_longest_match(0, len(chunk_text), 0, len(answer_span))
    start = match.a
    end = match.a + match.size
    score = match.size / max(len(answer_span), 1)
    return start, end, score


def _expand_to_sentence(chunk_text: str, start: int, end: int) -> tuple[int, int]:
    """Expand ``[start, end]`` outward to the nearest sentence boundaries within
    ``chunk_text``. The result is still a slice of ``chunk_text``.
    """
    n = len(chunk_text)
    if n == 0:
        return 0, 0
    # Walk left to the start of the current sentence.
    left = start
    while left > 0:
        prev = chunk_text[left - 1]
        if prev in ".!?\n":
            break
        left -= 1
    # Skip whitespace after the previous sentence boundary.
    while left < n and chunk_text[left] in " \t\r\n":
        left += 1
    # Walk right to the end of the current sentence.
    right = end
    while right < n and chunk_text[right - 1] not in ".!?\n":
        right += 1
        if right >= n:
            break
    # Clamp and ensure non-empty when possible.
    left = max(0, min(left, n))
    right = max(left, min(right, n))
    if right == left and n > 0:
        return 0, min(n, max(end, 1))
    return left, right


def _leading_sentence(chunk_text: str) -> str:
    """Return the chunk's first sentence (always a verbatim substring)."""
    if not chunk_text:
        return ""
    m = _SENTENCE_END.search(chunk_text)
    if not m:
        return chunk_text
    return chunk_text[: m.end()].rstrip()


def extract_quote(
    chunk_text: str, answer_span: str, score_threshold: float = 0.4
) -> str:
    """Return a verbatim-substring quote from ``chunk_text``.

    Algorithm:

    1. Find the best fuzzy overlap span via :func:`best_quote_span`.
    2. If ``score >= score_threshold``, expand outward to sentence boundaries
       (still a substring of ``chunk_text``) and return that slice.
    3. Otherwise fall back to the chunk's leading sentence and ``print()``-log
       the score (D-03: thin logging — score only, never chunk text or keys).
    """
    if not chunk_text:
        return ""
    if not answer_span:
        return _leading_sentence(chunk_text)

    start, end, score = best_quote_span(chunk_text, answer_span)
    if score < score_threshold or end <= start:
        print(f"[citation] low-score quote fallback (score={score:.3f})")
        return _leading_sentence(chunk_text)

    left, right = _expand_to_sentence(chunk_text, start, end)
    quote = chunk_text[left:right].strip()
    if not quote:
        # Pathological expansion — return the raw matched span (still a substring).
        return chunk_text[start:end]
    return quote
