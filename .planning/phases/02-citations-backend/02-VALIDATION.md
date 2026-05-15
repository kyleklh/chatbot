---
phase: 2
slug: citations-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` or `backend/pyproject.toml` (confirm in Wave 0) |
| **Quick run command** | `cd backend && pytest -q -m "not semantic"` |
| **Full suite command** | `cd backend && pytest -q` |
| **Estimated runtime** | ~30–60 seconds (quick); semantic LLM-judge tests gated separately |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Populated by the planner against the final PLAN.md task IDs. Each Success Criterion below MUST trace to at least one automated test.

| Success Criterion | Requirement | Test Type | Automated Command | File Exists | Status |
|-------------------|-------------|-----------|-------------------|-------------|--------|
| SC1 — `[N]` markers emitted DURING generation (not stitched at end) | REQ-grounded-citations | unit/integration | `pytest backend/tests/test_citations_eval.py -k stream_marker` | ❌ W0 | ⬜ pending |
| SC2 — each marker → chunk_id + document_id + page + verbatim quote substring | REQ-grounded-citations | unit | `pytest backend/tests/test_citations_eval.py -k verbatim` | ❌ W0 | ⬜ pending |
| SC3 — per-message `sources[]` carries chunk_id + page + quote (LOCKED schema) | REQ-grounded-citations | unit | `pytest backend/tests/test_citations_eval.py -k done_event_schema` | ❌ W0 | ⬜ pending |
| SC4 — LLM call site behind a thin provider abstraction (swap-ready) | REQ-provider-flexible-llm | unit | `pytest backend/tests/test_llm_provider.py` | ❌ W0 | ⬜ pending |
| SC5 — `/chat/stream` `document_ids` filter regression-free + citation provenance | REQ-no-happy-path-regressions | integration | `pytest backend/tests/test_pipeline_smoke.py -k document_ids` | ✅ (extend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_llm_provider.py` — stubs for the `LLMProvider` Protocol seam + `get_provider()` factory + a fake/stub provider for deterministic citation tests (REQ-provider-flexible-llm)
- [ ] `backend/tests/test_citations_eval.py` — stubs for tolerant parser, marker resolution, verbatim-quote extraction, `DoneEvent` schema (REQ-grounded-citations)
- [ ] `backend/tests/test_pipeline_smoke.py::test_document_ids_filter` — EXTEND existing test to assert citation provenance (every cited chunk's `document_id` ∈ requested filter) for SC5
- [ ] Migrate `backend/tests/test_groq_client.py` — 4 existing tests patch `_client` / assert `HTTPException(503)`; they break when `groq_client.py` shrinks into `GroqProvider`. Plan a migration task, not a deletion.
- [ ] Confirm pytest config + `semantic` marker registration (RESEARCH.md notes semantic LLM-judge tests are gated)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Claim-to-source faithfulness (cited chunk actually supports the claim) | REQ-grounded-citations | Semantic judgment — LLM-judge needs human calibration before trusted (AI-SPEC Section 5) | Run `pytest -m semantic` against `citations_golden.jsonl`; spot-check faithfulness scores against expected labels |
| Calibrated abstention on retrieval miss | REQ-grounded-citations | Requires adversarial "answer-not-in-doc" examples + human threshold judgment | Manual UAT with the 3 adversarial golden-dataset records |

*Note: the deterministic half of every Success Criterion (SC1–SC5) has automated verification. Only the semantic eval dimensions are manual/gated.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (4 test files above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
