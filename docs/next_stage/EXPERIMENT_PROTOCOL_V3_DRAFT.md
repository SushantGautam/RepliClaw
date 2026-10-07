# V3 DRAFT — externally benchmarked intervention-matched RepliClaw experiments

Status: **PROPOSED, NOT PREREGISTERED, NOT APPROVED FOR LIVE CAMPAIGN**; prepared 2026-10-09. A frozen, timestamped V3 + independent Science-Judge sign-off + explicit human authorization are mandatory before holdout/live experiments. P08 files and measurements remain immutable; do not revise old P08 results.

## Primary causal question and estimand (interactive track I)

For independent fault scenarios (not repeated model rolls on one case), at a fixed per-case action/token/time/intervention **cap**, compare:
- **D-E (RepliClaw)**: decentralized investigator choice + independent pre-outcome escrow + shared verified observations.
- **C-EQ (intervention-matched adaptive centralized manager)**: an honestly strong central planner coordinating the same number of investigators and same permissible diagnostic/intervention tools, including adaptivity after each observation; no artificial fixed script.
**Primary estimand:** case-level paired difference in successful root-cause diagnosis, D-E minus C-EQ, aggregated with equal case weighting. Failed or abstained trials count as non-success for the primary ITT metric. Run-level seeds are nested within cases; case—not sample rollout—is the unit for CI/generalization.

**[AMENDED 2026-10-10 — A5/D-V3-007: no access-claim drift.]** Results may claim **capability differences** (selection/coordination, escrow effect on diagnostic quality) — they may **never claim dataset-access advantages**; live mitigation problems give ALL arms full causal access, and P08's access mechanism does not transfer to track-I and must not be cited as transfer evidence.

**Decision rule to freeze BEFORE heldout:** meaningful positive if a paired cluster bootstrap 95% CI of the per-case difference lies entirely above zero; otherwise not established. This is a design proposal, NOT a currently established victory. Report effect and interval regardless. Pin bootstrap RNG/replicate count before final. Specify multiplicity approach for any co-primary outcomes; all others descriptive or multiplicity-adjusted. Do not claim a powered null-equivalence test without preplanned equivalence margin/power.

**[AMENDED 2026-10-10 — A1/D-V3-008: minimum-effect floor, freeze candidate, NOT yet frozen (G4 pending).]** The verdict "MEANINGFUL_POSITIVE" is a tier, not a binary, and the minimum effect floor is fixed at freeze as: **Δ_min = 0.15 absolute per-case success difference.** Exact freeze wording (to be adopted verbatim at G4, subject to Science-Judge + statistician sign-off): *"A heldout is scored MEANINGFUL_POSITIVE iff the paired cluster-bootstrap 95% CI of the per-case difference (D-E minus C-EQ) lies entirely above zero AND the point estimate is at least Δ_min = 0.15 absolute per-case success difference. If the CI lies entirely above zero but the point estimate is below 0.15, the verdict is POSITIVE_SUBTHRESHOLD. If the upper CI endpoint is below −0.15, the verdict is HARM_SIGNAL and may be reported as a true harmful finding. Otherwise the verdict is NOT_ESTABLISHED."* The 0.15 floor is justified by the MC power grid (D-V3-008 / `science/monte_carlo_power_v3.md`: at Δ=0.15 the design is under-powered anyway — 0.615 at k=4 — so the floor does not exceed what the design can resolve; below 0.15 the S-sat rule, not the CI, is the operative guard). The grid's `rule_a1` variant was simulated at Δ_min=0.10; if the frozen value 0.15 is held, the `rule_a1` variant must be re-run at 0.15 before freeze so the prereg cites the exact variant. The earlier proposed default of 0.10 (D-V3-007) is a **superseded candidate**, retained for the record.]

## Secondary mechanism arms (all can intervene in track I)

- **D-N**: same decentralized action/selection policy but no escrow (pass-through).
- **D-R**: escrow intact but random admissible next-test selection (seeded), subject to identical constraints.
- **C-NE**: centralized manager without escrow, standard strong baseline; C-EQ by default uses best-performing fair central protocol and the same observational timing; do NOT impose artificial escrow on central just to make names symmetrical.
- **S-I**: strong single investigator, can run same causal tools; tokens/tool-call cap equal, note parallelism as an intrinsic architectural effect.
- Optional **C-OracleSelection** (upper-bound selection-only diagnostic) NOT leaderboard entry and NEVER allowed oracle during a primary run; may be computed only in evaluator after all runs.
- **No-intervention** arm is explanatory only, NOT the main fairness comparator; label it explicitly as mechanism-access contrast.
- **CAR** replay comparator only when faithful replay semantics, action set and outcomes are genuinely identical; otherwise report a separate CAR protocol.

