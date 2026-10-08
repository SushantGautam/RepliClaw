# AMEND_V3_1_PILOT_ENVELOPE — versioned amendment, DRAFT PENDING HUMAN APPROVAL (2026-10-11)

**Status:** DRAFT. This document changes NO frozen value until a human explicitly
approves it, after which it is versioned `AMEND_V3_1_PILOT_ENVELOPE_20261011`,
frozen (sha recorded in the V3.1 freeze table), and executed. Under the frozen
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
- Volume-band crash mode is **structural, not stochastic**: it fires on the same
  case (RCA-P-03) in both rounds with nearly identical ratios (R1: 1.2883/1.2845
  both seeds; R2: 1.2891 on the one seed whose D-E partner was non-completed)
  because D-E's burned budget inflates the C-EQ/D-E prompt-volume denominator
  while C-EQ completes short. See amendment item A2.

## Amendments (exact, minimal set — judge-endorsed Q6 shape)

| # | Frozen value (V3, FROZEN-CONSTANTS) | → Amended value (V3.1) | Justification |
|---|---|---|---|
| A1 | `MAX_TOKENS_PER_RUN = 60_000` (telemetry_arms.py:82; status.json envelope field) | **90_000** | Observed near-cap: every D-E budget abort lands at 55.3K–64.1K, i.e., the arm is truncated 15–25% before its evidence-gathering would end. 90K gives ≥40% headroom over the max observed abort (64,089) without an order-of-magnitude scope change. Wall cap 900 s unchanged (observed walls ≪ cap). |
| A2 | Volume-band canary crash: `assert_volume_band` outside [0.6, 1.25] raises → run status `crashed`, counted in stop-2 denominator | **Frozen baseline definition:** if the D-E arm of the case/seed pair does not `completed` (aborted or crashed), the C-EQ prompt-volume ratio is **not computed** (ratio = null, `canary_status: "skipped_de_noncompleted"`) and the C-EQ run is NOT crashed. If the ratio is computed and out-of-band, the crash behavior is unchanged. | Removes the cross-arm interaction where one arm's *budget outcome* (an honest, pre-registered feasibility signal) deterministically crashes the other arm. The canary still guards actual prompt-volume parity whenever both arms produced a completed prompt record. Ratios stay recorded in the report for disclosure. |
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

## Execution surface (post-approval)

1. Code: A1 (constant), A2 (canary skip logic in `pilot_run.py` execute path),
   A3 (constant), A4 (status field). Tests: unit tests for A2 (completed/non-
   completed D-E → ratio null vs computed), constant-value tests, status-field
   test. Full gate suite green.
2. Freeze: V3.1 freeze table = V3 table + this amendment + pre-freeze repo SHA
   + file hashes of all changed constants. New `docs/next_stage/design/
   v31_prereg_freeze.md` stamped only at launch.
3. Pilot V3.1: fresh round, same 10-case roster, same model id `default`
   (pinned; echoed `backend_model` recorded per run), fresh per-round ceiling
   4,320,000. This is a **new pilot under the amended instrument**, not a
   "re-pilot" under the V3 cap (which is consumed); it is authorized only by
   this amendment + explicit human approval of spend ceiling (free endpoint).
4. Same stop rules apply. A stop-2 trip on V3.1 goes back to the human with the
   full cause-decomposition; it does NOT silently trigger the V3 ladder.

## Approval record (to be filled at approval)

- Approver: ____  Date: ____
- Approval scope: this amendment AS WRITTEN (no silent partials); pilot V3.1
  launch; spend ceiling 4,320,000 free-endpoint tokens for the pilot round
  (+ at most 2 re-pilots under the V3.1 ladder if stop-1 trips, each
  4,320,000).
- Pre-freeze SHA at approval: ____
