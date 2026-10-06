# AgentRx Adapter (Stage 2, Wave 1) — Observational Track O-A

**What this adapter is.** A **READ-ONLY** loader/scorer for the `microsoft/AgentRx`
benchmark (arXiv:2602.02475), pinned to repo `7a18c79708e7671be15124460f4f7296107c2a55`
and 4 pinned HF dataset files (sha256-verified on every load, fail-loud on mismatch).
It exposes:

- `loader.py` — the 73-case eval set (29 tau_retail + 44 magentic_one = 334 annotated
  failure instances); tau id prefix drift (`tau_retail_N` raw vs `N` annotated) is
  stripped for the join; the 14 unannotated raw magentic trajectories are excluded
  and counted in the eval-set notes.
- `taxonomy.py` — the 10 canonical categories (enum ints 0-10) plus
  `normalize_category()`, a **verbatim copy** of the mapping logic in
  `agentrx/reports/analyze_metrics.py:47-76` (pin `7a18c797`). All 11 observed
  annotation strings normalize (test-enumerated).
- `manifest.py` — one `CaseManifest` per trajectory (`source_benchmark="agentrx"`,
  pinned SHA, per-file data hashes, `strata={"domain": ...}`), `ground_truth` is a
  pointer-only record. Future heldout split rule: stratified 50/50 by domain,
  seed 20261009, every-2nd-by-case_id within domain; **label-free and
  deterministic**; no case in this commit consumes the heldout flag
  (all `heldout=False` by default).
- `scoring.py` — offline metrics matching the official schema (root-cause category
  accuracy; step-number accuracy exact and ±1..±5; denominators = Correct+Incorrect
  / total step-prediction cases per the contract §7). It scores
  `(prediction, case)` pairs from an **external predictor callable** — the adapter is
  baseline-agnostic. Every `Prediction` carries model/endpoint/judge-mode provenance
  (Science Judge Wave-0 F8: any G1 baseline record must pin which judge model and
  endpoint produced the numbers).

**What this adapter is NOT.** It runs **no LLM, no judge, no baseline, and no causal
intervention**. The trajectories are **stored observational traces**; per program
rules nothing in this package executes, resamples, or intervenes on a live system.
No paper or re-derived baseline numbers are claimed by this adapter.

**G1 status.** The official AgentRx judge baseline is **BLOCKED on LLM provider
availability** (contract §9, blocker B1: Copilot CLI monthly quota exhausted; Azure
endpoint requires Azure AD identity unavailable here; trapi is Microsoft-internal).
No baseline row exists yet and none may be fabricated. This read-only adapter does
not depend on B1: the eval set, taxonomy, manifest, and scorer math are fully
executable offline (verified by the test suite in `tests/benchmarks/`).
