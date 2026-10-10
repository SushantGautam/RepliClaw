# RepliClaw fast-finish status (coordinator-owned)

**As of 2026-10-11 20:35 UTC:** FF-01 CI clean install DONE (dev green). FF-02 label isolation DONE + integrated (merge b196e06); its review nit (single-service stratum guard) fixed and committed d74b58f. FF-03 null-model correction DONE + integrated (merge 5702e52, DRAFT pending independent signoff). FF-04 intervention parity DONE + integrated (merge 209653e; 554-line test proves D-E vs C-EQ share the real interface, no arm asymmetry). **FF-05 LIVE PILOT (round 0) PARTIAL RESULT obtained** with human-provided SimulaChat creds (model=default = Qwen3.8-27B): 4 cases RCA-P-01..04, seed 20261011 only (driver refused resume of non-completed records so seed 20261012 did not run → 8/16 arm-runs). Result is an honest NEGATIVE/feasibility finding: C-EQ-TELEM completed 4/4 and submitted rankings (~10 tool calls, ~50k tok each); D-E-TELEM hit 0/4 (3 aborted_budget @~150k tok + 1 crashed on malformed action output). Root cause is architectural thrashing, NOT a cap artifact: each D-E investigator (inv-a/b/c) uses only 3 distinct tools and re-issues the SAME calls 60–90% of the time (inv-b RCA-P-01: 27/30 redundant), exhausting the token budget before committing a ranking. NO effect/superiority claim — single seed, 4/10 cases, §6 no-confirmatory-reuse applies. Report: `.artifacts/rcaeval/pilot/run_live_r0/round0/pilot_report_round0.md`.

## Primary goal
An intervention-matched multi-case D-E vs C-EQ result, no false claims of escrow/decentralization superiority.

## Known starting facts
- main `97a455947...` frozen P08; dev previously inspected at `4f54d757...`. Re-read actual `git rev-parse HEAD` at execution start.
- P08: 120 runs, one case, intervention-access effect; escrow/decentralization unproven.
- C-EQ module exists on dev; 352 passed / 8 skipped reported by prior local gate, **no new execution from this status file**.
- GitHub public main CI on 2026-10-09 failed collection: `simpleaudit` / `opentelemetry` dependencies absent from clean install; fix/re-run gate.
- RCAEval: 735 indexed cases, 42 candidate cases, 10-case BARO RE1/RE2 CPU smoke; **observational only**.
- AgentRx: 73 annotated accessible trajectories; official LLM judge baseline not yet run. **DEFER from critical path**.
- AIOpsLab: upstream interface documented; real cluster and equal intervention reset **not verified**. Fast feasibility only, no unapproved cloud deployment.
- Leakage risk: root-cause-service-derived ordinal and case ID may still reveal answers; independent hostile test required.
- Statistical concern: forced one-arm saturation with otherwise equal nominal Δ does NOT preserve true zero effect; correct null simulation and reassess stop-rule interpretation.

## Execution queue (update at real checkpoint, not every hook)
| Task | Status | Owner | Latest artifact/command | Blocker |
|---|---|---|---|---|
| FF-01 CI clean install | DONE | coordinator (direct; subagent registry was stale this session) | dev @ c0cda69; CI run 38166853788 success (3.11+3.12 install/pytest/ruff/mypy); fresh-venv repro green | none |
| FF-02 label isolation | DONE | coordinator+rc-review | merge b196e06; nit fixed d74b58f (_select_stratum single-service guard + test); 91 benchmark tests pass | none |
| FF-03 judge/statistical correction | DONE (DRAFT) | rc-implement | merge 5702e52; AMEND_NULL_MODEL_CORRECTION_20261011.md + 1-line erratum; needs independent science signoff before P4 | independent signoff |
| FF-04 actual intervention parity | DONE | rc-implement | merge 209653e; tests/experiments/test_intervention_match.py (6 executable tests, no arm asymmetry) | none |
| FF-05 exploratory multi-case pilot | PARTIAL RESULT | coordinator (direct) | live round-0 seed-20261011, 4 cases: C-EQ 4/4 hit, D-E 0/4 (3 budget + 1 crash) from investigator thrashing (3 tools, 60-90% redundant calls). Report run_live_r0/round0/pilot_report_round0.md. Seed 2 not run (resume-refusal). | full multi-seed/multi-case needs cap/prompt fix or explicit authorization to spend more tokens |
| FF-06 prereg freeze/approvals | WAITING | pending | v3 draft | pilot + judge signoff |
| FF-07 heldout results | WAITING | pending | none | FF-06 |

## Human gate / known stop
A final heldout run requires prospectively frozen V3, independent science signoff and approved use of resources under existing G4. No new live comparative results are claimed here. Do not change this row until the approval artifact exists.
