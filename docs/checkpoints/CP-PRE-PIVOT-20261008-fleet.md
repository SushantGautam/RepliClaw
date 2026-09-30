# CP-PRE-PIVOT — Full fleet inventory before the Evidence-Escrow pivot (2026-10-08 ~15:00)

**Status:** PAUSED BY STRATEGY PIVOT — new program defined in GitHub PR #1
(`strategy/evidence-escrow-swarm-20261008`, OPEN, docs-only, no `src/`/`tests/` edits).
All work preserved on branches. Nothing reset/cleaned/merged/pushed. No worktree deleted.

---

## 1. Main tree (repl-claw-dev @ `90d5c5d`)

| Commit | Content |
|---|---|
| `a14fa67` | Test baseline (66 passed, ruff/mypy clean — `logs/G0-baseline-20261008.txt`) |
| `2ba5847` | Fleet contracts (`docs/fleet/README.md` + `F01..F05.md`) |
| `2ccb629` | **F04 MERGED** — `docs/design/NEED_DISPATCH.md` (840 lines, decision-complete), `tests/test_need_dispatch_spec.py` (8 frozen scenarios, skipped), `docs/fleet/handoff-F04.md`. Dual-judge PASS (Code: 5 minors; Science: 4 must-fix → all captured in `docs/checkpoints/CP-20261008-F04.md` §F06 carry-over). Post-merge gate: 66 passed + 8 skipped, ruff/mypy clean. |
| `3108420` | F06 ticket drafted (`docs/fleet/F06.md`) — 8 F04 carry-overs baked in |
| `fd8c41c` | DECISIONS.md reuse-matrix entry for distributed need-dispatch |
| `6815a08`/`90d5c5d` | State updates (judge verdicts, remediation dispatch) |

Main-tree gate at checkpoint: **66 passed + 8 skipped, ruff clean, mypy clean** (post-F04-merge, `2ccb629`).

## 2. Feature branches (all worktrees under `.worktrees/`, each with own `.venv/`)

### f01 — `w1/F01-baseline-validity` @ `c4c95c8` (clean) — IMPLEMENTED, re-review incomplete
- **Implemented:** peer-visibility flag (`isolation.py`, default off), `LLMInvestigator` honors it, `open_debate`/`fixed_dag` opt in, `isolated_vote` = pure strict majority (tie→INCONCLUSIVE) bypassing `compute_verdict`, `vote_counts`/`majority_label` in agreement.
- **Remediation R1 (W1) landed** (`ab446fc` code / `c4c95c8` docs) for the 4 science Majors: `peer_exposure` audit events at render point (true `includes_peer_materials`), `IsolationViolation` guard for blind-gate peer render, handoff benchmark-impact disclosure (open_debate byte-identical offline; isolated_vote flips INCONCLUSIVE→SUPPORTED on 3/6 toy fixtures; 7/3 vs 8/2 red-run provenance), sentinel test + flag-pinning tests.
- **Tests actually executed:** gate at R1: **82 passed, ruff clean, mypy clean** (W1-verified); round-1 judges independently reproduced 76 passed and red→green on base `a14fa67` (7/10 fail pre-fix).
- **Incomplete:** F01 **re-review (R2) both judges** — sessions were cancelled at pause; no R2 report exists. R1 scope is docs+tests+2 src files; R2 expected to be fast.
- **Verdict so far:** Code Judge R1 PASS (3 minors, disposition in re-review prompt); Science Judge R1 PASS-with-4-Majors (remediated, unverified by re-review).

### f02 — `w2/F02-execution-honesty` @ `2afa7df` (clean) — PARTIAL (2 red tests, 2 mypy errors)
- **Implemented:** `src/repliclaw/execution.py` (337 lines: `ExecutionRecord`, `run_python_execution`, `verify_execution`), investigators rework (+90), models (+10), protocol wiring (+127/-118).
- **Tests actually executed (orchestrator-verified at checkpoint):** **70 passed, 2 failed** — `test_self_attestation_rejected`, `test_swapped_record_rejected` (AssertionError :232); ruff clean; **mypy 2 errors** at `investigators.py:450` (tuple arity).
- **Incomplete:** make the 2 failed scenarios pass, fix mypy arity, full gate, handoff completion, dual-judge review.
- Resume notes + reuse inventory: `.worktrees/f02/docs/fleet/handoff-F02.md` §PRE-PIVOT STATUS.

