# Science Judge — Wave 0 Review (G0 gate), 2026-10-09

**Judge:** J-SCI (independent Science Judge, review-only; wrote none of the reviewed work)
**Worktree:** `/Users/sushantgautam/Documents/RepliClaw-stg2-dev` @ `a8e2b0e` (branch `dev`)
**Scope:** `docs/next_stage/science/statistical_protocol_v3.md` (v3-draft-0), `docs/next_stage/design/ceq_arm_design.md`, `docs/next_stage/adapters/{agentrx,rcaeval,aiopslab}_contract.md`; cross-checked against `docs/experiments/P1_RESULT_STATEMENT_20261009.md`, `docs/reviews/SCIENCE-JUDGE-CAMPAIGN-RESULTS-20261009.md`, and sibling drafts `EXPERIMENT_PROTOCOL_V3_DRAFT.md`, `LITERATURE_AND_BENCHMARK_DECISION.md`.
**Posture:** adversarial. This is the gate that prevents a weak study.

---

## VERDICT: **APPROVE-WITH-CONDITIONS**

The Wave-0 package is scientifically disciplined in ways that matter: the P08 negative
finding (access, not escrow/decentralization, drove the effect) is preserved *verbatim in
spirit* in every document reviewed; the estimand is case-level paired with seeds nested;
observational and interactive tracks are explicitly separated; no document fabricates a
measurement. None of the documents recasts P08 as evidence for decentralization, escrow,
or autonomy — verified by directed scan, see §6 (finding F12).

However, the package is **not yet G0-frozen-ready** because (a) the *live* (track-I)
estimand is not fully specified — "intervention" has a defined meaning on the frozen
`policy_rag_v1` fixture but **no defined provenance in the AIOpsLab live environment**
(F2, the largest gap); (b) the primary decision rule's *name* exceeds what its *formula*
guarantees (F1); (c) the power calculation contradicts its own one-sided decision rule
(F3); and (d) C-EQ has residual parity holes a hostile reviewer will exploit (F4–F6).
All conditions are fixable before G2; none requires redesign.

---

## Findings table

