# V3.1 PILOT PREREGISTRATION FREEZE — AMEND_V3_1_PILOT_ENVELOPE (2026-10-11)

**Frozen by:** integrator (autonomous, under D-V3-016 human approval)
**Applies to:** pilot V3.1 only. The V3 freeze (`v3_prereg_final_freeze.md`) is
retained as the record for rounds 1–2; this document is the operative
instrument for round 3.
**Approval:** D-V3-016 (DECISIONS.md, 2026-10-10T21:36+02:00, human): options
b + c approved, d not; model pinned to SimulaChat `default`; unlimited spend
within the approved ceilings; binding model-fairness clause (same model, tool
set, envelope, budgets for both arms — orchestration is the only intended
difference).

## 1. Inherited unchanged (from the V3 freeze, verbatim)

| Surface | Value | Source |
|---|---|---|
| Case roster | 10 pilot cases, id-list sha256 `955a462175200909577c8c71db64e3fc8f879c83f1a9028e307926c471503a02` | v3_prereg_final_freeze S1 §2 |
| Seeds | k=2: (20261011, 20261012) | frozen spec §4 |
| Arms / order | D-E-TELEM then C-EQ-TELEM, both arms every case/seed (20 runs) | frozen spec §2/§4 |
| Temperature | 0.2 | frozen spec §4 |
| Wall cap | 900 s per arm-run | frozen spec §4 |
| Tool budget | 24 OBS tool calls per arm-run | frozen spec §4 |
| Stop rule 1 (S-sat) | per-arm sat ≥ 0.25 at each completed case → pause + difficulty-ladder re-pilot | frozen spec §5.1 |
| Stop rule 2 (crash) | per-arm crash rate > 0.25 of FULL 20-run cohort (≥6 non-completed runs; `aborted_budget` counts; ITT) | frozen spec §5 rule 2 (I4.7 denominator) |
| Stop rule 4 (floor) | either arm < 2/20 run-level successes OR ≥ 9/10 cases with all-seeds success 0 | S-W2-1 |
| Scorer | service-level top-5 hit, scorer-side only, no label in prompts | frozen spec §6 |
| ITT / no confirmatory reuse | all non-completed runs count; pilot evidence cannot be reused as heldout evidence | frozen spec §5/§6 |
| Δ_min, heldout rule | 0.15 MDE reference; heldout (42 cases) still requires explicit human approval at G4 | D-V3-013 |
| Label | MODEL-SUBSTITUTION (SimulaChat default, Qwen3.8-27B) — NOT the official released baseline | J-SCI rule |

## 2. Amended surfaces (AMEND_V3_1 — the only changes vs V3)

| Item | V3 (rounds 1–2) | V3.1 (round 3) | Evidence/rationale |
|---|---|---|---|
| A1 — per-run token envelope | 60,000 | **90,000** (SHARED constant `MAX_TOKENS_PER_RUN`, both arms identical; `_Envelope` rejects any explicit value above the shared constant) | Every round-2 D-E budget abort landed at 55,271–64,089 (15–25% truncated pre-cap); envelope is the model-invariant structural constraint on D-E (cross-model finding, I4.8) |
| A2 — prompt-volume canary | [0.6, 1.25], crash on violation | **UNCHANGED** (draft A2 repealed at approval — its D-E-partner mechanism claim was verified false; the band is a C-EQ-internal fairness guard) | Audit-data verification: band = C-EQ manager prompts vs C-EQ's own investigator pool; P-03 ratios 1.2843–1.2895 both rounds/models (case-intrinsic) |
| A3 — per-round token ceiling | 2,880,000 | **4,320,000** (= 48 × 90,000; mechanical follow-on of A1; stop-3 pre-emptive) | amendment A3 |
| A4 — backend provenance | not recorded | **`backend_model` in each run's status.json** = gateway-echoed `response.model`, per agent (first-LLM-call capture); pure provenance, no behavioral effect | W3i: model identity must be verifiable per run (Borealis2-preview turned out to be a Qwen-base-class variant) |
| Model | round 1 `default` (Qwen3.8-27B); round 2 `Borealis2-preview` | **`default` pinned** (no other model ids in round 3 or its re-pilots) | D-V3-016 human pin |

