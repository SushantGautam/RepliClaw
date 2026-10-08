# RepliClaw — ScienceClaw 2026 Application: DRAFT ANSWERS

**Status:** DRAFT for human review/fact-check/submit. **NOT submitted.** Prepared 2026-10-08.
Companion files: `FACT_CHECK_LIST.md` (every claim → file + commit SHA or UNVERIFIED) and
`SUBMISSION_CHECKLIST.md` (step-by-step human submission procedure).

**How to read this file.**
- Paste-ready prose is in each `## Field N` block. Strip the grayed "Verified-fact basis"
  bullets and all `[PENDING: …]` tokens before pasting into the official form.
- Every number used below is either (a) a verified result from a checkpoint, or (b) an
  explicit `[PENDING: <ticket>]` placeholder. No invented numbers.
- Claims are scoped ("as of 2026-10-08, across the surveyed prior art…"). We never claim
  firstness, reviewer approval, or competition success.
- Date note: commit author/committer dates are 2026-10-08 (today). The P02/P03/P04 checkpoint
  headers are dated 2026-10-10; this mismatch is flagged in `FACT_CHECK_LIST.md` (A6). We use
  "as of 2026-10-08" for public scoping.
- **State note (2026-10-08, run branch `repl-claw-dev` @ `1012ff7`):** the per-module gates
  below (P02/P03/P04, 78/73/74) are *historical module checkpoints*. Since the draft was first
  written, P05/P06/P07/P08 components have landed on the run branch. The **run-branch full gate
  is 149 passed, 8 skipped; ruff clean; mypy clean (54 files)** and the scorer self-test passes
  (`p08.score --self-test` → PASS). We distinguish, and keep distinct, three things:
  (1) *implemented + unit/contract-tested offline* (the live-LLM arm, scorer),
  (2) *runnable deterministic now* (the offline campaign), and
  (3) *scheduled for the live window, not yet executed* (the live LLM runs). See F20–F28 in
  `FACT_CHECK_LIST.md`.

**Project name / one-line claim** (per `docs/APPLICATION_V2.md` "Naming"):
- Project: **RepliClaw: an Evidence-Escrow Scientific Swarm**
- Short claim: "Autonomous scientists that predict before they believe, intervene before they
  conclude, and show which evidence changed their minds."
- Attribution: we keep Hans's "Decentralized Hypothesis Swarm" concept and authorship attributed
  to Hans in team docs. **Challenge area:** Open Scientific Challenge / decentralized scientific
  collectives — but the application form may not ask for a challenge-area choice
  (`[PENDING: ORGANIZER]` confirm).

---

## Field 1 — What is a difficult, meaningful problem you would like to solve at the hackathon, and why is it significant?

AI systems can fail for several plausible reasons at once — wrong retrieval, conflicting or
stale instructions, flawed reasoning, or even a mistaken evaluator — yet many audits report a
score without discovering *which* mechanism actually caused the failure. A single confident
post-hoc explanation can be wrong, and a group of agents sharing early conclusions can amplify
that mistake into a false consensus.

We want to solve **causal diagnosis of AI failures**: given a reproducible failure, determine
which factor (retrieval vs. policy/instruction conflict vs. evaluator/judge error) actually
produced the bad output, and show the evidence that changed our mind. We approach it with a
decentralized scientific collective — **RepliClaw, an Evidence-Escrow Scientific Swarm** — in
which agents create competing falsifiable hypotheses, **commit to their predicted intervention
outcomes before seeing any peer's unpublished findings**, execute controlled counterfactual
interventions through a frozen auditor, and publish only execution-verified observations to a
shared ledger. Each agent then chooses its next experiment locally from the updated evidence,
and the coordination service enforces leases, budgets and atomic task claims but never prescribes
the research trajectory.

This is scientifically significant because it asks a concrete, measurable question: **does
autonomous, evidence-driven, pre-outcome-committing coordination improve *validated* causal
explanations (rather than merely increasing persuasive agreement), and is it worth its cost
compared to a strong adaptive central manager?** Under the rubric weights we were given
(Problem significance 20%, Impact 25%, Decentralized agency 20%, Collective capability 25%,
Execution 10%), a faithful matched-budget comparison with ablations is the load-bearing result.
We treat a negative or null result as an equally valid, publishable answer.

