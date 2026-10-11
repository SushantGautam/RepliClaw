# V3 telemetry-observational arm addendum (D-E-TELEM / C-EQ-TELEM)

**Status:** DESIGN (I4, 2026-10-10, post-D-V3-013). Additive to `ceq_arm_design.md` and
`g3_pilot_spec_draft.md`; supersedes nothing. Written as a versioned addendum
motivated by a pre-registered defect surfaced at T0 recon (the frozen pilot spec's
"arms run on the D-E/C-EQ arms" could not be executed as written — see §1).

## 1. The defect that motivates this addendum

The frozen D-E and C-EQ arms (`eess_live/arm.py`, `experiments/v3/ceq.py`) run on the
**SimpleAudit counterfactual substrate** (`counterfactual/executor.py`): their "counterfactual
tools" perturb the four AI-system factors (retrieval / policy_conflict / judge_reference /
model_prompt) of the `policy_rag_v1` case. That substrate:

1. has **no RCAEval telemetry case** (`case_loader.py` refuses non-canonical cases by
   design — same-task enforcement),
2. has **no intervention menu** for the 10 pilot cases (`load_interventions` returns
   `policy_rag_v1` factors only),
3. therefore the two arms cannot be executed "verbatim" on pilot cases without either
   (a) fabricating telemetry counterfactual interventions (forbidden: never invent
   counterfactual outcomes from recorded data) or (b) gutting the arms (forbidden: no
   handicapping).

Per D-V3-013, Track-I (AIOpsLab, the only real live-intervention track) is DECLINED.
The V3 campaign is Track-II (RCAEval) only.

## 2. Addendum resolution: matched-ACCESS observational arms

Both pilot arms become **observational diagnostic agents with byte-identical access
parity** to the frozen case's telemetry, through one shared sandbox. What the arms
still demonstrate — the actual H1 contrast — is:

- **D-E-TELEM**: decentralized committee (3 investigators) with **pre-outcome
  hypothesis escrow** (each commits a ranked diagnosis + confidence BEFORE the shared
  reveal), local evidence-need negotiation, and a final escrow-weighted adjudication.
- **C-EQ-TELEM**: a single **adaptive central manager** that iteratively (≤4 planner
  rounds) picks which tool queries to issue, sees a **volume-bounded union evidence
  view**, collects 3 investigator findings once post-loop, and commits a final ranked
  diagnosis.

Parity (the "same information and tools, same budgets" rule, D-V3-013(c)):
identical sandbox tool set, identical per-query result payloads, identical per-arm
token budget (60,000), identical wall cap (900 s), identical opaque case id, identical
model (SimulaChat default, Qwen3.8-27B), identical temperature (0.2), identical
system context. The ONE designed difference (disclosed, per protocol S5) is the
coordination regime and the C-EQ union evidence view (superset, volume-bounded).
The C-EQ prompt-volume band [0.6, 1.25] canary applies exactly as in
`ceq_arm_design.md` §5.

**Honest limitation (goes in the pilot report + prereg addendum):** on recorded
telemetry there are no executable interventions, so "intervention-matched" parity is
relaxed to **access-matched** parity on this track. The counterfactual-intervention
contrast remains represented (i) by P08 (frozen, single-case) and (ii) by Track-I
design (frozen, human-declined). Neither arm gets more or less information than the
other; the no-escrow (D-N-TELEM) and random-selection (D-R-TELEM) controls are
available as deferred arms exactly as in the frozen pilot spec §3.

## 3. Telemetry sandbox (OBS tools — both arms, byte-identical)

Case data (already downloaded, I4 T0+1): `metrics.parquet`, `logs.parquet` (8 cases),
`traces.parquet` (4 cases), `inject_time.txt`. `inject_time` is presented to agents as
"anomaly onset (reported)" — it is public incident metadata, not ground truth.

Tools (one module `src/repliclaw/experiments/v3/telemetry.py`):

| Tool | Returns | Note |
|---|---|---|
| `system_context()` | service inventory, per-service metric count, time window, anomaly onset, suite/system names | static per case; deterministic |
| `top_anomalies(k=20)` | ranked (service, metric, score) list from the official anomaly scorer | same math as BARO windowing/scaling — a shared method, not an arm; the agent may or may not use it |
| `service_metrics(svc, k=30)` | per-metric fault-vs-normal window statistics for one service | agent-directed drill-down |
| `service_logs(svc, k=50)` | up to k log lines around anomaly onset | absent for RE1 cases → returns "no logs" |
| `service_traces(svc, k=30)` | up to k span rows (service, operation, latency, status) around onset | absent for 6 cases → "no traces" |

