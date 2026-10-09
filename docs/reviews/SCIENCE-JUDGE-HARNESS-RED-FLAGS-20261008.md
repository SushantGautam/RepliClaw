# Science-Judge Adjudication — P08 Red-Flag List (RepliClaw harness)

- **Date:** 2026-10-08
- **Branch / SHA:** `repl-claw-dev` @ `17b37a4` (17b37a42993a99d7570abf4f49d074892ebcc462)
- **Adjudicator scope:** Independent READ-ONLY scientific adjudication of the 7 hotspots in `docs/P08_SCIENCE_VALIDITY_HOTSPOTS.md` (all 7 independently pre-verified real by the orchestrator; this report is the *adjudication* + correction text, not re-spotting).
- **Authoritative sources (committed tree):** `src/repliclaw/eess_live/`, `src/repliclaw/needmarket/`, `src/repliclaw/slice/orchestrate.py`, `src/repliclaw/comparators/managers.py` (HEAD), `src/repliclaw/investigators.py`, `src/repliclaw/p08/score.py`, `docs/`.
- **Ignored per instruction (uncommitted in-progress):** `src/repliclaw/comparators/` (working copy incl. `managers.py`, `runner.py`), `src/repliclaw/strategies.py`, untracked `comparators/case_loader.py`. Where the working copy and HEAD differ (e.g. `managers.py` line numbers), **HEAD is cited**.
- **Method:** Read-only. All controlled numbers below were computed with the repo `.venv` using the scorer's *exact* LCG bootstrap (`score.py:53-79`, seed 20261010, 10,000 resamples) to replicate `score.py:445-467` byte-for-byte. No live LLM API key was used.
- **Prior judge:** `docs/fleet/reviews/SCIENCE-JUDGE-PREREG-P08-2026-10-08.md` (Q1 S3 relabel).
- **Gate source:** `docs/STEER_ACTIVE_ORCHESTRATOR.md` (read-only audit mandate; no bulk live run before independent science approval + human authorization).

---

## 1. Verdict table (7 rows)

| # | Hotspot | Verdict | Severity | Blocks live run? | One-line basis |
|---|---------|---------|----------|------------------|----------------|
| 1 | P1 decision rule (sign reversal + comparator mismatch) | **VERIFIED** | **CRITICAL** | **YES** | Prereg `:34/:194/:211` define a S5 *loss* as success and compare S5 to S3, not S4; scorer `score.py:445-467` encodes both errors. |
| 2 | Post-evidence verdict prompt lacks verified evidence | **VERIFIED** | **HIGH** | **YES** (blocks the RQ1 mechanism question) | `orchestrator.py:445-451` prompt carries no evidence map/run-hashes/observation IDs; the data exists in `build_evidence` `:128-155` but is never injected. |
| 3 | Autonomy framing overstated | **VERIFIED** | MEDIUM | NO (blocks claims, not mechanics) | Hypothesis+arm are pre-assigned (`orchestrator.py:45/:297`, `orchestrate.py:54`) before any LLM output; docs claim open-ended "agents create hypotheses / autonomous trajectory." |
| 4 | S3 comparability (confound) + relabel | **VERIFIED** | MEDIUM | NO (relabel already in D-1) | `managers.py:46/:56` S3 = incumbent RepliClaw protocol (own escrow-like follow-up); `:52` docstring overclaims it "isolates" decentralization. |
| 5 | Matched-cap ≠ equal-consumption; `reference_truth` fallback | **VERIFIED** | **HIGH** (latent M4 leak) | **YES** | `managers.py:192` arm-side read of sealed oracle in committed `EESSArm._verdict`; not on the live S5 path but a committed M4-class oracle read that must be guarded. |
| 6 | Effective-treatment run_metadata gap | **VERIFIED** | MEDIUM | NO (blocks the parity *claim*) | `investigators.py:29-37`/`:84-97` send no `reasoning_effort`/`enable_thinking`; contract `:20` omits `max_tokens` and explicit `reasoning_effort:null`. |
| 7 | RandomPolicy double draw | **VERIFIED** | **LOW** (trace only) | NO | `policy.py:167-168` consumes two independent RNG draws; only `utility` (1st) drives selection; `rng_draw` (2nd) is a mislabeled trace field → affects T4 auditability, not M1-M11. |

