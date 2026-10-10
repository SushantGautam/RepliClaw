
## I4.10 — PILOT V3.1 ROUND 3 (2026-10-10/11)
- What changed: launched and executed pilot V3.1 round 3 (AMEND_V3_1, D-V3-016) after both pre-launch judges PASS; stop-2 tripped after case 3 (D-E 6/20).
- Commands/evidence: `pilot_run.py run --round 3 --out .artifacts/rcaeval/pilot/run_v31 --autonomous` (model default, 90K envelope, 4.32M ceiling); STOP.json + ledger 12 runs; T0+4 report `round3/pilot_report_round3.json/.md`; suite 463/8/3, ruff+mypy clean (at I4.9b de27319).
- Observed result: D-E 0/6 (3× budget-abort 90.7–92.8K, 2× new ToolBudgetExhausted @24 calls, 1× protocol); C-EQ 4/6 completed, 4/4 hits, 2× canary crash P-02 @1.3476 (N2 pre-record matched); 815,858/4,320,000 tokens; N3 echoes 12/12 consistent.
- Judges: code-judge PASS (record + routing); science-judge RECORD-AND-HOLD + 2 refinements (multi-resource D-E constraint; canary-asymmetry disclosure).
- Next: HUMAN DECISION POINT #3 — options (i) record-and-hold, (ii) new both-constraints V3.2 instrument, (iii) pivot to AgentRx/RCAEval baselines.

## I4.12 — V3.2 round 4 live run (2026-10-11)
- **Command:** `scripts/pilot_parallel.py run --round 4 --out .artifacts/rcaeval/pilot/run_v32 --concurrency 6` (launch env SIMULACHAT_BASE_URL + SIMULACHAT_API_KEY, SIMULACHAT_MODEL unset). Exit 10 (stop trip).
- **Result:** STOP.json written after ledger line 16 (cumulative 1.13M/7.2M — verified sum of lines 1–16), ~2 min wall; 4 in-flight D-E runs then completed and were recorded (by design) → final ledger 20 lines (1.74M), 20 per-run dirs. stop1_ssat (D-E sat 0.0, C-EQ sat 0.30) + stop2_crash (at trip: D-E 8/20=0.40>0.25 — the tripping arm; C-EQ 5/20=0.25 is NOT >0.25 under strict inequality). D-E 0/12 (8× budget-abort via repeated-identical-call loops at ~152–154K/43–49 tools; 2× malformed-output crashes; 2× per-tool 4-call sub-budget crashes). C-EQ 3/8 (5× B3-band crash, ratios 1.60–1.80; 3 completions all hit=True).
- **Key findings:** (1) D-E infeasibility is multi-resource and confirmed across 6 cases — not a single-case artifact; (2) the C-EQ volume canary is over-sensitive: same case/seed/arm completed at 1.235 in canary, crashed at 1.601 in round 4 → live model makes the ratio non-deterministic; (3) stop rules + parallel driver + ceiling gate all behaved exactly as designed (bounded spend, correct trip, clean STOP.json).
- **Artifacts:** `.artifacts/rcaeval/pilot/run_v32/round4/` (STOP.json, parallel_meta.json, 16 run dirs, pilot_report_round4.json/.md); log `.artifacts/rcaeval/pilot/run_v32_round4.log`.
- **Next:** outcome judges (dispatched); then HUMAN GATE per D-V3-017 (stop trip → human).