Sandbox guarantees: every tool payload is identical for both arms (pure function of
case + args); payloads contain **no upstream case id, no root_cause_service, no
fault_description** (leak guards unit-tested); all calls are token-counted into the
arm ledger; per-run tool-call cap (≤ 24 calls total, 4 per tool for logs/traces) so a
degenerate arm cannot brute-force the label.

## 4. Diagnostic commitment + official scoring

Both arms must end with exactly one **committed ranked list of services** (top-5)
(`DiagnosticSubmission`). Per-run success = **service-level accuracy@5** computed with
the **official RCAEval `Evaluator` logic** (contract §3: coarse-grained
`_accuracy_service[5]`), ground truth resolved ONLY through
`rcaeval.manifest.heldout_ground_truth` under `ScorerContext` (C-SCI-1 gate; the
scorer is the only code path that reads `root_cause_service`). Run-level success =
top-5 service hit. Case-level success (the estimator s) = both k=2 seeds succeed.
This matches the frozen pilot estimands (σ̂_D of the paired difference, per-arm
saturation s).

## 5. BARO feasibility (frozen spec §3, item "BARO")

BARO runs on the 8 RE2-OB delay pilot cases with the **official repo code path**
(venv `rcarun`, pinned `259ea41`) as the W1 smoke did, converted-layout, producing
Avg@5-CPU. In-range check vs the W1 RE2-OB cpu smoke (0.66) is a harness-reproduction
feasibility check only — MODEL-SUBSTITUTION labels apply to the arm runs, BARO is
the official baseline reproduced with its own code (no LLM in BARO).

## 6. What changes in the frozen pilot spec (addendum list, all additive)

1. "Arms {D-E, C-EQ}" → executed as D-E-TELEM / C-EQ-TELEM per §2 (access-matched
   observables), with the §2 limitation disclosure verbatim in the pilot report.
2. Per-run envelope 60,000 tokens / 900 s unchanged; tool caps added (harness-side).
3. Success rule = official service-level accuracy@5 via `ScorerContext` (this makes
   the scorer path concrete for the pilot; the heldout reuses the same rule).
4. Nothing in §4 budget, §5 stop rules, §5.1 ladder, or the 42-case heldout changes.

Frozen-constants impact: new code is new (sha-pinned at T0+6 final freeze); the
C-EQ template pins apply to the C-EQ-TELEM prompt templates; D-E-TELEM template
pins are recorded alongside at the same freeze.

### 6.3 Amendment W3g (harness-side, additive — no frozen number touched):
context compaction of stale tool observations in the provider send-view

Observed on pilot launch #2 (RCA-P-01, both arms, both seeds, real
MODEL-SUBSTITUTION runs): all 4 runs ended `aborted_budget` at ~60.6K–64.3K
tokens **with the model behaving correctly** (clean `system_context` →
`top_anomalies` → one `service_metrics` per each of the 13 services → `commit`
as the final action). Token composition (audit `audit_llm.json`, real gateway
`usage`): D-E inv-a = **43,343 prompt / 600 completion** over 15 calls; C-EQ
manager = **52,609 prompt / 480 completion** over 14 calls. Individual
`service_metrics` observations are only ~180–200 tokens each; the envelope was
blown by **full-history re-prompting** — every turn re-sends the entire growing
transcript and the gateway bills it (O(turns²) prompt growth). This is a
harness cost defect, not a model-capability signal and not an information-access
change: the spec's own §4 stop-2 note ("the 60,000 cap is structurally too
small for the case class") applies only if the exhaustion persists after this
harness-side fix; it must not be read as a science result for launch #2.

Fix (W3g, `telemetry_arms.py`, `LLMToolSession._compacted_view`): the provider
send-view keeps the system prompt, the first (phase) instruction, and the most
recent 6 messages verbatim; older *user* messages (tool observations —
idempotent, re-fetchable via a tool call) are replaced by a ≤120-char stub
with a "re-issue the tool call" hint. Model responses are never compacted.

What does NOT change (all frozen/scientific surfaces intact):
- the 60,000-token per-run envelope and 900 s wall cap (unchanged);
- agent information access (any compacted observation is re-fetchable);
- the audit transcript (`transcript` keeps full text — provenance intact);
- the prompt-volume canary (computed from `self.prompts`, full text);
- the sandbox tool budget (24 calls) and one-shot `submit_diagnosis`.