| # | Severity | Doc / section | Scientific risk | Required correction |
|---|---|---|---|---|
| F1 | **HIGH** | `statistical_protocol_v3.md` §2.3 + §3 (verdict naming) | Verdict string `MEANINGFUL_POSITIVE` is triggered by CI lower bound > 0 with **no minimum-effect floor**. A true case-success advantage of 0.01 with CI [0.01, 0.09] yields the headline positive verdict. The name promises a practical-effect claim the rule does not test; a future reader (or committee) will read "MEANINGFUL" as "≥ predeclared MDE". This is the classic route by which a statistically real but practically empty result is dressed as a positive. | Either (a) rename the verdict to `POSITIVE` / `NOT_ESTABLISHED` and reserve the word "meaningful" for a secondary statement; or (b) define the decision as *lower bound > 0 AND point estimate ≥ MDE_floor* with `MDE_floor` predeclared at freeze. Additionally: when the point estimate is ≤ −MDE (D-E *worse* than C-EQ), the current rule still returns "not established", and §2.3 **forbids** the word "negative". A genuinely harmful effect would be reported as neutral. Add a predeclared `HARM_SIGNAL` annotation (point estimate ≤ −MDE, always reported, decision-gating only via disclosure) so a negative can never be dressed as a null. |
| F2 | **HIGH** | `statistical_protocol_v3.md` §1/§6.3 (action-vocabulary hash) + `ceq_arm_design.md` §8 (AIOpsLab out of scope) + `EXPERIMENT_PROTOCOL_V3_DRAFT.md` track-I | The primary estimand is "successful root-cause diagnosis" with equal case weighting, but the *mechanism under test* (interventions) is only concretely defined on the offline `policy_rag_v1` fixture (registered `I0…IC` suite via `load_interventions`). On AIOpsLab the agent-visible action space is a raw shell/command API (`exec_shell`, kubectl, app ops). The docs do not specify: (i) the per-case **admissible action/intervention set** for the live track and its freeze/hash mechanism (the prereg template references an "action-vocabulary hash" with no filled meaning); (ii) how D-E's escrow *intervention selection* maps onto that space (registered suite per case, or open action grammar?); (iii) the step/action *count* budget (AIOpsLab's `max_steps` is not frozen by any Wave-0 doc); (iv) how "pre-outcome sealed forecast" + "verified observation" generalize when the agent probes a live system whose state is itself the evidence. Without these, the "intervention-matched" claim is a shell, and the D-E-vs-C-EQ contrast could be re-contaminated by *differences in what counts as an intervention*. This is the single biggest route by which the study silently tests something other than its stated estimand. | Before G2: a **per-case action-set manifest** for track I (allowed actions, authorized effects, count cap, reset-state signature, information-timing rules), frozen + hashed in the prereg; an explicit mapping of the escrow selection mechanism onto that manifest for *both* D-E and C-EQ; and a one-page *estimand note* for track I stating exactly what "intervention" means on a live system and why the P08-style access asymmetry does **not** silently re-enter (see F10). |
| F3 | **MEDIUM** | `statistical_protocol_v3.md` §4.2 | The power formula uses **two-sided** `z_{1−α/2}` (1.96) and a normal approximation, while the frozen decision rule (§2.3) is **one-sided** (CI lower > 0). §2.2 even justifies the percentile choice by saying "the decision rule is one-sided". Using the two-sided constant understates the N derivation for the actual one-sided rule, and the normal approximation mis-states power for the discrete percentile rule at N in the 20s (with k=2, `d_c ∈ {0, .5, 1}`; the one-sided bootstrap rejection region is discrete and asymmetric). Net: the N locked from the pilot could be mis-sized relative to the decision that will actually be made, and the doc presents 80% as if guaranteed. §4.3's saturation caveat partially mitigates but does not fix the α mismatch. | Use the one-sided constant (`z_{1−α} + z_{0.80}`) or, better, compute attained power **by Monte Carlo from the frozen bootstrap mechanism itself** (simulate `d_c` under the planned effect at the pilot variance; apply the exact §2.3 rule; report empirical power). State the k=2 discreteness caveat explicitly. Keep §4.3's saturation handling — it is good. |
| F4 | **MEDIUM** | `ceq_arm_design.md` §3.2, §5 (no parity check on consultation count) | C-EQ's manager "may consult investigators (one prompt each, accounted)" — the design never fixes whether that is once per round or once per case, nor caps it. Across 4 planner rounds the manager can therefore issue up to 12 investigator prompts while D-E's investigators issue their finding prompt **once each per case**. Prompt volume is a shared-budget consumption, so this is not a cap violation — but it is an *unmeasured, unbounded information-channel asymmetry* a hostile reviewer will frame as "the central manager simply asked more questions". As written, test 5 (volume ≥ D-E) and no other canary bounds it from above. | Freeze the consultation budget (max M prompts per investigator per round and per case), record per-agent prompt counts in `run_metadata`, and add a parity check that D-E's per-agent prompt count is reported in the same table (descriptive, always disclosed). Symmetric disclosure, bounded channel. |
| F5 | **MEDIUM** | `ceq_arm_design.md` §5.6 / test 5 (anti-cripple prompt volume) | The canary is **one-sided** (C-EQ volume ≥ D-E volume) and uses fake tokenization (`len//4`). One-sidedness only guards "C-EQ starved of prompting"; it does nothing to stop C-EQ from consuming *more* prompt volume (see F4), the opposite cripple — a reviewer will then say D-E was the starved arm. Fake tokenization also diverges from real provider counts, so the offline canary can pass while live runs are asymmetric. | Make the canary **two-sided** (ratio bound, e.g., total prompt volume within [0.8, 1.25]× of D-E on the same case state) and compute live runs with the **real provider tokenizer** (recorded in `run_metadata`); keep the fake-token offline test only as a mechanics check, clearly labeled. |
| F6 | **MEDIUM** | `ceq_arm_design.md` §3.2 (MAX_PLANNER_ROUNDS = 4, frozen) | C-EQ has a fixed 4-round planner loop; D-E's maximum number of reasoning rounds is not stated as a matched frozen constant anywhere in the design. If D-E's EESS loop can run more rounds per case, the round budget is a hidden asymmetry (each planner round = a distinct decision opportunity + budget consumption). | At prereg freeze, state the **maximum rounds/decision-calls per case for both arms** in the parity table and check equality (or disclose the difference as an architectural parameter with its direction). Round budget is capability, not implementation detail. |
| F7 | **MEDIUM** | `rcaeval_contract.md` §4 (pilot = cheapest stratum) + §6 (BARO Avg@5-CPU = 1.0) | The pilot deliberately selected the *easiest* stratum ("smallest metric-only stratum, cheap to download"), and the official BARO baseline scored **1.0** on it (rank 1–2 in all 10 cases; Chance@5 = 0.23). The contract does not overclaim — §7 correctly confines the track to observational ranking — but there is a **ceiling bias** risk downstream: if the O-R heldout stays on RE1-style metric strata, *both* the official baseline and any RepliClaw observational arm will saturate, and the track will report "not established" on a vacuous metric (the §4.3 ceiling scenario, with a baseline that also saturates). The document does not yet mandate which strata the *heldout* covers. | Add to the O-R frozen estimand doc: the heldout manifest **must** include ≥1 RE2 and/or RE3 stratum (logs+traces, harder faults) with per-fault-type reporting; and an explicit sentence that the RE1-CPU pilot BARO = 1.0 is **not generalizable** — it is an easy-stratum ceiling check, not an estimate of baseline performance on the track. A 1.0-scoring baseline cannot discriminate arms; the heldout must contain strata where it does not. |
| F8 | **MEDIUM** | `agentrx_contract.md` §6/§9 (endpoint-dependent pipeline) | The entire metric chain (static/dynamic/check/judge) is an **LLM judge whose identity is not pinned**: `AGENT_VERIFY_COPILOT_MODEL` is an environment variable, paper numbers were produced with Microsoft-internal or specific Copilot endpoints, and the contract's baseline reproduction is blocked (B1, quota). Root-cause accuracy is therefore *model-conditioned*: an AgentRx baseline number re-derived on a different judge model is not the paper's number. The contract is honest about the blocker (good — no fabricated numbers), but G0 should not close while the judge model is a free variable, because the frozen estimand doc cannot fix comparability to the published baseline until the judge identity is pinned. | G1 condition: pin the judge model + endpoint + `--mode`/`--exec_mode` in the frozen estimand doc; report published-vs-re-derived numbers as **separate** rows with the model named; treat "re-derived baseline" and "paper baseline" as distinct quantities (never substitute one for the other in the same claim). The B1 quota blocker then blocks the *baseline row only*, not the RepliClaw observational arm, provided the arm is run under the same pinned judge. |
| F9 | **MEDIUM** | `aiopslab_contract.md` §5 (all six FEASIBLE verdicts by code reading only) | The feasibility verdicts are sound *as code-reading* and the contract is scrupulous about what was not executed (read-only mandate, reset semantics traced to `orchestrator.py`). But three empirically unverified things carry the entire track: (i) **reset fidelity** — `app.delete()/deploy()` + `recover_fault()` + namespace/PV purge is claimed deterministic, yet PV-finalizer residue, OpenEBS state, and node-level state after a crashed run are untested; (ii) **workload nondeterminism** — `wrk`/`wrk2` load generation means symptom onset is not pinned, so two arms on the "same case" may experience different fault dynamics (case-level variance, not seed noise); (iii) the **16 GB macOS host** verdict is unexecuted for even the lightest app. A "FEASIBLE" that has never been run is a hypothesis, not a fact — G0 language should say so. | Gate G2 on a **smoke problem**: run `k8s_target_port-misconfig-mitigation-1` twice with a full reset between; assert (a) start-state telemetry signatures are byte-identical across the two `init_problem` calls, (b) the two runs' symptom onsets are within a predeclared window (else record workload nondeterminism as a case-level covariate), (c) kind image digest is pinned (the `:latest` risk the doc itself flags). Add one sentence to §3: verdicts are *by code inspection, not by execution*. |
| F10 | **MEDIUM** | `aiopslab_contract.md` §4–5 (mitigation success = live system state) | On mitigation problems, **success is measured against live system state after `submit()`** (`wait_until_pods_healthy` / `targetPort==9090`), and every agent — of any architecture — can *probe that same state at will* (`get_metrics`, `exec_shell`). This is fair to centralized and decentralized arms (nothing biases toward decentralization — I checked: the action vocabulary is handed identically via `MitigationTask`, one cluster per arm, symmetric action grammar), but it **neutralizes the P08-style access asymmetry**: in a live environment there is no "no-intervention" arm with less causal access, because *any* agent has full causal access by probing. Consequence: a track-I positive cannot be read as "access to interventions matters" (P08's actual mechanism); it can only be read as *selection/coordination of interventions matters*. The docs do not yet state this estimand shift. | Add to the track-I estimand note (F2): "On AIOpsLab mitigation problems all arms have equivalent live-system access; the primary contrast is therefore **selection and coordination of actions under a shared cap**, not access to interventions as such. P08's access-attribution finding does not transfer to this environment, and no report may imply it does." Also freeze `max_steps` and the step-accounting rule per arm in the prereg (currently unspecified). |
| F11 | **LOW** | `statistical_protocol_v3.md` §4.1/§4.2 (pilot inflation rule) | σ̂_D from n_pilot ∈ [6,10] is a 6–10-sample variance estimate; the 1.3 inflation cushion may be optimistic at the low end, and a wrong σ̂_D silently propagates into locked N. Also, the frozen bootstrap RNG seed (20261009) is a calendar-date number with no allocation scheme preventing collision with case/seed-generation seeds. | Set a floor: if n_pilot < 8, use inflation 1.5 (or require n_pilot = 10); add one line to the prereg template listing the **seed allocation scheme** (bootstrap seed, case-generation seed pool, RNG streams) so no two statistical streams share a seed. |
| F12 | **PASS (verified)** | all Wave-0 docs | P08 recast check — **no document recasts P08 as evidence for decentralization, escrow, or autonomy.** Verified: `statistical_protocol_v3.md` §3 carries the A1/A3 negative finding forward as a *mandatory counterevidence* attached to any D-E claim and names it "a negative finding about escrow and selection strategy"; `LITERATURE_AND_BENCHMARK_DECISION.md` states "Do not recast P08 as evidence for autonomy" and restates the attribution correctly; `EXPERIMENT_PROTOCOL_V3_DRAFT.md` re-pins the estimand on intervention-matching rather than decentralization; `ceq_arm_design.md` frames S3's weakness as a confound to *fix*, not a centralization-cost finding; `P1_RESULT_STATEMENT_20261009.md` §0 leads with counterevidence. One nuance worth recording (not a violation): the V3 *primary estimand* (D-E vs C-EQ) is exactly the question P08 **could not answer** (confounded with intervention access) — asking it again in a matched-access environment is scientifically correct, not a recast, *provided* F2/F10 make the new estimand explicit. |
| F13 | **LOW** | `statistical_protocol_v3.md` §2.2 (percentile vs BCa) | The predeclaration "if BCa and percentile disagree on the decision, percentile stands" is good freeze practice, but the stated justification that the percentile lower endpoint "is conservative (wider) relative to BCa for mildly skewed statistics" is **not guaranteed** — for a left-skewed statistic (possible when D-E saturates and few negative `d_c` exist) the percentile lower endpoint can be *narrower* than BCa's. The predeclared tie-break still holds, but the justification should not be asserted as a mathematical property. | Reword: "percentile is chosen for auditability and stability at small n; the tie-break is predeclared so the choice cannot drift." |
| F14 | **LOW** | `agentrx_contract.md` §4/§7 (unit of inference for O-A) | The 73 annotated trajectories are the natural unit for the observational estimand, but tau_retail cases share task-template structure (29 cases from one domain family); if cases within a domain are not independent, a trajectory-level bootstrap over 73 still mixes dependence. The contract does not address clustering of trajectories by domain/template. | The O-A frozen estimand doc must declare the resampling unit (trajectory, or domain-cluster with trajectory nested) and justify it from the dataset's authoring structure, mirroring the case-nesting discipline of the main protocol. |

---

## C-EQ: is it honestly strong? (adversarial review)

**Cripple vectors I attacked and their status:**

- *Prompt-volume asymmetry* — **partially closed, re-openable (F4/F5).** One-sided canary +
  fake tokenization + unbounded manager consultation leave a channel through which C-EQ
  can silently consume more (or less) prompt volume than D-E, in either direction.
- *Information-timing asymmetry* — **closed (best part of the design).** Single publish
  point `build_evidence` after `run_case` returns, for both arms; tests 6–7 pin it;
  capability table forbids any pre-outcome leak. I found no residual timing hole.
- *Hidden fixed scripts* — **closed.** No case/defect literals (test 13), adaptivity
  demonstrated by evidence dependence (test 8), prompt-template sha frozen at prereg.
- *Agent-count caps favoring decentralization* — **no such bias found — and I want that on
  the record in reverse:** C-EQ actually *uses* the full 4-agent cap (3 investigators +
  manager) while D-E uses 3 of 4. The matched envelope is, if anything, slightly more
  favorable to C-EQ. This is the right direction for a fair central manager, and R8's
  disclosure (typical deployments 3 vs 4, cap identical) is honest.
- *Budget accounting asymmetry* — **closed at envelope level** (one shared
  `BudgetEnvelope`, same `LiveBudgetLedger`, `assert_budget_parity`). *However*:
  per-call concentration is unexamined — a single manager prompt can consume a large
  token share in one call while D-E's spend is distributed. That is legitimate (a central
  manager *should* be able to spend the envelope on one call), but per-decisioner spend
  must be **reported** in every results table (with F4) or a reviewer will call it hidden.