Main hypotheses: H1 D-E improves case-level root-cause success vs C-EQ; H2 D-E vs D-N changes false consensus, independent forecast disagreement and detection/recovery on ambiguity; H3 D-E vs D-R improves verified information gain / causal discrimination per intervention; H4 D-E vs C-EQ improves efficiency or cost-to-quality under comparable ceilings. H1 is primary; freeze metric names, denominators and signs. Negative/null results fully acceptable.

## Benchmark tracks: do not mix estimands

### O-A: AgentRx observational generalization
- Use the released dataset labels for critical-step localization and released taxonomy category, not five-way P08 labels.
- Reproduce original AgentRx first where permitted, plus same-model zero-shot/CoT prompting, trace-only strong central and RepliClaw's multi-investigator observational variant.
- No executable intervention => RepliClaw escrow/selection mechanisms can be measured as process, **cannot** claim benefits from counterfactual execution or head-to-head causal control.
- Register exact accessible subset; official HF microsoft/AgentRx requires human click-through access; paper 115 trajectories may not equal any mirror; document coverage. Evaluate classification + critical-step accuracy with official scripts if present and inspect annotation agreement and inconclusives.
- Do not use test labels in adaptive prompts; no benchmark item IDs in prompts if they can retrieve published answers.

### O-R: RCAEval observational transfer
- Original official root-cause service/fault indicator and ranking top-k, Avg@5 where applicable. Use original evaluator and run at least one named official RCA baseline (BARO or suitable multi-source baseline) with *the same cases*.
- Start with a **stratified representative pilot** across service, fault type and microservice system; selection manifest frozen before reading labels. Then expand to multiple systems/suites to assess generalization.
- Dataset is recorded fault-injection telemetry; running code over traces does NOT mean counterfactual experiment on that historical incident.
- Telemetry quotas, context windows and retrieval must be matched. Different access modalities (metrics-only vs logs+traces) are separate subtasks.
- **[AMENDED 2026-10-10 — S1/S4/S7: heldout disclosure block (candidate heldout: 42-case RCAEval, reps 1–2).]**
  - **(a) Ground-truth stratification gate (C-SCI-1, G4 blocker):** `root_cause_service` was used **only to define the heldout quota pre-experiment** (stratification at selection time, frozen 2026-10-09); at runtime it is **scorer-only**. Agents never receive the heldout manifest, `strata`, or any on-disk `root_cause.txt` ground-truth file while solving; those are gated to scorer-only access at G4.
  - **(b) Opaque case IDs (honest caveat, cannot be fixed upstream):** upstream RCAEval case IDs embed the root-cause service (e.g. `re1ob_adservice_mem_1`) and data files are named by case id. The V3 runtime MUST present **opaque random case ids** to agents and keep upstream ids evaluator-side only.
  - **(c) Selection disclosure (S4):** the candidate heldout covers **repetition 1–2 only** (lowest reps per service — a possible easy-within-stratum bias) and **Train-Ticket is absent** (Online Boutique + Sock Shop only). It must NOT be presented as "stratified across all reps/systems."
  - **(d) Smoke ordering disclosure (S4):** the 10 BARO smoke cases were run **before** the quota table was finalized (smoke precedes the 2026-10-09 freeze; the 10 smoke ids have 0 overlap with the 42-case candidate set per J-SCI S9 — disclose this ordering and the 0-overlap, do NOT re-run). **No tuning has been done against those 10 smoke cases; the candidate heldout stays untouched by any tuning**, and the exploratory pilot must run on cases segregated from these 42.
  - **(e) C-EQ adaptivity disclosure (S5):** C-EQ's adaptivity is **on machine-verified evidence only** (round-N planner prompt rebuilt from all machine-verified evidence of earlier rounds + sealed forecast line + budget-so-far); there is **no investigator-feedback loop** (the 3 investigator findings are collected once, post-loop, and inform only the final diagnosis). C-EQ's union evidence view (all hypotheses' verified evidence + baseline vs D-E's per-hypothesis view) is a **designed, volume-bounded central advantage, not parity**: wherever any document (e.g. `design/ceq_arm_design.md` §5.3, which says the manager "contains exactly the same set of `evidence_id=` lines") describes the manager's evidence view as "exactly the same set" as a D-E investigator's, the operative wording is **"a superset of, volume-bounded against"** the D-E investigator's set.

