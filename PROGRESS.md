
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

## I4.28 — Round 9 (V3.7, D-E-only phase-2 tool-cap 4→8) executed + adjudicated + closeout (2026-10-11)
- **Round:** §7 option (ii) human-approved (2026-10-11). Worktree `RepliClaw-stg2-v37`, branch `wip/v37-toolcap`, chain `cff7d748` → `da4a142` (instrument: `DE_PHASE2_TOOL_CAP` 4→8 D-E-only + record-only `abort_reason`) → `3818f3f` (freeze DRAFT) → `d77c638` (falsely-stamped) → `af2799a` (compliant FINAL). 2 fresh pre-run judges: V37-PRECODE `4fab502e` PASS; V37-PRESCI `0d4601b8` CONDITIONAL-PASS (8 REQUIRED, all applied doc-only).
- **PROCESS ERROR (disclosed, rider 16 (vii)):** premature launch at `d77c638` ("both PASS" misread from a 500-char preview) → stopped at ~20/32 runs → quarantined (`artifacts/dev/v37-round9-premature-19runs/`: 20 runs, 3,494,442 tok counted, NOT in official ledger) → freeze re-stamped compliant → relaunched fresh. Official round validity preserved (fresh draws, stateless backend).
- **Command:** `pilot_parallel.py run --round 9 --out .artifacts/rcaeval/pilot/run_v37 --concurrency 6 --label v37-round9` at `af2799a` (parallel_meta git_rev verified). Exit 10 (stop1_ssat at case 5).
- **Result (machine-verified):** 25/32 runs, **0 crashes / 0 aborts / 25/25 completed**. Coverage **D-E 14/16, C-EQ 11/16** (7 unlaunched). **All 5 round-8 cap-abort slots completed.** D-E case-hit **8/8** (ALL hit; median 299,373 tok); C-EQ **6/8** (median 59,539) — both ceiling lower bounds, inter-arm non-parity; intra-round cost ~5.0× (NOT comparable to round-8 3.7×). Final ledger **4,817,798 = 3,738,102 + 1,079,696 — EXACT**.
- **Machine verdict (frozen R1/R5/R7, `/tmp/adjudicate_round9.py`):** **H-nonconv / mechanism-negative** — R5 guard FAILED (ref 316.3% / thr 321.3% / new-5 318.1%; 5/5 new completions with a (tool,args) ≥5×). ≥5× loops concentrated in **out-of-scope phase 1**; **cap-8 never bound** (max p2 usage 7 < 8); 5 recovered slots needed 5–7 phase-2 calls.
- **Judges (2 fresh outcome, independent, both CONDITIONAL-PASS, 0 data/instrument defects):** V37-OUTCODE `dba1eb1f` (integrity 1-13 all verified; REQUIRED: exact 14/16 coverage, quarantine = 20 runs) + V37-OUTSCI `6433088d` (all numbers independently verified; MF-1..MF-5; **R8: tool-cap axis CLOSED at cap 8, cap-16 predictable null NOT run, H-cap-branch NOT triggered**; process-error taint: validity preserved).
- **Standing negative finding: REAFFIRMED** — five envelopes + cap axis, no demonstrated D-E/escrow advantage. One named open lever: phase-1 non-convergence (NEW prereg if pursued) or model change (c, NOT authorized).
- **Artifacts:** `.artifacts/rcaeval/pilot/run_v37/round9/` (gitignored); freeze `docs/next_stage/design/v37_prereg_freeze.md` @ `af2799a` (v37 worktree); quarantine `artifacts/dev/v37-round9-premature-19runs/`; adjudicator `/tmp/adjudicate_round9.py`; scorer sha256 `6956b5e0…`.
- **Report/state:** `v3_campaign_final_report.md` (round-9 row §2, §2h/§2i, §4f, §5 +9 bullets, rider 16, §7 rewritten, §8); `EXECUTION_STATE.md` I4.28 (CLOSEOUT); `DECISIONS.md` D-V3-021.
- **Next:** HUMAN DECISION POINT (§7): (i) accept the round-9 refined negative as the V3 record [judge-recommended] / (ii) NEW prereg for phase-1 non-convergence / (iii) stop the series / (c) model change [NOT authorized]. NO cap-16 without new freeze + 2 fresh judges + human re-confirm.