- *What would make it unimpeachable to a hostile reviewer:* F4 (consultation budget),
  F5 (two-sided real-token volume parity), F6 (round/decision-call parity), plus one
  already handled well — **verdict aggregation** is covered (R10: M1 uses `defect_class`
  extraction, not `verdict`, so aggregation locus cannot bias the primary metric), and the
  S-I single-voice disclosure is present. With F4–F6 fixed and a per-decisioner spend
  column, I would accept C-EQ as "the strongest fair central manager" for review purposes.

## G0 gate recommendation per track

| Track | G0 status | Rationale |
|---|---|---|
| **agentrx** (O-A) | **PASS, with G1 conditions (F8, F14)** | Pin, license, access, hashes, taxonomy audit, and discrepancy documentation all verified against the actual release (5 files re-fetched and byte-matched; 73-trajectory evaluation set correctly scoped; flash absence honestly documented; 115-vs-87-vs-73 trajectory reconciliation surfaced rather than hidden). The baseline-reproduction blocker (B1) is a *G1* blocker and is honestly blocked — no fabricated numbers. Conditions: pin the judge model before any frozen estimand doc is written (F8); declare the resampling unit (F14). |
| **rcaeval** (O-R) | **PASS, with G1 conditions (F7)** | Pin, public access, evaluator formulae, and a genuine (partial) BARO reproduction with per-case artifacts — the strongest of the three contracts on evidence. The one scientific hazard is easy-stratum ceiling bias: the pilot is the cheapest stratum and the official baseline saturates at 1.0. That does **not** disqualify the track (the 735-case, 3-suite population is real and the estimand doc is explicitly deferred, per stats-protocol Q4), but the heldout manifest must include RE2/RE3 strata and the pilot's 1.0 must be permanently labeled as a non-generalizable easy-stratum check (F7). |
| **aiopslab** (I) | **PASS (conditional) — the weakest of the three** | Feasibility verdicts are code-verified and scrupulously labeled as read-only; the reset/isolation/action-vocabulary analysis is genuinely fair to both architectures (I found no hidden bias toward decentralization). But the track is also the one where the *study* lives, and it rests on unexecuted empirical claims: reset fidelity, workload nondeterminism, and the macOS host verdict (F9). G0 *declaration* is defensible (it is a feasibility contract, and G0 is read-only by mandate); G2 is **not** open until the smoke problem, kind-image digest pin, `max_steps` freeze, and the track-I estimand note (F2, F10) are done. |

