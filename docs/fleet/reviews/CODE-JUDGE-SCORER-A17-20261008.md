# CODE-JUDGE-SCORER-A17 (2026-10-08) — H1 scorer alignment to prereg v1.2 P1 rule

**Scope:** commit `a9779fb` on `p08/scorer-align` (worktree `.worktrees/p08-scorer-align`, base `dc0e78f`), fixing NO-GO blocker **H1** (score.py P1 rule was sign-reversed AND compared S5 vs S3).
**Reviewer:** independent Code Reviewer subagent (ce9d8497), read-only.
**Verdict: MERGE-OK — required fixes: none.**

## Verdict table (all PASS)

| # | Item | Verdict | Evidence |
|---|------|---------|----------|
| 1 | `p1_decision["rule"]` byte-identical to A1.3 canonical string | PASS | AST-extracted both sides: len 1224, sha256 `766f4eb9ac2c97a7c2bbef531492c5ffbbdc274a430eabed5077dd2020e0c988`, byte-identical True (independent of builder's claim). |
| 2 | Estimand = S5 − S4; resamples 10,000; seed 20261010; percentile | PASS | `score.py:465-466` arms S5/S4; `:477` diffs; `:26-27` constants; `:478-481` percentile. Resampling "independently within each arm" matches A1.3 wording exactly (two-sample bootstrap). |
| 3 | STRICT branches; no `>=`/`<=` | PASS | `decision_branch` `:421-427`: `lo>0`→SUPPORTED, `hi<0`→FALSIFIED, else NOT_SUPPORTED. Boundary probes: `(0.0,1.0)→NOT_SUPPORTED`, `(1e-9,1.0)→SUPPORTED`, `(-1.0,-1e-9)→FALSIFIED`, `(-1.0,0.0)→NOT_SUPPORTED`, `(0,0)→NOT_SUPPORTED`. |
| 4 | 10-run interim = screening only, never a stop | PASS | `score_runs` consumed only by CLI print + tests; no disqualification path. A1.2/§8.1 confirm interim removed from trigger. |
| 5 | Sealed-fixture tests construct known-M1 two-arm inputs, assert exact CI + branch, strict edge | PASS | 13 passed in 2.51s; `test_p08_score.py:406-530`; strict edge `lo==0.0→NOT_SUPPORTED` at `:490-508`; all 4 fixtures independently re-run, deterministic. |
| 6 | No leftover old-rule artifacts in P1 context | PASS | No `s3_m1_mean`/`S5 vs S3`/`worsened` remain in score.py P1 path; remaining hits are legitimate test assertions of the NEW shape. |
| 7 | Degraded path safe (no fake verdict) | PASS | `score.py:506-508`: S4 absent/counts differ → `decision="no_valid_runs"`, no `ci95`, no `rule` key. M1 always 1.0/0.0, never None → no zero-fill possible. |
| 8 | Out-of-scope floor-test change | PASS (benign, no merge hazard) | 16 passed; import sort + unused-import removal; post-commit blob `f6ca3571` byte-identical to main's blob (converges, not diverges) — resolves as clean no-op in merge. |
| 9 | M1–M11 metrics unchanged for non-P1 | PASS | Diff touches only `p1_decision` block + scorecard header; `_per_run_metrics`, oracle gate, bootstrap_ci, parity, stopping_rules untouched. |

## Non-blocking notes (adversarial observations)

1. **Seed in rule string vs `--seed` flag:** canonical string hard-codes "seed 20261010"; `--seed` is overridable (default 20261010). Non-primary seeds would compute the CI with a different seed while the rule text stays fixed. Not silent (`result["bootstrap"]["seed"]` records the real value). **Live-run operator convention: always use `--seed 20261010`** — recorded here as an operational note.
2. **"Paired" terminology:** A1.3 mandates independent per-arm run-index resampling (two-sample bootstrap); code matches the source of truth.
3. **Import-resolution trap:** bare `import repliclaw` from a worktree resolves to MAIN-tree src via the editable .pth; pytest is safe (conftest prepends worktree src). Throwaway scripts must set `PYTHONPATH=./src`.

## Gate at worktree (re-run by orchestrator pre-merge)

- pytest: 172 passed, 8 skipped
- ruff: All checks passed
- `p08.score --self-test`: PASS (replay_ok, determinism_ok)
