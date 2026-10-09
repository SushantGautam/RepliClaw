# SCIENCE JUDGE — ROUND-2 SIGN-OFF (read-only) — P08 prereg v1.1 + v1.2-AMENDMENT A1–A8

**Verdict: NOT-APPROVE** — new BLOCKING defect M-1 (M1 structural asymmetry). RC-1 (executor parity, A8) is genuinely resolved (Q1 PASS); A8 engineering is sound and green.

---

I have enough verified evidence to render the round-2 science verdict. Below is the structured sign-off. I verified by reading the actual code and documents at the pin, running the suite, and — critically — running the live/fake S5 vs S4/S3/S0 arms through the real runner + scorer to empirically test the P1 estimand.

---

# SCIENCE JUDGE — ROUND-2 SIGN-OFF (read-only) — P08 prereg v1.1 + v1.2-AMENDMENT A1–A8

**Reviewed:** `repl-claw-dev`, code pinned at `a708523` (verified: `src/` + `tests/` byte-identical between `a708523` and live `HEAD` `5704683`; the latter is docs-only).
**Independence:** I judge the science; I do **not** self-certify the code-judge (MERGE-OK is engineering) and I did **not** run any live benchmark. Where I executed code it was the **deterministic `FakeLLMClient` fixture only** — used as structural evidence, never as a real-world finding.

## Verified green (independently reproduced @ a708523/5704683)
- `pytest -o addopts="" -q` → **225 passed, 8 skipped** (matches claim).
- `bash experiments/policy_rag/preflight.sh` → **ALL 5 GATES PASS** (5704683).
- `p08.score --self-test` → **PASS**.
- **A1.3 rule string:** `score.py` `diff["rule"]` (≈`score.py:553`) is **character-identical** to the amendment A1.3 blockquote — `len=1224`, `sha256=766f4eb9…20e0c988` (my earlier 2-char mismatch was an extraction artifact of the surrounding quotes; after stripping, `IDENTICAL=True`).

---

## Q1 — Is RC-1 genuinely resolved? Guard before bootstrap / bypass?  → **PASS (executor axis), with a caveat at Q2/Q7**
- **Like-for-like at the executor level: YES.** `runner.py:642` `is_live = arm_key in LIVE_KEYS and (not spec.secondary or arm_key in _LIVE_ONLY_KEYS)`; all six primary arms are in `LIVE_KEYS` (`runner.py:195`). On primary, S0/S3/S4 route through `_run_live_strategy` (`runner.py:743`) using `_llm_investigator_factory` → `LLMInvestigator` (`runner.py:458-473`), the **same `LLMClient()` factory** (`runner.py:236`) and `LLMConfig` as S5. Envelope is the shared `default_envelope` = **60k/900s/4** (`case_loader.py:208`).
- **Guard runs BEFORE bootstrap and vetoes only a mixed S5/S4:** `score.py:530` `if _pair_executor_mismatch(clean,"S5","S4"): diff["decision"]="executor_parity_violation"`; the bootstrap (`score.py:536+`) is in the `elif`, so a mixed pair **cannot reach a decision**. `_pair_executor_mismatch` = union of `(model, offline_arm)` signatures across both arms has size > 1 (`score.py:446-462`).
- **Cannot be bypassed:** SUPPORTED/FALSIFIED/NOT_SUPPORTED are emitted only by `decision_branch`, which is only called in the `elif`. Any executor mismatch forces the `if` branch. No alternate code path emits a P1 decision outside `score_runs`, and the guard is internal to it. `parity.ok` (`score.py:506-507`) is flipped only by mixed **S5/S4** or **S5/S3** (not S5/S0). Residual: the guard keys on operator-written `run_metadata` (tamper only via a forged sealed artifact — an out-of-scope trust assumption, same as every other scorer field).

## Q2 — Is the estimate still scientifically valid?  → **FAIL (new BLOCKING defect — see Q7)**
Executor parity is real, **but the P1 estimand Δ = M1(S5) − M1(S4) is still not a valid like-for-like comparison at the *metric* level.** A8 removed the executor confound and thereby **promoted the next defect into the driver of the primary decision**: S4 (and S3, S0) are **structurally incapable of scoring M1** under the merged code. See Q7 for the reproduction. The "audit-only seed" concern you raised is fine (A8.2 correctly scopes it; like-for-like is defined on `LLMConfig`, which is enforced by construction) — that is *not* the blocker.

