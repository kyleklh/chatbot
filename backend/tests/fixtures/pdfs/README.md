# Sample PDFs for Phase 01 verification

This directory holds **three real PDFs** that the chunking-rebuild work
(Phase 01) must handle correctly before the phase is signed off. They are
gitignored on purpose — drop your own files here at phase-verification time.

## What to put here

Per D-13 and Plan 01 success criterion SC1, place **3 PDFs** in this folder
that exercise the chunker in realistic ways:

1. A PDF with clear headings and prose (e.g. a paper or report).
2. A PDF with at least one multi-row table.
3. A PDF with mixed layout (headings spanning pages, lists, etc.).

File extensions must be `.pdf` (lowercase).

## Verification gate

Once ≥3 `.pdf` files exist here, `tests/test_fixtures.py::test_sample_pdfs_present`
flips from xfail to passing. Downstream Wave 4 SC1 tests then run against
these files.

## Note

These PDFs are **never committed** beyond this README — they may contain
user-private content. See `backend/.gitignore` (or the project root) for
the ignore rule.
