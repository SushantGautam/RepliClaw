# G3 Pilot Outcome Statement — V3 frozen instrument, 2 rounds (2026-10-11)

**Status:** RECORD-AND-HOLD deliverable (decision-point option (c)). If option
(b)/(d) is chosen instead, this statement is retained as the G3 record for the
frozen V3 instrument (its scope of admissibility is exactly the V3 surface).

## Verdict

**FEASIBILITY-FAILED (cause-mixed, disclosed) for the V3 frozen instrument under
available model access.** The G3 pilot (10-case roster × 2 arms × 2 seeds,
60,000-token per-run envelope, 2,880,000-token per-round ceiling, SimulaChat
MODEL-SUBSTITUTION) completed **two full rounds** and tripped the pre-registered
**stop-2 (crash ≥ 6/20 in D-E-TELEM)** at cohort scale in both. Per the frozen
instrument, the pilot is **not admissible for heldout launch**, and no effect
estimate, power claim, or superiority statement is reported from pilot data
(frozen no-confirmatory-reuse clause).

## Round ledger (actual, from ledgers/STOP.json — no rounding)

| Round | Model id | D-E-TELEM (of 6; cohort n=20) | C-EQ-TELEM (of 6) | Tokens used / ceiling | Stop |
|---|---|---|---|---|---|
| 1 (pilot #4) | `default` (echoed Qwen3.8-27B) | 0/6: 4× aborted_budget, 2× crashed (AgentProtocolError, RCA-P-02 both seeds) | 2/6 completed (RCA-P-01 both seeds, **hit=true**); 2× aborted_budget (RCA-P-02); 2× crashed (volume-band 1.2883/1.2845, RCA-P-03) | 663,214 / 2,880,000 | stop-2 trip (16:49:36Z) |
| 2 (re-pilot, D-V3-015) | `Borealis2-preview` (W3i: same Qwen-base-class variant) | 0/6: 6× aborted_budget (60,182–64,089), **0 protocol violations** | 3/6 completed (RCA-P-01 both seeds + RCA-P-03/20261011, **all hit=true**); 2× aborted_budget; 1× crashed (volume-band 1.2891, RCA-P-03) | 713,441 / 2,880,000 | stop-2 trip (18:48:02Z) |

Cross-round: 1,376,655 free-endpoint tokens total; both rounds valid (no harness
defect in the stopping arithmetic; the I4.7 driver fix predates round 1's
trip and round 2 re-verified it).

## Cause decomposition (what the two rounds DID establish)

1. **The 60,000-token per-run envelope is the structural binding constraint on
   D-E-TELEM** — model-invariant budget exhaustion (0/6 on two model ids; every
   abort lands within ~8% of the cap, mid-investigation). C-EQ-TELEM completes
   at 49,011–55,108 under the same envelope.
2. **D-E protocol violations are model-specific** (Qwen echo only; round 2:
   zero) — a disclosure-level model-behavior observation, not an arm defect.
3. **The C-EQ prompt-volume canary interacts structurally with D-E non-
   completion** (same case RCA-P-03, ratios ≈1.284–1.289 across rounds/seeds):
   a budget-aborted D-E partner inflates the canary denominator and
   deterministically crashes the C-EQ run. This is a frozen-instrument
   interaction, pre-registered in the instrument's known-interactions table.
4. **No D-E completing run exists in the frozen instrument**, so no paired
   per-case Δ can be computed on any case; S-sat / floor gate / comparability
   are structurally unreachable for the D-E arm as frozen.

## What was NOT established (anti-claim list, frozen)

- No effect estimate, no σ̂_D-based power claim (T0+5 emitted the
  deterministic INSUFFICIENT-ESTIMATE artifact in both rounds: only 1
  both-saturated case < 8 minimum), no superiority or non-inferiority claim
  for decentralized agents, evidence escrow, or adaptive selection —
  **including** any C-EQ-over-D-E statement (n=3 completed C-EQ cells with
  3/3 hits is an ITT n=6 non-result).
- No "stronger model would make D-E feasible" claim: round 2's model id
  (`Borealis2-preview`) is, per the W3i identity probe, a **same Qwen-base-class
  variant** (it self-identifies as Qwen3.8-27B). The genuinely stronger-model
  hypothesis (GLM-5.2) was access-blocked (HTTP 401, "api key expired").
- One C-EQ cell (round 2, RCA-P-01/seed20261011) carries a bounded
  contamination caveat (W3i residual E6) and is flagged in the record.

## Negative/feasibility findings preserved (per mission rule)

The prior 120-run campaign's negative finding (no demonstrated advantage of
decentralization or escrow on one seeded case) is **preserved, not superseded**:
the G3 pilot could not even reach an effect test under the frozen instrument,
so the honest G3 result is a **cause-decomposed feasibility failure with a
structural mechanism** (envelope + canary interaction), not an inconclusive
null.

## Admissible next actions (human-gated)

- **(b)** Approve `AMEND_V3_1_PILOT_ENVELOPE` (design/amendment_v31_pilot_envelope_DRAFT.md:
  90K envelope, canary skip on non-completed partner, 4.32M ceiling, backend
  provenance field) → new freeze → pilot V3.1 on the free endpoint.
- **(c)** Accept this statement as the G3 deliverable and hold the heldout.
- **(d)** New-spec next pilot — only meaningful with a genuinely stronger model
  (requires refreshed GLM-5.2 access) or materially different instrument scope.

## Evidence pointers

- Rounds: `.artifacts/rcaeval/pilot/run/round{1,2}/` (gitignored; STOP.json,
  ledger.jsonl, per-run status/audit/score, `pilot_report_round{1,2}.json/.md`).
- Investigation: `docs/next_stage/data/w3i_caching_investigation_20261011.json`;
  `docs/next_stage/data/model_probe_20261010T184411Z.json`;
  `docs/next_stage/data/model_probe_borealis27b_20261010T191703Z.json`.
- State: EXECUTION_STATE.md I4.7/I4.8; DECISIONS.md D-V3-014/D-V3-015;
  T0+5 artifacts `docs/next_stage/data/t05_pilot_sigma_mc_round{1,2}.json`.