**Overall G0:** scientifically legitimate to declare G0 *passed on all three tracks at the
G0 scope* (pin/access/license/feasibility), **but not to declare G0 "complete"** in the
sense of "ready to preregister": F1 (verdict floor / harm signal), F2 (track-I action-set
manifest + estimand note), and F3 (power/α consistency) are pre-prereg defects in the
*statistics* doc, and the stats doc's own Q4/Q5 (observational-track estimand docs, case
pool availability) remain open. The draft prereg structure (§6 skeleton, §5.3 freeze/
amendment mechanics, two-key sign-off, append-only amendment log) **does** prevent
post-hoc amendments in the ways that matter — no edit-after-hash path, forward-only
amendment scope, P08 immutability, BCa/percentile tie-break predeclared, "no prompt/
scorer tuning after any heldout outcome is observed". The one structural gap: §5.3 does
not explicitly forbid prompt tuning *between pilot and freeze*; add one line — "pilot
outcomes may inform N and MDE only via the §4.2 channel; no prompt, arm, or scorer
changes based on pilot *outcome* patterns are allowed before or after freeze".

## What this gate checked (the weak-study routes) and their status

1. **Null dressed as positive** — closed by §2.3 (forbidden "negative" + point estimate
   always reported); *but* **positive dressed as meaningful** is open (F1) — fixed by the
   floor/rename; **harm dressed as null** is open — fixed by the HARM_SIGNAL rule.
