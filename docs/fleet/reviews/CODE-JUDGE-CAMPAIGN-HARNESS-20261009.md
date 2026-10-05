# Code Judge — P08 Campaign Harness (2026-10-09)

> **Reviewer:** general-purpose agent `571cb735` (read-only, code-judge mandate)
> **Target:** `scripts/campaign.py`, `tests/test_p08_campaign.py`, `docs/experiments/LIVE_CAMPAIGN_LAUNCH_PROTOCOL.md`
> (uncommitted WIP on top of `75c1aa7` as reviewed)
> **Initial verdict: MERGE-NOT-OK** — 1 BLOCKER, 1 MAJOR, 5 minor findings.
> **Disposition (integrator, same day): ALL FINDINGS REMEDIATED.** B1/M1/m1/m2/m3 fixed in
> `scripts/campaign.py` + `tests/test_p08_campaign.py` (tightened ceiling test + 2 new regression
> tests, 7 total), m5 runbook note added. Gate after remediation: **248 passed / 8 skipped;
> ruff clean; mypy 56 files clean.** Finding text below is verbatim from the judge's report
> (raw output file has since expired; all file:line refs verified by the integrator against the
> reviewed WIP).

## BLOCKER

**B1 — Master-ceiling pre-check does not skip the flagged run; it launches it.** `scripts/campaign.py:275-281`
The check that trips for run N set `stopped_master = True` but execution fell through to
`run_one_arm` at :290, so the very run the pre-check flagged WAS launched; only runs N+1..
were caught by the later `if stopped_master:` guard. Exit 4 and "no scoring" held, but the
skip did not.
**Empirical evidence (judge):** fake client, `run_campaign(runs_per_arm=2, master_token_ceiling=60_300, score=False)`
→ S0×2 (52 tok) + S3/run-001 (208 tok) ran; before S3/run-002 the check tripped
(312 + 60,000 = 60,312 > 60,300) → **S3/run-002 still launched**. 4 runs launched where 3 were expected.
**Why it matters live:** in the real 10.8M campaign this launches one unapproved live run beyond the
preregistered ceiling (prereg §5.1 / runbook "further runs are skipped"), invalidating the R-2 floor
check the runbook tells the operator to rely on.
**Fix applied:** flagged run now gets `status="skipped_master_ceiling"` and `continue`s before any
launch; `test_master_ceiling_stops_campaign` tightened to `completed_or_recorded == 3` and asserts
`S3/run-002 == "skipped_master_ceiling"` with exactly 9 skipped (m1 folded in — the old `>= 3`
assertion passed with the bug present).

## MAJOR

**M1 — Re-run after a crash mid-flatten crashes with unhandled OSError (runbook recovery path broken).**
`scripts/campaign.py:305-309`. On POSIX, `os.replace` of a directory onto an existing NON-EMPTY
directory raises `OSError` (errno 66, `ENOTEMPTY`) — proven on this platform by the judge with a
scratch probe. Scenario: a strategy/EESS arm run dir contains a subdirectory (the RunStore at
`run-01/run/`); a crash after that child was moved but before `run_dir` is complete leaves
`run_dir/run/` non-empty and `_run_completed(run_dir)` false; the documented recovery
("re-run the exact same command") then re-runs the arm and the flatten hits
`os.replace(new run/ → existing non-empty run/)` → unhandled traceback, exit 1. File children
are fine (atomic overwrite); only directory children are the hazard, and those exist in all
six primary arms' layouts.
**Fix applied:** new `_flatten_run()` helper removes a leftover dir child (`shutil.rmtree`)
before `os.replace` — reachable only in the not-yet-complete partial state (a complete run is
never re-flattened), so it can never delete a completed run. Regression test
`test_rerun_after_partial_flatten_recovers` seeds the partial state and re-runs the same command.

## MINOR

**m1 — The ceiling test masks B1.** FIXED with B1 (exact-count assertions + per-entry status
checks as specified by the judge).

**m2 — Unexpected runner exceptions crash the harness as a traceback, mislabeled by the exit-code
table.** The runner re-raises unexpected exceptions (only BudgetOverflow/BudgetExceeded/
InvalidUsage are caught); in-process that propagated out of `run_one_arm` → traceback, exit 1
mapped to "scorer error", losing all remaining runs.
**Fix applied:** `try/except BaseException` around the launch; `SystemExit` treated as a clean
runner refusal code, anything else recorded per-run as `error:<ExcName>` and the campaign
CONTINUES; new `EXIT_RUN_ERROR = 5` + `summary["errored"]` field + runbook entry; regression test
`test_unexpected_runner_exception_records_and_continues` (both arms error → rc 5, statuses
recorded, campaign continued past the first error, not scored).

**m3 — 60k floor hardcoded while `--envelope-tokens` is a knob.** A `--envelope-tokens` > 60,000
would make the pre-check optimistic and admit runs past the ceiling (latent: the frozen campaign
uses the default, case_loader `max_tokens=60_000`).
**Fix applied:** `envelope_floor = max(60_000, --envelope-tokens)` computed once before the
launch loop.

**m4 — `_assert_frozen` raises SystemExit(2), a BaseException, which would propagate through the
in-process harness as a traceback (defensive note only; cannot trigger for the frozen campaign).**
COVERED by the m2 fix: `SystemExit` is now explicitly intercepted and treated as a clean runner
refusal code.

**m5 (informational) — Leftover `staging/` after a crash is discovered by the scorer as an arm
(`score.py:105-116`); in that residual case the gate fails loudly (`oracle_read: False`) —
fail-safe.** FIX APPLIED as suggested: runbook now states leftover `staging/` is safe to delete
(`rm -rf $RUN/staging`) and that a stranded `staging` dir makes the completeness gate fail loud.
(Integrator note: the m2 exception path also `rmtree`s its own per-run staging dir, and every
launch pre-cleans its stage, so the harness keeps `staging/` empty in normal operation.)

## Verified-true (judge's 8-point contract review)

1. **Scorer layout — TRUE.** `score.py:105-116` keys arms by run-root subdir name; flatten
   produces exactly `<root>/<LABEL>/run-NNN/` with contract files at top level.
2. **Budget integrity — PARTIALLY TRUE (B1 was the false part, now fixed).** Pre-check
   expression correct; tokens read exactly once per run (no double count on resume); exit 4 +
   no-scoring held.
3. **Two-key safety — TRUE.** Harness never sets `REPLICLAW_LLM_ALLOW_LIVE` (read-only);
   refusal happens before any dir creation; runner gate intact at `runner.py:754-761`; fake
   factory has no network path.
4. **Oracle safety — TRUE.** No oracle read or oracle-content write in harness or runner;
   `score.load_oracle` is the sole reader, post-completeness-gate.
5. **Resume semantics — TRUE.** `_run_completed` → `continue` with zero file writes; a fully
   complete set still reaches phase-4 scoring.
6. **Flatten collisions — TRUE with the M1 caveat (now fixed).**
7. **Concurrency/robustness — PARTIALLY TRUE (M1/m2 hazards, both now fixed).** Harness is
   single-threaded; no true concurrency issue.
8. **Lint/type — TRUE at review time.** 5/5 campaign tests, ruff clean, mypy 56 files clean.

Judge environment note: reviewed HEAD `75c1aa7` with the WIP files uncommitted; no files
modified by the reviewer; scratch probe dirs deleted.
