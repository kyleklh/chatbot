"""SC1/SC2/SC3 tests for the grounded-citations parser, verbatim-quote
substring guarantee, and DoneEvent schema.

Plan 02-02 implements parser/quote/schema tests (SC2 + SC3); Plan 02-03 will
replace the SC1 stream-marker integration stub.
"""

from __future__ import annotations

import random

import pytest

from app.models.schemas import DoneEvent, Source
from app.services.citations.parser import CitationStreamParser
from app.services.citations.quotes import best_quote_span, extract_quote


# ---------------------------------------------------------------- fixtures


def _src(idx: int, text: str, *, page: int = 1, document_id: str | None = None) -> dict:
    """Build a `filtered_sources` element matching the langgraph_rag shape."""
    doc_id = document_id or f"doc{idx}"
    chunk_id = f"chunk_{idx:02d}"
    return {
        "text": text,
        "metadata": {
            "document_id": doc_id,
            "chunk_id": chunk_id,
            "page": page,
            "file_name": f"f{idx}.pdf",
        },
        "filename": f"f{idx}.pdf",
        "page": page,
        "chunk_id": chunk_id,
        "distance": 0.1,
    }


@pytest.fixture
def filtered_sources() -> list[dict]:
    return [
        _src(1, "The rent is 5000 dollars per month. Tenants pay on the first."),
        _src(2, "The lease term is twelve months starting January."),
        _src(3, "Security deposit equals one month of rent."),
        _src(4, "Late fees apply after the fifth day of the month."),
    ]


# ---------------------------------------------------------------- SC1 stub
# Stream-marker integration is wired in Plan 02-03; keep the stub here.


def test_stream_marker_emitted_during_generation():
    """SC1 — stream emits the citation marker tokens during generation."""
    pytest.skip("Wave 0 stub — implemented in Plan 02-03")


# ---------------------------------------------------------------- SC2 quote


def test_verbatim_quote_is_substring_of_chunk(filtered_sources):
    """SC2 — every cited verbatim quote is a substring of the source chunk."""
    parser = CitationStreamParser(filtered_sources)
    list(parser.feed("The rent is 5000 dollars per month [1]."))
    list(parser.flush())
    enriched = parser.enriched_sources()
    assert len(enriched) == len(filtered_sources)
    for s in enriched:
        assert s["quote"] in s["text"], (
            f"quote {s['quote']!r} not a substring of chunk text {s['text']!r}"
        )


def test_best_quote_span_returns_verbatim_indices():
    """`best_quote_span` returns indices that re-slice to a verbatim substring."""
    ct = "Security deposit equals one month of rent."
    span_start, span_end, score = best_quote_span(ct, "deposit equals one month")
    assert ct[span_start:span_end] in ct
    assert score > 0.5


def test_extract_quote_falls_back_on_low_score(capsys):
    """Low-score input falls back to the leading sentence + logs the score."""
    ct = "First sentence here. Second one too."
    quote = extract_quote(ct, "totally unrelated xyz abc")
    assert quote in ct
    assert quote.startswith("First sentence")
    captured = capsys.readouterr()
    assert "low-score" in captured.out
    # D-03: must not leak chunk text.
    assert "First sentence" not in captured.out


# ---------------------------------------------------------------- SC3 schema


def test_done_event_schema_validates(filtered_sources):
    """SC3 — final DoneEvent payload validates against the schema."""
    parser = CitationStreamParser(filtered_sources)
    list(parser.feed("Rent is 5000 dollars [1] and the term is twelve months [2]."))
    list(parser.flush())
    enriched = parser.enriched_sources()
    marker_map = parser.marker_to_chunk_id()
    sources = [Source(**{k: v for k, v in s.items() if k in Source.model_fields}) for s in enriched]
    event = DoneEvent(sources=sources, marker_map=marker_map)
    assert event.done is True
    assert event.marker_map == {"1": "chunk_01", "2": "chunk_02"}


def test_done_event_rejects_unknown_chunk_id():
    s = Source(text="t", page=1, filename="f", chunk_id="chunk_01")
    with pytest.raises(Exception):  # noqa: PT011 — ValidationError
        DoneEvent(sources=[s], marker_map={"1": "nope"})


# ---------------------------------------------------------------- SC2 shuffle