<sub>Verified-fact basis (strip before submit): rubric weights 20/25/20/25/10(+10) —
`docs/EVIDENCE_ESCROW_SWARM.md` "Rubric evidence obligations" [F19]. Mechanism description —
`docs/EVIDENCE_ESCROW_SWARM.md`, `SEED_PROMPT.md`.</sub>

---

## Field 2 — What have you built, researched, or accomplished that demonstrates your ability to tackle this problem?

**Team.** Our team combines AI-safety and multimodal-AI research, auditing infrastructure, agent
engineering, and scientific/product design. At SimulaMet we have developed **SimpleAudit and
SimpleAuditStudio** for reproducible AI-system auditing (scenario-based evaluation, run tracking,
evidence analysis) [F17 — human to confirm]. `[PENDING: TEAM]` — exact teammate names, roles,
backgrounds, and public profile links to be inserted before submission; we do not add unsupported
metrics or prizes.

**What is already built and machine-verified (as of 2026-10-08, run branch `repl-claw-dev` @
`1012ff7`).** We have a working, test-verified vertical prototype built on ScienceClaw primitives
— not a claim of superiority. The module gates below (P02/P03/P04) are the historical per-module
checkpoints; since then the components have been integrated on the run branch, whose **full gate
is 149 passed, 8 skipped; ruff clean; mypy clean (54 files)**, with the scorer self-test passing
[**F20**]. The building blocks:

- **Real SimpleAudit counterfactual execution (P02, module checkpoint @ `3f452b2`).** We drive a
  real `ModelAuditor.run_scenario` (SimpleAudit engine 0.3.3 pinned) with a deterministic RAG
  target and a frozen offline judge, so each intervention is a genuine, replayable execution — not
  a model self-report of "executable". Module gate: **78 passed, 8 skipped**; ruff clean; mypy
  clean (21 files) [F1]. On one controlled case (a returns-policy RAG assistant that cites a stale
  14-day window because retrieval omits the current 30-day doc), the five-arm canonical run
  **discriminates the cause factor**: fixing retrieval (I_R) changes the target output 14d→30d;
  changing the judge's reference (I_J) leaves the output byte-identical but flips the verdict
  (showing the baseline "pass" was an evaluator artifact); changing policy conflict resolution
  (I_P) leaves the output byte-identical (ruling that factor out); retrieval + judge together (I_C)
  pass. The canonical run replays byte-identical (sha256-pinned), and the ground-truth oracle is
  sealed and never on any code path [F4][F5][F6][F7].
- **Evidence-escrow ledger (P03, module checkpoint @ `ba71a4d`).** Pre-outcome prediction packets
  follow a COMMIT→REVEAL→EXECUTE→RESOLVE protocol with byte-level pre-reveal isolation,
  tamper-detecting hash chaining, and deterministic content-addressed snapshots. Module gate:
  **73 passed, 8 skipped**; ruff clean; mypy clean (20 files) [F2]. We are explicit about what it
  does **not** guarantee: it detects tampering but does not prevent it, and it does not establish
  wall-clock ordering, process isolation, or epistemic independence [F8][F9][F10].
- **Decentralized need market (P04, module checkpoint @ `1b48ac2`).** Agents rank unmet needs
  locally and claim work atomically; two **real OS subprocesses** racing one `O_EXCL` claim
  produced exactly one winner with no partial lock files, a SIGKILL crash matrix exercised lease
  expiry and a generation-2 re-claim, and we observed a genuine evidence-induced ranking flip
  (I_R→I_J) recorded with the prior and new ranking and the snapshot hash that caused it. The
  broker exposes **no** ranking/assignment API, so the service enforces but does not direct.
  Module gate: **74 passed, 8 skipped**; ruff clean; mypy clean (22 files) [F3][F11][F12][F13][F14].

**Integrated on the run branch now (2026-10-08).** Beyond the modules above, the following are
committed on `repl-claw-dev` and green under the 149/8 full gate [F20]:

