# Scientific-Mismatch Audit — 2026-10-12

## Scope
This audit identifies terminology errors and heldout-contamination issues in the V3 campaign documentation that affect the validity of the "intervention-matched" claim for TELEM arms. It does NOT rewrite historical results; it classifies each finding as HISTORICAL-DO-NOT-REWRITE or CORRECTABLE-LABEL (forward-looking docs only).

## §1 Terminology: "intervention-matched" vs "access-matched / observational"

### Finding
The TELEM arms (D-E-TELEM, C-EQ-TELEM) operate exclusively on read-only telemetry queries against a frozen incident snapshot. No live system is ever executed against, no action perturbs the environment, and no counterfactual intervention is applied. The correct label is **access-matched observational** (or simply **access-matched**), not intervention-matched.

The term "intervention-matched" is legitimately used for the AIOpsLab mitigation track (which has a real `exec_shell` channel), but that track was BLOCKED and never deployed. Applying it to the TELEM arms is a terminology error.

### Classification table

| File | Line(s) | Context | Classification |
|------|---------|---------|----------------|
| `src/repliclaw/experiments/v3/ceq.py` | 1 | Module docstring: "C-EQ: intervention-matched adaptive centralized manager (V3 design)" | CORRECTABLE-LABEL — forward-looking code; change to "access-matched" |
| `src/repliclaw/experiments/v3/det_deadline.py` | 8,10 | V4 module docstring correctly notes the error and uses "access-matched" | CORRECT — already fixed |
| `docs/next_stage/science/fast_finish_result.md` | 1, 142 | Title: "Intervention-Matched Comparison"; §conclusion: "intervention-matched comparison has been executed" | HISTORICAL-DO-NOT-REWRITE — published findings memo; add a forward-looking errata note at top instead |
| `docs/next_stage/science/statistical_protocol_v3.md` | 27, 287 | §1 arm description; prereg template field | CORRECTABLE-LABEL — forward-looking protocol; change to "access-matched" |
| `docs/next_stage/reviews/SCIENCE_JUDGE_WAVE0_20261009.md` | 34, 44 | F2 critique (correctly identifies the gap); F12 PASS note | HISTORICAL-DO-NOT-REWRITE — review record; the critique itself is valid and remains accurate |
| `docs/next_stage/design/v3_telemetry_arm_addendum.md` | 51 | Correctly states "there are no executable interventions, so 'intervention-matched' parity is..." | CORRECT — already acknowledges the issue |
| `docs/next_stage/design/ceq_arm_design.md` | 1 | Title: "intervention-matched adaptive centralized manager" | CORRECTABLE-LABEL — forward-looking design doc |
| `docs/next_stage/design/a2_live_action_set_manifest.md` | 11, 95 | Source-of-truth doc for both arms; line 95 correctly notes "intervention-matched comparison is undefined" for detection variants | CORRECTABLE-LABEL for line 11 (change to "access-matched"); line 95 is CORRECT as-is |
| `docs/next_stage/adapters/aiopslab_contract.md` | 206, 224 | Legitimate use for the AIOpsLab mitigation track which DOES have exec_shell | CORRECT — leave unchanged |
| `docs/next_stage/SEED_PROMPT.md` | 10 | "intervention-matched causal coordination experiment" | CORRECTABLE-LABEL — forward-looking seed prompt |
| `docs/next_stage/LITERATURE_AND_BENCHMARK_DECISION.md` | 15, 17, 55 | Track I description; Track S deferral; P1 task | CORRECTABLE-LABEL — forward-looking decisions |
| `docs/next_stage/FLEET_EXECUTION_PLAN.md` | 7 | "intervention-matched central manager vs RepliClaw" | CORRECTABLE-LABEL — forward-looking plan |
| `docs/next_stage/FAST_FINISH_STATUS.md` | 3, 9, 14, 33 | Sprint status checkpoints | HISTORICAL-DO-NOT-REWRITE — checkpoint log |
| `docs/next_stage/EXPERIMENT_PROTOCOL_V3_DRAFT.md` | 1, 9, 103 | Title; C-EQ description; G2 gate | CORRECTABLE-LABEL — forward-looking draft protocol |
| `docs/next_stage/COPILOT_FAST_SEED.md` | 3 | "first reproducible, intervention-matched multi-case D-E vs adaptive C-EQ result" | CORRECTABLE-LABEL — forward-looking seed |

### Required corrections (forward-looking docs only)
For each CORRECTABLE-LABEL row above, replace "intervention-matched" with "access-matched" (or "access-matched observational") where it refers to the TELEM arms. Do NOT touch aiopslab_contract.md (legitimate use) or any HISTORICAL-DO-NOT-REWRITE file.

For fast_finish_result.md, add an errata block at the top:
```
> **ERRATA (2026-10-12):** The title and body of this memo use "intervention-matched"
> to describe the TELEM arms. The TELEM arms are access-matched observational agents
> (read-only telemetry queries against a frozen snapshot; no live system is perturbed).
> See `AUDIT_SCIENCE_MISMATCH_20261012.md` §1 for the full classification.
> Historical numbers and verdicts are unchanged.
```

## §2 Heldout contamination: RCA-P-08 exposure

