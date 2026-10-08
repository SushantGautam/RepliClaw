# RepliClaw — Active execution state
Last updated: 2026-10-08 15:05
status: PAUSED (pre-pivot checkpoint complete; awaiting PR #1 migration)
program: ScienceClaw competition readiness — OLD program (superseded by PR #1 Evidence-Escrow pivot; do NOT resume old tickets)
full_inventory: docs/checkpoints/CP-PRE-PIVOT-20261008-fleet.md (authoritative resume record)
branch: repl-claw-dev
HEAD: 2ccb629 (F04 merged; fleet contracts 2ba5847; test baseline a14fa67)
current_milestone: Wave A — F04 integrated; F01 awaiting science judge; F02/F03/F05 workers running
gate: G0 PASS (66 passed, ruff/mypy clean @ a14fa67); post-F04-merge: 66 passed + 8 skipped, ruff/mypy clean @ 2ccb629
current_ticket: F01 (judging), F02 (W2 running), F03 (W3 running), F05 (W5 running)
done_workers: W4 F04 @ 0ca2e61 MERGED (Code+Science PASS)
repair_rounds:
  - W1 F01 @ 6fad37f — Code PASS; Science PASS w/ 4 Majors → R1 dispatched (audit includes_peer_materials, PhaseGate guard, handoff disclosure, test sentinel+flag-pinning). BOTH judges re-review after.
  - W5 F05 @ 083b4aa — Code PASS (no blockers); Science PASS conditional w/ 1 MAJOR → R1 dispatched (paired-McNemar F08 hook + claim_freeze.json + CI/p-value/label minors). Re-review after.
f08_carry_overs: (a) Tox21 case arms are PAIRED — F08 falsifier must use McNemar (b=9, c=25, p=0.009), not independent two-arm RR; (b) statistician/analyst need mean_*/sd_*/n keys + a claim-threshold slot the lens can consume (code-judge M1); (c) metrics.json now carries paired_discordant + n_pairs.
running_workers: W1 F01 R1, W2 F02, W3 F03, W5 F05 R1
worker_contracts: docs/fleet/README.md + docs/fleet/F01..F05.md
integration_owner: primary VS Code orchestrator session (this session); merges F01→F02→F03→F05; F06 ticket must carry the 8 F04 carry-over items (see CP-20261008-F04.md)
latest_checkpoint: docs/checkpoints/CP-20261008-F04.md
next_action: (1) F01 science judge verdict → merge w1/F01-baseline-validity + full gate + checkpoint. (2) Await W2/W3/W5 handoffs → dual judges per ticket → merge in order F02→F03→F05. (3) Then write F06 ticket from NEED_DISPATCH.md + carry-overs, dispatch W6.
blockers: none verified
source_of_truth: docs/COMPETITION_STRATEGY.md, IMPLEMENTATION_PLAN.md, docs/QUALITY_GATES.md

## Baseline honesty
Old EXECUTION_STATE.md stated COMPLETE for 18 prototype criteria, reported 66 passing tests, and saved deterministic + live demos. This NEW program is NOT complete. Prior reports are historical evidence and have not been independently rerun in this planning update.
Scientific gap: deterministic 6/6 on toy fixtures; the live-model misleading case is a tie across 5 strategies. No causal proof of distributed collective advantage, no documented independent cross-team use.
Engineering gap: direct central follow-up, context-only blindness, erroneous debate peer serialization, model-self-certified execution, non-budget-matched comparator suite.

## Environment note (verified 2026-10-08)
- Anaconda system python 3.11 breaks pip build isolation (`_distutils_hack` assertion). ALWAYS use a venv: main tree `.venv/` (install `pip install -e ".[dev,otel]"`), each worktree `.worktrees/fNN/.venv/` (install with `-e` from INSIDE the worktree so `repliclaw` resolves to that worktree's src).
- Live LLM API key exists in env but fleet workers are FORBIDDEN to use it (quota + fairness); live runs are F08-only with explicit budgets.

## State update contract
Only the orchestrator/integration owner updates this file, after verifying underlying branch/tests. Record current ticket, owner/worktree, HEAD, gate status, command outputs, latest checkpoint, blockers and next action. Never mark COMPLETE without docs/QUALITY_GATES.md G6 and real-science evidence. Never infer running sessions just because a work plan exists.
