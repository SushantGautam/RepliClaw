# AMEND_V3_1_PILOT_ENVELOPE — versioned amendment, APPROVED (D-V3-016), A2 REPEALED (2026-10-11)

**Status:** APPROVED by human at D-V3-016 (2026-10-10T21:36+02:00), with
**amendment item A2 REPEALED at approval** (false mechanism claim, see the
repeal note below A2). Executable set = A1 + A3 + A4 only. This document changes
no frozen value until the V3.1 freeze (v31_prereg_freeze.md) is stamped at
launch with pre-freeze SHA + file hashes.

**Model fairness clause (binding, D-V3-016 human-verbatim intent):** C-EQ and
D-E must use the same model, same tool set, same per-run envelope, same
budgets; the only intended difference is orchestration. A1 is a SHARED constant
(change applies identically to both arms). A2 was repealed because weakening
the volume canary would favor one arm (asymmetry forbidden by this clause). Under the frozen
"instrument" clause (v3_prereg_final_freeze.md §1.1 After-column), any parameter
change not in the After-column requires a versioned amendment motivated by a
pre-registered defect. This document is that vehicle for decision-point option
**(b)**.

**Motivating defect (pre-registered, evidenced, cross-model):**
The frozen 60,000-token per-run envelope is the **structural binding constraint**
on the D-E-TELEM arm: under the frozen instrument, D-E completed 0/12 runs across
two full pilots (round 1: 4× aborted_budget + 2× crashed-protocol; round 2:
6× aborted_budget, zero protocol violations). Observed burn at the abort cap:
55,271–64,089 (R1) and 60,182–64,089 (R2) tokens — every budget-aborted run dies
within ~8% of the cap, i.e., mid-investigation, not at a natural stopping point.
C-EQ-TELEM completes at 49,011–55,108 tokens. Without a D-E completing run the
frozen instrument cannot produce a paired Δ on any case, so S-sat / the floor
gate / any comparability claim are structurally unreachable for this arm.

## Evidence basis (frozen-surface-external, disclosed per no-confirmatory-reuse)

