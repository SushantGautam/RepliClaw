# CODE JUDGE — A8 Executor-Parity PR (`p08/executor-parity`) — ROUND 2: MERGE-OK

- **Reviewed:** `p08/executor-parity` @ **`247208f`** (base `d5c6701`)
- **Reviewer:** RepliClaw Code Judge (read-only agent `d7430df4`), 2026-10-08
- **Verdict: MERGE-OK** (round 1 @ `5393e54` was BLOCK; the fix is verified closed)

## Round-1 outcome (context)
- **BLOCKER #1 (reproduced):** live strategy arms (S0/S3/S4) wrote a stray top-level
  `<out>/run` RunStore dir; `score.discover_runs` treats every arm-dir subdir as a
  run dir, so the stray dir (no contract files) failed the completeness gate → the
  whole six-arm run-set was unscoreable.
- **MINOR #2:** no test proving mixed S5/S0 does not flip `parity.ok`.
- **MINOR #3:** 224-vs-223 calibration (10 tests, param expansion) — no action.
- **MINOR #4:** venv editable install points at MAIN tree; CLI/self-test need
  `PYTHONPATH=<worktree>/src`.
- **MINOR #5:** `harness_seed` audit-only for the deterministic strategy arms.
- **INFO #6:** A8.3.4(a) amendment self-contradiction — corrected in main tree by the owner.

## Fix @ `247208f` (verified)
1. **BLOCKER #1 CLOSED (reproduced):** `run_one_arm` branches `work_dir` — strategy arms
   (S0/S3/S4) get `work_dir=<out>/run-01` so the RunStore nests at `<out>/run-01/run`
   (invisible to `discover_runs`, which scans one level deep); EESS live arms
   (S5/A1/A3) keep `work_dir=out` and offline arms keep `work_dir=<out>/run-01`
   (both byte-identical to base).
   - Judge repro: `S5`+`S4` run-set → S4 subdirs = `['run-01']` only; `score_runs` →
     **SCORE OK, `parity.ok=True`, P1=`SUPPORTED`** (round 1: `ScoreError`).
2. **MINOR #2 covered:** `test_a8_s5_s0_mixed_does_not_flip_parity_ok` (mixed S5/S0
   reported, `parity.ok` stays True, P1 proceeds with `ci95`).
3. **New BLOCKER regression:** `test_a8_six_arm_primary_runset_is_scoreable` — six-arm
   CLI run-set scores without `ScoreError`; each arm has exactly `{"run-01"}`; no stray
   top-level `run/`.
4. `_normalized_tree` now skips the internal `run/` RunStore (uuid4 ids,
   non-deterministic by design) so the 6-arm parity test stays contract-only.

## Gate evidence (worktree, run by judge)
| Check | Result |
|---|---|
| `pytest -o addopts="" -q` | **225 passed, 8 skipped** (0 failed; +2 = the two new tests) |
| `ruff check src tests scripts` | **All checks passed!** |
| `mypy src` | **Success: no issues found in 55 source files** |
| `p08.score --self-test` (worktree PYTHONPATH) | **PASS** |

## Specific verifications (judge)
1. BLOCKER #1 closed — repro now `SCORE OK`.
2. S5/A1/A3 unchanged — file sets byte-identical to base (RunStore `out/run-01/runs/`,
   escrow `out/run-01/escrow/`); `final_verdict.json` identical (volatile-stripped).
3. Offline path unchanged/complete — provable no-op; `test_cli_tox21_offline_arms_complete`
   green; live S5 on secondary still refuses exit 2.
4. Contract files at `<out>/run-01`; nested `run-01/run` not double-counted
   (`discover_runs` scans one level deep).
5. No NEW issues — abort path (1-token envelope) exercised: contract files written,
   run-set scores cleanly (`parity.ok=True`); no code reader depends on the old
   top-level `<out>/run`.

## Remaining (non-blocking)
1. **INFO:** `_normalized_tree` skip is slightly broader than needed (any nested `run/`
   at any depth); inert in the current tests. Owner applied the suggested one-line
   comment clarification.
2. **NOTE (carryover):** venv editable-install → gate CLI/self-test steps must use
   `PYTHONPATH=<worktree>/src`; `pytest` is immune via `conftest.py`.
3. **NOTE (carryover):** `harness_seed` is audit-only for deterministic S0/S3/S4; the
   EP guard keys on `model`+`offline_arm` — consistent with A8.2/C2 (now documented
   in the amendment).

**No correctness bugs, no regressions, no oracle-leak or prompt-leak findings.**
A1.3 rule string `766f4eb9…`, A4 oracle guard, C1 routing, EP guard + C4 non-veto,
RC-2/3/4, offline secondary preservation all remain satisfied.

**Recommendation: merge.**