---

## 2. Per-hotspot adjudication

### H1 — P1 decision rule (CRITICAL) — VERIFIED

**The P1 hypothesis (comparator = S4).** `docs/experiments/PREREG-2026-10-v1.1.md:33`:
> "P1 (escrow value, RQ1/S5 vs S4). … EESS (S5) matches or beats the open-sharing swarm **(S4)** on the primary metric M1 …"

**M1 polarity (higher is better).** `:169`: M1 = "Fraction of runs whose final verdict matches the sealed oracle … (policy_rag_v1: `retrieval_omission` …)". A fraction of *correct* diagnoses ⇒ **higher is better**. `:181`: "Primary metric: **M1** (S5 vs S4, RQ1)."

**The P1 decision rule (comparator = S3, sign inverted).** `:34` (and, character-identical, `:194` §7.2 and `:211` §8.1 S4):
> "S5 succeeds P1 iff bootstrap 95% CI upper bound of the 10-run interim difference **(S5 minus S3** on M1) is < 0, i.e. the entire CI is below zero; otherwise P1 fails …"

**Two independent defects:**

**(a) Sign reversal (defines a S5 *loss* as success).** For higher-is-better M1, "CI upper of (S5 − S3) < 0" means the whole CI for (S5 − S3) lies below zero ⇒ S5 is *significantly lower* than S3 ⇒ **S5 loses**. The rule names that outcome "S5 succeeds P1." Conversely, when S5 *wins*, the CI upper is ≥ 0, so the rule does **not** fire ⇒ "P1 fails." The success criterion is exactly backwards.

**(b) Comparator mismatch (S3 in the rule, S4 in the hypothesis).** The rule measures S5 − **S3**; the hypothesis, RQ1, and the primary metric all concern S5 vs **S4**. S3 is the *central-arm* comparator of RQ2/P2. Even with the sign corrected, this string tests the wrong pair.

**(c) Internal self-contradiction (success vs falsification).** `:211` (§8.1, row S4) labels the same string as "Counterevidence to our own mechanism … the P1 decision rule fires" — i.e. treats a *firing* as **falsification**, while `:34` says "succeeds P1 iff … fires." On top of the sign/comparator errors, the string is ambiguous about whether it defines success or falsification.

**Scorer encodes both errors.** `src/repliclaw/p08/score.py`:
- `:445-447` — hardcodes `s5m` vs `s3m` (S5 − **S3**).
- `:453-462` — bootstrap CI on that difference.
- `:402-410` — `decision_branch` returns `"improved"` if `lo > 0`, `"worsened"` if `hi < 0`, else `"inconclusive"`. So the scorer's *own* semantic labels ("improved" = CI lower > 0, "worsened" = CI upper < 0) are the **opposite** mapping from the prereg's "success = CI upper < 0." The two are mutually inconsistent; neither is right for the stated P1.
- `:466-468` and `:566` — the bad rule string and a "P1 decision (S5 vs S3)" report header are emitted verbatim.

