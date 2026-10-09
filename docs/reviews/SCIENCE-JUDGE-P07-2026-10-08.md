Agent is idle (waiting for messages). agent_id: ca89d310-98be-43f1-b394-a3f46b4ec980, agent_type: RepliClaw Science Judge, status: idle, description: Science judge: EESS mechanism review, elapsed: 5037s, total_turns: 1

[Turn 0]


I have enough evidence to render the science-judge review. I traced the code, the canonical run artifacts, the tests, the checkpoints, and the docs. Below is my assessment as a genuinely critical science judge. I am scoring observed artifacts only, not inventing competitive scores.

---

# Independent Science Review — RepliClaw EESS (`p07/integration` @ HEAD, `68a27c7`/`251dead`)

**Scope of what I actually read:** `src/repliclaw/{counterfactual,escrow,needmarket,comparators}/`, `strategies.py`, `protocol.py`, `investigators.py`, `models.py`; `experiments/policy_rag/{case,interventions,oracle/oracle}.json`; `artifacts/science/p02-hero-canonical/` (all 5 arm outputs + manifest); `tests/test_{counterfactual,escrow,needmarket,comparators}.py`; `docs/EVIDENCE_ESCROW_SWARM.md`, `PRIOR_ART_NOVELTY_GATE.md`, `design/EESS_CONTRACTS.md`, `EXPERIMENT_PROTOCOL_V2.md`, `checkpoints/CP-P0{2,3,4}.md`.

## TL;DR
The individual mechanisms (counterfactual engine, escrow ledger, need market) are **real, deterministic, unit-tested, and honestly scoped**. But as a *scientific result* they do not yet demonstrate the headline claim. Three structural facts drive the verdict:
1. **There is no S5/EESS arm.** The comparator registry contains only `single_agent`(S0), `adaptive_central`(S3), `open_sharing_swarm`(S4). The "EESS vs strong central manager at matched budget" comparison — the paper's central claim — **cannot be executed** because the EESS system is not an arm.
2. **The P07 vertical slice is `NOT_STARTED`** (IMPLEMENTATION_PLAN.md:20). The escrow ledger, the need market, and the counterfactual executor are **not wired to each other or to any real agent** — grep confirms no non-test source imports `escrow`, `needmarket`, or `counterfactual`. Each module runs only in its own unit tests.
3. **The "matched-budget" harness runs a different, 0-token deterministic statistical task** (bundled t-test/RR data via `DeterministicInvestigator`), **not** the `policy_rag` counterfactual case.

---

## Answers to the five questions

### Q1. Is `policy_rag_v1` a genuine experiment or a scripted narrative?
**A genuine *controlled toy*, not a genuine *experiment*.** The five arms do manipulate structurally distinct factors, and the single-factor discipline is real and tested (`test_one_factor_at_a_time`, `tests/test_counterfactual.py:57`):
- `I_R` → retrieval, `I_P` → policy_conflict, `I_J` → judge_reference, `I_C` → retrieval+judge (documented 2-factor control).
- Different evidence does separate the hypotheses *in form*: changing R changes the target output (14d→30d); changing J flips the verdict without changing output.

**But the "system under test" is a hand-written Python parrot, not a model.** `frozen_backend.rag_assistant_reply` (`frozen_backend.py:37`) does exactly one thing: regex the top-1 retrieved snippet and parrot its `N days`. The judge is a string-match `FrozenJudgeClient` (`executor.py:146-147`). The oracle's `expected_arm_outcomes` are **tautologically satisfied** because the authors wrote both the deterministic code and the oracle. The result ("retrieval omission is the cause") is **baked into the code**, not discovered.

**The `I_P` null result is by construction, not by measurement.** `policy_conflict` and `model_prompt` are config fields that the target **never reads** (verified: no reference in `frozen_backend.py`; the executor only passes `retrieved` to the target and `reference_days` to the judge). So `I_P` is byte-identical to `I0` *guaranteed by the code*, independent of any real effect. Presenting "H_P not supported because output identical" as an empirical null is a **tautology**, not a falsification test. A skeptical reviewer reads this as: "we designed a target that can only respond to one knob, so the other knob's null is pre-decided."

**Sealed-oracle pattern — legitimate as leakage control, *not* a substitute for an independent evaluator.** The oracle (`experiments/policy_rag/oracle/oracle.json`) is genuinely hidden from the arms (the executor has "no oracle import path"; `test_oracle_not_leaked` greps the artifact tree for the literals and passes). That part is sound. **Its limit:** the oracle is *co-authored with the deterministic target*, so "arms match oracle" proves self-consistency, not correctness. It validates one planted fault in one case. It cannot be cited as an independent evaluator.