### Finding
The v33_heldout_feasibility_protocol claims P-08/09/10 were "never used in any prior run." This is FALSE for P-08.

### Per-case exposure table (from artifact inspection)

| Case | Round | Arm | Status | Evidence path |
|------|-------|-----|--------|---------------|
| RCA-P-08 | R8 | D-E-TELEM | completed (hit) | `run_v37/round8/RCA-P-08/*/D-E-TELEM/status.json` |
| RCA-P-08 | R8 | C-EQ-TELEM | completed (hit) | `run_v37/round8/RCA-P-08/*/C-EQ-TELEM/status.json` |
| RCA-P-08 | R9 | D-E-TELEM | completed (hit, 344K tok) | `run_v37/round9/RCA-P-08/s20261011/D-E-TELEM/status.json` |
| RCA-P-08 | FF-05 (r0c) | D-E-TELEM | aborted_budget | `run_live_full_r0c/round0/RCA-P-08/*/D-E-TELEM/status.json` |
| RCA-P-08 | FF-05 (r0c) | C-EQ-TELEM | completed (hit) | `run_live_full_r0c/round0/RCA-P-08/*/C-EQ-TELEM/status.json` |

P-08 s11 was also noted as "pre-existing in V3.4" alongside P-02 s12, P-04 s11, P-06 s12.

### Conclusion
RCA-P-08 is EXPOSED. It must be excluded from any prospective holdout set. RCA-P-09 and RCA-P-10 require similar per-round verification before being declared fresh.

### Fresh holdout candidates (verified never-run, rep-1, ob suite)
From `data/cases.parquet` (735 rows), the following 16 cases have NO appearance in any historical round directory:
re1ob_checkoutservice_cpu_1, re1ob_checkoutservice_delay_1, re1ob_adservice_disk_1,
re1ob_adservice_loss_1, re1ob_adservice_mem_1, re2ob_checkoutservice_cpu_1,
re2ob_recommendationservice_delay_1, re2ob_checkoutservice_disk_1,
re2ob_checkoutservice_loss_1, re2ob_checkoutservice_mem_1, re2ob_checkoutservice_socket_1,
re3ob_currencyservice_f1_1, re3ob_emailservice_f2_1, re3ob_emailservice_f3_1,
re3ob_adservice_f4_1, re3ob_adservice_f5_1

sha256 over sorted ids: 0235241c8adc1034b67b3c398574063ba882a9127926b14583e012405a0908b4

Caveat: RE1 picks have has_logs=False, has_traces=False (tool surface differs from pilot cases). RE2/RE3 picks have logs+traces. Selection rule must be frozen prospectively with rationale.

## §3 D-E phase-1 sequential execution (confirmed)

From round-9 artifacts (600K envelope):
- Phase-1 investigators run SEQUENTIALLY (inv-a → inv-b → inv-c), not concurrently.
- Sequential span: 52–109 s across rounds (last p1 commit = time-to-first-diagnosis proxy).
- Per-investigator tokens: 49K–187K (mean ~100K); 18–50 LLM calls per investigator.
- Repeated actions (≥3× same tool+args): common (e.g., `service_metrics(cartservice)` ×6–7, `top_anomalies(k=20)` ×3–5).
- Total D-E tokens: 188K–410K vs C-EQ 49K–74K.

The V4 instrument fixes this by running all three investigators CONCURRENTLY (threads) with a hard per-investigator deadline.

## §4 150K failures vs R9 600K/cap-8 explanation

Round 4 (150K envelope): D-E aborted_budget at 151–154K tokens mid-phase-1. inv-c had 0 calls in P-02 s11 (never started). Several early runs crashed.

Round 9 (600K envelope, cap-8): D-E completed 8/8 hits. Cap-8 was never binding (max phase-2 usage was 7 < 8).

Explanation: D-E needs ~260–410K tokens to finish (3 sequential investigators + committee). At 150K the shared envelope is exhausted before phase 2 begins. Cap-8 is a red herring — it was never the binding constraint. The V4 instrument's concurrent phase-1 + deadline fallback directly addresses this: total wall time drops, and the fallback ensures a commit even if an investigator loops.

## §5 Smallest genuinely executable counterfactual environment

| Environment | Location | Executable? | Notes |
|-------------|----------|-------------|-------|
| SimpleAudit P02 hero case | `src/repliclaw/counterfactual/` | YES — deterministic, replayable, byte-identical | RAG policy case (not incident-telemetry); factor dimensions: retrieval/policy_conflict/judge_reference/model_prompt |
| AIOpsLab scratch checkout | `/Users/sushantgautam/Documents/stg2-worktrees/AIOpsLab/` | PARTIAL — has exec_shell but deployment BLOCKED | Never deployed; adapter exists but untested |
| Telemetry sandbox (OBS) | `src/repliclaw/experiments/v3/telemetry.py` | OBSERVATIONAL ONLY — read-only queries against frozen snapshot | Correctly labeled access-matched in V4 |

For the V4 instrument as scoped, interventions remain "executable queries against a frozen environment snapshot" (OBS tools), honestly labeled access-matched/observational. The SimpleAudit P02 case is the smallest genuinely executable counterfactual available in-repo but is a different problem type (RAG policy, not incident diagnosis).
