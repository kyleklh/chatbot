"""Wave 0 test stubs for SC4 — LLM provider Protocol seam.

These stubs are implemented in Plan 02-01 (provider seam + factory + GroqProvider).
All tests skip cleanly so the suite collects without ImportError before the
provider module exists.
"""

import pytest


def test_get_provider_returns_groq_for_default_config():
    pytest.skip("Wave 0 stub — implemented in Plan 02-01")


def test_get_provider_unknown_raises_valueerror():
    pytest.skip("Wave 0 stub — implemented in Plan 02-01")


def test_get_provider_caches_instance():
    pytest.skip("Wave 0 stub — implemented in Plan 02-01")


def test_fake_provider_satisfies_protocol():
    pytest.skip("Wave 0 stub — implemented in Plan 02-01")


def test_groq_provider_stream_yields_tokens():
    pytest.skip("Wave 0 stub — implemented in Plan 02-01")


def test_groq_provider_generate_returns_string():
    pytest.skip("Wave 0 stub — implemented in Plan 02-01")


def test_groq_provider_raises_native_exception_not_httpexception():
    pytest.skip("Wave 0 stub — implemented in Plan 02-01")


def test_groq_provider_token_count():
    pytest.skip("Wave 0 stub — implemented in Plan 02-01")