### Q2. Does the escrow actually prevent post-hoc narrative construction?
**Within one ledger/phase machine, yes — and it is tested. But it is *detection*, not *prevention*, it is *self-verified*, and it is *not wired to any real agent*.**

What I traced in `escrow/ledger.py` + `escrow/phase.py`:
- `commit()` is legal only in the `COMMIT` phase; the `PhaseGate` is a strict monotonic chain `COMMIT→REVEAL→EXECUTE→RESOLVE` (`phase.py`). After the reveal boundary, `commit()` raises `PhaseViolation` — so **you cannot register a *new* prediction after the outcome is known**.
- Duplicate `packet_id` is rejected (`DuplicateCommitment`), so you cannot re-commit an "amended" packet under the same id.
- `reveal(agent, packet)` recomputes the hash and compares to the commitment; a mismatch is an **integrity event, never published, original preserved** (`ledger.py`, `reveal()`; tested in `test_reveal_verifies_and_preserves`, `test_tampered_reveal_mismatch`). This is the correct anti-rationalization anchor: the *commitment hash* is the reference, so revealing a better post-hoc packet fails the check.
- Events are hash-chained; `verify_ledger` catches hash-edit and reordering (`test_verify_ledger_catches_tampering`).

**Trust assumptions that remain (all honestly acknowledged in CP-P03/handoff, but the judge should weight them):**
1. **Reveal never cross-checks the on-disk private packet.** `reveal()` trusts the *caller-supplied* packet and compares it to the commitment; it does **not** read `private/<agent>/<packet_id>.json` (`load_private_packet` exists but is not called on the reveal path). So the guarantee is "what you revealed matches what you committed," not "what you revealed is what you privately stored." A trusted third party reading the private store is required for a stronger claim.
2. **Self-verification, single trust root.** There is no independent verifier, no signature, no trusted timestamping — the ledger verifies itself.
3. **No process isolation.** `private/` is readable by any process with filesystem access → **pre-reveal read leak**. "Pre-reveal isolation" is enforced by a *byte-level content check* (`project_commitment` asserts the private sentences don't appear in the public projection) — good, but it is content screening, not access control.
4. **Wall-clock ordering is not anchored.** `committed_at` is real time and is *excluded from the hash chain* (deliberately, for snapshot determinism). "Committed before seeing the outcome" is enforced by in-run phase order, not by a tamper-evident external timestamp.
5. **Not exercised by real agents.** The escrow tests use synthetic `make_packet(...)` calls. No real LLM/agent commits in the escrow anywhere in the codebase.

Net: the *mechanism* is sound and well-tested for what it claims (tamper-evident, verify-and-preserve, no post-reveal amendment); the *property* it is meant to deliver (independence/anti-rationalization across *autonomous* agents) is not yet demonstrated because no autonomous agents use it.

### Q3. Is "autonomous experiment selection" real or theater?
**It is real as a deterministic ranking over its inputs, and *theater* as "evidence-driven" — because the decisive input is injected, not derived.**

- `LocalEigPolicy` ranks by `U = gain/cost + λ·diversity − μ·crowding` (`needmarket/policy.py`). This is transparent, deterministic, agent-local, and the broker genuinely does **not** rank (`test_no_central_ranking` asserts the broker has no ranking API). Those are real.
- **Where do the `discriminability` numbers come from?** Nowhere in the codebase. I grepped for any computation of discriminability/information-gain from evidence: **there is none.** `discriminability` is a constructor argument / `set_discriminability` call. The docstring concedes it: *"est_info_gain comes from a caller-supplied discriminability… P07 feeds real numbers derived from public evidence, tests use fixtures."* CP-P04's "NOT proven" list concedes superiority is open. So the system is **honest** that the input is caller-supplied — but that means the current selection is **oracle-tinted / externally fed**, not evidence-driven.
- **The T4 "evidence-induced pivot" does not prove the mechanism.** In `test_evidence_changes_choice` the worker is re-run with `EVID_B` (a different snapshot sha) *and* `policy.set_discriminability({"I_J": {"H_R":0.95,...}})` is called by hand. The ranking flips because the *discriminability table was manually changed*, not because the worker *derived* anything from the observed evidence. `NeedWorker.cycle(evidence)` only hashes the evidence into the snapshot for the trace; the choice is fully determined by the policy's supplied table. So "a new observation changed the choice" is really "I changed the input table and the (deterministic) ranking changed." The *causal link* observation → posterior → choice is **not mechanistically demonstrated**.

**What would make it genuinely evidence-driven (not oracle-tinted):** a `derive_discriminability(evidence_snapshot) -> mapping` function that computes per-need, per-hypothesis expected information gain **from the verified arm outcomes** (i.e., a posterior over hypotheses updated by observed severities/output diffs), with **no externally set numbers**; plus a test that the *same* evidence→choice map is *derived* (injecting different evidence yields different, correctly-directed choices) rather than *injected*. That closes the loop and is currently absent.

### Q4. Is the matched-budget comparison (S0/S3/S4/S5) scientifically fair?
**As it stands it is not a valid test of the claim, for three compounding reasons.**

1. **There is no S5 arm.** `comparators/runner.py::arm_registry` returns exactly `{single_agent, adaptive_central, open_sharing_swarm}`. The headline comparison "EESS vs strong central manager" is *unrunnable* today. This is the thing a skeptical reviewer attacks first and it is unanswerable as submitted.
2. **The arms run a different task than the hero case.** `test_comparators.py` builds `Claim(data={mean_treat, mean_ctrl, sd_*, events_*})` and uses `DeterministicInvestigator` — the statistical bundled-data task. The counterfactual engine, the escrow, and the need market are **never in this loop.** So "matched budget" is being proven over an unrelated, 0-token task.
3. **The S3/S4 labels do not match the intended contrast:**
   - **S3 = `repl_claw` = the *incumbent* full RepliClaw protocol** (`managers.py:53`). That protocol *already* does blind commit/reveal + a **central** `_fulfill_need` follow-up (`protocol.py:383`). So S3 already contains an escrow-like mechanism *and* the exact centralized follow-up the new design is meant to beat. The "central vs decentralized" and "with vs without escrow" contrasts are **muddled** — part of the novelty is in the baseline.
   - **S4 = `open_debate` does *not* actually share peer conclusions.** `run_open_debate` sets `ctx.revealed_materials` (`strategies.py:253`), but `LLMInvestigator.run` calls `context.to_prompt_block(revealed=False)` (`investigators.py:218`) → the peer material **never reaches the prompt**. So S4 is *effectively isolated*, i.e. the "open-sharing" baseline is **crippled** (this is the same G3 flagged in COMPETITION_STRATEGY). That biases any future comparison *in favor* of a swarm that is supposed to be compared against true open sharing.

**Other confounds:** matched *cap* (`envelope_sha256` parity) ≠ matched *spend*; with `DeterministicInvestigator` every arm spends **0 real tokens**, so the parity check is **degenerate** (it proves same declared ceiling, not same cost, and spend is degenerate). No multi-seed, single case, no variance, no CI. `assert_budget_parity` is a sound *mechanism*, but it is not currently *proving* a fair head-to-head on the causal task.

**A skeptical reviewer's first two attacks:** (a) "Show me the S5 arm and a single run where S3 and S5 hit the *same* counterfactual case at the *same* non-zero token budget." (b) "S3 already has blind commit/reveal and a central follow-up, and your 'open sharing' S4 doesn't actually share — so what exactly is being isolated?"

### Q5. Novelty scoping and what's demonstrated
The **novel contribution** — *the combination* of time-ordered, verify-and-preserve sealed pre-outcome commitments **plus** single-factor counterfactual intervention arms **plus** measured-difference causal attribution of AI failure under a sealed oracle, evaluated against a matched central manager — is a **plausible novel combination/application**. The team's own `PRIOR_ART_NOVELTY_GATE.md` scopes it correctly: *"the originality may be in the rigorous combination, application and evaluation, not new atomic primitives."* I agree: escrow-as-primitive (commit/reveal+hash) pre-existed in the prototype; what is new is the phase-gated ledger, the counterfactual engine, and the local need market, and — *if run* — the comparative evidence.

**Is the current state sufficient to *demonstrate* it? No — it is sufficient to make it *plausible*.** "Mechanism exists" is established (each component runs in isolation with red-first tests). "Demonstrated" requires a single executed, matched-budget, evidence-driven run where escrow + autonomous selection *causes* a measurable diagnostic improvement — and that does not exist yet:
- No S5 arm, no E2E slice (P07 NOT_STARTED).
- The causal-attribution claim is shown for **one planted fault in one deterministic toy** with a parrot target and a co-authored oracle — that is a *controlled fixture result*, not a general capability.
- The "autonomous" selection is externally fed (Q3).

**The specific empirical result that moves the claim from "mechanism exists" to "demonstrated":**
> On ≥12–24 held-out controlled multi-fault cases, ≥2 seeds, with real model calls at a non-degenerate matched token/wall envelope, run **S3 (adaptive central)** vs **S4 (true open-sharing)** vs **S5 (EESS: escrow + needmarket local choice + counterfactual executor, all on the same case)**, and show **S5 ≥ S3** on the primary metric (validated root-cause accuracy, partial-credit, paired, bootstrap CI across cases) **and** — critically — that the **no-escrow ablation (A1)** specifically increases false-consensus / duplicate-experiment rate relative to S5, with the need-market discriminability **computed from evidence** (not injected). That paired, mechanism-isolated difference is the demonstration.

---

## Scorecard (gate G4 rubric; PASS/WEAK/FAIL on observed artifacts)

| Dimension | Grade | Basis |
|---|---|---|
| SIGNIFICANCE | **WEAK** | Real, consequential question (causal attribution of AI failure), but currently scoped to one toy. |
| ACTUAL_RESULT | **FAIL** (for the claim) / WEAK (as a toy) | Only artifact is a deterministic 5-arm run matching a co-authored oracle; the headline comparison is unrun. |
| EVIDENCE | **WEAK** | Strong replay/provenance/oracle-leak tests for counterfactual; escrow/needmarket unit-tested; but no real-model evidence and no S5. |
| CAUSALITY_OF_COLLECTIVE | **FAIL** | The core "collective" behavior (evidence-driven autonomous reallocation) is not demonstrated E2E; selection is fed, and P07 is NOT_STARTED. |
| REPRODUCIBILITY | **PASS** | All three modules are deterministic; `replay()` two-pass verified; hash-chained ledger; red-first tests. |
| GENERALIZATION | **FAIL** | Single case, single planted fault, no held-out set, no second failure family, no CI. |

## Overall verdict: **CONDITIONAL**

The build quality and scientific *honesty* of the individual modules are good (they don't overclaim in their own docs; red-first tests; oracle-leak and replay checks). But the **CURRENT artifacts do not scientifically validate the central EESS claim**. This is a checkpoint, so CONDITIONAL is the fair call — with the following required before any "demonstrated" language is used.

## Findings (severity + evidence)

**BLOCKER**
- **B1 — No S5/EESS arm; headline comparison unrunnable.** `comparators/runner.py::arm_registry` = `{single_agent, adaptive_central, open_sharing_swarm}`; no EESS arm exists. The paper's central claim (EESS ≥ strong central manager at matched budget) cannot be executed. *Evidence: `src/repliclaw/comparators/{runner,managers}.py`, `tests/test_comparators.py:128`.*
- **B2 — No vertical slice (P07 NOT_STARTED); modules not wired together.** No non-test source imports `escrow`/`needmarket`/`counterfactual`; `NeedWorker`/`EscrowLedger`/`SimpleAuditExecutor` are instantiated only in tests. There is no single run: real agents commit in escrow → claim a need → run a counterfactual arm → publish verified evidence → re-rank → resolve. *Evidence: grep over `src/repliclaw/` (no cross-imports); `IMPLEMENTATION_PLAN.md:20` (P07/P08 NOT_STARTED).*
- **B3 — Matched-budget harness runs a different, 0-token task, not the hero case.** `tests/test_comparators.py` uses statistical `Claim` + `DeterministicInvestigator`; the counterfactual/escrow/needmarket never enter the loop, and all arms spend 0 real tokens, so "matched budget" is degenerate and off-task. *Evidence: `tests/test_comparators.py:44-76,179-196`.*

**MAJOR**
- **M1 — `policy_rag_v1` is a scripted toy, and the I_P null is by construction.** The target is a parrot (`frozen_backend.py:37-58`) that reads only `retrieved[0]`; `policy_conflict`/`model_prompt` are never read, so `I_P` is byte-identical to `I0` *guaranteed by code*, not measured. The causal finding is baked in. *Evidence: `frozen_backend.py` (no policy_conflict/model_prompt refs), `artifacts/science/p02-hero-canonical/interventions/*` (I_P target_output == I0 target_output).*
- **M2 — Autonomous selection is oracle-tinted / externally fed.** No code derives `discriminability`/EIG from evidence; it is a constructor arg. The T4 "pivot" is driven by a manual `set_discriminability` call, not by observed evidence content. *Evidence: `needmarket/policy.py:14-20` (docstring admits caller-supplied), `tests/test_needmarket.py:233-262` (EVID_A/EVID_B + hand-set mapping).*
- **M3 — S4 baseline is crippled (G3).** `open_debate` sets `revealed_materials` but `LLMInvestigator` prompts with `revealed=False`, so peer conclusions never reach the model → "open sharing" is effectively isolated. *Evidence: `strategies.py:253` vs `investigators.py:218`.*
- **M4 — S3 label conflicts with the intended contrast.** S3 = `repl_claw` = incumbent protocol that *already* does blind commit/reveal and a *central* `_fulfill_need`. Part of the "novel" escrow is in the baseline, and the central-follow-up under test *is* S3's own behavior. *Evidence: `comparators/managers.py:53`, `protocol.py:119-260,383-460`.*
- **M5 — No uncertainty / tiny-n.** Single case, single seed, deterministic; no CI, no held-out set, no second failure family. *Evidence: `EXPERIMENT_PROTOCOL_V2.md` (12–24 cases are "targets not claims"); no metrics.json/comparison.md exists in `artifacts/`.*

**MINOR**
- **m1 — Escrow is detection + self-verification, not prevention; not cross-checked against the private store on reveal; private/ readable pre-reveal; wall-clock `committed_at` unanchored; no independent verifier/signature.** Sound for what it claims, but the anti-rationalization property is bounded. *Evidence: `escrow/ledger.py` (`reveal()` uses caller packet; `load_private_packet` unused on reveal path), `escrow/phase.py` (chain excludes `ts`), CP-P03 "Escrow does NOT guarantee…".*
- **m2 — Sealed oracle is co-authored with the deterministic target; agreement is tautological.** Valid only as a leakage-control device, not an independent evaluator. *Evidence: `experiments/policy_rag/oracle/oracle.json` + `frozen_backend.py` (same authors).*

## Minimum evidence bar for the final submission
1. **Register an S5/EESS arm** in the comparator harness that runs **escrow + needmarket local choice + the counterfactual executor** on the *same* case as S3, so B1 is closed and the headline comparison is executable.
2. **One executed vertical slice (P07):** ≥3 real agents commit in escrow → ≥1 *different* agent claims a need via atomic lease → a counterfactual arm runs → verified evidence is published → at least one *observed, evidence-induced* re-rank (`choice_changed`) → resolved/abstained with a stop reason. Must be a single traceable run, not stitched unit tests.
3. **Evidence-derived selection:** ship `derive_discriminability(evidence_snapshot)` (no injected numbers) and a test showing the choice change is *derived* from the observation (different evidence → correctly directed different choice), closing M2.
4. **A fair head-to-head on the causal task:** S3 vs S4(true open-sharing, fix M3) vs S5 at a **non-degenerate matched token/wall envelope with real model calls**, ≥12–24 held-out multi-fault cases, ≥2 seeds. Primary: validated root-cause accuracy (partial credit), paired, bootstrap CI across cases.
5. **Mechanism isolation (the actual novelty):** the **no-escrow ablation (A1)** must show escrow specifically reduces false-consensus / duplicate-experiment rate vs S5 — this is the result that distinguishes EESS from AutoScientists-style open sharing and from the incumbent `repl_claw`.
6. **Reframe `policy_rag_v1` as a controlled *fixture* (not a scientific result)** in the narrative, and make I_P's null result explicit as "by-design inert factor" or remove it as a hypothesis arm; do not present the tautological I_P null as an empirical falsification.
7. **State escrow's trust boundary precisely:** tamper-*detection*, self-verified, in-process, wall-clock ordering, no process isolation — and (ideally) add a trusted-verifier cross-check of the private packet on reveal.

If items 1–3 are not in place by the submission window, the defensible fallback (per `PRIOR_ART_NOVELTY_GATE.md`'s own guidance) is to present this as *"a controlled empirical study of evidence-escrow and counterfactual diagnosis in agentic AI auditing"* with the single-case fixture reported as a mechanism demonstration — not as a claim that decentralized EESS outperforms a matched central manager. That fallback is honest; the current artifacts support it and do not yet support the stronger headline.