**Controlled numerical proof** (computed with the scorer's exact LCG, seed 20261010, 10,000 resamples; replicates `score.py:445-467`). Let `literal` = rule fires (CI upper < 0); `corrected` = CI lower > 0; all at n = 10:

| Case | S5 vs S3 | Δ mean | 95% CI (S5−S3) | literal (upper<0) | corrected (lower>0) | `decision_branch` |
|------|----------|--------|----------------|:---:|:---:|---|
| A — S5 **wins** | 8/10 vs 5/10 | +0.300 | (−0.1000, +0.7000) | **No** | No | inconclusive |
| B — S5 **loses** | 4/10 vs 7/10 | −0.300 | (−0.7000, +0.1000) | **No** | No | inconclusive |
| B′ — S5 **loses**, rule **does** fire | 4/10 vs 9/10 | −0.500 | (−0.8000, −0.1000) | **Yes** | No | worsened |
| C — tie | 5/10 vs 5/10 | 0.000 | (−0.4000, +0.4000) | No | No | inconclusive |
| A′ — S5 **wins** decisively | 10/10 vs 6/10 | +0.400 | (+0.1000, +0.7000) | **No** | **Yes** | improved |

Reading:
- **Case A** refutes the task's first illustration *as a "success" trigger*: S5 wins 8/10 vs 5/10, yet the literal rule does **not** fire (CI upper +0.700 ≥ 0) ⇒ the rule reports "P1 fails" for a S5 win.
- **Case B′** is the sign-reversal smoking gun: the literal rule **fires** (=> "S5 succeeds P1") **only when S5 has catastrophically lost** (4/10 vs 9/10). Success is defined as a significant S5 loss.
- **Honest correction to the brief:** the task's second illustration ("S5=0.4, S3=0.7 → fires even though S5 loses") does **not** reproduce at n = 10 under the scorer's exact LCG (Case B: CI upper = +0.1000, so it does *not* fire). My computed numbers supersede that illustration; the *directional* point stands and is in fact stronger — the literal rule can fire *only* on S5 losses, and never on a S5 win.

**Firing boundary of the literal rule (upper < 0), n = 10, full (S5,S3) grid:** fires **only** at (0,4..10), (1,6..10), (2,7..10), (3,8..10), (4,9),(4,10), (5,10), (6,10) — i.e. **S5 far below S3 in every case; never when S5 wins.**

**Firing boundary of the corrected rule (lower > 0):** n = 10 fires only for lopsided wins, e.g. (8,0..3), (9,0..4), (10,0..6); at **n = 20 (final)** it has real power — e.g. S5 = 12/20 beats S3 ≤ 5/20; S5 = 14/20 beats S3 ≤ 7/20; S5 = 16/20 beats S3 ≤ 9/20. This is consistent with the design that the 10-run interim is a *screen* and the 20-run block is the *decision*.

**Direction-sensitive sweep of the whole prereg** (every "upper bound" / "lower bound" / "< 0" / "> 0" / dominance / CI-bound occurrence):

| Line | Text (abridged) | Directionally correct? |
|------|-----------------|------------------------|
| `:34`, `:194`, `:211` | P1 "CI upper of (S5−S3) < 0 = success" | **NO — the P1 rule (sign + comparator).** |
| `:36` | P2 "S3 strictly dominates S5 on both M1 and M9 latency at equal-or-lower M6" | **YES** (see below). |
| `:38` | P3 "Falsified if A1 > S5 or A3 > S5 on M1 (CI lower bound > 0)" | **YES** — difference (A − S5), ablation significantly *better* ⇒ mechanism not load-bearing ⇒ falsified; orientation correct. |
| `:161` | `usage_present < 0.99` (completeness gate) | N/A (completeness threshold, not a directional claim). |
| `:169` | M4 "any count > 0 voids run" (leakage) | **YES** (more leakage = worse). |
| `:146` | "≥41× margin" | Prose (parity), not a directional test. |

**Only `:34/:194/:211` (the P1 rule) carry the sign/comparator error.**

**P2 (line 36) checked for the same class of error.** `:36`: "Falsified if: S3 strictly dominates S5 on both M1 and M9 latency at equal or lower M6 tokens per run." Each leg is a *direct* dominance comparison, oriented to the metric's polarity: S3 "more accurate" ⇒ S3·M1 > S5·M1 (M1 higher-is-better ✓); S3 "faster" ⇒ S3·M9 < S5·M9 (M9 latency lower-is-better ✓); S3 "no costlier" ⇒ S3·M6 ≤ S5·M6 (M6 tokens/correct lower-is-better ✓). P2 uses **no CI-boundary sign**, so it is **not** the same class of error and is **directionally consistent** — no fix required. (Minor observation, not a red flag: P2 is a point-estimate dominance test, not a CI test, so it is less robust to run noise than P1's CI rule; acceptable as pre-registered.)

---

### H2 — Post-evidence prompt lacks verified evidence — VERIFIED

