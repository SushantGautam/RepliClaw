# RepliClaw quality gates and independent judges
A gate is **PASS** only with an artifact and a verifiable command/result, not a written assurance. Statuses: NOT_STARTED / RUNNING / PASS / FAIL / BLOCKED_EXTERNAL. Reviewers must cite code locations and give `BLOCKER / MAJOR / MINOR`.

## Stage G0 — Reproduce before editing
Record current branch/SHA/status, environment and locked dependencies. Run:
```bash
python -m pytest -q
ruff check src/repliclaw/ tests/
mypy src/repliclaw/
```
Record exact pass/fail instead of copying historical 66-test claim. If commands unavailable, log the missing dependency and next diagnostic. No baseline scores without the corresponding stored artifact/run manifest.

## Stage G1 — Red test / contract
For each P0 ticket, demonstrate current incorrect behavior (or a test that fails for the missing feature). Define public interfaces and backward-compatibility checks. Reviewer verifies the test actually exercises the alleged defect.

## Stage G2 — Unit and negative-path checks
Test normal case, error/abstention, replay/tamper, race/retry, empty evidence, malformed LLM response and resource limits as applicable. No weakening existing tests to pass.

## Stage G3 — Integration evidence
Run a complete vertical path claim → independent investigation → commitment → reveal → conflict/need → independent fulfillment → executable evidence → verdict. Validate need ownership, deduplication, provenance, cancellation and retry across worker restarts. Assert chronological commitment ordering and deny pre-reveal access.

## Stage G4 — Scientific QA
- Ground-truth labels/held-out splits, domains, dataset licenses and preprocessing documented.
- No reference truth, seeded fault flag or label leak to any investigator.
- Fair baselines: equalized model/tool/cost caps, faithful peer sharing in debate, no artificial crippling.
- Actual executable artifacts: command, environment, hash, logs, output, independent result check; LLM self-reports are not execution proof.
- Correct denominator for false acceptance/refutation and recovery; separate errors from abstention; paired runs and uncertainty intervals.
- Report both successes and failures; confidence must be calibrated or named a heuristic score.
- Science judge must challenge alternative explanations (additional compute, different data access, evaluator peeking, posthoc case selection).

## Stage G5 — Engineering QA (independent)
Review reliability, secrets handling, prompt/tool injection, subprocess isolation limitations, runaway agent loops, idempotency, duplicate messages, file write races, clean install, API changes, OTel behavior, human reproducibility. If a reviewer finds BLOCKER/MAJOR, worker repairs and reruns checks; author cannot self-approve a P0 ticket.

## Stage G6 — Release/demo readiness
- Clean fresh environment reproducibility check;
- `python -m pytest -q`, ruff, mypy, integration checks all PASS;
- at least one real case replicated from captured artifacts;
- sample commands and live demo agree with saved result;
- real independent peer/third-party reuse documented or collaboration explicitly labeled NOT YET DEMONSTRATED;
- no fabricated metrics, timestamps, citations or claimed integrations;
- official final hand-in instructions freshly verified and recorded.

## Judge scorecards (not self-congratulatory scoring)
**Scientific judge:** SIGNIFICANCE / ACTUAL_RESULT / EVIDENCE / CAUSALITY_OF_COLLECTIVE / REPRODUCIBILITY / GENERALIZATION. For each, report `PASS/WEAK/FAIL`, reproducible counterexample, bias/leakage risk and correction.
**Code judge:** FUNCTIONALITY / SECURITY / CONCURRENCY / CORRECTNESS / CONTRACTS / TEST_QUALITY / MAINTAINABILITY. Report actionable file:line evidence, high-impact defects, exact reproduction, suggested regression.
**Rubric judge:** predicted readiness (not invented official score) against organizer weights 20/25/20/25/10 plus possible +10 cross-team; grade only observed evidence, with links to the particular run/artifact.

### Review report template
```md
# Review: <ticket / branch / commit>
Reviewer role: <role>; different session/model from author when available
Scope and observed commands:
Blockers: <file:line, behavior, repro>
Majors:
Minors:
Scientific concerns (fairness, evidence):
Gate result: PASS | FAIL | BLOCKED_EXTERNAL
Required remediation:
Independent re-review evidence:
```

## Gate evidence and accountability
After each stage, write results to `docs/checkpoints/CP-<id>.md` and append a short entry to `PROGRESS.md`. State must contain links and SHA, not unsupported 'passed' statements. Independent reviewers use read-only worktrees/sessions; integrations require explicit orchestrator sign-off. No false 'judge approval'.

## G-v2 additions — mandatory before declaring a scientific finding
- Novelty skeptic must read AutoScientists, Co-Scientist, Robin, AgentRx and explain precise non-overlap/limits in a review artifact.
- Pre-outcome private predictions must be committed before seeing peer unpublished hypotheses, with event chronology verified; hash consistency alone is not true isolation.
- Real frozen SimpleAudit interventions must be executed, independently replayable and causally discriminative; model's own executable flag is insufficient.
- Validate independent **local choice changes** under controlled before/after evidence snapshots; server may enforce leases/budget but not choose scientific experiments.
- Strong central adaptive manager must receive same tools, evidence, worker slots and resources as escrow swarm. Include open-sharing, no-escrow and random policies.
- Never leak planted causes, hidden rubric or truth into prompts, worktrees or tools. Benchmark labels belong only to evaluator.
- Review raw actual run traces with every scientific claim. Reject unsupported '100% competition winner' claims; disclose ties, failures and missing final submission instructions.