- **A runnable offline, deterministic, matched-budget comparison campaign (0-token, no network).**
  The comparator harness runs the four named offline arms — **S0 single-agent (`single_agent`),
  S3 adaptive central manager (`adaptive_central`), S4 open-sharing swarm (`open_sharing_swarm`),
  and S5 EESS** (offline parity arm `eess`) — under ONE shared frozen `BudgetEnvelope`, and emits
  a machine-checked **budget-parity report** (parity is true only if every arm consumed the same
  envelope hash and none overran it; parity is never faked) [**F21**][**F23**]. It is runnable
  today; we ran it during this fact-check and all four arms returned with `parity=True` and 0 live
  tokens. This is the *feasibility + offline-parity* arm, **not** the live primary subject.
- **A wired EESS vertical slice (end-to-end):** three agents (alpha/beta/gamma) holding the
  competing falsifiable hypotheses **H_R (retrieval), H_P (policy conflict), H_J (judge error)**,
  committing pre-outcome packets, executing real SimpleAudit arms, and resolving with a genuine
  evidence-induced re-rank (a `choice_changed` event with the causing snapshot hash). Runnable now
  via `scripts/demo_slice.py` (prints `DEMO OK`, re-verified by independent re-execution) [**F22**].
- **A secondary, independent, deterministic case (Tox21 AR-agonist functionalization)** as a
  transfer study of a different failure family [**F24**].
- **An oracle-gated scorer (`repliclaw.p08.score`).** It is the *only* code path that may read the
  sealed oracle, and only after every run directory under every arm is verified complete — on any
  gap it writes `run_manifest_incomplete.json` and aborts without touching the oracle. Its
  **P02 replay self-test passes** (`python -m repliclaw.p08.score --self-test` → `SELF-TEST:
  PASS`) and it is covered by 8 exact-number/oracle-gate tests [**F25**].
- **A LIVE-LLM arm, `repliclaw.eess_live`** — the escrowed EESS full protocol with the A1
  no-escrow and A3 random-select scaffolds (`EESSLiveS5Arm` / `EESSLiveA1Arm` / `EESSLiveA3Arm`,
  registry keys `eess` / `eess_no_escrow` / `eess_random_select`). It is **implemented and
  unit/contract-tested offline under a fake LLM client (no network, no key)** — 7 contract tests
  green (escrow pass-through never gates, A3 seeded determinism, budget abort, invalid-usage
  invalidation, canonical run, artifact-set contract, shared-envelope hash) [**F26**]. **We state
  this precisely: the live arm is *implemented + tested*; the *live LLM runs themselves have NOT
  been executed yet.***

**Honesty about limits.** These are foundations, not proof of scientific advantage. The baseline
we started from (G0, `a14fa676`) passed 66 tests but we confirmed real defects (peer conclusions
never reached the debate prompt, the "isolate-and-vote" mode ran the full verdict engine, the
"executable" flag was model self-attestation, and the evaluation was a 6-fixture dev set with no
held-out split, no budget parity, no confidence intervals) [F15]. What is and is **not** a
measured result, precisely:

- **Measured now (offline/deterministic):** the parity machinery (arms under one shared envelope,
  parity report), the four-arm offline campaign, the end-to-end EESS slice, the Tox21 secondary
  case, and the scorer + its P02 replay self-test — all green on the run branch [F20][F21][F22][F23][F24][F25].
- **Implemented + tested, but NOT yet run live:** the live-LLM EESS arm (S5/A1/A3). It is
  contract-tested under a fake client only; **no live LLM run has been executed** [F26].
- **Still to be measured (the actual headline result):** the **live** matched-budget comparison —
  escrow swarm vs. a strong adaptive central manager, plus single-agent, open-sharing and
  no-escrow / random-select ablations, on the live model at a measured token budget. That is
  **scheduled for the run window (2026-10-10 → 2026-10-23) and is gated on two keys: science-judge
  approval of prereg v1.1 + human (project-lead) authorization** [F27][F28]. Also in flight before
  the window can open: the runner CLI, the same-task `case_loader`, usage-invalidation wiring, the
  D-10 hyperparameter pin (λ=μ=0.5, max_cycles=6, offer TTL=120s), and a measured live token floor
  — none of these are yet complete [F27].