`src/repliclaw/eess_live/orchestrator.py:445-451` (the RESOLVE-phase LLM verdict prompt):
```
prompt = (
    f"{VERDICT_MARKER}\n"
    f"AGENT_ID: {agent_id}\n"
    f"Evidence has been observed for hypothesis {packet.hypothesis_id}. "
    f"Your pre-outcome commitment was: {packet.predicted_outcome!r}. "
    f"Respond with JSON containing conclusion (supported|refuted|uncertain), "
    f"confidence, defect_class, target_artifact, statement."
)
```
The prompt contains **only** `VERDICT_MARKER`, `AGENT_ID`, a *generic* "Evidence has been observed" line, and the agent's **own pre-outcome commitment**. It contains **no** verified evidence map, **no** run hashes / `config_sha256`, **no** `observation_id`, **no** `run_id`, **no** `intervention_id`, **no** measured `severity`, **no** `target_window_days`, **no** artifact hashes. The LLM therefore renders its verdict **without** having seen the data that the hypothesis was meant to be tested against.

The data *exists* and is *verified* just above: `build_evidence` at `orchestrator.py:128-155` (fields at `:133` `observation_id`, `:136` `run_id`, `:139` `intervention_id`/`severity`, `:139-140` `target_window_days`/`config_sha256`, `:151` `config_sha256`, `:153` `artifact_hashes`) — it is simply **never injected** into the verdict prompt. Meanwhile the *outer Python* does read the outcome (deterministic hypothesis outcome at `:488-500` from `run.severity`), and `LocalEigPolicy` re-ranks on the evidence snapshot — so the *preamble* is evidence-driven while the *verdict* is not.