### f03 — `w3/F03-eval-fairness` @ `32b6330` (clean) — PARTIAL (red-test-first, impl not started)
- **Implemented:** 9 frozen held-out fixtures (`tests/fixtures/heldout/*.json`, new domains/fault types `p_hack`, `selection_bias`; 3 supported / 6 refuted) + `manifest.json` sha256 pins (all 9 re-verified); `tests/test_evaluation.py` — 10 RED tests pinning the `repliclaw.evaluation` API + report shape (fail on `ModuleNotFoundError`, the right reason).
- **Tests actually executed:** pre-existing suite **66 passed** with `--ignore=tests/test_evaluation.py`; full collection red (by design).
- **Incomplete:** `src/repliclaw/evaluation.py` (not started), benchmark additive extension, held-out eval report → `artifacts/evaluation/heldout-deterministic/`, dual-judge review.
- **Flagged decision:** red test expects `repl_claw` per-run `n_investigators == 3`, but follow-up can spawn a 4th — resolve with a separate additive key (handoff §partial #2).
- Resume notes: `.worktrees/f03/docs/fleet/handoff-F03.md` §PRE-PIVOT STATUS.

### f04 — `w4/F04-need-dispatch` @ `0ca2e61` (clean) — DONE + MERGED (`2ccb629`)
See §1. Design is decision-complete; F06 ticket ready (`docs/fleet/F06.md`).

### f05 — `w5/F05-science-feasibility` @ `ef3584b` (clean) — IMPLEMENTED + REMEDIATED, re-review pending
- **Case:** Tox21 AR-agonist screen, PubChem AID 743053, Zenodo 20269909 (DOI 10.5281/zenodo.20269909, CC-BY-4.0, live-verified by code judge), extract `data/tox21_ar_7069.tsv` sha256-pinned (7,069 compounds, 220/6,849).
- **Results (frozen held-out, seed 2026, n_test=1414):** accuracy 0.9802 [0.9729, 0.9875], AUC 0.8588 (DeLong CI), active recall 0.5682 (25/44), all-negative baseline 0.9689, **McNemar exact p = 0.009041** (b=9, c=25), 5-fold CV 0.9774±0.0037, shuffled-label control ≈0.936/AUC 0.498. Offline, byte-identical across runs (`reproduce.sh` exit 0).
- **Remediation R1 complete** (W5, cancelled before R2): §7.1 "PAIRED, not independent" F08-hook fix (two-arm counts relabeled descriptive-only), `claim_freeze.json` (`repliclaw.claim_freeze/v1`, frozen 2026-10-08 pre-inspection), CIs + method labels; orchestrator fixed one ruff F601 duplicate key.
- **Tests actually executed (orchestrator-verified at checkpoint):** **74 passed, ruff clean, mypy clean, run_case.py exit 0.**
- **Incomplete:** F05 dual-judge **re-review (R2)** (was pending; expected fast).
- Code judge R1 PASS (no blockers; F08-adapter M1/M2 → M2 closed by freeze artifact, M1 carried to F08); Science judge R1 PASS-conditional (MAJOR closed by R1, unverified by re-review).

## 3. Worker/judge sessions at pause
- W1 (F01): idle after R1 — work committed by W1 itself.
- W2 (F02): **cancelled** by pivot; WIP committed by orchestrator (`cb8a92e` + handoff).
- W3 (F03): **completed checkpoint on its own** (`32b6330`, handoff written).
- W4 (F04): idle after done+merged. W5 (F05): **cancelled**; WIP committed by orchestrator (`7324465` + F601 fix + handoff).
- Judges completed: F01 Code R1 PASS, F01 Science R1 PASS(4 Majors), F04 Code PASS, F04 Science PASS, F05 Code PASS, F05 Science PASS-conditional.
- Judges **cancelled mid-R2 (no report):** F01 Code R2, F01 Science R2.

## 4. Scientific findings so far (valid regardless of pivot)
1. F01: isolated_vote with weighted-verdict engine silently overrode majority on the toy backend (false-INCONCLUSIVE); strict majority is honest. Debate peer-blindness was a real delivery defect (fixed, LLM-layer effect only — deterministic backend ignores peers by design).
2. F04: ScienceClaw's need system is per-agent, single-locked, no cross-process claim/dedup — central `_fulfill_need` dispatch confirmed as the G1 defect with exact file:line citations (20+ verified).
3. F05: a real, offline, reproducible Tox21 AR-agonist case exists with frozen held-out performance; the model-vs-baseline comparison is PAIRED — independent two-arm statistics refute a real effect (RR 1.012, CI ∋ 1) while McNemar supports it (p=0.009). Any live F08-style protocol must use the paired test.
4. Live-LLM tie (pre-pivot evidence): `artifacts/demo-llm/demo_summary.json` — misleading case, all 5 strategies REFUTED; no live-model advantage demonstrated yet.

## 5. What the new program (PR #1) can reuse
- **Infrastructure:** G0 gate harness, venv-per-worktree setup, fleet contracts/ground rules, judge procedure (`docs/fleet/JUDGES.md`), checkpoint discipline.
- **Code on branches:** f01 (valid comparators + honest isolation audit/guard), f02 (`ExecutionRecord`/subprocess runner/verifier + honesty red tests), f03 (9 held-out fixtures + manifest + red evaluation API tests), f05 (entire Tox21 case incl. paired statistics + `claim_freeze/v1` schema), f04→main (need-dispatch design + spec).
- **Evidence:** G0 baseline log, F04 dual-judge PASS + carry-over list, F05 provenance (live-verified DOI/md5/sha256), McNemar vs two-arm finding.
- **Not yet merged (needs salvage triage in new program):** f01, f02, f03, f05 branches — none contain uncommitted work; all are clean, per-branch, and gate-documented.

## 6. Environment invariants (verified this session)
- Anaconda python breaks pip build isolation → always venvs (`.venv/`, `.worktrees/fNN/.venv/`).
- LLM API key in env; F08-only in old program (budget-capped); workers forbidden.
- Never `git add -A` in main tree (`.worktrees/` gitlink hazard — fixed once in `0422105`).
- Integration rule (old program): `git merge --no-ff` + full gate; judges must be independent sessions.

## 7. Resume protocol for the new orchestrator
1. Read PR #1 docs: `docs/AGENT_MIGRATION.md`, `SEED_PROMPT_V2.md`, `docs/EVIDENCE_ESCROW_SWARM.md`, `docs/PRIOR_ART_NOVELTY_GATE.md`, `docs/FLAGSHIP_CASE.md`, `docs/EXPERIMENT_PROTOCOL_V2.md`.
2. Inventory this checkpoint + each `docs/fleet/handoff-*.md` (f02/f03/f05 have §PRE-PIVOT STATUS).
3. Salvage per new ticket mapping; re-run gates in each worktree before building on them (commands in each handoff).
4. F01 R2 and F05 R2 re-reviews can be re-dispatched cheaply if the new program reuses those branches.
