# AMEND_V3_3 (DRAFT — NOT authorized, NOT frozen) — make the contrast actually executable

> **STATUS: DRAFT.** This is a *proposal* for the next instrument, written in
> code-level detail so it is turnkey for human approval. It is **NOT** an
> authorization to spend. It requires, in order: (1) explicit human approval
> of the change set + scope + spend; (2) two FRESH independent reviews (code +
> science) on the diff; (3) a new freeze stamp (`v33_prereg_freeze.md`) with
> fresh code hashes. Until then, no run is launched and no code below is applied
> to the live path. The V3.2 freeze and round-4 evidence are unaffected.

## Why V3.3 is needed (from the round-4 outcome judges)

Round 4 (V3.2) stopped at the D-E crash-rate stop and, per both judges, the
original scientific contrast — "does decentralized + escrow + adaptive-selection
beat a central manager with the SAME tools/budget/information?" — was **never
cleanly instantiated**:

- **D-E's decentralized machinery (phase-2 commit-reveal, phase-3 committee)
  never executed** in any of the 12 D-E runs. One investigator looped to the
  token wall (48.1% of 378 D-E tool calls were identical `(tool,args)` repeats)
  before its turn to hand off. So round 4 measured *phase-1 agent
  non-convergence under the substituted model*, not the cost of decentralization.
- **C-EQ's 5 non-completions were crashes of its own instrument**: the
  prompt-volume crash-gate (`assert_volume_band`) exists **only** on the control
  arm, was set 0.05 above the observed deterministic maximum, and the live model's
  run-to-run prompt-length variance (proven by P-01: 1.235 → 1.601 on the same
  case/seed) exceeds that margin. Left in place it would bias any D-E-vs-C-EQ
  contrast **in favor of** the decentralized arm — the exact confound the parity
  check exists to prevent.

V3.3's goal is the **minimal** set of changes that (i) lets the decentralized
mechanism actually reach phases 2–3, and (ii) removes the asymmetric,
over-sensitive control-arm crash instrument — while **preserving** the scientific
question, the model, the cases, the seeds, the scorer, and the no-confirmatory-
reuse clause.

## Amended parameters (everything else FROZEN and UNCHANGED)

| Parameter | V3.2 (current) | V3.3 (proposed) | Rationale |
|---|---|---|---|
| Per-run token envelope | 150,000 | **150,000 (unchanged)** | No further headroom requested; the failure was non-convergence, not a single-point wall. |
| Total per-sandbox tool budget | 48 | **48 (unchanged)** | B2's total already in force. |
| **Per-tool sub-caps** (`service_logs`, `service_traces` = 4) | 4 each | **REMOVE** (total-budget-only) | 4 of 12 D-E deaths were per-tool 4-call exhaustion at 47–55K tokens; the frozen B2 rationale already noted per-tool usage "never bound" at 24. At 48 they bind spuriously. |
| **Anti-loop guard** | none | **ADD: symmetric, both arms** — a repeated identical `(tool, args)` call in the same sandbox returns the **cached sanitized payload without consuming budget** (tools are idempotent/re-fetchable, see compaction note `telemetry_arms.py:108-117`). | Neutralizes the non-convergence confound **symmetrically** — it treats agent behavior, not arm structure, so it cannot manufacture the effect under test. (Hard-refuse is the alternative; cache is cheaper and loses no information.) |
| **C-EQ prompt-volume canary** | crash-on-violation, band [0.6, 1.40] | **LOGGED canary (no crash)**: `prompt_volume_ratio` is still measured and reported in status/escrow; a band violation sets a `volume_band_violation=true` flag + disclosure, never aborts the run. | Removes the asymmetric, over-sensitive instrument while **preserving the fairness measurement** (the ratio is still computed and disclosed). D-E still reports ratio=None (it has no manager). |
| Saturation rule (seed level) | (defect: recorded-seed denominator) | **FIXED in V3.2 code already (57d1e1f)**: all k=2 seeds must be recorded AND successful. Carried forward. | Round-4 false stop-1 co-trip. |

**Explicitly UNCHANGED (frozen from V3.2):** the 10-case roster (sha `955a4621…`),
k=2 seeds (20261011/20261012), the two arms and their agent rosters/counts, the
150,000 envelope, the 48 total tool budget, the 7,200,000 round ceiling, the
scorer + hit/miss definition + scorer_sha, temperature 0.2, 900s wall,
stop rules 1/2/4 (with the seed-saturation fix), full-cohort denominators, ITT,
S-W2-1 floor, **model `default` (SimulaChat, echoes Qwen3.8-27B — MODEL-
SUBSTITUTION, not the official baseline)**, the no-confirmatory-reuse clause
(rounds 1–4 remain feasibility-only; a V3.3 round is feasibility-only too), and
the heldout requirement (still needs its own G4 human approval).

## Exact code sites (for the reviewers + the integrator)

1. **Per-tool sub-caps** — `src/repliclaw/experiments/v3/telemetry.py:279-286`
   `_check_budget`: drop the two per-tool branches (`service_logs`,
   `service_traces`); keep the `MAX_TOOL_CALLS` total check. Constants
   `MAX_LOGS_CALLS`/`MAX_TRACES_CALLS` (`:85-86`) removed or left unused.
2. **Anti-loop cache** — `src/repliclaw/experiments/v3/telemetry.py`: add a
   per-sandbox `self._call_cache: dict[(tool, args_json) -> sanitized_payload]`
   consulted at the top of each OBS tool method; on a hit, return the cached
   payload and record the call in `call_log` with `"repeated_cached": true`
   **without** incrementing `_total_calls`/`_invoked`. Applied in
   `TelemetrySandbox` (shared by both arms → symmetric by construction).
3. **C-EQ volume canary** — `src/repliclaw/experiments/v3/telemetry_arms.py:1108-1113`:
   keep `ratio = prompt_volume_ratio(...)`, **replace**
   `assert_volume_band(ratio)` with a logged flag
   (`volume_band_violation = not (FLOOR <= ratio <= CEIL)`), pass it through to
   `_result`/`status.json`. `assert_volume_band` stays for the offline canaries
   (which intentionally crash).
4. **Tests:** update `test_v3_telemetry.py` (sub-cap removal, anti-loop cache:
   repeated call returns identical payload, does not consume budget, is logged),
   `test_v3_telemetry_arms.py` (C-EQ run does NOT crash on band violation;
   flag recorded; offline canary still crashes), and `test_pilot_driver.py`
   (constants). New regression: a D-E investigator that re-issues identical
   `service_metrics` calls now makes forward progress to submit instead of
   burning the envelope.
5. **Re-freeze:** new `v33_prereg_freeze.md` with fresh code hashes + the full
   disclosure list (V3.2's 11 items, plus a new item: "V3.3 removed the
   control-arm crash-gate and added a symmetric anti-loop cache; round 5 is
   feasibility-only under these repaired instruments").

## Non-authorizations (this DRAFT grants none)

- No round 5 launch. No spend. No model change (`default` only, per D-V3-017).
- No effect estimate from any round (no-confirmatory-reuse preserved).
- No P08-surface changes (ENVELOPE_TOKENS=60,000 stays).
- No public release (`main` stays human-gated).

## Open decision for the human (with the science judge's recommendation)

The science judge recommends **this** change set as the minimal path to
instantiating the contrast. Two variants are on the table for the per-tool caps:
**(i) total-budget-only** (recommended, cleaner) or **(ii) raise sub-caps to 8**
(a floor). The integrator can apply either once the human picks.
