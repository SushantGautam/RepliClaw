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

## B. Context / framing claims

| ID | Claim | Source | Status |
|---|---|---|---|
| F17 | Team built SimpleAudit / SimpleAuditStudio at SimulaMet (capability base for the project) | `docs/APPLICATION_V2.md` @ `1fe944c` (asserts it) | **UNVERIFIED** — **human must confirm** before submit; capability claims in Field 2/4 rest on this |
| F19 | Rubric weights 20 / 25 / 20 / 25 / 10 (+10 cross-team reuse) | `docs/EVIDENCE_ESCROW_SWARM.md` @ `0587308` (cites official site, accessed 2026-10-08) | **NO-NETWORK** — P09 could not re-check the official site; weights used only to *organize* answers, not claimed as fact in the body |

> Note: **F18 is intentionally unused** — fact IDs are assigned to claims, not slots; the draft
> references F1–F17 and F19.

## C. `[PENDING]` placeholders in the draft (what resolves each)

| Placeholder (location) | Meaning | Resolved by |
|---|---|---|
| `[PENDING: P05/P08]` (Fields 2, 3) | matched-budget comparison numbers (escrow swarm vs strong adaptive central manager, + variants) | **P05** fair strong comparators (IN_PROGRESS) + **P08** real baselines/ablations (NOT_STARTED) |
| `[PENDING: P06]` (Field 2) | secondary held-out case of a different failure family | **P06** (IN_PROGRESS) |
| `[PENDING: P07]` (Field 2) | wired end-to-end swarm run (escrow -> need market -> P02 executor -> comparators) | **P07** integration (NOT_STARTED) |
| `[PENDING: P08]` (Field 2) | real token/cost metering + live-model run | **P08** (NOT_STARTED) |
| `[PENDING: TEAM]` (Fields 2, 4) | exact teammate names, roles, profiles, and which Field-4 boxes to tick | **human team** |
| `[PENDING: ORGANIZER]` (Field 1) | challenge-area selection | **organizer / official form** |
| `[PENDING: P11/external-reuse]` (Field 5) | evidence another team actually reused the component | **P11** external-team reuse (NOT_STARTED) |

Ticket status source: `IMPLEMENTATION_PLAN.md` (P05 IN_PROGRESS, P06 IN_PROGRESS, P07 NOT_STARTED,
P08 NOT_STARTED, P11 NOT_STARTED) — read by P09 2026-10-08.

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
| A6 | **Date discrepancy:** P02/P03/P04 checkpoint *headers* are dated **2026-10-10**, but the git commit dates (and P09's re-verification) are **2026-10-08**. | Draft uses "as of **2026-10-08**" consistently (the reproducible, commit-backed date). Human should reconcile the checkpoint header dates. |

## E. Things P09 explicitly did **not** do (so no one mistakes a gap for a check)

- Did **not** re-run `replay.sh` (regenerates artifacts outside P09's owned paths) -> F5 is SOURCE-ONLY.
- Did **not** re-execute the P04 subprocess/SIGKILL experiments -> F11-F14 are SOURCE-ONLY.
- Did **not** verify any DOI, arXiv ID, or the official site online (no network) -> F16, F19, A5 are NO-NETWORK.
- Did **not** confirm team member identities/roles -> F17, `[PENDING: TEAM]` are UNVERIFIED.
- Did **not** edit any path outside `docs/application/**`.