**Claims invalidated / downgraded:**
- **Evidence-driven replanning / verdict claims** — the LLM verdict is *not* causally informed by observed evidence; "the agents look at the evidence and decide" is false for the verdict step.
- **M2 (falsification discipline) verdict fidelity** — a "refuted"/"supported" emitted by a model that has not seen the outcome cannot be credited as evidence-conditional falsification; M2 becomes a measure of prompt-elicited self-labeling, not disciplined falsification.
- **The mechanism story** (RQ1's "escrow → independent commitments → evidence-driven local re-ranking changes the verdict") — the "verdict changes with evidence" leg is not actually exercised by the LLM.

**Minimal amendment-triggering prompt injection (what to add / what must stay out):**
- **INCLUDE** (per agent, for that agent's hypothesis arm) the machine-verified map from `build_evidence`: `observation_id`, `run_id`, `intervention_id`, `severity`, `target_window_days`, `config_sha256` (short), `artifact_hashes` (short). Frame it as *verified public evidence of the run outcome*, plus the agent's pre-outcome commitment (already present) so the model commits-vs-observes.
- **MUST STAY OUT:** the **sealed oracle** — no `true_cause`, no `reference_truth`, no `expected_arm_outcomes`, no oracle path/hash. The injected evidence must be the *arm's own observed severity/target output* (public, arm-side-readable), not the oracle's ground truth. This preserves the M4 invariant (arm-side never reads the oracle).
- **Parity re-runs the amendment requires:** for the same committed forecast, run the arm under **two contradictory *public* evidence views** (e.g. an exposed-severity view vs a masked-severity view, neither using the oracle) at **identical budget / model / settings**; assert (i) the verdict is *reachable* from authentic `run_id`s (no fabricated evidence), and (ii) grep-confirms **no leaked oracle** token in either prompt (M4 re-grep clean). If the verdict does not respond to the (public) evidence, the "evidence-driven verdict" claim remains unsupported and must be downgraded to "evidence-driven *re-ranking*; verdict is model-asserted."

---

### H3 — Autonomy framing overstated — VERIFIED (framing, not mechanics)

What the harness actually does:
- `orchestrator.py:45` `AGENT_IDS = ("alpha","beta","gamma")`; `:297` `hyp = HYP_BY_AGENT[agent_id]` — the **hypothesis is pre-assigned** to each agent *before* any LLM output.
- `slice/orchestrate.py:54` `HYP_BY_AGENT = {"alpha":"H_R","beta":"H_P","gamma":"H_J"}`; `ARM_BY_HYP` maps each hypothesis to a **fixed intervention arm** (`derive.py`). The LLM supplies `hypothesis_statement` / `forecast`, **not** the choice of hypothesis or intervention.
- Re-ranking uses deterministic `LocalEigPolicy` (needmarket), not a free LLM planner; agents loop **sequentially** (`:293`, `:343`, `:441`).

**Strongest defensible claim (use this wording in all hand-in docs):**
> "RepliClaw runs **local, decentralized experiment selection over a frozen, preregistered menu of interventions**, with each agent making an **independent, escrowed pre-outcome commitment**, and performing **local, evidence-driven re-ranking** of which preregistered arms to execute next — within a fixed budget and a fixed case."

**Current docs phrasings that overstate it (must be reworded to the defensible claim):**
- `docs/APPLICATION_V2.md:11` — "decentralized scientific investigation collective," "Agents create competing falsifiable hypotheses," "autonomous evidence-driven coordination." (Hypotheses are pre-assigned, not created.)
- `docs/APPLICATION_V2.md:17` — "locally decide to replicate, falsify, or explore alternatives instead of following a fixed DAG," "never prescribes the research trajectory." (The menu is frozen/preregistered; selection is *over* a fixed menu.)
- `docs/EVIDENCE_ESCROW_SWARM.md:14`, `:24` — "Show at least one observed evidence-induced pivot," and `:47` "Real autonomous decision." (Must be bounded to "evidence-induced re-ranking of a preregistered arm," and gated on the H2 amendment actually producing the pivot.)
- `docs/EXPERIMENT_PROTOCOL_V2.md:7` — RQ3 "autonomous reallocation." (Reallocation is over the frozen menu via deterministic `LocalEigPolicy`.)
- `docs/DEMO_AND_FINAL_HANDIN_V2.md:36` — "autonomous local selection test." (Retitle: "local selection over a preregistered menu.")

---

### H4 — S3 comparability (confound) + required relabel — VERIFIED

`src/repliclaw/comparators/managers.py` (HEAD):
- `:46` `class AdaptiveCentralManager(ArmRunner)`; `:56` `strategy = "repl_claw"` — S3 **wraps the incumbent `RepliClawProtocol`** (its own blind commit/reveal + central adaptive follow-up), i.e. it is *the existing product's protocol*, not a neutral central manager with no escrow-like behavior.
- `:52` docstring **overclaims**: "… so the comparison **isolates** the decentralized-vs-central coordination choice at matched budgets." It does **not** isolate decentralization, because S3 already contains an escrow-like (commit/reveal) mechanism — so **centrality vs. escrow are confounded**.

**What the S5-vs-S3 contrast actually isolates:** "escrow + decentralized re-ranking (S5)" vs. "incumbent central adaptive protocol (S3)." It is *not* a clean "decentralized vs. centralized at equal mechanism" contrast, and it is **not** the P1 estimand (which is S5 vs S4, RQ1). The confounded S5-vs-S3 contrast is the *P2/RQ2* question and must be labeled accordingly.

**Exact required relabel (prior judge Q1; adopted in prereg D-1, `PREREG-2026-10-v1.1.md:74` and `:306`):**
> **"incumbent RepliClaw full protocol (blind commit/reveal + central adaptive follow-up)"** — *not* "a neutral adaptive central manager" — and S3 must run the **same task / case / oracle as S5** (§3.1).

Status: the relabel is **adopted in the prereg** (`:74`, `:306`), but the **code docstring** at `managers.py:52` still says the comparison "isolates the decentralized-vs-central coordination choice." **Fix:** update the docstring to the D-1 label and the "does not isolate; centrality×escrow confounded" caveat, so source and prereg agree.

---

### H5 — Matched-cap ≠ equal-consumption + `reference_truth` fallback — VERIFIED (with path nuance)

**`reference_truth` fallback (committed arm-side oracle read).** `src/repliclaw/comparators/managers.py` (HEAD):
- `:172` `EESSArm._verdict(...)`; `:192` `truth = getattr(claim, "reference_truth", None)` — when the deterministic slice yields **no** determined per-hypothesis outcomes, `_verdict` falls back to reading `claim.reference_truth` (the sealed oracle verdict, `models.py:59` `"supported"|"refuted"|None (benchmark only)`) and maps it to the arm's verdict label. This is an **arm-side read of the sealed oracle**, violating the "arm-side code may never read the oracle" invariant that M4 exists to enforce (`PREREG:169`: "any count > 0 voids the affected run" + stopping rule S1).

**Path nuance (important for severity):**
- The fallback lives in the **offline, deterministic** `EESSArm` (`managers.py:85`), whose `run` calls `run_slice(work_dir/"eess")` at `:125` — a **hardcoded canonical P02 case** (`orchestrate.py` `COST_TOKENS_PER_ARM` / fixed case), independent of the passed `claim`.
- The **live S5 arm is `EESSLiveS5Arm`** (`src/repliclaw/eess_live/arm.py:244`; registered as `"eess"` in `arm.py:265-276` `live_arm_registry`). It does **not** call `EESSArm._verdict`; its verdict is the LLM verdict + deterministic severity-based hypothesis outcome (`orchestrator.py:488-500`).
- **Consequence:** on the **live S5 path scored by `score.py`, the fallback does not fire**, so it does **not** corrupt live M1/M2. It **would** leak M1 only if the offline `EESSArm` comparator were the scored arm.
- **Why it still blocks a live run:** it is a **committed, reachable, arm-side oracle read** in the comparator package. M4 is defined as a *teardown re-grep* of arm-side code/paths for oracle references; a committed `getattr(claim, "reference_truth", ...)` in a `*_verdict` reachable from the comparator runner is exactly the class of artifact M4 > 0 voids and S1 stops the campaign for. It must be eliminated from every reachable arm-side path before live runs, with a negative-path assertion that no arm-side code path reads `reference_truth`/`true_cause`.

**Matched-cap vs equal-consumption.** `score.py` parity re-check (`:430-443`) asserts **identical `envelope_sha256` + no token overrun**. That is a **matched ceiling**, **not** equal consumption. Prereg §5.2 already states this honestly ("does not prove equal consumption"). The residual risk is **report over-claiming** ("equal budget ⇒ equal consumption"). **Fix:** (1) remove or hard-guard the `reference_truth` fallback (raise `ScoreError`/`AssertionError` on any arm-side oracle access) + add the negative-path no-oracle-leak assertion; (2) in the report, state "matched envelope (identical ceiling, no overrun)," never "equal consumption."

---

### H6 — Effective-treatment run_metadata gap — VERIFIED

- `src/repliclaw/investigators.py:29-37` `LLMConfig` = `base_url, api_key, model, max_calls, max_tokens(=4096), temperature(=0.2), timeout`. **No** `reasoning_effort`, `enable_thinking`, `extra_body`, or `model_parameters`.
- `investigators.py:84-97` `chat` sends only `model`, `messages`, `max_tokens`, `temperature`. No reasoning-mode control is transmitted.
- `docs/experiments/P08-ARTIFACT-CONTRACT.md:20` — `run_metadata.json` currently requires: "Tree SHA, seed, model, temperature, endpoint, envelope sha256, start/end wall." **Missing:** `max_tokens` and an explicit `reasoning_effort: null` (or the exact reasoning parameter if/when used).

**What run_metadata MUST record (to make "effective treatment" auditable):** model (exact id), endpoint (`base_url`), `temperature`, `max_tokens`, and `reasoning_effort: null` (or the literal value if a reasoning mode is enabled). Since all arms share the same investigator factory, effective treatment is identical *by construction* — the gap is that you currently **cannot prove it post-hoc**. **Application must NOT claim** a pinned "high" thinking / `enable_thinking` mode across arms (none is set); and note the 4096-completion ceiling can truncate long reasoning → the JSON-retry path (`investigators.py:116`), which is itself an effective-treatment behavior to record.

---

### H7 — RandomPolicy double draw — VERIFIED (LOW / trace-only)

`src/repliclaw/needmarket/policy.py:167-168` (inside `RandomPolicy.rank`, seeded `rng = random.Random(f"{rng_seed}|{agent_id}|{evidence_snapshot_sha}")` at `:163`):
```
utility=float(rng.random()),
components={"rng_draw": float(rng.random())},
```
Two **independent** uniform draws are consumed. Selection is driven by `utility` (the **first** draw) via `_stable_order` sort on `(-utility, need_id)` (`policy.py:77`); `components["rng_draw"]` (the **second** draw) is a **mislabeled trace value** only (surfaced in `worker.py` ranking view).

**Severity:** does **not** affect any preregistered metric (M1–M11) — selection is a deterministic function of `(rng_seed, agent_id, evidence_snapshot_sha)` and remains fully reproducible under a fixed seed. It **does** affect **trace/auditability (T4)**: a reader cannot reconstruct which draw actually selected the arm, and the "rng_draw" field mislabels a non-selected draw. **Fix (minor):** use a single draw and store *that* value in `components["rng_draw"]`, or store both draws with distinct keys (`utility` and `tiebreak`).

---

## 3. VERBATIM corrected P1 decision string (ready to paste into a v1.2 amendment)

```
P1 decision rule (prereg v1.2; character-identical in §2 and §8.1 S4).
Estimand: Δ = M1(S5) − M1(S4), the run-level mean difference in correct-diagnosis
rate (M1, higher is better) between the escrow arm (S5) and the open-sharing swarm
(S4), on the same case/oracle at the matched envelope.
Polarity / null: H0: Δ ≤ 0 (S5 does not exceed S4); favorable direction: Δ > 0
(S5 better than S4).
CI convention: bootstrap percentile 95% CI on Δ, 10,000 resamples, seed 20261010,
run-level within-case resampling (resample run indices independently within each
arm; Δ_b = mean_b(M1,S5) − mean_b(M1,S4)).
Final decision (primary, n_run = 20 per arm):
  P1 SUPPORTED (S5 beats S4)  iff CI_lower(Δ) > 0.
  P1 FALSIFIED (S5 worse)     iff CI_upper(Δ) < 0; the report leads with this
                               falsification per §8.1 and preserves all S5
                               artifacts verbatim.
  Otherwise (CI contains 0):  P1 NOT SUPPORTED; report descriptively
                              (point estimate + 95% CI).
Interim screen (n_run = 10 per arm, first 10 runs): the 10-run 95% CI on Δ is a
screening device only. It supports and falsifies nothing, triggers no stop, no
amendment, and no report change; it is reported solely to monitor whether the
20-run block is tracking toward or away from the decision boundary.
Note on "matches": the hypothesis verb "matches OR beats" is a non-inferiority
claim; this rule (CI_lower(Δ) > 0) certifies only "beats" (superiority, δ = 0).
The "matches" (non-inferiority) half is NOT supported by this rule and, if
asserted, requires a further amendment pre-registering a margin δ (e.g. δ = 0.10)
with the support condition CI_upper(Δ) > −δ.
Fixes vs v1.1: (a) SIGN — "CI upper bound < 0" defined a statistically
significant S5 LOSS as "success"; replaced by CI_lower(Δ) > 0 (support) and
CI_upper(Δ) < 0 (falsification). (b) COMPARATOR — the rule referenced S3 (the
RQ2/P2 central arm); the P1 estimand is S5 vs S4 (RQ1, primary metric, §6). The
S5-vs-S3 contrast belongs to P2, not P1.
```

**Companion code fix (required, else the scored `p1_decision` stays wrong/contradictory):** `src/repliclaw/p08/score.py:445-467` must (1) compute the difference as **S5 − S4** (not S5 − S3), (2) map the CI to support/falsify with `CI_lower(Δ) > 0` / `CI_upper(Δ) < 0`, (3) separate the 10-run *screen* from the 20-run *decision*, and (4) drop the `:566` "P1 decision (S5 vs S3)" header. Re-validate the corrected scorer on the sealed fixtures (including a known S5> S4 and a known S5< S4 case) **before** any live scoring.

---

## 4. Amendment requirements (v1.2), in priority order

1. **P1 rule (H1, blocking):** adopt the verbatim corrected string above in §2 *and* §8.1 S4 (character-identical); fix `score.py:445-467` + `:566`; re-validate scorer on sealed fixtures (S5>S4 and S5<S4).
2. **S3 label (H4):** in *source and* report, relabel S3 to "incumbent RepliClaw full protocol (blind commit/reveal + central adaptive follow-up)" and state the S5-vs-S3 contrast is the confounded P2/RQ2 comparison, not the P1 estimand; fix `managers.py:52` docstring.
3. **Post-evidence prompt (H2, blocking for the mechanism question):** inject the verified `build_evidence` map (oracle-free) into the verdict prompt; run the two-contradictory-public-evidence parity re-runs; assert authentic `run_id`s and no leaked oracle (M4 re-grep clean).
4. **Oracle-read guard (H5, blocking):** remove or hard-guard `managers.py:192` `reference_truth` fallback; add a negative-path assertion that no arm-side path reads `reference_truth`/`true_cause`; report "matched envelope," never "equal consumption."
5. **Effective treatment (H6):** extend `run_metadata.json` (contract `:20`) to record model, endpoint, `temperature`, `max_tokens`, and `reasoning_effort: null`; do not claim a pinned thinking mode.
6. **Autonomy wording (H3):** reword the five cited doc passages to the defensible "frozen-menu local selection + independent escrowed commitments + local evidence-driven re-ranking" claim.
7. **RandomPolicy draw (H7, minor):** single consistent draw (or two distinct-labeled draws) for T4 trace integrity.
8. **Two-key start:** independent judge sign-off on the v1.2 amendment **before** any live outcome, then human authorization (per `STEER_ACTIVE_ORCHESTRATOR`).

---

## 5. READINESS gate (which findings block any live run)

**HARD BLOCKERS — fix + sign off BEFORE any live run:**
- **H1 (P1 rule + scorer):** the decision rule the campaign is scored against is sign-inverted and compares the wrong pair; the scorer hardcodes the same errors. Running live now and scoring against this rule yields an invalid primary decision. *(prereg `:34/:194/:211`; `score.py:445-467`)*
- **H5 (arm-side oracle read):** a committed, reachable `getattr(claim, "reference_truth", …)` in `EESSArm._verdict` (`managers.py:192`) is an M4-class oracle leak. M4 > 0 voids the run and stopping rule S1 halts the campaign, so it must be eliminated from every reachable arm-side path (with a negative assertion) before live runs. *(Note: it does not fire on the live S5 path — `EESSLiveS5Arm` — but it is committed comparator code and a teardown re-grep target.)*

**SOFT BLOCKER — blocks the scientific question (spend no live budget on a mis-specified experiment):**
- **H2 (post-evidence prompt):** as-is, the LLM verdict is not evidence-informed, so the run would not answer RQ1's mechanism question and the evidence-driven-verdict / M2-fidelity claims would be false. Amend the prompt and pass the parity re-runs first; otherwise the live run is measuring a different, weaker thing.

**NON-BLOCKING — fix before the report/hand-in, do not block run mechanics:**
- **H3** (reword autonomy claims), **H4** (enforce S3 relabel; already in D-1), **H6** (record run_metadata; arms share one factory so effective treatment is identical by construction — this is an *auditability* gap, not a confound), **H7** (trace-only draw fix).

## 6. GO / NO-GO for bulk live runs

# **NO-GO**

Bulk live runs are **not** authorized. Blocking conditions, in order:
1. Issue **prereg v1.2** with the verbatim corrected P1 string (§3) and **fix + re-validate** `score.py:445-467` on sealed fixtures.
2. **Eliminate/guard** the `managers.py:192` arm-side `reference_truth` read and add the negative-path no-oracle-leak assertion.
3. **Amend the post-evidence verdict prompt** (H2) and pass the two-contradictory-public-evidence parity re-runs.
4. **Independent judge sign-off** on the v1.2 amendment, then **human authorization** (two-key start) per `STEER_ACTIVE_ORCHESTRATOR.md`.

A positive, a tie, and a negative P1 result must all be reported once the run proceeds; the run must not be stopped or respecified on the 10-run interim (screening only). Until 1–4 are complete, any live outcome would be scored against a broken rule and/or measured against a mis-specified prompt, and the harness carries a committed latent oracle-read — **NO-GO**.
