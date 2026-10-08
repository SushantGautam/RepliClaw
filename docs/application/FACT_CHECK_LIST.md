# P09 — Fact-Check List (DRAFT_ANSWERS.md)

One factual claim per line. Each row gives the claim, its **source** (file + commit SHA where
tracked; worktree/branch where the artifact is not git-tracked), and a **status**.

**Statuses.** `RE-VERIFIED` = P09 independently re-ran the command or re-read the artifact on
**2026-10-08** and it reproduced. `SOURCE-ONLY` = claim taken verbatim from the cited checkpoint
doc; P09 did not re-run it (would regenerate artifacts outside P09's owned paths).
`UNVERIFIED` = **human must confirm before submit.** `NO-NETWORK` = originally a web claim; P09 has
no network access and could not re-verify online.

**Do not submit any number or claim that does not have a `RE-VERIFIED` or `SOURCE-ONLY` row here.**
The human may change a claim only if the new source is recorded on the same row.

> **Re-verified to run-branch state (2026-10-08, `repl-claw-dev` @ `617b329`).** Rows F1–F19 cover
> the historical per-module checkpoints (P02/P03/P04 + G0 + prior art + team/rubric). Since the
> original P09 draft, P05/P06/P07/P08 components have landed on the run branch. **Rows F20–F29
> (Section A below) cover that run-branch state** — each `RE-VERIFIED` by re-running the command or
> re-reading the artifact at `617b329` on 2026-10-08, or `SOURCE-ONLY` where the source doc is
> authoritative and re-running would mutate state (e.g. would spend live tokens). The "critical
> discrepancy" note below still applies to the *historical* module counts (F1–F3).
>
> **Re-verification history (kept for audit trail):** the first pass verified **exactly**
> `1012ff7` (isolated worktree re-run: `149 passed, 8 skipped`). Since then the run branch
> advanced: leak-guard two-layer fix (`ae68211`/`a934a48`: `EESSArm._verdict` `reference_truth`
> fallback removed + `runner.py` `redact_claim_for_arms` harness redaction + CLI wiring),
> runner CLI merge (`d269a15`: new `runner.main`/`run_one_arm` CLI, `case_loader.py`,
> content-derived broker `claim_token`, 25-test comparator suite), and preflight gate 5
> (`6a9f2b7`: runner CLI smoke). This second pass re-verified **exactly** `617b329`
> (full gate re-run: `202 passed, 8 skipped`). **The run branch is a moving target, not a
> permanent pin — the human must pin the exact run-branch SHA at submit time and re-run the
> Step-2 gate there before trusting the 202/8 number** (see `SUBMISSION_CHECKLIST.md` Step 2).

---

## ⚠️ Critical discrepancy found by P09 — test counts 62/69 vs 78/73 (read first)

The task brief and the checkpoint docs cite **62 / 69 / 74** as the P02/P03/P04 test counts. P09
re-ran the full gate in each worktree **at the exact clean checkpoint commit** (working trees
`dirty=0`) and got **78 / 73 / 74 passed, 8 skipped each** (reproduced twice per tree):

| tree | branch @ commit | functions (committed) | P09 re-run (2026-10-08) | checkpoint says |
|---|---|---|---|---|
| `.worktrees/p02` | `p02/simpleaudit-counterfactual` @ `3f452b2` | 86 | **78 passed, 8 skipped** | CP-P02: 62 passed, 8 skipped |
| `.worktrees/p03` | `p03/evidence-escrow` @ `ba71a4d` | 81 | **73 passed, 8 skipped** | CP-P03: 69 passed, 8 skipped |
| `.worktrees/p04` | `p04/need-market` @ `1b48ac2` | 82 | **74 passed, 8 skipped** | CP-P04: 74 passed, 8 skipped (matches) |

Why P09 is confident the checkpoint numbers 62 and 69 are transcription errors, not a state drift:

- Base `b5f7bfb` = **66 passed + 8 skipped** (74 functions). CP-P04 states "66 base + 8 new" and
  its re-run (74) matches, so the base count is solid.
- The 8 skipped are a fixed spec module (`tests/test_need_dispatch_spec.py`, all
  `@pytest.mark.skip(reason="F06 spec")`) present in every tree, so skipped=8 is constant.
- **62 < 66** is arithmetically impossible for p02 (it can only *add* tests to a base that already
  passes 66). 86 committed functions − 8 skipped = 78 passed, which matches P09's run.
- p03: 81 committed functions − 8 skipped = 73 passed, matching P09's run; 69 has no support.
- **74 (p04) reproduces exactly** from the checkpoint.

**Action for the human:** DRAFT_ANSWERS.md now cites **78 / 73 / 74** (the re-verified values). If
the checkpoint values must be preserved for an audit trail, correct the CP-P02/CP-P03 numbers at
the source (this is **not** a P09-owned path). The draft's claim text does not otherwise depend on
which pair is right — only the numbers change.

---

## A. Verified-result claims (the backbone of the application)

| ID | Claim (as used in DRAFT_ANSWERS.md) | Source (file + commit SHA / branch @ SHA) | Status |
|---|---|---|---|
| F1 | P02 gate: pytest **78 passed, 8 skipped**; ruff clean; mypy clean (21 files) | re-run in `.worktrees/p02` @ `3f452b2` (base `b5f7bfb`); recorded (as 62) in `docs/checkpoints/CP-P02.md` @ `50dd599` | **RE-VERIFIED** (count corrected; see discrepancy note) |
| F2 | P03 gate: pytest **73 passed, 8 skipped**; ruff clean; mypy clean (20 files) | re-run in `.worktrees/p03` @ `ba71a4d`; recorded (as 69) in `docs/checkpoints/CP-P03.md` @ `1a02982` | **RE-VERIFIED** (count corrected; see discrepancy note) |
| F3 | P04 gate: pytest **74 passed, 8 skipped**; ruff clean; mypy clean (22 files) | re-run in `.worktrees/p04` @ `1b48ac2`; `docs/checkpoints/CP-P04.md` @ `0dd8d15` | **RE-VERIFIED** (matches checkpoint) |
| F4 | Real SimpleAudit execution via `ModelAuditor.run_scenario` (async); engine 0.3.3 pinned @ git `9783293241390586be8a648814c7e765256e9a14`; case `policy_rag_v1` | `docs/checkpoints/CP-P02.md` @ `50dd599`; `.worktrees/p02/artifacts/science/p02-hero-canonical/manifest.json` (read directly by P09) | **RE-VERIFIED** (manifest read; code path not re-executed) |
| F5 | Canonical run replays byte-identical, sha256-pinned; `replay.sh` present + executable | `docs/checkpoints/CP-P02.md` @ `50dd599`; `.worktrees/p02/.../replay.sh` (exists, mode `+x`) | **SOURCE-ONLY** (P09 did not re-run replay; would regenerate artifacts outside owned paths) |
| F6 | Arm discrimination: I0 pass (14d target / 14d judge-ref); I_R critical (30d target, 14d ref, output changed); I_P pass (output byte-identical to I0); I_J critical (output byte-identical to I0, 30d ref, verdict flipped); I_C pass (30d / 30d) | `.worktrees/p02/artifacts/science/p02-hero-canonical/manifest.json` (per-arm severity/output/judgment read directly by P09); `docs/checkpoints/CP-P02.md` @ `50dd599` | **RE-VERIFIED** (manifest read) |
| F7 | Sealed oracle (`true_cause=retrieval_omission`) never on any code path | `docs/checkpoints/CP-P02.md` @ `50dd599`; oracle dir exists at `.worktrees/p02/experiments/policy_rag/oracle` | **SOURCE-ONLY** (dir presence confirmed; "never on code path" is CP-P02's attestation) |
| F8 | Escrow protocol COMMIT->REVEAL->EXECUTE->RESOLVE; byte-level pre-reveal isolation; reveal verify/preserve; no post-hoc amendment | `docs/checkpoints/CP-P03.md` @ `1a02982` | **SOURCE-ONLY** |
| F9 | Hash chain `prev_event_sha256 = sha256(canonical prev event minus prev/ts)`; genesis 0x64; `verify_ledger` catches hash-edit + reorder; **detection only, no prevention** | `docs/checkpoints/CP-P03.md` @ `1a02982`; prohibition cross-ref `docs/PRIOR_ART_NOVELTY_GATE.md` @ `d992cd7` | **SOURCE-ONLY** |
| F10 | Escrow does **not** guarantee wall-clock ordering, process isolation, or epistemic independence | `docs/checkpoints/CP-P03.md` @ `1a02982` | **SOURCE-ONLY** |
| F11 | Two real OS subprocesses racing one `O_EXCL` claim -> exactly 1 `need_claimed` event, 1 winner, no partial lock files | `docs/checkpoints/CP-P04.md` @ `0dd8d15` | **SOURCE-ONLY** |
| F12 | SIGKILL crash matrix: durable claim event observed; lease expired after real 0.5s TTL; generation-2 re-claim + fulfilment | `docs/checkpoints/CP-P04.md` @ `0dd8d15` | **SOURCE-ONLY** |
| F13 | Evidence-induced ranking flip I_R->I_J with `choice_changed` event {prev, new, snapshot_sha, delta_reason} | `docs/checkpoints/CP-P04.md` @ `0dd8d15` | **SOURCE-ONLY** |
| F14 | `NeedBroker` public surface exposes **no** ranking/assignment API (asserted by an inspection test) | `docs/checkpoints/CP-P04.md` @ `0dd8d15` | **SOURCE-ONLY** |
| F15 | G0 baseline: 66 passed @ `a14fa6766aa3af51e92c8272f8a344fab144569a`; confirmed defects G3a (debate context never reaches prompt), G3b (vote runs full verdict engine), G4 (executable = model self-attestation), G5 (6-fixture dev set, no held-out/budgets/CIs), G1 (central dispatch) | `docs/checkpoints/CP-20261008-G0.md` @ `f2372f3` | **SOURCE-ONLY** |
| F16 | Prior art surveyed 2026-10-08: AutoScientists (arXiv:2605.28655), Co-Scientist (doi:10.1038/s41586-026-10644-y), Robin (doi:10.1038/s41586-026-10652-y), AgentRx (github.com/microsoft/AgentRx), Dubova et al. (doi:10.1177/26339137261421577); therefore **no firstness claimed** | `docs/PRIOR_ART_NOVELTY_GATE.md` @ `d992cd7` | **NO-NETWORK** (P09 did not re-verify DOIs/links online; rely on the gate doc's survey) |

**Run-branch state (P05/P06/P07/P08 components landed since the original draft). All rows
`repl-claw-dev` @ `617b329`, re-verified 2026-10-08 (second pass; first pass was @ `1012ff7`).**

| ID | Claim (as used in DRAFT_ANSWERS.md) | Source (file + commit SHA / re-run) | Status |
|---|---|---|---|
| F20 | Run-branch **full gate: 202 passed, 8 skipped; ruff clean; mypy clean (55 files)**; `p08.score --self-test` → PASS | re-run in `.` @ `617b329`: `.venv/bin/python -m pytest -o addopts="" -q` → `202 passed, 8 skipped in 13.03s`; `.venv/bin/ruff check src tests scripts` → `All checks passed!`; `.venv/bin/python -m mypy src` → `Success: no issues found in 55 source files`; `.venv/bin/python -m repliclaw.p08.score --self-test` → `SELF-TEST: PASS`, exit 0. (Prior pass @ `1012ff7` measured 149/8, 54 files — superseded by the leak-guard + runner-CLI test additions.) | **RE-VERIFIED** |
| F21 | Offline **runnable now** 4-arm deterministic matched-budget campaign: `ComparatorHarness.run(claim, envelope, root)` runs `single_agent` (S0) / `adaptive_central` (S3) / `open_sharing_swarm` (S4) / `eess` (S5 offline parity) under ONE shared `BudgetEnvelope`; re-ran it during this pass: **4 arms, `parity=True`, 0 live tokens**. **Leak-guard update:** `ComparatorHarness.run` now redacts the shared claim via `redact_claim_for_arms` (evaluator/sealed truth nulled) before any arm is constructed | `src/repliclaw/comparators/runner.py` @ `617b329` (`ComparatorHarness`, `arm_registry` = 4 keys; `redact_claim_for_arms` at line 47, applied in `run` at line 132 and in the CLI `run_one_arm` path at line 451); re-ran the harness offline on 2026-10-08 → `arms: [adaptive_central, eess, open_sharing_swarm, single_agent]`, `parity: True`, `n_arms: 4`, `tokens=0` for S0/S3/S4 | **RE-VERIFIED** |
| F22 | Wired **EESS vertical slice** (alpha/beta/gamma; H_R/H_P/H_J; COMMIT→REVEAL→EXECUTE→RESOLVE; genuine evidence-induced `choice_changed` re-rank); **runnable now** — `scripts/demo_slice.py` → `DEMO OK`, independent re-execution `PASS`; 7 slice tests green | `src/repliclaw/slice/orchestrate.py` @ `617b329`; `tests/test_slice.py` (7 tests, all in 202/8 gate); re-ran `scripts/demo_slice.py` on 2026-10-08 (second pass) → `DEMO OK` + `Independent re-execution verification: PASS` (the transient untracked run dir produced was removed; the tracked `artifacts/demo-slice/run-20261008-160137` is unchanged) | **RE-VERIFIED** |
| F23 | Matched-budget **parity machinery** is machine-checked, not claimed: `assert_budget_parity` returns `parity=True` only if every arm consumed the same envelope hash **and** none overran it; over-budget raises `BudgetOverflow` (parity never faked); 25-test P05 parity suite green (count unchanged by the runner-CLI merge — the 25 tests are the same parity suite) | `src/repliclaw/comparators/runner.py` @ `617b329` (`assert_budget_parity`); `tests/test_comparators.py` (25 tests incl. `test_parity_fails_when_envelopes_differ` @ line 222, `test_parity_fails_when_an_arm_exceeds_budget` @ line 234, `test_harness_rejects_oversized_envelope_for_swarm` @ line 296) | **RE-VERIFIED** |
| F24 | Secondary independent **Tox21 AR-agonist** deterministic case (different failure family, transfer study) present and tested; oracle sealed | `src/repliclaw/counterfactual/cases/tox21_ar_agonist/` @ `617b329` (oracle dir + `data/`); `tests/test_secondary_case.py` (7 tests, green); landed at `859aa4e` (merged into run branch) | **RE-VERIFIED** |
| F25 | **Oracle-gated scorer** `repliclaw.p08.score`: the only oracle reader, opens the oracle ONLY after every run dir is verified complete (else writes `run_manifest_incomplete.json` + `ScoreError`, no oracle touch); **`--self-test` P02 replay self-test PASSES** (exit 0); 8 tests (exact-number metrics, oracle-gate safety proof, bootstrap determinism, envelope-mismatch flag, voided-run denominator, usage-threshold). **P1 decision rule — IN-FLIGHT, not a verified fact:** at `617b329` the scorer still contains the OLD v1.1 rule, verbatim: `"S5 succeeds P1 iff bootstrap 95% CI upper bound of the 10-run interim difference (S5 minus S3 on M1) is < 0, i.e. the entire CI is below zero"` (`score.py` `diff["rule"]`, lines ~467–469; `decision_branch` at line 402 labels `hi < 0` → `"worsened"`; header reads "P1 decision (S5 vs S3 on M1)"). The v1.2-AMENDMENT (A1, DRAFT pending science-judge sign-off) supersedes this with a Δ = M1(S5) − M1(S4) rule (SUPPORTED iff CI_lower > 0; FALSIFIED iff CI_upper < 0; else NOT SUPPORTED). An in-flight worker is aligning `score.py` to the v1.2 canonical rule — **do not cite the scorer's P1 rule as the campaign rule until that alignment lands and is re-verified** | `src/repliclaw/p08/score.py` @ `617b329` (merged `3f3928b`); re-ran `.venv/bin/python -m repliclaw.p08.score --self-test` on 2026-10-08 (second pass) → `SELF-TEST: PASS`, exit 0; `tests/test_p08_score.py` (8 tests, green); P1 rule string read directly at `617b329` | **RE-VERIFIED** (scorer gate) / **IN-FLIGHT** (P1 rule alignment to v1.2 — flagged, not verified) |
| F26 | **Live-LLM arm `repliclaw.eess_live`** implemented + unit/contract-tested **offline under a FakeLLMClient (no network, no key)** — NOT a live-run claim. `EESSLiveS5Arm`/`EESSLiveA1Arm`/`EESSLiveA3Arm` (keys `eess`/`eess_no_escrow`/`eess_random_select`); 7 contract tests green (A1 pass-through never gates, A3 seeded determinism, budget-abort, invalid-usage→`invalid_usage`, S5 canonical run, artifact-set contract, shared-envelope hash); **live LLM runs NOT yet executed**. The runner CLI (`d269a15`) now wires these live keys (`LIVE_KEYS = {eess, eess_no_escrow, eess_random_select}`) to a real/fake client under the D-10 frozen pin (λ=μ=0.5, max_cycles=6, TTL=120 s) | `src/repliclaw/eess_live/arm.py` @ `617b329` (merged `d0cb054`; deviant `arms.py` removed `d3beaeb`); `tests/test_eess_live.py` (7 tests; module docstring: "offline — FakeLLMClient, no network, no key"); re-ran `pytest tests/test_eess_live.py` on 2026-10-08 → 7 passed | **RE-VERIFIED** |
| F27 | **Live campaign is SCHEDULED, not executed.** Run window **2026-10-10 → 2026-10-23** (shortenable, not extendable); **two-key start**: science-judge approval of prereg **v1.1 + v1.2-AMENDMENT** (the amendment is DRAFT and unsigned — no live run may start on v1.1 alone while it is unsigned) + human (project-lead) authorization, both recorded in `EXECUTION_STATE.md`. **Landed since the first pass:** runner CLI (`runner.main`/`run_one_arm`, `d269a15`), same-task `case_loader.py` (present at `617b329` — the first pass's "absent" finding is superseded), D-10 hyperparameter pin (λ=μ=0.5, max_cycles=6, offer TTL=120 s, `FROZEN_*` constants in `runner.py`), usage-invalidation propagation. **Still in flight:** measured live token floor; v1.2-AMENDMENT science-judge sign-off; `score.py` P1-rule alignment to v1.2 (see F25) | `docs/experiments/PREREG-2026-10-v1.1.md` @ `617b329` (§9.2 authorization+window; D-9b live arm landed; D-10 registry + hyperparam discrepancy; §12 `[PARTIAL: live-S5]`); `docs/experiments/PREREG-2026-10-v1.2-AMENDMENT.md` @ `617b329` (header: "DRAFT — requires independent science-judge sign-off BEFORE any live run"); confirmed `src/repliclaw/comparators/case_loader.py` **exists** at `617b329` (merged `d269a15`); `EXECUTION_STATE.md` next-actions | **SOURCE-ONLY** (window/authorization per prereg §9.2 + v1.2 amendment header; `case_loader.py` presence RE-VERIFIED at `617b329`) |
| F28 | **Prereg status**: v1.0 `PREREG-2026-10.md` was **REJECTED on READINESS (not merit)** by the internal science judge (8 blocking items); **v1.1** (`PREREG-2026-10-v1.1.md`) is the current re-submission **awaiting re-review**; **v1.2-AMENDMENT** (`PREREG-2026-10-v1.2-AMENDMENT.md`) is a **DRAFT** versioned amendment (corrects the P1 decision rule A1, M11→M6 label A2, S3 display label A3, post-evidence prompt condition A4, honesty framing A5, honest-semantics re-affirmation A6) that **requires independent science-judge sign-off before any live run** — after sign-off the campaign runs against "v1.1 + v1.2-AMENDMENT" as a single frozen pair; frozen hyperparameters λ=μ=0.5, max_cycles=6, TTL=120s; defaults-discrepancy documented in **D-10** | `docs/experiments/PREREG-2026-10-v1.1.md` @ `617b329` (header: "v1.1 RE-SUBMISSION — awaiting science-judge re-review"; §9.2 judge REJECT recorded in `EXECUTION_STATE.md`); `docs/experiments/PREREG-2026-10-v1.2-AMENDMENT.md` @ `617b329` (header status line read directly); `EXECUTION_STATE.md` ("SCIENCE-JUDGE-PREREG-P08: REJECT on readiness (not merit)") | **SOURCE-ONLY** |
| F29 | Novelty positioning: EESS mechanism = **escrow-gated pre-outcome commitments + provenance + local selection + matched-budget comparison**; **each piece alone is NOT novel**; no firstness; comparison vs AutoScientists / Co-Scientist / Robin / AgentRx + Dubova et al. | `docs/PRIOR_ART_NOVELTY_GATE.md` @ `d992cd7` ("Closest prior work" table + "Candidate defensible contribution (conditional)" + "Prohibited novelty claims"); `docs/EVIDENCE_ESCROW_SWARM.md` @ `0587308` ("Combined novel *candidate*, not novel-by-declaration") | **NO-NETWORK** (relies on gate doc's surveyed sources; not re-checked online) |

## B. Context / framing claims

| ID | Claim | Source | Status |
|---|---|---|---|
| F17 | Team built SimpleAudit / SimpleAuditStudio at SimulaMet (capability base for the project) | `docs/APPLICATION_V2.md` @ `1fe944c` (asserts it) | **UNVERIFIED** — **human must confirm** before submit; capability claims in Field 2/4 rest on this |
| F19 | Rubric weights 20 / 25 / 20 / 25 / 10 (+10 cross-team reuse) | `docs/EVIDENCE_ESCROW_SWARM.md` @ `0587308` (cites official site, accessed 2026-10-08) | **NO-NETWORK** — P09 could not re-check the official site; weights used only to *organize* answers, not claimed as fact in the body |

> Note: **F18 is intentionally unused** — fact IDs are assigned to claims, not slots; the draft
> now references F1–F17, F19, and F20–F29.

## C. `[PENDING]` placeholders in the draft (what resolves each)

State as of this rework (2026-10-08, `repl-claw-dev` @ `617b329`). **Resolved / removed** since the
original P09 draft are shown first — the offline campaign (P05/P07), the Tox21 secondary case (P06),
the scorer and the live arm are now **built and tested**, so their `[PENDING: …]` tokens were removed
from `DRAFT_ANSWERS.md`. What remains in the draft is honestly-worded "not yet executed" language.

| Placeholder (location) | Meaning | Status now |
|---|---|---|
| `[PENDING: P05/P08]` (was Fields 2, 3) | matched-budget comparison numbers | **REMOVED.** The **offline** 4-arm parity campaign is built + runnable (F21/F23) and the scorer is built + self-test green (F25). Only the **live** result remains, now expressed as `[PENDING: P08 live]` below — do **not** paste the offline parity numbers as the live matched-budget result. |
| `[PENDING: P06]` (was Field 2) | secondary held-out case of a different failure family | **REMOVED.** Tox21 AR-agonist deterministic case is built + tested (F24). |
| `[PENDING: P07]` (was Field 2) | wired end-to-end swarm run | **REMOVED.** The EESS vertical slice is built + runnable (`DEMO OK`, F22). |
| `[PENDING: P08]` (was Field 2) | token/cost metering + live-model run | **REMOVED / re-scoped.** The live arm is implemented + tested (F26) and the metering/oracle-gate lives in the scorer (F25); **no live run has been executed** — see `[PENDING: P08 live]`. |
| `[PENDING: P08 live]` (Field 3) | the **live** matched-budget result (escrow swarm vs adaptive central manager + ablations) at a measured token budget | **P08 live runs** — in the run window 2026-10-10→23, gated on judge + human authorization (F27). Landed since the first pass: runner CLI, same-task `case_loader`, usage-invalidation, D-10 hyperparameter pin (F27). Still in-flight before the window can open: measured live token floor, v1.2-AMENDMENT science-judge sign-off, `score.py` P1-rule alignment to v1.2 (F25/F27/F28). Report only after measured; a null/negative result is equally valid. |
| `[PENDING: TEAM]` (Fields 2, 4) | exact teammate names, roles, profiles, and which Field-4 boxes to tick | **human team** (unchanged) |
| `[PENDING: ORGANIZER]` (Field 1) | challenge-area selection | **organizer / official form** (unchanged) |
| `[PENDING: P11/external-reuse]` (Field 5) | evidence another team actually reused the component | **P11** external-team reuse — no external reuse yet (unchanged) |

Ticket status source: `EXECUTION_STATE.md` (re-verified 2026-10-08, current) — the P02–P08 modules
are on the run branch; the live window is pre-flight with the runner CLI / `case_loader` /
usage-invalidation / D-10 pin now **landed** (`d269a15`), leaving the measured token floor,
v1.2-AMENDMENT sign-off, and the `score.py` P1-rule alignment still in flight (F25/F27). The older
`IMPLEMENTATION_PLAN.md` statuses (P05 IN_PROGRESS, P06 IN_PROGRESS, P07/P08 NOT_STARTED) are **stale**
and are no longer the source of record.

---

## D. Ambiguities found in `docs/APPLICATION_V2.md` (source: @ `1fe944c`)

The draft follows the doc's structure **verbatim**; these are recorded here per the task brief.

| ID | Ambiguity | How P09 handled it |
|---|---|---|
| A1 | Doc has **5 "Field" sections**, but its own submission checklist says "three long free-text answers" (Fields 1-3; Field 4 is a set of checkboxes; Field 5 is short). | Drafted all **5** fields so nothing is missing; human trims to the form's actual fields (see A4). |
| A2 | No explicit **project-title** field in the doc. | Added a short **Naming / title** block with a fallback title so the human can override. |
| A3 | **Challenge area** may not be a form field at all. | Left as `[PENDING: ORGANIZER]`; do not hard-code a choice. |
| A4 | Official form's exact **field order, character limits, and required media** unknown. `scienceclawhack.ai/apply.html` is authoritative and **P09 had no network access**. | Draft is written to be *paste-able* into any field order; human must confirm limits on the live form. |
| A5 | Event window **Oct 30-Nov 1**, application **deadline 2026-10-16**, decisions **Oct 19** (per the doc). | Taken at face value from the doc; **human must confirm on the official site** (no network re-verify). |
| A6 | **Date discrepancy:** P02/P03/P04 checkpoint *headers* are dated **2026-10-10**, but the git commit dates (and P09's re-verification) are **2026-10-08**. | Draft uses "as of **2026-10-08**" consistently (the reproducible, commit-backed date). Human should reconcile the checkpoint header dates. **Still applies after this rework:** all new run-branch rows (F20–F29) cite the commit-backed date 2026-10-08 and the run-branch SHA `617b329` (first pass: `1012ff7`); note the prereg itself names the *live-run* window 2026-10-10→23, which is a *schedule*, not a commit date — do not conflate the two "10-10"s. |
| A7 | **Offline-arm naming.** The offline S5 comparator is registered under key **`eess`** by `comparators.managers.EESSArm` / `comparators.runner.arm_registry()` on the run branch; prereg v1.1 calls it **`eess_offline`**. **Updated at `617b329`:** `case_loader.py` now **exists** (merged `d269a15`), and the runner CLI's `ARM_ALIASES` accepts `eess_offline` as an alias that routes to `EESSArm` (the offline 0-token parity arm, v1.1 §3.3) — but `arm_registry()` itself still exposes only the 4 keys `single_agent` / `adaptive_central` / `open_sharing_swarm` / `eess`. | Draft names the offline parity arm by its **actual run-branch registry key `eess`** (F21) and describes it as "the offline parity arm", matching both the code and the prereg's intent. `eess_offline` is now a valid CLI alias (not a distinct registry key) and `case_loader.py` is present (F27) — but do not paste `eess_offline` as if it is a distinct `arm_registry()` key. |
| A8 | **"Implemented + tested" vs "live runs executed."** A live arm that is unit/contract-tested under a fake client can be (and was, in the stale draft) read as if live runs happened. | Draft **always** qualifies the live arm as "implemented + unit/contract-tested offline under a fake client (no network, no key)" and states "live LLM runs have NOT been executed" (F26). The three states — (a) built+tested, (b) runnable offline, (c) scheduled live — are never merged. |

## E. Things explicitly **not** done (so no one mistakes a gap for a check)

- Did **not** execute any **live** LLM run — the live arm (F26) is only contract-tested under a
  fake client; "live runs executed" is **not** claimed and is a `[PENDING: P08 live]` item.
- Did **not** start the live window — no judge approval / human authorization recorded yet (F27/F28);
  the runner CLI / `case_loader.py` / usage-invalidation / D-10 pin are now **landed** (`d269a15`),
  but the measured token floor, the v1.2-AMENDMENT sign-off, and the `score.py` P1-rule alignment
  (F25) are **not** presented as done.
- Did **not** treat the **offline** 4-arm parity numbers (F21/F23) as the **live** matched-budget
  result — the offline campaign is feasibility/parity evidence only.
- Did **not** re-run `replay.sh` (regenerates artifacts outside owned paths) -> F5 is SOURCE-ONLY.
- Did **not** re-execute the P04 subprocess/SIGKILL experiments -> F11-F14 are SOURCE-ONLY.
- Did **not** verify any DOI, arXiv ID, or the official site online (no network) -> F16, F19, F29, A5
  are NO-NETWORK.
- Did **not** confirm team member identities/roles -> F17, `[PENDING: TEAM]` are UNVERIFIED.
- **Did** re-run, on `repl-claw-dev` @ `617b329` (2026-10-08, second pass): the full gate (202/8),
  ruff (clean), mypy (55 files), the scorer `--self-test` (PASS), `pytest tests/test_eess_live.py`
  (7 passed), the offline `ComparatorHarness` 4-arm run (`parity=True`, 0 tokens), and
  `scripts/demo_slice.py` (`DEMO OK`). The transient untracked run dir that `demo_slice.py` created
  was removed; only `docs/application/**` was edited. (First pass @ `1012ff7` measured 149/8,
  54 files — superseded.)
- Did **not** edit any path outside `docs/application/**`.