We will report whatever the live runs produce, including null or negative results. **We do not
present the implemented-and-tested live arm as if live runs have been executed, and we do not
present the offline parity numbers as the live matched-budget result.**

**Research / prior-art posture.** As of 2026-10-08, across the prior art we surveyed
[F16][F29] — **AutoScientists** (decentralized long-running agents that self-organize around
hypotheses, share experimental state and run controlled, budgeted, ablated experiments),
**Co-Scientist** (an asynchronous, specialized agent coalition with debate/tournaments and a
central supervisor), **Robin** (end-to-end iterative hypothesis → experiment → analysis →
update), and **AgentRx** (debugging agent trajectories with executable constraint checks and fault
localization), plus the experiment-selection theory of Dubova et al. — decentralized and
self-organizing multi-agent science already exists. We therefore **do not claim firstness**, and we
are explicit that **each individual piece of our mechanism is not novel on its own**: pre-outcome
commitment has prior art, open-sharing swarms are AutoScientists' model, executable
constrained-checks debugging is AgentRx' model, and a utility/ranking heuristic is neither novel
nor our claim. Our scoped, testable contribution is the **combination and evaluation** of the
**Evidence-Escrow mechanism** — *escrow-gated pre-outcome commitments* (predictions sealed until
a phase boundary, execution-verified before entering a shared ledger) **+ provenance** (every
published observation carries its run/config/artifact hashes) **+ local, evidence-driven
selection** (agents re-rank and atomically claim their next experiment from the updated evidence;
the broker enforces leases/budgets but never ranks the science) **+ a matched-budget comparison**
against a strong adaptive central manager and the open-sharing and ablation arms. We test whether
that specific combination — *predict before you believe, intervene before you conclude, and show
which evidence changed your mind* — improves *validated* causal diagnosis of AI failure relative to
each named prior system's paradigm. This is an honest boundary claim, not a novelty-by-declaration.

<sub>Verified-fact basis (strip before submit): all per-fact source + commit SHA are in
`FACT_CHECK_LIST.md` F1–F19 (historical modules) and F20–F28 (run-branch live-arm, scorer,
offline campaign, Tox21, window). Do not submit any number without a matching green entry there.
"Implemented + tested" and "live runs executed" are distinct claims — only the former is made
for the live arm.</sub>

---

## Field 3 — Why would a decentralized agent collective be particularly well-suited to solving this problem?

A trustworthy causal diagnosis needs **competing** explanations to be tested before the group
converges. If agents share early interpretations freely, a plausible-but-wrong root cause can
propagate and crowd out the rival that would have been falsified by a cheap test. Decentralization
helps in three specific ways we can actually measure:

1. **Pre-outcome commitment prevents anchoring.** Each investigator privately commits a
   canonical prediction packet *before* seeing a peer's unpublished finding or an experiment
   outcome. Our escrow ledger enforces this at the protocol level (byte-level pre-reveal
   isolation, verify/preserve with no post-hoc amendment, tamper detection) [F8][F9][F10].
2. **Local, evidence-driven reallocation.** After execution-verified evidence enters the shared
   ledger, each agent re-ranks the unmet needs on its own and claims the next experiment
   atomically. We observed a genuine, non-scripted evidence-induced pivot (I_R→I_J) recorded with
   the snapshot hash that caused it, and the broker exposes no ranking API, so the infrastructure
   enforces leases/budgets but never chooses the science [F13][F14].
3. **Specialization + honest comparison.** Agents can specialize across retrieval, policy
   reasoning, evaluator validity and statistical testing with distinct tools. Critically, we
   compare the escrow swarm against a **strong adaptive central manager** with the same tools,
   evidence, concurrency and budget — plus single-agent, open-sharing, no-escrow and random-select
   variants (the DAG / no-local-choice / no-verified-evidence variants are defined in the prereg
   but only a subset are built now). The **offline, deterministic** parity comparison of the four
   named arms is implemented and runnable now [F21][F23]; the **live** matched-budget comparison
   and its ablation numbers are the pending measured result, scheduled for the run window (see
   Field 2) [PENDING: P08 live]. The ablations, not the architecture, tell us whether independent
   commitments and local selection actually help; if not, we report the limitation.

