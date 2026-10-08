
## I4.10 — PILOT V3.1 ROUND 3 (2026-10-10/11)
- What changed: launched and executed pilot V3.1 round 3 (AMEND_V3_1, D-V3-016) after both pre-launch judges PASS; stop-2 tripped after case 3 (D-E 6/20).
- Commands/evidence: `pilot_run.py run --round 3 --out .artifacts/rcaeval/pilot/run_v31 --autonomous` (model default, 90K envelope, 4.32M ceiling); STOP.json + ledger 12 runs; T0+4 report `round3/pilot_report_round3.json/.md`; suite 463/8/3, ruff+mypy clean (at I4.9b de27319).
- Observed result: D-E 0/6 (3× budget-abort 90.7–92.8K, 2× new ToolBudgetExhausted @24 calls, 1× protocol); C-EQ 4/6 completed, 4/4 hits, 2× canary crash P-02 @1.3476 (N2 pre-record matched); 815,858/4,320,000 tokens; N3 echoes 12/12 consistent.
- Judges: code-judge PASS (record + routing); science-judge RECORD-AND-HOLD + 2 refinements (multi-resource D-E constraint; canary-asymmetry disclosure).
- Next: HUMAN DECISION POINT #3 — options (i) record-and-hold, (ii) new both-constraints V3.2 instrument, (iii) pivot to AgentRx/RCAEval baselines.