## Q3 — RQ correctness (S0 = RQ3 ablation, not RQ2 arm)?  → **PASS**
- Text: A8.2 "RQ pairing correction (C4)" states S0 is RQ3, not in any P1/P2 pair, S5/S0 parity reported but does **not** veto.
- Code: `parity.ok` = envelope ∧ no overruns ∧ `executor_parity["S5_S4"]` ∧ `executor_parity["S5_S3"]` (`score.py:506-507`) — **S0 excluded**. `executor_parity` still reports `S5_S0` for the record (`score.py:491-494`).
- Test: `test_a8_s5_s0_mixed_does_not_flip_parity_ok` (in `tests/test_a8_executor_parity.py`, part of the 12; suite green).

## Q4 — Case-conditional routing (C1)?  → **PASS**
- Primary: S0/S3/S4 live (`test_a8_s0_s3_s4_live_on_primary`: `offline_arm=false`, `model="fake-v1"`). Secondary `tox21_ar_agonist`: S0/S3/S4 **offline** (`offline_arm=true`, `model="deterministic"`, exit 0 — `test_a8_s0_s3_s4_offline_on_tox21_secondary`); S5/A1/A3 **refuse** (exit 2). This preserves the frozen RQ4/P4 no-LLM sub-study (§4.2: "all LLM budgets zero by construction").
- **No cross-case arm comparison:** S5 never runs secondary, so no arm straddles cases; P1/P2 are computed per-case on the primary run-set only. All six arms are internally consistent (live) on primary.

## Q5 — Fairness / strong-comparator (S3) integrity?  → **PASS (strengthened)**
A8 **strengthens** RQ2: S3 is now live on primary, making S5-vs-S3 a like-for-like RQ2 (it was live-vs-deterministic before — the same class of flaw A8 fixed for P1). The A3 confounding disclosure (S3 bundles escrow-like commit/reveal → not a clean decentralization isolation) is **now reconciled in source** — `managers.py:46-58` `AdaptiveCentralManager` docstring matches A3 (RC-2 closed). S3's honest agent accounting (Q6) makes it consistent. S3 remains a genuine strong baseline, not a strawman.

## Q6 — Honesty of accounting (live `n_agents`)?  → **PASS**
- Live path: `arm.py` `n_agents = max(1, orch.ledger.distinct_agents)`; the **parent** ledger receives exactly **one** aggregate `BudgetRecord` carrying the true distinct count; the orchestrator's per-call records (`n_agents=0`) live in its **own** `LiveBudgetLedger` and are never forwarded → **no double count** (asserted in `test_a8_live_arm_agent_accounting`: `sum(r.n_agents)==n`).
- Offline/strategy path: `arms.py` `n_agents = len({e.agent_id …})` — true observed distinct count; the `d54cb71 min()` clamp is **removed** (`arms.py:128+`), so S3's 4th follow-up is recorded honestly and the 4-cap binds no arm (A8.5 supersession is **honest** — the clamp had hidden it).
- M5 (tokens) is real LLM usage (`usage_present=true`, `runner.py:559`) on the live strategy arms, **not** `COST_TOKENS_PER_ARM`. M6 = mean M5 over M1=1 runs (`score.py:370+`), denominator honest.
  - *Minor (non-blocking):* the strategy-arm `budget_ledger.json` collapses all usage into a **single synthetic call** with `llm_calls:1`, `completion_tokens:0`, all tokens as `prompt_tokens` (`runner.py:540-565`). `totals.total_tokens` (what M5 reads) is correct; only the per-call granularity is not.

## Q7 — Any NEW scientific defect A8 exposed?  → **YES — BLOCKING (not "new" from A8, but made load-bearing by A8)**
**DEFECT M-1 (BLOCKING, pre-existing, now the driver of the primary decision): M1 is structurally asymmetric — the comparators S4/S3/S0 can never be "correct."**

Reproduction (deterministic `FakeLLMClient` fixture, **not** a live finding) — one arm, one run, `--case policy_rag`:
| arm | `final_verdict.defect_class` | `target_artifact` | scored M1 |
|----|----|----|----|
| S5 | `'retrieval_omission'` | `'retrieval'` | **1.0** |
| S4 | `None` | `None` | **0.0** |
| S3 | `None` | `None` | **0.0** |
| S0 | `None` | `None` | **0.0** |

