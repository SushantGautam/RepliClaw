# P08 Live-Window Launch Protocol — one-command campaign (frozen procedure)

> **STATUS: READY — gated on the human two-key** (project lead authorization
> recorded in `EXECUTION_STATE.md`). This protocol launches the PRIMARY live
> campaign only. R-2 token floors (`R2_TOKEN_FLOOR_PREFLIGHT_PROTOCOL.md`) must
> be CLOSED first. No step here may be executed before both keys are green.

## Why a harness (and why it is new)
The frozen arm runner (`python -m repliclaw.comparators.runner`) executes ONE
arm × ONE run. The preregistered campaign is **six primary arms × 20 runs**
(prereg v1.1 §3.1 primary matrix; v1.2 A1 decision rule over the 20-run sets).
`scripts/campaign.py` (code-judge + tested, see FACT_CHECK_LIST) is the launch
harness: it calls the runner in-process per (arm, run) — so every D-10 pin,
the `--assert-frozen` check, and the **two-key live gate** (`REPLICLAW_LLM_ALLOW_LIVE`)
are enforced by the frozen runner itself — then stages the scorer layout
(`<root>/<S-label>/run-NNN/`), enforces the 10.8M master token ceiling, is
resumable (completed runs are reused, never re-launched), and hands off to the
frozen scorer. It never reads the sealed oracle and never flips the live gate.

## Pre-window checklist (all must be green at HEAD)
1. [x] Science sign-off 1 (independent judge) — FILLED (PREREG v1.2 §9; round-3 APPROVE-WITH-CONDITIONS @ c0e92ea).
2. [ ] MUST-1 disclosures folded — DONE (`docs/application/P1_RESULT_DISCLOSURES_DRAFT.md` = FOLDED).
3. [x] MUST-2 R-2 floors — DONE 2026-10-09T11:02Z: `artifacts/p08/token_floor_r2_20261009T105739Z/floor_r2.json` committed (S4=16,300 / S3=15,993 / S0=8,588 tokens; max fraction 0.2717 < 0.60; verdict OK; sigma2 Qwen3.8-27B; pin 81256a3).
4. [x] `bash experiments/policy_rag/preflight.sh` → ALL 5 gates pass (verified 2026-10-09), pin 81256a3 = actual HEAD.
5. [x] Full gate @ 81256a3: pytest **248 passed / 8 skipped**, ruff clean, mypy (56) clean, self-test PASS (verified 2026-10-09).
6. [x] Human two-key recorded in `EXECUTION_STATE.md` — science key = round-3 APPROVE-WITH-CONDITIONS (agent 713aa9b8, 2026-10-09); operator key = human authorization 2026-10-09T12:56 ('authorize test, use sigma2 endpoint').

## Launch (single command, from repo root)
```bash
cd /Users/sushantgautam/Documents/ScienceClawHackathon
export REPLICLAW_LLM_ALLOW_LIVE=1        # authorized orchestrator only (two-key start)
RUN=runs/p08-live-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$RUN"
.venv/bin/python scripts/campaign.py \
  --case policy_rag --case-id policy_rag_v1 \
  --client-factory live \
  --runs-per-arm 20 \
  --harness-seed 20261010 \
  --out "$RUN"
```
(`--assert-frozen` is ON by default in the harness; `--no-assert-frozen` opts out — never use the opt-out for the frozen campaign.)

Behaviour:
- 120 runs (S0, S3, S4, S5, A1, A3 × 20), each under the 60k/900s/4-agent envelope.
- Progress: one JSON line per run + a `campaign_summary.json` at the end.
- Master ceiling 10.8M: if `cumulative + 60k > 10,800,000`, further runs are
  skipped (exit 4) and the campaign is NOT scored — check R-2 floors first.
- Scoring: the scorer runs at the end and opens the sealed oracle ONLY after
  its completeness gate; outputs at `$RUN/scores/` (`scores.json`,
  `scorecard.md`, `per_run.csv`, `run_manifest.json`).
- Crash/interruption: **re-run the exact same command** — completed runs are
  reused (byte-identical, no re-launch); only missing runs execute.
- Leftover `staging/` after a crash is safe to delete (`rm -rf $RUN/staging`)
  — it holds only partial run staging, never contract artifacts, and a
  stranded `staging` subdir would make the scorer's completeness gate fail
  loudly (oracle NOT read) rather than score bad data.
- Refusal (exit 2): the two-key env is missing or the runner refused a live
  call — stop, record the refusal, fix authorization; do not bypass.
- Run error (exit 5): at least one run raised an unexpected runner
  exception (recorded per-run in the manifest as `error:<ExcName>`); the
  campaign continued, but the set is incomplete — investigate, then re-run
  the same command to fill the gaps.

## Post-campaign (same session as launch)
1. Commit `$RUN` artifacts (run trees + scores + manifest) — this is the
   signed evidence tree; record the HEAD SHA in `EXECUTION_STATE.md`.
2. Scorecard is **counterevidence-first** (P1 FALSIFIED leads with the
   falsification per PREREG v1.2 §8.1). No P1/P2/P3 result may be reported
   without the 7 mandatory disclosure items
   (`docs/DEMO_AND_FINAL_HANDIN_V2.md` → "P1 result statement").
3. Update `EXECUTION_STATE.md`, `PROGRESS.md`, `docs/application/FACT_CHECK_LIST.md`.

## What this protocol does NOT authorize
- The secondary (no-LLM) RQ4 case — frozen v1.1 H sub-study, separate command
  (offline arms + S5/A1/A3 live on `tox21_ar_agonist`), not part of this launch.
- Any bulk live scoring beyond this run-set (S0 stopping rule and the A7
  4-distinct-agent cap remain in force via the frozen arm code).
- Form submission (deadline Oct 16) — human action, separate from this window.
