# Regime report — when RepliClaw's escrow / independent-reasoning / adaptive-experiment machinery helps, when it hurts (2026-10-12 sprint)

**Scope.** Exploratory, bounded measurements on the already-approved SimulaChat endpoint (Qwen3.8-27B via `default` — **MODEL-SUBSTITUTION**, not a released baseline). Two evidence classes, kept separate per protocol:

- **OBSERVATIONAL / ACCESS-MATCHED** (no executable interventions): HiddenBench (ICML 2026) three-arm run, and a single-case D-E v2 vs C-EQ telemetry smoke.
- **EXECUTABLE-COUNTERFACTUAL** (real target reruns): the P08 `policy_rag_v1` one-seed three-arm demo, and verified new single-cause / compound-cause cases (offline rerun matrix, no LLM).

No confirmatory campaign. No p-values from reused/exploratory cases. Negative and null results are preserved verbatim.

## 1. Observed results

### 1a. HiddenBench (ICML 2026), observational — `docs/next_stage/results/hiddenbench/`

Official benchmark vendored unmodified (`third_party/hiddenbench`, sha256 in each run's `summary.json`). Three arms, identical task set:

| run | arm | group accuracy | indiv. final-vote acc | LLM calls | tokens |
|---|---|---|---|---|---|
| tasks 1–4 | escrow (RepliClaw packet + pre-reveal commit) | **0/4** | — | 90 | 92,266 |
| tasks 1–4 | open-share (official discussion protocol) | **0/4** | — | 75 | 77,024 |
| tasks 1–4 | central (pooled info, single controller) | **4/4** | 1.00 | 4 | 3,064 |
| tasks 5–12 | escrow | **0/8** | 0.031 | 180 | 200,368 |
| tasks 5–12 | open-share | **0/8** | 0.031 | 150 | 159,721 |
| tasks 5–12 | central | **6/8** | 0.750 | 8 | 7,476 |
| **combined 12** | escrow / open-share / central | **0 / 0 / 10** | 0.057 / 0.120 | 270 / 225 / 12 | 292.6K / 236.7K / 10.5K |

**Null/negative result:** on this model slice, neither escrow nor open-sharing multiagent deliberation beat the same-information centralized controller; the multiagent arms hit their 200K-token caps while scoring 0. Caveat: the central controller receives pooled information directly, so this measures *multiagent pooling under escrow/open protocols* vs *direct pooled access*, not a pure protocol ablation at fixed information.

### 1b. Mechanism smoke — D-E v2 vs C-EQ, observational — `docs/next_stage/results/mechanism_smoke/`

One reused pilot case (RCA-P-05), seed 0, both arms, 30K-token envelope/arm, tool cap 6 (final run `smoke_RCA-P-05_seed0_20261012T161240Z`):

| arm | status | acc@5 | top-1 | tokens | LLM calls | escrow commitments |
|---|---|---|---|---|---|---|
| D-E-TELEM (v2: independent investigators, bounded turns, pre-outcome escrow, best-evidence commit) | completed via **best-evidence commit** (30,542 > 30,000 → `budget_exhausted`, not masked) | HIT | MISS | 39,267 | 25 | 3/3 (rankings disagreed: 3 different top-1s) |
| C-EQ-TELEM (strong centralized manager, batch parallelism) | completed (prompt-volume canary breach disclosed) | HIT | MISS | 10,659 | 13 | 1 sealed forecast |

**Null result on this single case:** mechanism v2's independence + commitment machinery worked as designed (3 independent escrowed rankings, best-evidence commit on overrun), but spent 3.7× the tokens of C-EQ with no top-1 gain. Two honest earlier failures in the same case are preserved in `LIVE_RUN_2.log` / `LIVE_RUN_3.log`.

### 1c. Executable P08 one-seed demo — `docs/next_stage/results/p08_mechanism_demo/`

`policy_rag_v1` (reused, **not** a fresh case), harness seed 20261012, matched envelope 60K tok / 900 s / 4 agents (identical `envelope_sha256` across arms; executor parity confirmed by the scorer), live LLM, `REPLICLAW_LLM_ALLOW_LIVE=1` two-key start:

| arm | verdict | M1 (correct diagnosis) | counterfactual slots exec/granted | tokens | wall s |
|---|---|---|---|---|---|
| S5 `eess` (escrowed decentralized) | refuted | **1.0** | 4/4 (all verified against the target) | 3,212 | 26.0 |
| S4 `open_sharing_swarm` | supported (wrong) | 0.0 | 0/0 | 5,130 | 21.3 |
| S3 `adaptive_central` (incumbent full protocol; NOT a neutral central — see `comparators/managers.py`) | supported (wrong) | 0.0 | 0/0 | 4,162 | 19.8 |

Scorer output: Δ = M1(S5) − M1(S4) = 1.0, 95% CI [1.0, 1.0] — **degenerate by construction at n = 1 run/arm**; the mechanical decision string "SUPPORTED" is reported as a 1-case × 1-seed **mechanism demo**, not an effect estimate. Direction is consistent with the public main P1 campaign (P1 SUPPORTED, 120 runs).

### 1d. Verified fresh executable cases — `docs/next_stage/results/compound_causal/`

Two new frozen cases, ground truth sealed (oracle-leak scan: 0 hits on all persisted artifacts; hidden fields documented in `HIDDEN_FIELDS.md`), verified by **actual target reruns** (seed 0, 0 LLM calls):

- `flowmeter_single_cause_v1` (single-cause): baseline MISMATCH (95,737.9784 L); fix calibration → PASS (101,417.35 L = sealed truth); non-cause fix → MISMATCH. ✓
- `drift_sign_and_v1` (AND two-cause): baseline MISMATCH (485.178711 µg/mL); each single fix alone → PASS (479.706706 µg/mL); both fixes → PASS. ✓ (interaction verified: failure needs both causes)

These are ready targets for a multi-case executable arm comparison; they are **not yet wired** into the live EESS agent lifecycle (see §3).

## 2. When RepliClaw helps / hurts (exploratory answer)

- **Helps (regime: executable diagnosis with falsifiable interventions).** Where the correct answer requires *committing* a hypothesis *before* seeing intervention outcomes and then *executing* verified counterfactuals, the escrowed decentralized arm diagnosed correctly and produced verified counterfactual slots (1c), while both non-escrow arms endorsed a defective claim and ran no counterfactuals. This is the regime the public main P1 campaign already established; this sprint reproduced it on one fresh-seed run.
- **Hurts / neutral (regime: pure observational reasoning under this 27B model).** HiddenBench multiagent deliberation (escrow *and* open-share) was dominated by direct pooled centralized access on every task (0/12 vs 10/12) at ~20–28× the token cost (1a). The telemetry smoke showed the v2 mechanism working correctly but costing 3.7× C-EQ with no top-1 gain on a single case (1b).
- **Which mechanism causes the difference.** On this model slice, the binding factor is *information pooling*: centralized access to all evidence beats multiagent pooling through escrow or open discussion. Escrow's added value shows up only where the task structure rewards pre-outcome commitment + verified execution (no post-hoc rationalizing of a diagnosis), not in pooling observational evidence. Counterfactual slot execution (the adaptive-experiment loop) is the observable mechanism that separated S5 from S4/S3 in 1c.

## 3. Limitations (do not over-read)

1. All LLM results use MODEL-SUBSTITUTION Qwen3.8-27B; generalization to frontier models untested.
2. Small n everywhere (12 observational tasks; 1 telemetry case; 1×1 executable demo); no statistical claim from reused cases.
3. HiddenBench's central arm had pooled access by design (access-matched claim is "multiagent protocol vs pooled central", not a pure protocol ablation).
4. `policy_rag_v1` is the reused P08 instrument — labeled as such, never counted as fresh evidence.
5. The new compound/single-cause cases are verified at the *target* level (rerun matrix); the agent-lifecycle wiring (`comparators/case_loader` claim adapters + parameterizing the EESS orchestrator's case binding) is the remaining work for a multi-case executable arm comparison — a small, bounded follow-up, not done here.
6. Pre-existing environment issue (present at pre-sprint base `c33715e`, not introduced here): `tests/experiments/test_pilot_driver.py::test_report_backend_echo_provenance` and `::test_simula_client_adapter_chat_create_surface` fail with `ModuleNotFoundError: No module named 'scripts'` in this checkout.

## 4. Reproduce

```bash
export SIMULACHAT_BASE_URL="https://simulachat.sushant.pp.ua/api/v1"
export CUSTOM_SIMULACHAT_KEY="<operator key>"
export REPLICLAW_LLM_ALLOW_LIVE=1

# 1a HiddenBench (12-task combined = two runs; per-run READMEs in results/hiddenbench/)
uv run python -m repliclaw.benchmarks.hiddenbench.runner --task-ids 1,2,3,4 --out <dir1>
uv run python -m repliclaw.benchmarks.hiddenbench.runner --task-ids 5,6,7,8,9,10,11,12 --out <dir2>
# 1b mechanism smoke
uv run python scripts/mechanism_smoke.py
# 1c executable demo (per arm), then score
for arm in eess open_sharing_swarm adaptive_central; do
  uv run python -m repliclaw.comparators.runner --arm $arm --case policy_rag \
    --client-factory live --harness-seed 20261012 --out docs/next_stage/results/p08_mechanism_demo/$arm
done
mkdir -p docs/next_stage/results/p08_mechanism_demo/scored
ln -sfn ../eess scored/S5; ln -sfn ../open_sharing_swarm scored/S4; ln -sfn ../adaptive_central scored/S3
uv run python -m repliclaw.p08.score --run-root docs/next_stage/results/p08_mechanism_demo/scored --case policy_rag_v1
# 1d compound-case verification (offline, no LLM)
uv run python docs/next_stage/results/compound_causal/run_verification.py
```

Repo state: `dev` at the commit containing this report; all raw artifacts under `docs/next_stage/results/{hiddenbench,mechanism_smoke,p08_mechanism_demo,compound_causal}/`; `main` and all prior ledgers/preregistrations untouched.
