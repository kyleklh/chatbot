"""Header detection wrapper for the chunking pipeline (Plan 01-02).

Per D-01 we delegate font-size-mode header detection to
`pymupdf4llm.IdentifyHeaders` (which already implements "most-frequent rounded
font size = body, larger sizes = H1..Hn"). On top of that we layer a secondary
"whole-line bold" signal so headings rendered bold at body size still get
caught (RESEARCH Open Question #4).

D-02 caps header levels at H1 + H2 (max_levels=2 by default).
D-01 forbids both numbered-prefix regex sniffing and `doc.get_toc()` reliance.
"""
from __future__ import annotations

import pymupdf
from pymupdf4llm.helpers.pymupdf_rag import IdentifyHeaders

# PyMuPDF span["flags"] bit 16 == bold. See PyMuPDF text-extraction docs.
_BOLD_FLAG = 16

# Whole-line-bold fallback gate parameters (RESEARCH OQ #4).
_BOLD_FALLBACK_MAX_LEN = 80
_BODY_TERMINAL_PUNCT = (".", ";", ":")


class HeaderClassifier:
    """Classify spans/lines as H1 (1), H2 (2), or body (0).

    Delegates the primary font-size signal to
    `pymupdf4llm.IdentifyHeaders.get_header_id`. Adds a whole-line-bold
    fallback for headings styled bold at body-size.
    """

    def __init__(self, doc: pymupdf.Document, max_levels: int = 2) -> None:
        # max_levels=2 enforces D-02 (H1 + H2 only). pymupdf4llm validates
        # the integer range (1..6) itself.
        self._id = IdentifyHeaders(doc, max_levels=max_levels)

    def classify_span(self, span: dict, page) -> int:
        """Return 1 for H1, 2 for H2, 0 for body — based on font-size mode only."""
        marker = self._id.get_header_id(span, page=page).strip()
        if marker == "#":
            return 1
        if marker == "##":
            return 2
        return 0

    def classify_line(self, line: dict, page) -> int:
        """Return 1 / 2 / 0 for a whole line.

        Order of precedence:
          1. If any span on the line is flagged H1 or H2 by font-size mode,
             return the max level present.
          2. Else apply the whole-line-bold fallback: ALL spans bold (flag
             bit 16) AND combined stripped text length <= 80 AND no terminal
             ``.;:`` punctuation → H2.
          3. Else body (0).
        """
        spans = line.get("spans", [])
        if not spans:
            return 0

        best = 0
        for span in spans:
            level = self.classify_span(span, page)
            if level == 1:
                return 1
            if level == 2:
                best = 2
        if best:
            return best

        # Whole-line-bold fallback (D-01 secondary signal).
        all_bold = all((s.get("flags", 0) & _BOLD_FLAG) for s in spans)
        text = "".join(s.get("text", "") for s in spans).strip()
        if (
            all_bold
            and 0 < len(text) <= _BOLD_FALLBACK_MAX_LEN
            and not text.endswith(_BODY_TERMINAL_PUNCT)
        ):
            return 2
        return 0


__all__ = ["HeaderClassifier"]
