# CODE JUDGE — 120-run live campaign EXECUTION-INTEGRITY review
Run dir: `runs/p08-live-20261009T122444Z` (sigma2 Qwen3.8-27B, policy_rag_v1, seed 20261010)
Date: 2026-10-09 | Verdict: **MERGE-OK** (with MINOR provenance note; no BLOCKING/MAJOR)

## Verdict: MERGE-OK

The on-disk evidence is internally consistent, the token math reconciles exactly, the
scorer is correct, and the 7-run recovery is clean. The on-disk evidence is
**trustworthy for a public result claim.**

## Verification results (reproduced, not assumed)

1. **Resume correctness — PASS.** `campaign.py` phase-1 counts tokens of any dir with
   `final_verdict.json`+`budget_ledger.json` and marks them `"reused (resume)"`; phase-2
   `continue`s past completed dirs, so completed runs are never re-run/re-flattened
   (byte-reused). Final `campaign_manifest.json` shows 0 non-reused entries in the last
   pass. `cumulative_tokens` strictly monotonic across every log:
   664,021 (resumed) → 1,604,063 → 1,623,930 → 1,697,971 → … → 1,716,411. No re-scoring drift.
2. **Error-recovery integrity — PASS.** The 7 `ValueError` (empty LLM) runs —
   `S5/011, A1/007, A1/019, A1/020, A3/009, A3/013, A3/015` (from `resume.log`) — were
   re-run into the SAME run dirs. All 120 run dirs now have complete, schema-valid
   `final_verdict.json`/`budget_ledger.json`/`run_metadata.json`/`traces.jsonl`
   (`usage_present_ratio ≥ 0.99`, correct envelope sha) — indistinguishable from
   first-pass runs. No empty/partial dirs; no `staging/` leftover. Recovery = 6/7
   (resume2) + 1/7 (resume3).
3. **Scorer correctness — PASS.** Oracle gate is load-bearing and ordered correctly:
   `gate_all_runs` (score.py:521) BEFORE `load_oracle` (score.py:524) — no peeking.
   `policy_rag_v1` M1 = `defect_class == oracle.true_cause AND target_artifact`
   (score.py:267-269). Spot-check S5/run-001: `defect_class=retrieval_omission` == oracle
   `true_cause=retrieval_omission`, target present → M1=1.0; `per_run.csv` matches tokens
   (16,030), wall_s (97.557), envelope sha exactly. Bootstrap = 10,000 resamples, seed
   20261010, deterministic LCG, independent per-arm run-level resampling (score.py:596-606).
   S4's 16/20 `judge_stale` misdiagnoses are genuine model content, not scorer bias.
4. **Manifest consistency — PASS.** `run_manifest.json` = exactly 120 runs (6×20), all
   `completed`, `incomplete:false`; `campaign_manifest.json` matches (pin 1df4c71…, seed
   20261010, client live, assert_frozen true, 20/arm).
5. **Token/metric audit — PASS.** `per_run.csv` token sum = **1,716,411** =
   `campaign_summary.json` `cumulative_tokens` EXACTLY. No run at 0 tokens or >60,000
   envelope. `parity.ok:true`, `overruns:[]`, single envelope sha, executor parity all true.
6. **Manipulation / leakage — NONE.** Scores (19:22:45) written AFTER the last run
   (19:22:43). 0 run artifacts contain the oracle path string (M4 proxy). `model`,
   `harness_seed`, `client_factory`, `endpoint`, `temperature`, `envelope_sha256`,
   `a9_defect_instruction_sha256` uniform across all 120 runs. Logs append-only/continuous.

## MINOR findings

- **M1 — 3 distinct `tree_sha` across the 120 runs** (`de77fba` n=7, `484dc66` n=44,
  `1df4c71` n=69). NOT a code mutation: `git diff de77fba..1df4c71 -- scripts src tests`
  is EMPTY — only `EXECUTION_STATE.md`/`PROGRESS.md` (provenance docs) changed.
  `--assert-frozen` (runner.py:287-299) pins D-10 parameters (λ/μ/max_cycles/TTL), not the
  commit; `tree_sha` = `git rev-parse HEAD` captured per run. Frozen code is byte-identical
  across all runs. **Action:** the public claim should cite the per-run `tree_sha` /
  code-identical range `de77fba..1df4c71` rather than the single scoring-time pin.
- **M2 — launch.log narrative:** `launch.log` (pin de77fba, 12:24) is the FAILED first
  launch: all 120 → AuthenticationError, 0 completed, 0 tokens. `launch2.log` empty. The
  51 "resumed" runs were produced by the later successful launch under 484dc66→1df4c71
  (15:1x–15:43, matching the "pause @ 51/120" commit). Consistent; auth-failure cycle
  produced zero artifacts — no impact on results.
- **M3 — resume3.log line ordering:** scorer JSON prints before parent's
  `{"resumed_tokens":1697971}` line due to subprocess/stdout buffer flushing. Cosmetic;
  scorer ran exactly once, after the last run completed.

## Execution-integrity conclusion

The 120-run, 0-errored, 1,716,411-token result is the genuine output of the frozen code:
byte-identical code across every run (only docs commits differ), complete schema-valid
artifacts, token accounting reconciling to the exact token, oracle read strictly after the
completeness gate, correct deterministic bootstrap CI + M1, and 7 stochastic-failure
recoveries that are byte-clean and indistinguishable from first-pass runs with no sign of
manual editing, cherry-picking, or scorer bypass. No BLOCKING or MAJOR integrity
violations found.