Chain of cause:
- M1 = `defect == oracle.true_cause and bool(target)` (`score.py:251-257`); oracle `true_cause="retrieval_omission"`.
- The **strategy** contract writer **hard-codes** `"defect_class": None, "target_artifact": None` — `_write_offline_artifacts` (`runner.py:376-377`) **and** `_write_live_strategy_artifacts` (`runner.py:588-589`). **A8's new live path inherits the same nulls.**
- The strategy `Verdict` model (`models.py:224`) has **no `defect_class`/`target_artifact` field at all**, and the strategy investigators (`strategies.py` → `LLMInvestigator.run`) return only the `FINDING_SCHEMA` (`conclusion/statement/plan/evidence/confidence/executable`, `investigators.py:152-160`) — i.e., S4's agents are **never asked to name a defect class or target artifact**, and there is no code path that would surface one even if they did. Only S5's EESS `LiveRunResult` carries `defect_class/target_artifact` and is emitted (`orchestrator.py:374-381,652-653`).

**Consequence:** Δ = M1(S5) − M1(S4) is a **metric-level asymmetry**, not a measured autonomy effect. S5 (post-evidence RESOLVE prompt explicitly asks for `defect_class`/`target_artifact`) *can* be correct; S4 *cannot*, regardless of LLM quality, temperature, or seed. Under A8's guard, a "clean" live run will produce `M1(S4)≡0`, so P1 can read **SUPPORTED** whenever S5 is correct at all — a **false positive** attributable to the task interface, not to decentralized escrow. P1-FALSIFIED becomes essentially unreachable. This is the same class of defect as RC-1 (a comparison the campaign's own prereg declares invalid), now at the **M1 interface** rather than the **executor**: the round-1 sign-off's "not faulting" list (S7 scope, matched-cap, novelty) did **not** cover it, and no prior review (hotspots, my round-1 NO-GO, the A8 design review) flagged it — it was masked because the P1 decision was already void at the executor level.

**This is not a "deterministic toy" artifact I'm inventing:** it holds for any executor because the *code path* drops the fields for S4. Real-LLM execution cannot fix it unless the strategy arms are made capable of emitting a defensible `defect_class`/`target_artifact`.

**Required fix (pre-window, no data peeking) — versioned amendment A9, one of:**
1. **(Preferred) Arm-neutral M1 surface:** extend the strategy arms to produce a `defect_class`/`target_artifact` from their *own* output with **equivalent diagnostic access** to S5 (e.g., a post-evidence adjudication prompt, or per-agent defect fields threaded through `Verdict` → `ArmResult` → both `final_verdict` writers), then **re-pin** the A3 random-comparator and re-run the FakeLLM parity + 6-arm scoreable regression. Register the exact prompt/field contract and confirm it changes no estimand/threshold.
2. **OR re-scope M1/P1** to an arm-neutral correctness definition that S4 can actually satisfy (e.g., correct *verdict label* vs oracle stance for the seeded fault), with a registered change to §6 M1 and A1.3.
3. Whichever path: add a **scorer precondition** asserting that, in the primary run-set, at least one comparator run in each of S4/S3/S0 **can** be non-null (a canary that the M1 interface is not structurally degenerate), so a degenerate baseline can never silently yield a SUPPORTED P1.

Until one of these lands and is signed, **the primary decision the live window exists to make still cannot be produced validly.** This is a MUST-FIX, not optional hardening.

## Q8 — Novelty framing (AutoScientists/Co-Scientist/Robin/AgentRx gate)?  → **PASS**
A8 adds **no new mechanism claim**. The only mechanism A8 changes is the *executor* of S0/S3/S4, and the RC-2 relabel (`managers.py:46-58`) now **matches** the A3 confound disclosure (no overclaim of a clean decentralization isolation). No "first"/firstness claims introduced. Prior-art positioning unchanged.