def test_marker_resolves_by_chunk_id_after_shuffle(filtered_sources):
    """SC2/SC3 — marker resolution is chunk_id-based, not position-based.

    After shuffling `filtered_sources` we must still resolve `[N]` markers to
    the chunk_id of the source at position N in the (new) list — i.e. the
    parser's contract is positional within its OWN list, and the chunk_id
    written into marker_map is whichever chunk happens to be at that position.
    The key invariant: every marker_map value is some chunk_id that exists
    in the parser's source list, and is exactly the source[N-1].chunk_id.
    """
    rng = random.Random(42)
    shuffled = list(filtered_sources)
    rng.shuffle(shuffled)

    parser = CitationStreamParser(shuffled)
    list(parser.feed("Citing [1] and [3] and [4]."))
    list(parser.flush())

    marker_map = parser.marker_to_chunk_id()
    expected = {
        "1": shuffled[0]["chunk_id"],
        "3": shuffled[2]["chunk_id"],
        "4": shuffled[3]["chunk_id"],
    }
    assert marker_map == expected
    # Every value resolves to a chunk_id that actually exists in the parser's source list.
    known = {s["chunk_id"] for s in shuffled}
    for v in marker_map.values():
        assert v in known


# ---------------------------------------------------------- parser semantics


def test_parser_normalizes_source_n_drift(filtered_sources):
    """`[Source 2]` and `[1, 2]` drift normalizes to canonical discrete `[N]`."""
    parser = CitationStreamParser(filtered_sources)
    pieces = list(parser.feed("Lease term [Source 2] and combined [1, 2] facts."))
    pieces += list(parser.flush())
    out = "".join(pieces)
    assert "[2]" in out
    assert "[1][2]" in out
    assert "[Source 2]" not in out
    assert "[1, 2]" not in out
    assert parser.marker_to_chunk_id() == {"1": "chunk_01", "2": "chunk_02"}


def test_parser_strips_unresolvable_marker(filtered_sources):
    """An unresolvable `[5]` against 4 sources is stripped + logged (D-03)."""
    parser = CitationStreamParser(filtered_sources)
    pieces = list(parser.feed("Bogus citation [5] should vanish."))
    pieces += list(parser.flush())
    out = "".join(pieces)
    assert "[5]" not in out
    assert "Bogus citation  should vanish." == out  # marker stripped, surrounding text kept
    # The unresolvable marker must NOT appear in marker_map.
    assert "5" not in parser.marker_to_chunk_id()


def test_parser_handles_marker_split_across_tokens(filtered_sources):
    """Pitfall 2: a marker split as `"["` then `"2]"` across feeds resolves."""
    parser = CitationStreamParser(filtered_sources)
    out1 = "".join(parser.feed("See ["))
    out2 = "".join(parser.feed("2]"))
    out3 = "".join(parser.flush())
    final = out1 + out2 + out3
    assert "[2]" in final
    assert parser.marker_to_chunk_id() == {"2": "chunk_02"}


def test_parser_handles_source_n_split_across_tokens(filtered_sources):
    """A `[Source N]` marker arriving in many small tokens still resolves."""
    parser = CitationStreamParser(filtered_sources)
    tokens = ["See [", "Sou", "rce ", "3", "]", " for details."]
    out = "".join(piece for tok in tokens for piece in parser.feed(tok))
    out += "".join(parser.flush())
    assert "[3]" in out
    assert "[Source 3]" not in out
    assert parser.marker_to_chunk_id() == {"3": "chunk_03"}


def test_parser_unterminated_bracket_emitted_literal(filtered_sources):
    """A bracket-content that never closes is emitted as literal text."""
    parser = CitationStreamParser(filtered_sources)
    out = "".join(parser.feed("Open [bracket but never close"))
    out += "".join(parser.flush())
    assert "Open [bracket but never close" == out


def test_parser_literal_bracket_with_non_marker_content(filtered_sources):
    """`[hello]` (non-digit content) is left untouched in output."""
    parser = CitationStreamParser(filtered_sources)
    out = "".join(parser.feed("Markdown [link](url) and [hello] text."))
    out += "".join(parser.flush())
    assert "[link]" in out
    assert "[hello]" in out
    assert parser.marker_to_chunk_id() == {}