### Pre-recorded honest consequence of A1 × A2-repeal (disclosed, NOT a forecast)
Corrected per science-judge N2 (review of e602041, 2026-10-11): (i)
`aborted_budget` IS a stop-2 crash (counted as non-completed) — the 60K
transition is between two counted statuses, not "crash-free → crash"; (ii)
RCA-P-03 already crashed ON the canary at 60K in round 1 (~49K < cap), so 90K
does not cause P-03's crash; (iii) the genuine 90K-induced transition is
RCA-P-02 (manager loop may now finish, reach the canary, and crash there; its
~1.326–1.350 ratio is a PROJECTION from round-1/2 partial data, not a
completed-run measurement); (iv) the 90K change is neutral-to-favorable for
C-EQ (never increases its non-completed count). All such runs count in stop-2
as non-completed, ITT, no special handling.

## 3. Freeze evidence

| Artifact | Value |
|---|---|
| Pre-freeze repo state | `dev` @ `e602041f6927d47ca1f74601246808a1db239d61` (I4.9 commit) |
| `src/repliclaw/experiments/v3/telemetry_arms.py` sha256 (prefix) | `41a13e8edbf245bd` |
| `scripts/pilot_run.py` sha256 (prefix) | `cf7f46b6a05d062a` |
| `scripts/pilot_report.py` sha256 (prefix) | `864dffb263d2588c` |
| `src/repliclaw/experiments/v3/telemetry.py` sha256 (prefix) | `be357ff1ddf50800` |
| Gate evidence (at I4.9) | pytest `462 passed, 8 skipped, 3 xfailed`; mypy telemetry_arms.py clean; ruff src+scripts+tests clean |
| Post-judge-fix files (I4.9b; docstrings + N3 report fields only — no behavioral change to arms) | `telemetry_arms.py` `04b6070d1b72b87f` · `pilot_report.py` `dbc18d436e8cdeaf`; suite `463 passed, 8 skipped, 3 xfailed`; ruff + mypy clean |
| Offline canaries (V3.1 instrument) | 5/5 PASS — `.artifacts/v31_canary_offline/canary_report.json` (both_arms_complete, payload_parity, scorer_path, label_gate, reset; no_llm_network) |
| New/updated V3.1 tests | `test_v31_amended_constants`, `test_stop3_ceiling_preemptive` (4.32M/90K arithmetic), `test_v31_amended_envelope_constants`, `test_v31_envelope_parity_guard`, `test_v31_backend_model_provenance_recorded`, `test_v31_canary_invariance_after_envelope_amendment` |

## 4. Launch protocol (round 3)

1. Live canary: 1 real run per arm on the first planned case (2 runs, `default`
   model; `--max-cases 1` into the round-3 out root) to verify gateway
   reachability, echo, token accounting, A4 field, and protocol compliance —
   the canary's round dir is WIPED before the full launch, so it never counts
   against the cohort or the round budget.
2. Full run (fresh out root, rounds 1–2 artifacts untouched):
   `pilot_run.py run --round 3 --out .artifacts/rcaeval/pilot/run_v31 --autonomous --label "MODEL-SUBSTITUTION (SimulaChat default, Qwen3.8-27B) — NOT the official released baseline"`, env `SIMULACHAT_MODEL` unset (driver defaults to `default`). Fresh 4,320,000 round budget.
3. Monitors: per-case stop-rule values (`pilot_run.py status --round 3`), token ledger, crash cause decomposition on any trip.
4. On completion or trip: T0+4-format report (`pilot_report.py`), independent
   code-judge + science-judge reviews, state update, checkpoint commit.
5. If stop-2 trips on V3.1: human decision with full cause decomposition (no
   autonomous further re-pilot; the D-V3-015 re-pilot is consumed and this
   pilot is the D-V3-016 instrument).

## 5. Judge notes carried forward (science-judge, e602041 review — all non-blocking)
- **N1 (calibration disclosure):** the frozen [0.6, 1.25] band was calibrated
  against a cross-arm F5 intent (ceq.py:329) but the pilot computes an
  intra-arm ratio (manager / own investigator pool); P-03's ceiling excess is
  partly an instrument-construction artifact, not purely case-intrinsic.
  Flag for any LATER recalibration amendment (would itself require a new
  versioned amendment + human approval; NOT done here).
- **N2:** see the corrected pre-record above.
- **N3 (heldout evidence rule):** per-run `backend_model` echoes become
  MANDATORY evidence for any heldout decision; add a within-run
  cross-agent echo-consistency check to the report; carry the W3i E6
  residual (silent same-family fallback) as a bounded, unresolved note.

## 6. What this freeze does NOT authorize
- The 42-case heldout (requires its own explicit human approval at G4).
- Any model id other than `default`.
- Any change to the V3 freeze, P08 results, or rounds 1–2 records.
- Any confirmatory reuse of pilot V3.1 evidence.