### I: AIOpsLab executable counterfactual diagnosis
- Choose only built-in registered detection/localization/diagnosis problems with documented labels/evaluators. Reuse official Orchestrator; do not invent truth labels.
- **[AMENDED 2026-10-10 — A2/D-V3-007: Track-I scope is explicitly "OFFLINE-FIXTURE ONLY"** until the live action-set manifest is frozen. No live AIOpsLab run and no G2 pass for Track-I before the manifest exists. The frozen live action-set manifest MUST contain: (1) the **admissible action list** (every action any arm may execute, per problem), (2) **max_steps** (per-arm step cap), (3) the **escrow-selection → action mapping** (how an escrowed selection maps to a concrete admissible action), and (4) a **reset digest** (deterministic-equivalent restart/snapshot digest proving per-arm reset to identical state). Until it is frozen, all Track-I claims are offline-fixture only; J-SCI W1 verified no live environment was touched by Wave 1.]
- **Feasibility barrier:** prove deterministic-equivalent restart/snapshot, independent isolate per arm, replay observation fidelity, ability to run controlled alternative interventions safely, per-arm identical interface, and evaluator oracle not agent visible. AIOpsLab supplies injection but does NOT automatically guarantee meaningful reversible causal replay for any specific problem.
- **[ADDED 2026-10-10 — J-SCI W2 S-W2-7: step semantics of max_steps=20.]** max_steps=20 is the per-episode step count in `Orchestrator.start_problem`, identical for both arms; how each arm's internal structure maps agents/rounds onto the 20 episode steps is arm-policy (part of the treatment), bounded identically by the 20-step loop and the shared `BudgetEnvelope`; the G2 budget-cap canary asserts the 20-step loop, not per-agent allocations.
- Intervention matching means matching **available action vocabulary, authorization, max number of tests, environment reset state, cumulative compute budget, information timing and simulator access**; not forcing both strategies to choose the same intervention in every run (selection is the treatment). Add a separate **fixed evidence tape** test for pure aggregation/escrow effects: same intervention results disclosed to all arms in a randomized standardized order.
- Capture observed output changes + unchanged-input/byte identity controls; separate correlations from causal claims when assumptions fail.

## Scientific design

- Candidate **pilot**: 6–10 independent cases with 2 seeds each; ~4-6 arms; pilot is for feasibility/variance, **not confirmatory**. No "p < .05" claims from pilot; pilot cases segregated from final case-level test.
- Candidate **heldout**: target ≥24 distinct cases across ≥3 fault families and ≥2 systems with 2–3 predeclared seeds per case, if attainable. These are **planning targets not commitments or power proof**; independent statistician to estimate variance/power from pilot (not test), choose feasible target and lock exact N.
- **[AMENDED 2026-10-10 — D-V3-008: MC power statement + S-sat stop rule.]** Power authority is the Monte-Carlo simulation of the frozen percentile bootstrap (`science/monte_carlo_power_v3.md`, 254 cells × 10,000 reps, SIMULATION-ONLY until re-run with pilot-estimated σ̂_D **before prereg freeze**). **Recommended heldout design: N = 24 cases × k = 4 seeds/case, MDE = 0.20** (~0.839 MC power at N=24, k=4, mid between-case variance; k=2 reaches only 0.556; MDE 0.15 is NOT achievable at N=24, k≤4 — needs N≈55 per the quadratic fit, an interpolation, so the prereg must cite direct grid cells for the operative MDE and use the fit only for interpolation). If the human-approved budget cannot cover k=4, MDE must be re-scoped to 0.20, not silently kept at 0.15. Type-I at Δ=0 measured 0.026 (≤ 0.05, conservative).
  - **Mandatory S-sat stop rule** (supersedes the judgment trigger): if at **either arm** saturation ≥ **25% of PILOT cases**, STOP and re-stratify before any heldout run (one-arm saturation at true Δ=0 fires MEANINGFUL_POSITIVE ~83% of the time at s=0.5; joint two-arm saturation erases the contrast). **The saturation fraction must be disclosed in every result report.**
  - The prior two-sided normal-approximation power formula of `statistical_protocol_v3.md` §4.2 is **SUPERSEDED** (retired per D-V3-008; wrong by ~3.4× in the 0.15–0.20 region — it uses between-case σ ≈ 0.18 vs measured effective σ_d ≈ 0.44): ~~N ≈ 7.85 · σ²_D / MDE² (two-sided α=0.05, 80% power, normal approximation — `statistical_protocol_v3.md` §4.2)~~ — retained struck-through, not deleted (no retroactive rewriting). It survives only as a labeled planning heuristic; MC simulation of the frozen one-sided rule is the sole power authority. The in-file strike-through in `statistical_protocol_v3.md` §4.2 itself requires an edit outside this worker's allowed file set — flagged in the amendment doc. **[ADDED 2026-10-10 — orchestrator W2m: this conflict is now RESOLVED — the in-file `~~…~~` SUPERSEDED marker has been applied in `statistical_protocol_v3.md` §4.2; see `amendments_AMEND_V3_FREEZE_20261010.md` §4 item 2.]**