We are explicit about the boundary of the claim: a hash proves later consistency of a packet, not
secrecy or epistemic independence; and "causal" here means *distinguished by controlled executed
interventions with documented confound controls*, not "proven" in a philosophical sense.

<sub>Verified-fact basis (strip before submit): F8–F14 in `FACT_CHECK_LIST.md`. Comparator design
— `docs/EXPERIMENT_PROTOCOL_V2.md`, `SEED_PROMPT.md` (S0–S5). Escrow guarantees/limits —
`docs/checkpoints/CP-P03.md`, `docs/fleet/P03.md`.</sub>

---

## Field 4 — What expertise or capabilities would you bring to a team?

`[PENDING: TEAM]` — select **only** boxes that match confirmed teammates; do not invent
backgrounds. Available options (from the application guide):
- [ ] AI / Machine Learning
- [ ] Agentic Systems
- [ ] Software / Coding
- [ ] Data Science
- [ ] Scientific Research / Experimentation
- [ ] Product / Entrepreneurship *(only if an actual team member has this skill)*
- [ ] Design / UX *(only if an actual team member has this skill)*

Working hypothesis to confirm (NOT a final answer): AI/ML, Agentic Systems, Software/Coding,
Scientific Research/Experimentation are supported by the team's SimpleAudit/SimpleAuditStudio
and RepliClaw work [F17]; Data Science, Product and Design/UX are **unconfirmed** and should only
be checked for named team members who genuinely hold them.

<sub>Verified-fact basis: capability *claims* rest on [F17], which the human must confirm.
Checkbox selection is a team decision, not something we may fabricate.</sub>

---

## Field 5 — What kind of collaborator or expertise would complement you?

We would be strengthened by a collaborator with **experimental-design / causal-inference**
expertise or **red-team evaluation** skill, or with a **scientific domain that supports controlled,
reproducible interventions** — any of which would sharpen our independent validation and external
stress-testing of the matched-budget comparison and the causal claims. We would also welcome
another ScienceClaw team to reuse our **portable verification endpoint**; if a second team actually
uses it, that is a measurable, honest signal (and a possible +10 cross-team term) that our
component contributes to the event ecosystem — we will only report external reuse if it genuinely
occurs. `[PENDING: P11/external-reuse]` — no external team has used it yet.

<sub>Verified-fact basis (strip before submit): +10 cross-team term and "actual other-team reuse"
— `docs/EVIDENCE_ESCROW_SWARM.md` "Rubric evidence obligations" [F19]. External reuse is currently
NOT demonstrated.</sub>

---

## Naming / title (for the form, if there is a title field)

- **Title (if required):** RepliClaw: An Evidence-Escrow Scientific Swarm for Causal Diagnosis of
  AI Failures
- **Short claim:** "Autonomous scientists that predict before they believe, intervene before they
  conclude, and show which evidence changed their minds."
- **Fallback title if the review weakens the novelty case:** "A controlled empirical study of
  evidence escrow and decentralization in agentic AI auditing." (We only use this if the pre-
  submission review concludes the novelty case is weak; it remains scientifically defensible even
  without a superiority result.)

---

## Global honesty constraints (applies to every field above)

- We do **not** claim: first decentralized AI scientist; first agent-swarmed hypothesis
  generation; "proven to beat central workflows"; "cryptographic guarantees of reasoning
  independence"; or "actual causal proof from LLM opinions alone." (Per
  `docs/PRIOR_ART_NOVELTY_GATE.md` "Prohibited novelty claims".)
- We distinguish three states, and never blur them: (a) **already built, integrated and
  machine-verified on the run branch** (P02/P03/P04 modules + P05 comparators/parity, P06 Tox21
  case, P07 end-to-end slice, P08 scorer + self-test, P08 live-LLM arm *implemented and
  contract-tested offline*); (b) **runnable deterministic now** (the offline 4-arm parity
  campaign and the slice demo, 0-token); (c) **scheduled for the event window, not yet executed**
  (the *live* matched-budget runs, gated on judge + human authorization). "Implemented + tested"
  is never written as "live runs executed."
- No number without a green entry in `FACT_CHECK_LIST.md`; anything unresolved is an explicit
  `[PENDING: …]`.
