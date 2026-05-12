"""Wave 0 gate: confirms ≥3 user-provided sample PDFs are present.

This test xfails by default. When the user drops ≥3 `.pdf` files into
`backend/tests/fixtures/pdfs/`, the assertion becomes true and the test
becomes xpass under strict=True — which fails — so we use a non-strict
xfail here so the test simply flips to PASSED once fixtures exist. This
mirrors the "fixture gate" pattern called out in plan 01-00 acceptance.
"""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "pdfs"


def _count_pdfs() -> int:
    if not FIXTURE_DIR.exists():
        return 0
    return sum(1 for p in FIXTURE_DIR.iterdir() if p.suffix.lower() == ".pdf")


@pytest.mark.xfail(
    condition=_count_pdfs() < 3,
    strict=False,
    reason="Drop ≥3 real PDFs into backend/tests/fixtures/pdfs/ for SC1.",
)
def test_sample_pdfs_present():
    assert _count_pdfs() >= 3, (
        f"Expected ≥3 .pdf files in {FIXTURE_DIR}, found {_count_pdfs()}."
    )