**[ADDED 2026-10-10 — J-SCI W2 S-W2-1: model-capability floor gate]**

S-sat (above) guards only the *ceiling* (an arm saturating at 100%). The floor is now guarded by an equally mandatory dual stop rule:

- **(a) Dual stop rule (floor gate + ceiling gate — both mandatory, one does not replace the other).** The floor gate is checked **at pilot scale AND as a running canary during the heldout**. It TRIPS if **EITHER arm** has **< 2/20 run-level successes** (pilot scale: 10 cases × 2 seeds) **OR per-case all-seeds success = 0 on ≥ 9/10 pilot cases** (heldout-scale canary: per-case all-seeds success = 0 on ≥ 6/24 heldout cases, checked at the 6-case (25%) heldout-canary checkpoint, consistent with the S-sat canary cadence). On trip: **STOP** — classify the campaign state **MODEL-CAPABILITY-SCREEN-FAILED**; **do NOT launch or continue the heldout on that model**; report the negative result with the saturation evidence (per-arm run-level success, per-case all-seeds success table, floor-gate numbers). This is a model-capability screen, not a stratification problem: re-stratification does not remedy floor saturation. The ceiling S-sat ≥ 25% rule above and this floor gate are **both mandatory**; a verdict is only admissible if neither gate tripped.
- **(b) Pre-freeze model-capability screen disclosure (evidenced, no new numeric claims).** Expected run-level success of Qwen3.8-27B on this telemetry class is **low-to-moderate and must be treated as the risk case** (J-SCI W2: "the more likely outcome of the heldout" under this model). Evidence available at pre-freeze time: (i) the **real W2g SimulaChat smoke** — 2 tau trajectories, **1/2 root-cause correct** (~21.4K tokens; every artifact labeled MODEL-SUBSTITUTION, not the official baseline): `stg2-worktrees/w2-simula/.artifacts/agentrx/simula_tiny_smoke/` (`summary.json`: "Correct cases": 1, "Incorrect cases": 1), as recorded in `docs/next_stage/EXECUTION_STATE.md` (Wave-2 I2 table, W2g row) and `docs/next_stage/design/g3_pilot_spec_draft.md` §3 (token figure); (ii) **P08 live campaign** on the same model (`docs/experiments/P1_RESULT_STATEMENT_20261009.md`: 120 runs, 6 arms × 20, sigma2 Qwen3.8-27B, single case `policy_rag_v1`): intervention arms S5/A1/A3 M1 = 1.000 (ceiling-saturated on an intervention-enabled retrieval case), S3 = 0.050, S4 = 0.200, S0 = 0.150 — i.e., this model's non-intervention RCA performance on a curated case was 0.05–0.20, and the intervention arms' 1.000 is a ceiling artifact of a single easy intervention-identifiable case (the statement's own counterevidence items 1 and 5), not evidence of general RCA competence. **Contingency (frozen):** if the floor gate trips at pilot, the authorized fallbacks are **(i) re-scope** to the narrower claim restricted to cases where the model demonstrably performs above the floor, **or (ii) request a human decision** on a stronger model. **Never silently switch models mid-heldout**; any model change is a protocol violation requiring versioned amendment + re-freeze, and results of a model whose floor gate tripped may only be reported as BLOCKED_ON_MODEL_CAPABILITY / MODEL-CAPABILITY-SCREEN-FAILED with the screen numbers.
- **(c) Results-section conditioning — mandatory verbatim language for every V3 result report (see "Results-reporting: model-conditioning" section below; adopted from J-SCI W2 verdict 2.5 items 1–3).**
- Blocking/randomization: paired strategies run same case+seed and frozen upstream scenario; counterbalance execution order and isolate namespaces/workspaces; no shared cache, messages, oracle, directories or mutable service state. Record randomization order and reruns.
- Leakage: evaluator-only answers encrypted/isolated or stored outside agent context; scan prompts/retrieval/tools/artifacts. Benchmarks may be in training data, so measure contamination risks, not assert perfect secrecy.
- **Cost accounting**: total tokens (input/output/cached, where known), provider billable tokens, tool invocations, intervention count and cost, total GPU/CPU seconds, wall clock, queueing, recovery cost. A cap is NOT equal spend; include accuracy-at-cost and tokens-to-correct-conclusion curves.
- **Timeouts and failures**: pre-register unambiguous abort/error/abstain handling; include failures in ITT denominator, optionally report clean-run sensitivity separately; keep retries bounded and auditable.
- **Statistical analysis**: equal weighting by independent case; paired differences by case+seed, cluster bootstrap over cases with all seeds attached, confidence intervals. No run-level bootstrap as generalization claim; stratified faults/domains as predeclared; report raw case-level predictions and confusion matrices, practical significance, abstention and negative findings.
- **Falsification and calibration**: count correct refutation across *multiple* unsupported hypotheses/cases (avoid P08 near-vacuous denominator=1); record pre-outcome test forecasts and proper Brier score only where probabilistic, otherwise report hit rate honestly.
- **Scientific process**: quantify actual evidence-induced policy pivot, independent agent diversity, false-consensus, evidence sharing, experiment coverage, causal discrimination vs random/EIG, and treatment leakage.
- **No hindsight fixes**: failed metric definitions trigger transparent versioned amendment with severity/sign-off; do not tune prompts/scorers after observing heldout outcomes.

## Results-reporting: model-conditioning (mandatory language)

**[ADDED 2026-10-10 — J-SCI W2 S-W2-1(c): results-section conditioning, required verbatim (or equivalent) in the prereg itself.]** Every capability comparison in this campaign is conditioned on the arm model (SimulaChat default = Qwen3.8-27B, D-V3-010; external-baseline comparisons additionally carry the mandatory MODEL-SUBSTITUTION label, never presenting as the official released baseline). A NOT_ESTABLISHED verdict is reported as model-conditioned, and when the S-W2-1 floor gate trips it is reported as a **MODEL-CAPABILITY-ARTIFACT** (BLOCKED_ON_MODEL_CAPABILITY with the screen numbers) rather than an absence-of-effect. No cross-model generalization claims are made from this campaign: "MEANINGFUL_POSITIVE under this model" means the winning arm outperforms the other arm on Qwen3.8-27B at pilot-verified competence level, and generalization to stronger or frontier models is explicitly out of scope (hypothesis-generating only).

## Standardized outputs and evaluator contract

Canonical per-case outputs must preserve original labels and original benchmark evaluator; add an additive RepliClaw metadata sidecar without replacing official benchmark score. At minimum:
- benchmark/version/sha/license/source/split, case ID, domain/fault family, oracle ref (evaluator-only), strata
- model exact ID, serving config, temperature, seed, endpoint provider alias (NO credentials), prompt SHA, git SHA
- strategy, intervention executor and allowed action schema hash, budget cap and actual spend, concurrency, case reset hash
- per-agent commitments/hypotheses, shared evidence events, intervention choices + valid responses, decision/recovery timestamps
- diagnosis + uncertainty + abstention + root-cause rank where supported, validation receipts
- status/errors/retry history and reasoned negative results
- official metric score, novel secondary metrics and case-level paired score by independent sealed scorer

Test invariants before any holdout: same action schema and executor for D-E vs C-EQ, same budget/concurrency, scorer blind to arm and inaccessible during run, no preloading gold in prompts, reset stability, controlled error case, all outputs idempotent and resume safe. Fixtures ≠ real measurements.

## Execution governance and honest stop rules

G0 upstream contract/access/license review approved; G1 benchmark's own evaluator/strong baseline runs successfully; G2 intervention-matching and oracle-isolation canaries pass; G3 pilot and independent review pass; G4 V3 prereg frozen + science key APPROVE + explicit human key for exact benchmark/arms/N/model/spend; G5 heldout scored only at permitted step; G6 independent Code/Science judges review counterevidence and claims; G7 public release only by public-readiness gate.

If G1/G2 fail, **STOP that track** and document blocker; keep work in independent tracks. No "just simulate it" replacement inside an external-benchmark result. Never silently downgrade to unverified synthetic cases. No full live campaign, paid cluster deployment or >pilot token spend without explicit human authorization.

## Reproducibility procedure

1. Pin source versions, contracts and baseline commands; save manifest (no dataset leakage into git).
2. Build read-only adapters and sealed evaluator; write canary integration tests.
3. Produce one reproducible official baseline case and one cross-strategy parity case with independent review.
4. Run strictly bounded pilot; freeze revised prereg/holdout and obtain two keys.
5. Run paired heldout matrix, separately monitor execution integrity without inspecting interim advantage.
6. Score with canonical evaluator; publish all failure cases and uncertainty; if H1 unsupported, pivot questions rather than fabricate success.

## Relation to previous stage

P08 documents remain historically valid; **DO NOT** overwrite P08 score, silently change prereg v1.2, relabel previous P1 as proof of decentralization, or conflate a 120-rollout *single case* with 120 independent cases. This protocol creates **new prospective estimands** and independent results.

## FROZEN-CONSTANTS appendix

**[ADDED 2026-10-10 — amendment AMEND_V3_FREEZE: constants to be frozen verbatim at G4. G4 is PENDING — no human approval has been given; this appendix records the freeze candidates only. Any drift from these values after freeze is a protocol violation requiring versioned amendment.]**

| Constant | Value | Source / verification |
|---|---|---|
| Bootstrap replicates B | 10,000 | `statistical_protocol_v3.md` §2.2 (L5); MC grid §1.1 |
| Bootstrap RNG seed | 20261009 (`numpy.random.default_rng`) | `statistical_protocol_v3.md` §2.2; MC grid §1.1 |
| Bootstrap RNG engine | PCG64 | `statistical_protocol_v3.md` §2.2 |
| CI percentile | 95% (percentile method) | `statistical_protocol_v3.md` §2.2 |
| C-EQ planner prompt static tail sha256 | `4df178e5124b8660033769aceb158c065151ebae2a8cacf20f209500821513dc` | `tests/experiments/test_v3_ceq_parity.py::test_canary_templates_pinned` (`ceq.PLANNER_PROMPT_STATIC_TAIL`) |
| C-EQ final-diagnosis prompt static head sha256 | `11150fa2b11206143ab1eee5b1d54efc28ae685e27f354ef733d3bb8984d0bcf` | same test (`ceq.FINAL_DIAGNOSIS_STATIC_HEAD`) |
| C-EQ final-diagnosis prompt static tail sha256 | `45e7ab3c2111395d9522e14da6855e9cf0171f4a391ac176ffa246bd88c9aa85` | same test (`ceq.FINAL_DIAGNOSIS_STATIC_TAIL`) |
| C-EQ prompt-volume canary band | [0.6, 1.25] (two-sided; floor 0.6 per code and tests — the `[0.8, 1.25]` module docstring was corrected to 0.6 in I1.1 per J-CODE F3/J-SCI S3; if 0.8 was intended, the constant and test must change before freeze). **[RECORDED-DECISION 2026-10-10 — orchestrator, on J-SCI W1 evidence, conflict #3 RESOLVED: floor stays 0.6.]** The 0.6 floor is a fair parity constraint, not a handicap: it is two-sided (bounded by the 1.25 ceiling) and constrains C-EQ's manager prompt volume *against D-E's TOTAL volume*, calibrated against the sha-pinned C-EQ templates above, so D-E does not win by default and C-EQ is not disguised under-invested. J-SCI W1 (S3 verdict) assessed the floor as "a fair parity constraint, not a handicap: … D-E would not win by default."
| L5 `cluster_bootstrap.py` sha256 | `e14d28add0ceb27bdef73daab268bf07041bd857d34ebd477e2793e0aa96258c` | `science/monte_carlo_power_v3.md` §7 (scratch `stg2-worktrees/statistics/`; repo pin at G3 per C-SCI-2) |
| L5 `monte_carlo_power.py` sha256 | `929d6fe99aed470080beb6df344e11b734e97e0ac44d9036bcc3abbd6844662a` | same |
| RCAEval `data/cases.parquet` sha256 | `c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb` | verified by `shasum -a 256 data/cases.parquet` in the dev worktree, 2026-10-10 (W2e) |
| RCAEval `download_manifest.json` sha256 | `bffa99801535a029ec6bb5cbc65a2e99e4fe4747514ee7787254133b9e899812` | verified by `shasum -a 256 .artifacts/rcaeval/download_manifest.json`, 2026-10-10 (W2e); pins 142 input files (J-SCI S9) |