## Q9 — Does the A8.4 "non-changes" list hold?  → **PASS (with the Q7 caveat noted, not counted here)**
- Rule string: **byte-identical**, len 1224, sha256 `766f4eb9…` (verified).
- Envelope 60k/900s/4 (`case_loader.py:208`); master ceiling **unchanged** — 10.8M = 6×20×60k (7.2M) + 6×10×60k (3.6M) (`v1.1:139`); `7.2M ≤ 10.8M` holds and is **executor-invariant** (arm set/counts/cap unchanged by going live).
- Arm set, M1–M11 definitions, 20/10 runs, seeds 20261010/20261020, window 2026-10-10→23, stopping rules S0–S3/S5, artifact contract, novelty framing — all unchanged in the amendment and the code.

---

# VERDICT (science key)

## **NOT-APPROVE** — round 2

**RC-1 is genuinely resolved** (Q1 PASS) and A8's *engineering* is sound and green — I am **not** reopening A1/A4/A6, RQ pairing (Q3), case-conditional routing (Q4), S3 fairness (Q5), or accounting (Q6). **But the live run may not start because the P1 primary decision is still not a valid like-for-like comparison — now at the M1 metric level.**

### BLOCKING
- **M-1 (Q7):** M1 is structurally asymmetric — S4/S3/S0 are hard-coded to `defect_class=None, target_artifact=None` (`runner.py:376-377`, `588-589`) and the strategy `Verdict`/investigator interface cannot emit them, so `M1(S4)≡0` by construction (`score.py:251-257`). Δ = M1(S5)−M1(S4) therefore measures a task-interface artifact, not an autonomy effect, and can yield a false P1-SUPPORTED. **Fix:** versioned amendment **A9** — (1a) arm-neutral defect surface with equivalent S4/S3/S0 diagnostic access + re-pin/re-run parity & 6-arm-scoreable regression, or (1b) arm-neutral M1 re-scope; **plus** (2) a scorer canary precondition that at least one S4/S3/S0 comparator run can be non-null on the primary case. My key stays withheld until A9 is registered, code-landed, code-judged, and I re-sign.

### REQUIRED (pre-live, verify-able) — fold into the A9 gate or the §9 GATE
- **R-1 (pin hygiene):** preflight prints run-branch **`5704683`**, not the task's stated pin **`a708523`**. Code is byte-identical (I verified) so science is unaffected, but **pin the run tree to the actual HEAD `5704683`** at run start so the `run_metadata.tree_sha` and the signed SHA match.
- **R-2 (C5 cost/throughput disclosure is thin):** A8.1 acknowledges 3→6 live arms (rate-limit/wall/cost) but does **not** name the unmeasured S4/S3/S0 live-token floors as a *pre-window calibration item*. v1.1 §5.1 [F] floor is S5-only (1,358–1,380 tokens). Require: measure S4/S3/S0 live floors on the first pre-flight live run and record them before the window, with the 60k/arm + 10.8M master + S0 stopping rule stated as the overrun backstop. (Disclosure, not a design change.)

### NON-BLOCKING (record; do not withhold the key on these)
- **N-1 (EP field scope, C2 remainder):** the live `LLMConfig` `max_tokens`/`max_calls`/`timeout` are **enforced by construction** (single `LLMClient()` per run) but are **not recorded** in `run_metadata`, so "same LLMConfig" is *asserted* for those three fields, not *per-run-verifiable* (only `model`/`endpoint`/`temperature`/`harness_seed`/`offline_arm` are). This is within A8.2's declared scope; hardening = write a `config_sha256` into `run_metadata` so a reviewer can re-verify the full config offline.
- **N-2 (ledger granularity):** strategy-arm `budget_ledger.json` uses a single synthetic call (`llm_calls:1`, `completion_tokens:0`) while S5 records real per-call granularity — M5 `totals` is correct, so no metric impact, but it is a fidelity asymmetry worth noting in the report.
- **N-3 (S0/RQ3 symmetry):** S0 shares the same M1-null issue; if left unfixed, P3 "S0 ≤ S5" is trivially always-true (S0 M1≡0). The A9 fix should cover S0 so the RQ3 ablation is interpretable.

I do not assert any competitive score and did not run a live benchmark; the S5=1.0/S4=0.0 numbers above are from the committed **deterministic fixture** and exist to prove the *structural* defect, which is executor-independent.

**SCIENCE JUDGE (round 2, vs code + amendment v1.2 A1–A8): NOT-APPROVE, 2026-10-09.** Key withheld pending A9 (M-1) + R-1/R-2.
