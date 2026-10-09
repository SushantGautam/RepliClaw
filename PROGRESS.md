
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

## I4.13 — Round-4 outcome reviews + defect fixes (2026-10-11)
- **Judges:** science-judge-r4 PASS-integrity / FAIL-WITH-DEFECT(stop-1) / RECOMMEND(b) V3.3; code-judge-r4 PASS (evidence admissible; stop-2 mislabel refuted; 1 SHOULD-FIX resume guard).
- **Defects fixed (57d1e1f):** arm_saturated seed-level denominator; STOP.json closed-round guard in both drivers. 471 passed / 8 skipped / 3 xfailed; ruff + mypy clean.
- **Next:** HUMAN GATE — choose (a) close out / (b) V3.3 amendment / (c) model change (not authorized).

## I4.14 — Final disclosures 8–11 (2026-10-11)
- Recorded disclosures 8–11 (stop-1 defect, STOP.json snapshot gap, D-E phase-2/3 never executed, asymmetric volume gate) as mandatory riders for any report citing round 4. See EXECUTION_STATE.md I4.14.

## I4.15 — Turnkey human-gate deliverables (2026-10-11)
- Wrote `science/v3_campaign_final_report.md` (path a) and `design/amendment_v33_both_arms_repair_DRAFT.md` (path b, DRAFT, code-level, pending approval).
- Next: HUMAN GATE choice (a)/(b); (c) not authorized per D-V3-017.

## I4.16 — V3.3 built + judged + canaried (2026-10-11)
- Implemented V3.3 both-arms repair in wip worktree (anti-loop cache, no per-tool caps, volume canary→logged); gates 472 green; 2 fresh judges PASS; live canary: C-EQ 4/4 hits, D-E 0/4 (non-convergence persists as distinct-call rate).
- Next: HUMAN GATE (a) run full round 5 / (b) raise envelope / (c) stop series / (d) model change[not authorized].

## I4.27 — Round 8 (V3.6, 600K) adjudicated + closeout (2026-10-12)
- **Round:** launched at frozen HEAD `cff7d748` (v36 worktree `wip/v36-600k`, exactly two constant changes: MAX_TOKENS_PER_RUN 300K→600K, ROUND_TOKEN_CEILING 12M→24M; 2 fresh pre-run judges CONDITIONAL-PASS, REQUIRED applied); stop-1 at 18-run snapshot; final 23-run ledger, 4,084,520 tok (delta 1,444,365 reconciles exactly); relaunch refused by closed-round guard.
- **Result (machine-verified):** D-E 9/14 completed ALL hit (180,020–324,901 tok) + 5 aborted_budget = **5/5 phase-2 tool-cap / protocol-overhead** (0 true token-cap — gate quantity ≡ ledgered total; 0 wall; 2 of the 5 ran past 300K and still aborted there). C-EQ 9/9 completed ALL hit (54,759–71,865 tok), 0 crashes. Case-level paired (frozen R3, FINAL LEDGER): **TIE 6/8 vs 6/8 — the most favorable-to-D-E reading** (C-EQ 7/16 slots never launched → ceiling lower bound). H-budget machine-refuted → **H-burn on the envelope axis, non-convergence persisting (mechanism-negative)** (repeat rate 76.0% per-run vs 48.1% round-4). STOP "2 crashes" = 2 non-completions over the /20 denominator (code-judge REQUIRED-2).
- **Judges (2 fresh outcome, independent):** R8-OUTCOME-CODE `41324f73` CONDITIONAL-PASS → resolved PASS (REQUIRED-1 5/5 tool-cap + adjudicator threshold bug fixed; REQUIRED-2 STOP wording); R8-OUTCOME-SCI `999d61cb` CONDITIONAL-PASS, all REQUIRED applied; Q5: **do NOT run a 1.2M round** (predictable null), close the envelope axis, optionally a NEW freeze for the tool-cap hypothesis. UNVERIFIABLE flags f1 (drift-recovery not instrumented) + f2 (repeat-rate pair not a controlled comparison) recorded.
- **Standing negative finding: EXTENDED to 600K — five envelopes (60/90/150/300/600K), no demonstrated D-E/escrow advantage.** Token-envelope axis CLOSED.
- **Artifacts:** `.artifacts/rcaeval/pilot/run_v36/round8/` (gitignored); report updated: `docs/next_stage/science/v3_campaign_final_report.md` (round-8 row in §2, §2f, §2g, §4e, §5 +5, rider 15, §7 rewritten, §8); state: `EXECUTION_STATE.md` I4.27 (CLOSED), `DECISIONS.md` D-V3-020.
- **Next:** HUMAN DECISION POINT (§7): (i) accept the round-8 refined negative as the V3 record [judge-recommended] / (ii) new freeze for the phase-2 tool-cap hypothesis / (iii) stop the series / (c) model change [NOT authorized].
