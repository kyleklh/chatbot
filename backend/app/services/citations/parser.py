"""Tolerant streaming citation-marker parser (D-01/D-02/D-03/D-04).

`CitationStreamParser` is constructed from a `filtered_sources` list (the
retrieved+filtered child-chunk dicts produced by langgraph_rag); it then
consumes raw LLM tokens via `feed()` and yields cleaned tokens with marker
text normalized to canonical discrete `[N]` form, unresolvable markers
stripped + print()-logged, and a marker→chunk_id map built incrementally.

Markdown-context blindness is an ACCEPTED v1 limitation: the parser does
NOT track code-fence state, so a `[1]` literal inside ``` code blocks WILL
be treated as a citation (RESEARCH Assumption A3 / edge-case table).

The buffered-regex hybrid:

* All input is appended to a single internal buffer.
* After each feed the buffer is scanned for COMPLETE marker matches
  (regex `_MARKER_RE`). Each match is replaced in-place with canonical
  discrete markers (or stripped, if unresolvable).
* Only the prefix of the buffer that CANNOT be part of an in-progress
  marker is yielded — a trailing ``[``, ``[Sou``, ``[1,`` is held back
  until more tokens arrive or `flush()` is called.
* `flush()` runs the regex one final time; any unterminated ``[...`` left
  over is emitted as literal text (the LLM produced a non-marker bracket).
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from .quotes import extract_quote

# Canonical marker regex — captures `[N]`, `[Source N]`, `[1, 2]`, `[ 3 ]`.
# Linear in the input length; no nested quantifiers over overlapping classes
# (T-02-02-01 — no ReDoS path). Do NOT add `.*` or nested optional groups.
_MARKER_RE = re.compile(r"\[\s*(?:Source\s+)?(\d+(?:\s*,\s*\d+)*)\s*\]")

# A trailing buffer chunk starting with `[` can still grow into a complete
# marker iff its content is a prefix of one. Anything else means the `[` is
# literal text and we can release it.
_POSSIBLE_PREFIX_RE = re.compile(r"^\[\s*(?:S(?:o(?:u(?:r(?:ce?)?)?)?)?\s*)?\d*(?:\s*,\s*\d*)*\s*$")


class CitationStreamParser:
    """Tolerant streaming citation parser.

    Construct with a list of `filtered_sources` (see plan `<interfaces>` for
    shape); feed raw LLM tokens; iterate cleaned tokens; call `flush()` once
    the upstream stream ends; then read `marker_to_chunk_id()` and
    `enriched_sources()` to assemble the DoneEvent payload.
    """

    def __init__(self, filtered_sources: list[dict]):
        self._sources: list[dict] = list(filtered_sources)
        self._buffer: str = ""
        self._marker_map: dict[str, str] = {}
        # Full cleaned answer text seen so far — used as the answer_span for
        # per-source quote extraction in enriched_sources().
        self._answer_text: str = ""

    # ------------------------------------------------------------------ feed

    def feed(self, raw_token: str) -> Iterator[str]:
        """Append `raw_token` to the buffer and yield any cleaned text that is
        safe to release (i.e. cannot become part of an in-progress marker)."""
        if raw_token:
            self._buffer += raw_token
        yield from self._drain(final=False)

    def flush(self) -> Iterator[str]:
        """Emit any buffered tail. After flush the buffer is empty; an
        unterminated `[...` is yielded as literal text."""
        yield from self._drain(final=True)

    # --------------------------------------------------------------- internals

    def _drain(self, *, final: bool) -> Iterator[str]:
        """Process the current buffer and yield as much cleaned text as is
        safe given `final` (on `final=True` everything is released)."""
        # 1. Find the safe boundary: the index up to which we can run the
        #    regex without risking truncating an in-progress marker.
        if final:
            safe_end = len(self._buffer)
            held_back = ""
        else:
            safe_end, held_back = self._split_safe_prefix(self._buffer)

        if safe_end == 0:
            # Nothing safe to release yet — keep buffering.
            self._buffer = held_back
            return

        head = self._buffer[:safe_end]

        # 2. Process complete markers in `head`.
        cleaned = self._process_markers(head)

        # 3. Update state and yield.
        self._buffer = held_back
        if cleaned:
            self._answer_text += cleaned
            yield cleaned

    def _split_safe_prefix(self, buf: str) -> tuple[int, str]:
        """Return ``(safe_end, held_back)`` such that ``buf[:safe_end]`` may be
        safely scanned for markers and ``buf[safe_end:] == held_back`` is the
        unsafe tail that could still grow into a marker."""
        # Walk from the right: the rightmost `[` whose suffix could still be a
        # marker prefix defines the boundary. If no `[` in buf, everything is
        # safe.
        idx = buf.rfind("[")
        if idx == -1:
            return len(buf), ""
        tail = buf[idx:]
        if "]" in tail:
            # The bracket is already closed — the regex will handle it (or
            # leave it as literal). Everything is safe to process.
            return len(buf), ""
        if _POSSIBLE_PREFIX_RE.match(tail):
            # Could still grow into a complete marker — hold back from idx.
            return idx, tail
        # The bracket is followed by content that cannot be a marker prefix
        # (e.g. `[hello`) — safe to release as literal text.
        return len(buf), ""

    def _process_markers(self, text: str) -> str:
        """Substitute every complete marker match in `text`. Resolvable markers
        become canonical discrete `[N]` (one per number; a `[1, 2]` becomes
        `[1][2]`). Unresolvable markers are stripped from the output and
        print()-logged."""

        def _sub(m: re.Match[str]) -> str:
            group = m.group(1)
            parts = [p.strip() for p in group.split(",")]
            out: list[str] = []
            for p in parts:
                if not p.isdigit():
                    continue
                n = int(p)
                if 1 <= n <= len(self._sources):
                    src = self._sources[n - 1]
                    chunk_id = src.get("chunk_id", "")
                    self._marker_map[str(n)] = chunk_id
                    out.append(f"[{n}]")
                else:
                    # D-03: strip + print()-log (counts only, no content).
                    print(
                        f"[citation] stripped unresolvable marker [{n}] "
                        f"(have {len(self._sources)} sources)"
                    )
            return "".join(out)

        return _MARKER_RE.sub(_sub, text)

    # ----------------------------------------------------------------- outputs

    def marker_to_chunk_id(self) -> dict[str, str]:
        """Return the marker-number → chunk_id mapping built during feeding."""
        return dict(self._marker_map)

    def enriched_sources(self) -> list[dict]:
        """Return the per-source enrichment list for the DoneEvent payload."""
        out: list[dict] = []
        for s in self._sources:
            metadata = s.get("metadata") or {}
            chunk_text = s.get("text", "")
            quote = extract_quote(chunk_text, self._answer_text)
            out.append(
                {
                    "chunk_id": s.get("chunk_id", ""),
                    "document_id": metadata.get("document_id", ""),
                    "page": s.get("page", 0),
                    "text": chunk_text,
                    "filename": s.get("filename", metadata.get("file_name", "")),
                    "distance": s.get("distance"),
                    "quote": quote,
                }
            )
        return out