| Round | Model id (echoed) | D-E 12→6 runs | C-EQ 6 runs | stop |
|---|---|---|---|---|
| 1 (pilot #4) | `default` → Qwen3.8-27B | 0/6: 4× aborted_budget (P-01, P-03), 2× crashed protocol (P-02 both seeds) | 2/6 completed (both RCA-P-01 seeds, hit), 2× aborted (P-02), 2× crashed volume-band (P-03, ratios 1.2883/1.2845) | stop-2 TRIP (D-E 6/20 incl. crashes, cohort denominator) |
| 2 (re-pilot, D-V3-015) | `Borealis2-preview` (W3i: same Qwen-base-class variant) | 0/6: 6× aborted_budget, 0 protocol violations | 3/6 completed (3/3 hit, incl. RCA-P-03/20261011), 2× aborted, 1× crashed (volume-band, ratio 1.2891) | stop-2 TRIP (D-E 6/20) |

- Budget exhaustion is **model-invariant** (0/6 under 60K on both model ids);
  protocol violations are model-specific (Qwen only) — so the amendment targets
  the envelope, not the model.
- W3i disclosure: `Borealis2-preview` self-identifies as Qwen3.8-27B
  (docs/next_stage/data/w3i_caching_investigation_20261011.json); round 2 is
  treated as a same-base-variant instrument re-test. One C-EQ cell
  (R2 RCA-P-01/seed20261011) carries a bounded contamination caveat.
- Volume-band crash mode is **case-intrinsic C-EQ volume** (corrected at
  D-V3-016, invalidating the draft's original A2 mechanism claim): the pilot's
  band (telemetry_arms.py:1071-1075) compares C-EQ's OWN manager prompt volume
  to C-EQ's OWN investigator pool — D-E is NOT in the denominator (verified from
  audit data: inv pool is case-constant 15,366–17,700 chars; manager volume
  scales with the manager's exploration, which is a legitimate C-EQ arm
  property). On RCA-P-03 the ratio is 1.2843–1.2895 (both rounds, both models,
  both seeds where computed) — just over the 1.25 ceiling. The canary is a
  legitimate fairness/integrity guard (F5, calibrated against the frozen
  design); it is NOT weakened by this amendment (A2 repealed).

## Amendments (exact, minimal set — judge-endorsed Q6 shape)

| # | Frozen value (V3, FROZEN-CONSTANTS) | → Amended value (V3.1) | Justification |
|---|---|---|---|
| A1 | `MAX_TOKENS_PER_RUN = 60_000` (telemetry_arms.py:82; status.json envelope field) | **90_000** | Observed near-cap: every D-E budget abort lands at 55.3K–64.1K, i.e., the arm is truncated 15–25% before its evidence-gathering would end. 90K gives ≥40% headroom over the max observed abort (64,089) without an order-of-magnitude scope change. Wall cap 900 s unchanged (observed walls ≪ cap). |
| A2 | ~~Volume-band canary: skip when D-E partner non-completed~~ | **REPEALED at D-V3-016 — the [0.6, 1.25] band and crash-on-violation behavior are UNCHANGED.** | The draft's justification was factually wrong: the pilot band does not involve D-E's prompts at all (verified from audit data + code), so there is no cross-arm interaction to remove. The canary is a legitimate integrity guard; per the D-V3-016 model-fairness clause it must not be weakened for one arm's benefit. Honest pre-recorded consequence: at the 90K envelope, C-EQ runs that previously budget-aborted *before* the canary check (status `aborted_budget`, crash-free) may now reach the check and crash on it (status `crashed`) — e.g., expected on RCA-P-02 (ratio ~1.33-1.35) and RCA-P-03 (~1.29) when the manager loop completes. These count ITT in stop-2 exactly as the frozen rules say; no special handling, no reclassification. |
| A3 | `ROUND_TOKEN_CEILING = 2_880_000` (pilot_run.py:87) | **4_320_000** (= 48 runs × 90K, full-cohort arithmetic) | Mechanically follows from A1; per-round ceiling resets per round as before. Campaign worst-case (1 pilot + 2 re-pilots + heldout): 4,320,000 × 4 = 17,280,000 — all on the free SimulaChat endpoint; no paid resource. |
| A4 | status.json records `model` (requested id) only | + **`backend_model`** field: the gateway-echoed `response.model` of the first LLM call of the run (W3i provenance) | Makes future rounds immune to the W3i residual (requested id ≠ serving backend). Code change in `scripts/pilot_run.py` (one field) + `telemetry_arms.py` (surface first-call echo). |

## Explicitly UNCHANGED (goalpost guards)

- Δ_min = 0.15 (lowering-only path per freeze §1.1); temperature 0.2;
  per-round wall; per-agent tool caps; planner rounds ≤4; k=2 seeds;
  scorer/label isolation; opaque runtime ids; all stop rules 1–4 verbatim
  (denominators per I4.7 fix: sat over n=10, crash over 20 runs/arm, floor
  gate conjunct); the 42-case heldout pool and the 10-case pilot roster
  (frozen sha `955a4621…`); the difficulty-ladder MAX-2 re-pilot cap;
  the S-W2-1 floor gate (unchanged per judge Q6); ITT counting;
  case-level bootstrap / no confirmatory reuse (rounds 1–2 data may inform
  feasibility ONLY, never estimate/confirm any effect).

## Execution surface (approved, D-V3-016)

1. Code: A1 (`MAX_TOKENS_PER_RUN` 60,000→90,000, shared by both arms),
   A3 (`ROUND_TOKEN_CEILING` 2,880,000→4,320,000), A4 (`backend_model` status
   field from the first LLM call's gateway echo). NO canary change (A2
   repealed). Tests: constant-value tests, canary-behavior invariance test
   (out-of-band still crashes; in-band passes — guards the repeal), A4
   provenance test, full gate suite green.
2. Freeze: V3.1 freeze table = V3 table + this amendment (A2 repeal recorded)
   + pre-freeze repo SHA + file hashes of all changed constants.
   `docs/next_stage/design/v31_prereg_freeze.md` stamped at launch.
3. Pilot V3.1: fresh round, same 10-case roster (frozen sha), same model id
   `default` (pinned per D-V3-016 — no other model ids), k=2 seeds,
   fresh per-round ceiling 4,320,000, `backend_model` recorded per run.
   This is a **new pilot under the amended instrument** (authorized by
   D-V3-016 + this amendment), not a "re-pilot" against the consumed V3
   D-V3-015 authorization.
4. Same stop rules apply. A stop-2 trip on V3.1 goes back to the human with the
   full cause-decomposition; it does NOT silently trigger the V3 ladder.

## Approval record (to be filled at approval)

- Approver: ____  Date: ____
- Approval scope: this amendment AS WRITTEN (no silent partials); pilot V3.1
  launch; spend ceiling 4,320,000 free-endpoint tokens for the pilot round
  (+ at most 2 re-pilots under the V3.1 ladder if stop-1 trips, each
  4,320,000).
- Pre-freeze SHA at approval: ____