Measured effect (real RCA-P-01 transcript, estimator): per-call prompt cost
plateaus at ~1,000 tokens vs ~3,200 un-compacted (3.2×); a 32-call session's
send-view stays ~2.4K tokens vs ~10K+. Predicted arm totals for this case
class: D-E ≈ 27K, C-EQ ≈ 37K — under the frozen 60K. Regression test:
`test_session_compaction_bounds_send_view_keeps_full_audit`
(`tests/experiments/test_v3_telemetry_arms.py`).

### 6.4 Amendment W3h (harness-side, additive — no frozen number touched):

**Defect class: driver stop-rule denominators, not model, not arms.** Live
pilot #3 (real SimulaChat, Qwen3.8-27B) ran RCA-P-01 (4 runs) and STOPPED
after case 1 because `evaluate_stop_rules` fired BOTH stop-1 (S-sat) and
stop-2 (crash) on a **running denominator**:

- `sat_per_arm` divided saturated-cases by **cases recorded so far** (1/1 = 1.0
  ≥ 0.25 → trip) instead of the spec's `n_pilot = 10`.
- `crash_rate_per_arm` divided crashes by **ledgered runs so far** (2/2 = 1.0
  > 0.25 → trip) instead of the spec's fixed per-arm cohort (10 × 2 = 20).

This is a harness defect, not a science result: at case 1, C-EQ saturated
**1/10 = 0.10** (< 0.25, no trip) and D-E crashed **2/20 = 0.10** (< 0.25, no
trip). The pilot should have **continued** to case 10 (or the first genuine
trip). The over-eager trip consumed no re-pilot budget (it is a defect
amendment, not a §5.1 ladder trip) and is reversible: round 1 is re-run from
scratch on the fixed driver.

**Real-run evidence (pilot #3, `round1/` before wipe):** C-EQ-TELEM completed
both seeds (54,717 / 54,721 tokens; W3g compaction held the manager under the
60K envelope) with `hit = true` both (adservice top-1; ground truth =
adservice). D-E-TELEM aborted_budget both seeds (62,751 / 60,537): compaction
reduced inv-a's prompt (43,343 → ~60K over 23 calls) but the decentralized
arm's genuinely verbose single-investigator sweep (system_context 1× +
top_anomalies 4× + service_metrics 17–18×) still exceeds the 60K per-run
envelope; inv-b/inv-c never got a call. That D-E aborted_budget behavior is a
**legitimate stop-2 input at cohort scale** (it is a real crash), so it must be
preserved as data — but only evaluated against 20 runs, not 2.

**Fix (`scripts/pilot_run.py`, W3h):**
- `sat_per_arm`: denominator = `TOTAL_CASES` (10), per spec §5 rule 1 verbatim
  ("3 of 10 cases saturated for either arm").
- `crash_rate_per_arm`: denominator = `TOTAL_CASES × len(PILOT_SEEDS)` (20),
  per spec §5 rule 2 verbatim ("≥ 6 of 20 runs").
- Regression: `test_stop_denominators_full_cohort_after_case_1`
  (exact pilot #3 state → no trip) + the existing
  `test_stop1_ssat_trip_at_3_of_10` / `test_stop2_crash_trip_at_6_of_20` now
  pin the true trip points. `test_run_fake_artifacts_and_score_schema`
  updated: a single saturated case no longer trips (driver pauses, exit 0).

**What does NOT change (frozen scientific surfaces intact):**
- the four stop-rule THRESHOLDS (0.25 / 25% / 2,880,000 / floor 2-of-20 and
  9-of-10) — only the DENOMINATORS were corrected to match the frozen spec text;
- the 60,000-token per-run envelope, 900 s wall, 24-call tool budget;
- the arms, tools, escrow, scoring, and the frozen pilot roster;
- the D-E aborted_budget runs: they remain crashes in the cohort denominator
  (no softening of the signal — only the arithmetic was corrected).

**Re-run consequence:** round 1 is discarded (it is a harness-defect artifact,
recorded as non-pilot evidence, consistent with the launch #1/#2 note). The
pilot re-runs fresh on the fixed driver. No re-pilot cap is consumed: a
§5.1 ladder rung is only consumed by a GENUINE trip (s ≥ 0.25 or ≥ 6/20
crashes at cohort scale) on the corrected checker.
