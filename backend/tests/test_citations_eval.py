"""Wave 0 test stubs for SC1/SC2/SC3 — grounded citations parser, verbatim
quote substring guarantee, and DoneEvent schema.

Parser/quote/schema tests are implemented in Plan 02-02; the stream-marker
integration test is implemented in Plan 02-03. All stubs skip cleanly so the
suite collects before any of those modules exist.
"""

import pytest


def test_stream_marker_emitted_during_generation():
    """SC1 — stream emits the citation marker tokens during generation."""
    pytest.skip("Wave 0 stub — implemented in Plan 02-03")


def test_verbatim_quote_is_substring_of_chunk():
    """SC2 — every cited verbatim quote is a substring of the source chunk."""
    pytest.skip("Wave 0 stub — implemented in Plan 02-02")


def test_done_event_schema_validates():
    """SC3 — final DoneEvent payload validates against the schema."""
    pytest.skip("Wave 0 stub — implemented in Plan 02-02")


def test_marker_resolves_by_chunk_id_after_shuffle():
    """SC2/SC3 — marker resolution is chunk_id-based, not position-based."""
    pytest.skip("Wave 0 stub — implemented in Plan 02-02")


def test_parser_normalizes_source_n_drift():
    pytest.skip("Wave 0 stub — implemented in Plan 02-02")


def test_parser_strips_unresolvable_marker():
    pytest.skip("Wave 0 stub — implemented in Plan 02-02")


def test_parser_handles_marker_split_across_tokens():
    pytest.skip("Wave 0 stub — implemented in Plan 02-02")
