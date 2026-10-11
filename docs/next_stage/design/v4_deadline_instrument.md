# V4 Deadline-Bound Concurrent Instrument — Prospective Protocol

**Status:** PROSPECTIVE — not yet executed. Human approval required before any live run.
**Date:** 2026-10-12
**Supersedes:** No prior protocol (new instrument)
**Related audit:** `AUDIT_SCIENCE_MISMATCH_20261012.md`

## §1 Purpose

Test whether decentralized scientific agents operating CONCURRENTLY under bounded local reasoning and hard deadlines provide additional diagnostic value over a strong adaptive centralized baseline, when both arms have identical access-matched observational tool access, identical token envelopes, and identical case sets.

The V3 campaign established that D-E-TELEM always diagnoses correctly WHEN it completes, but completion is envelope-bound: 0% at 150K, 43–50% at 300K, 64–88% at 600K tokens. The sequential phase-1 design means the shared envelope is consumed by three investigators in series before the committee can convene. The V4 instrument addresses this directly:

1. **Concurrent phase-1**: all three investigators run simultaneously (threads), each with its own sandbox and session.
2. **Hard per-investigator deadline**: 120 s wall clock. If an investigator has not committed by then, the arm commits a deterministic fallback ranking (top-5 anomaly scores from that investigator's sandbox + inventory padding) with confidence 0.3.
3. **Bounded local reasoning**: 12 tool calls per investigator in phase 1 (vs unlimited in V3).
4. **Preserved escrow**: commit-reveal mechanism unchanged from V3.7.
5. **Matching central baseline**: C-EQ-DET gets the same envelope, same tool menu, same case set, and concurrent post-loop consultations for wall-time parity.

This is an ACCESS-MATCHED OBSERVATIONAL comparison. No live system is perturbed. The term "intervention-matched" does NOT apply to these arms (see audit §1).

## §2 Arms

| Arm | Label | Design |
|-----|-------|--------|
| D-E-TELEM-DET | Decentralized + Escrow, deadline-bound | 3 concurrent investigators (threads), 12-tool cap each, 120 s deadline, fallback on timeout, escrow commit-reveal, optional phase-2 consult (cap 8), deterministic committee scoring, optional committee sandbox round (cap 4) |
| C-EQ-TELEM-DET | Centralized Equal-quality, deadline-bound | 1 adaptive manager, sealed pre-outcome forecast, ≤4 planner rounds (1–3 tools/round), 3 concurrent post-loop consultations (3 tools each), final commit through manager sandbox |

### Ablation hooks (D-E only)
- `consultation=False`: disable phase-2 reveal (escrow-only ablation)
- `committee=False`: submit deterministic committee ranking without fresh committee sandbox round

C-EQ-DET is never ablated (it is the reference arm).

## §3 Frozen constants

```python
DE_PHASE1_TOOL_CAP = 12          # per-investigator phase-1 tool calls
DE_INVESTIGATOR_DEADLINE_S = 120.0  # hard wall-clock deadline per investigator
DE_FALLBACK_CONFIDENCE = 0.3     # confidence recorded on deadline/crash fallback
DE_PHASE2_TOOL_CAP_V4 = 8        # phase-2 consult cap (same as V3.7 final)
DE_COMMITTEE_TOOL_CAP_V4 = 4     # committee sandbox round cap
MAX_TOKENS_PER_RUN = 150_000     # shared token envelope (identical for both arms)
WALL_CAP_S = 900.0               # shared wall cap
PLANNER_ROUNDS_MAX = 4           # C-EQ planner rounds
CEQ_INVESTIGATOR_TOOL_CAP = 3    # C-EQ per-consultation tool cap
RANKING_LENGTH = 5               # ranked-5 diagnosis
INVESTIGATOR_IDS = ("inv-a", "inv-b", "inv-c")
```

Model: Sigma2 Qwen3.8-27B (SimulaChat thinking/non-thinking). No fallback model. Temperature 0.2.

## §4 Case manifest

### Selection rule (frozen prospectively)
- Source: `data/cases.parquet` (735 rows), suites RE1/RE2/RE3, ob/ss/tt variants.
- Filter: rep-1 only, ob suite, n_metrics > 0.
- Exclusion: any case ID appearing in ANY historical round directory under `.artifacts/rcaeval/pilot/` (verified against R1–R9, FF-05 r0c, and all stg2 worktree artifact roots).
- P-08 is EXCLUDED (exposed; see audit §2).
- Preference: RE2/RE3 cases (have logs+traces, matching pilot-case tool surface). RE1 cases (no logs/traces) are included only if RE2/RE3 candidates are insufficient.

### Fresh holdout candidates (16, sha256: 0235241c8adc1034b67b3c398574063ba882a9127926b14583e012405a0908b4)

| # | Case ID | Suite | Service | Fault | Logs | Traces |
|---|---------|-------|---------|-------|------|--------|
| 1 | re1ob_checkoutservice_cpu_1 | RE1 | checkoutservice | cpu | NO | NO |
| 2 | re1ob_checkoutservice_delay_1 | RE1 | checkoutservice | delay | NO | NO |
| 3 | re1ob_adservice_disk_1 | RE1 | adservice | disk | NO | NO |
| 4 | re1ob_adservice_loss_1 | RE1 | adservice | loss | NO | NO |
| 5 | re1ob_adservice_mem_1 | RE1 | adservice | mem | NO | NO |
| 6 | re2ob_checkoutservice_cpu_1 | RE2 | checkoutservice | cpu | YES | YES |
| 7 | re2ob_recommendationservice_delay_1 | RE2 | recommendationservice | delay | YES | YES |
| 8 | re2ob_checkoutservice_disk_1 | RE2 | checkoutservice | disk | YES | YES |
| 9 | re2ob_checkoutservice_loss_1 | RE2 | checkoutservice | loss | YES | YES |
| 10 | re2ob_checkoutservice_mem_1 | RE2 | checkoutservice | mem | YES | YES |
| 11 | re2ob_checkoutservice_socket_1 | RE2 | checkoutservice | socket | YES | YES |
| 12 | re3ob_currencyservice_f1_1 | RE3 | currencyservice | f1 | YES | YES |
| 13 | re3ob_emailservice_f2_1 | RE3 | emailservice | f2 | YES | YES |
| 14 | re3ob_emailservice_f3_1 | RE3 | emailservice | f3 | YES | YES |
| 15 | re3ob_adservice_f4_1 | RE3 | adservice | f4 | YES | YES |
| 16 | re3ob_adservice_f5_1 | RE3 | adservice | f5 | YES | YES |

### Primary analysis set
Use the 11 RE2/RE3 cases (#6–#16) for the primary analysis. Include the 5 RE1 cases (#1–#5) in a secondary sensitivity analysis only (their tool surface differs: no logs/traces available).

### Seeds
Two seeds per case: 20261013, 20261014. Total runs: 11 × 2 × 2 arms = 44 primary runs (+ 20 secondary if RE1 included).

## §5 Metrics

| Metric | Definition | Primary/Secondary |
|--------|-----------|-------------------|
| top-1 accuracy | Submitted rank-1 service == ground-truth root cause | PRIMARY |
| top-5 accuracy | Ground-truth service in submitted top-5 | PRIMARY |
| causal identification | Rank-1 is the true causal service AND confidence ≥ 0.5 | Secondary |
| intervention/tool cost | Total tool calls across all agents in the arm | PRIMARY |
| total tokens | Sum of prompt+completion tokens across all sessions | PRIMARY |
| wall time | End-to-end seconds from arm start to submission | PRIMARY |
| completion rate | Fraction of runs with status="completed" (not aborted_budget/crashed) | PRIMARY |
| time-to-first-diagnosis | Seconds from arm start to first escrow commit (phase-1) | Secondary |
| repeated-action rate | Count of exact (tool,args) repeats beyond first occurrence, per investigator | Secondary |
| fallback usage | Fraction of investigators whose phase-1 commit was deadline_fallback | Secondary |
| phase-1 wall span | Max(investigator wall_s) - min(investigator wall_s) — measures concurrency benefit | Secondary |

## §6 Mechanism ablations

Run the following ablation conditions on a SUBSET (first 4 RE2/RE3 cases × 2 seeds × D-E arm only = 16 runs):

| Ablation | consultation | committee | Tests |
|----------|-------------|-----------|-------|
| Full | True | True | Baseline D-E-DET |
| No-consult | False | True | Contribution of phase-2 reveal |
| No-committee | True | False | Contribution of committee sandbox round |

These distinguish the contribution of decentralization (concurrency + deadline), escrow (commit-reveal), and intervention selection (phase-2 tool use after seeing others' rankings).

## §7 Stop rules

1. If either arm achieves 0% top-1 on the first 6 primary cases (3 cases × 2 seeds), pause and review.
2. If D-E-DET completion rate < 50% on the first 6 cases, investigate before continuing.
3. If total spend exceeds 2× the projected budget (based on V3.7 round-9 actuals), stop and report.
4. Any crash in > 20% of runs triggers immediate halt.

## §8 Fairness guarantees (parity by construction)

- Identical `MAX_TOKENS_PER_RUN` token envelope, enforced from one shared counter.
- Identical `WALL_CAP_S` wall cap.
- Identical per-sandbox tool budget and per-tool caps (inherited from TelemetrySandbox).
- Identical opaque case ID, model label, temperature, action protocol.
- Identical tool menu (OBS read-only telemetry queries).
- The deadline/fallback machinery exists ONLY in D-E-DET (it is the treatment). C-EQ-DET faces the identical binding constraint (shared token/wall envelope) without a deadline because a single manager already has the full envelope.

## §9 Execution plan

1. Offline tests (FakeLLMClient scripted): `tests/experiments/test_det_deadline.py` — 7 tests, all passing.
2. Tiny local smoke (offline, FakeLLMClient): run both arms once, verify status.json + escrow artifacts.
3. Live smoke (Sigma2 Qwen3.8, 1 case × 1 seed × 2 arms): requires human approval + SIMULACHAT_* env vars.
4. Full primary run (11 cases × 2 seeds × 2 arms = 44 runs): requires human approval.
5. Ablation subset (4 cases × 2 seeds × 3 D-E conditions = 24 runs): requires human approval.

No step 3+ is launched without explicit human sign-off on this protocol and the case manifest.

## §10 Model

Sigma2 Qwen3.8-27B via SimulaChat (thinking and non-thinking variants). No fallback model. Model substitution label: `MODEL_SUBSTITUTION_LABEL` (as defined in telemetry_arms.py).