2. **Silent overstatement of generalization** — closed: case is the unit, seeds nested,
   run-level bootstrap explicitly forbidden with the P08 lesson cited, contamination
   measured-not-asserted (§5.4), "not established" must carry the attainable-MDE and
   saturation statement (§5.5.3). The most robustly written section of the package.
3. **C-EQ weakened below fair** — mostly closed (timing, script, executor, envelope,
   agent-cap all parity-tested); open at the volume/consultation/round edges (F4–F6).
4. **Track mixing** — closed: O-A/O-R/I estimands explicitly separated; RCAEval §7
   forbids counterfactual claims on observational data; AgentRx "no executable
   intervention => process-only measurement" carries through.
5. **P08 recast** — verified absent (F12), with the attribution preserved as a
   *mandatory* counterevidence in the main protocol rather than a footnote.

**Required before G2 (checklist):** F1 fix (stats); F2 action-set manifest + track-I
estimand note (L3 + L4 + stats); F3 power re-derivation (stats); F4–F6 canaries (C-EQ
design + tests); F7 heldout stratification mandate (O-R estimand doc); F8 judge-model pin
(O-A estimand doc); F9 smoke problem + digest pin (L3); F10 live-access estimand
disclosure (L3 + stats); F11/F13/F14 wording. Independent re-review of this checklist by
J-SCI is requested before any G2 canary.

*Review-only: no reviewed file was modified by this judge; no scratch artifacts were
required.*
