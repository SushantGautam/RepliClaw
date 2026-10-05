# Application-Docs Fact-Check Report — 2026-10-09

> **Reviewer:** Verifier agent `1d4f8939-a440-4c5a-8a79-4f18f67ce48e` (read-only, independent)
> **Baseline:** `945986f` + WIP batch (campaign harness); full suite independently re-run 240 passed / 8 skipped
> **Scope:** all 5 docs/application/ docs, every concrete factual/numerical claim
> **Verdict:** no fabricated claims; 5 categories of STALE status/number text require updates (see findings table)

---

 # Fact-Check Report — Competition Application Docs
 
 **Scope verified:** all 5 `docs/application/` docs, every concrete factual/numerical claim checked against repo state at `945986f` + WIP batch (`scripts/campaign.py`, `tests/test_p08_campaign.py`, `LIVE_CAMPAIGN_LAUNCH_PROTOCOL.md`, modified `EXECUTION_STATE.md`/`FACT_CHECK_LIST.md`). Full suite re-run independently: **240 passed, 8 skipped** (with WIP), 235/8 committed @ `3491032`. `ruff` clean, `mypy` clean.
 
 **VERIFIED (spot-checks of load-bearing rows):** F1-F3 module gates (P02 = 78/8 reproduced at `3f452b2`; P03 73/2, P04 74/10 by citation); F4/F5/F6 worktrees at cited SHAs; F20 (235/8 @ `3491032`); F24 Tox21; F25 scorer 13 tests + rule string + CI branch semantics (`score.py:402-427`); F26 test counts (25/7/13/7/7 all reproduced); F27 run window; F28 round-1 history; F30/F31; F33a-c; F33d (all 9 sub-claims reproduced); S-1/N-2/R-2 disclosure code refs (`investigators.py:459-471`, `runner.py:351/581`, `orchestrator.py:453-463`); DEFECT_ADJUDICATION_INSTRUCTION 1201 chars / sha256 `5c7192eb…65996e7`; oracle fields; all frozen-config numbers (seed 20261010, λ=μ=0.5, max_cycles 6, TTL 120s, 60k/900s/4-agent envelope @ `case_loader.py:208`, 10.8M ceiling, temp 0.2/max_tokens 4096 @ `investigators.py:26,41-42`); DEMO_NARRATIVE hero numbers (all re-verified against today's `artifacts/demo-hero/run-20261009-083159/demo_report.json`); P1 disclosure doc (no fake scorecard anywhere; "M1 1.0 vs 1.0" appears nowhere); novelty framing (mechanism-level only; no "first decentralized" claim; consistent with `PRIOR_ART_NOVELTY_GATE.md:14-15`); run-window two-key PENDING (no full-approval or live-result claims anywhere). **No "87 tests" or "235 tests" strings found; no text treating 10-run as primary.**
 
 ## Findings table
 
 | doc | line | claim | status | evidence (file:line) | required-fix-suggestion |
 |---|---|---|---|---|---|
 | SUBMISSION_CHECKLIST | 15 | "213/8 full gate @ `d5c6701`" as current state | **STALE** | `FACT_CHECK_LIST.md:108` (235/8 @ `3491032`); suite re-run 235/8 committed, 240/8 with WIP | → "235/8 @ `3491032` (240/8 incl. uncommitted campaign harness F33d)" |
 | SUBMISSION_CHECKLIST | 50 | "all are green in the 213/8 run-branch gate" | **STALE** | same | update count + SHA |
 | SUBMISSION_CHECKLIST | 61 | "213 passed, 8 skipped @ `d5c6701` — the current verified count" | **STALE** | same | update |
 | SUBMISSION_CHECKLIST | 66 | "expect d5c6701 (or the current run-branch tip)" | **STALE** | `git rev-parse HEAD` = `945986f` | pin tip `945986f` (or `3491032` if submitting at A9 tip) |
 | SUBMISSION_CHECKLIST | 68 | "expect: 213 passed, 8 skipped (at d5c6701)" | **STALE** | re-run: 235 passed, 8 skipped | update expected output |
 | SUBMISSION_CHECKLIST | 77-78 | "current verified count is 213/8 @ `d5c6701`" | **STALE** | same | update |
 | SUBMISSION_CHECKLIST | 183 | "d5c6701 — current verified gate 213/8; re-run the Step-2 gate at the pinned SHA" | **STALE** | same | update pin + count |
 | SUBMISSION_CHECKLIST | 193 | "full gate (213/8 @ `d5c6701`)" | **STALE** | same | update |
 | SUBMISSION_CHECKLIST | 222-231 | Step 9: A8 "the A8 code PR **is in flight**"; start gated on "**round-2 sign-off** on A1–A8" + human key | **STALE** | `git merge-base --is-ancestor a708523 HEAD` (A8 merged); round-2 = NOT-APPROVE + A9 @ `3491032`; `EXECUTION_STATE.md:3` = science key SATISFIED @ `c0e92ea`, only human key pending | rewrite: A8 merged @ `a708523`, A9 merged @ `3491032`, round-3 = APPROVE-WITH-CONDITIONS, remaining gates = R-2 floors + human two-key |
 | SUBMISSION_CHECKLIST | 235-245 | "round-2 science-judge sign-off on A1–A8… the two-key requirement: round-2 science sign-off + human key" | **STALE** | `F33c` (`FACT_CHECK_LIST.md:121`); `EXECUTION_STATE.md:3` | gate is round-3 APPROVE-WITH-CONDITIONS (satisfied) + human key (pending) |
 | SUBMISSION_CHECKLIST | 252 | "round-2 v1.2-AMENDMENT science-judge sign-off on A1–A8 (F25/F27/F28/F30)" | **STALE** | round 2 happened & = NOT-APPROVE; round 3 is the operative key | → "round-3 sign-off (F33c)" |
 | SUBMISSION_CHECKLIST | 264-265 | "S4/S3/S0 land via the A8 PR; at `d5c6701` only S5/A1/A3 are in `LIVE_KEYS`" | **STALE** | `runner.py:196-203` LIVE_KEYS = all six arms; `campaign.py:26-33` PRIMARY_ARMS six-arm | → all six primary arms live on `policy_rag_v1` since A8 @ `a708523` |
 | SUBMISSION_CHECKLIST | 273 | "…the round-2 science sign-off not in hand" as blocker | **STALE** | `EXECUTION_STATE.md:3` | → "R-2 S5 floor not met and/or human two-key not satisfied" |
 | SUBMISSION_CHECKLIST | 283 | "two-key authorization (round-2 science sign-off + human key)" | **STALE** | same | → "(round-3 science sign-off — satisfied @ `c0e92ea` — + human key)" |
 | DRAFT_ANSWERS | 17-27 | State note "2026-10-08 @ `d5c6701`", "full gate is 213 passed, 8 skipped", "A8 code PR is in flight — round-2 sign-off… pending after the A8 PR merges" | **STALE** | `git log` (A8/A9 merged); F20; F33c | re-date to 2026-10-09/`945986f`; 235/8 (240/8 with WIP); A8+A9 merged, round-3 APPROVE-WITH-CONDITIONS |
 | DRAFT_ANSWERS | 20, 93, 122 | "213 passed, 8 skipped" as the current gate | **STALE** | F20; re-run | 235/8 @ `3491032` (240/8 with uncommitted campaign harness) |
 | DRAFT_ANSWERS | 24 | "RC-1 (the P1 pair S5 live-LLM vs S4 deterministic is not like-for-like)" as the open blocker | **PARTIALLY STALE** | RC-1 fixed by A9 @ `3491032` (`test_r2_parity.py`, 8 tests); still historically accurate as round-2's finding | mark as resolved by A9 |
 | DRAFT_ANSWERS | 90 | gate "at `d5c6701`" | **STALE** | same | update SHA |
 | DRAFT_ANSWERS | 163 | "the live matched-budget campaign (primary case `policy_rag_v1`, arms S5/A1/A3 live-LLM vs S4/S3/S0 deterministic)" | **STALE** | `runner.py:196-203`; `campaign.py:26-33` | → all six primary arms live on `policy_rag_v1` (A8 executor parity) |
 | DRAFT_ANSWERS | 175-183 | "A8 code PR (`p08/executor-parity`) is in flight; round-2 sign-off on A1–A8 is pending" | **STALE** | A8 @ `a708523`, A9 @ `3491032`, round-3 @ `c0e92ea` | rewrite status section |
 | DRAFT_ANSWERS | 316-321 | "the live campaign is SCHEDULED… gated on the two-key start — round-2 science sign-off on A1–A8 after the A8 PR merges + human key" | **STALE** | `EXECUTION_STATE.md:3`; F33c | → round-3 key satisfied; remaining = R-2 floors + human key |
 | FACT_CHECK_LIST | 114 (F26) | "Live-LLM arm `repliclaw.eess_live`… implemented" row describing LIVE_KEYS set as 3 arms | **STALE** | `runner.py:196-203` = 6 keys | update F26 LIVE_KEYS listing to six arms (post-A8) |
 | FACT_CHECK_LIST | 115 (F27) | "Live campaign SCHEDULED… gated on round-2 sign-off (F30/F31) + A8 code PR (F32)" | **STALE** | F33c; `EXECUTION_STATE.md:3` | → gate = round-3 (satisfied) + human two-key; R-2 floors |
 | FACT_CHECK_LIST | 116 (F28) | "round-3 IN FLIGHT" | **STALE** | `F33c` (round-3 complete @ `c0e92ea`) | → round-3 complete, APPROVE-WITH-CONDITIONS |
 | FACT_CHECK_LIST | 119 (F31) | "A8 registered @ `d5c6701`… code PR pending" (heading) | **STALE** | `git log a708523` merged | → "A8 merged @ `a708523`" |
 | FACT_CHECK_LIST | 120 (F32) | heading "A8 code is in flight, not merged" (body itself says MERGE-OK) | **STALE** (self-contradicting) | `git merge-base --is-ancestor a708523 HEAD`; body's own MERGE-OK text | fix heading to "A8 code merged @ `a708523`" |
 | FACT_CHECK_LIST | 121 (F33 heading) | "A9 registered + in flight" | **STALE** | `git merge-base --is-ancestor 3491032 HEAD`; F33c inside same row | fix heading to "A9 merged @ `3491032`; round-3 = APPROVE-WITH-CONDITIONS" |
 | FACT_CHECK_LIST | 193 | "round-2 sign-off + A8 code PR pending (F32)" in the state summary | **STALE** | F33c | → "round-3 APPROVE-WITH-CONDITIONS (F33c); human two-key PENDING" |
 | DEMO_NARRATIVE | 6 vs 83 | repro says "repo root (run branch)" but Step-7/appendix path is `.worktrees/p08-demo` | **UNSUPPORTED** (minor inconsistency) | `SUBMISSION_CHECKLIST.md` worktree table (p08-demo @ `a281006`) | state which root: committed demo runs from repo root; the cited artifact was regenerated at `945986f` |
 | P1_RESULT_DISCLOSURES_DRAFT | (all) | every claim | **VERIFIED** | code refs above; no fake-run scorecard anywhere in repo | none |
 
 ## Top-5 most consequential fixes (by severity)
 
 1. **Fix the stale "213 passed, 8 skipped @ `d5c6701`" current-gate claim + pin SHA** — SUBMISSION_CHECKLIST 15/50/61/66/68/77-78/183/193 and DRAFT_ANSWERS 17-20/90/93/122. A human following Step 2/Step 6 would check out `d5c6701` and expect 213; reality is 235/8 committed (`3491032`) or 240/8 with the WIP campaign harness. Directly undermines the doc's purpose as a hand-off checklist.
 2. **Replace the "A8 code PR in flight / round-2 sign-off pending / science key not in hand" narrative** — SUBMISSION_CHECKLIST 222-283, DRAFT_ANSWERS 17-27/175-183/316-321. Actual state: A8 merged @ `a708523` (code-judge MERGE-OK), round-2 = NOT-APPROVE → A9 merged @ `3491032`, round-3 = APPROVE-WITH-CONDITIONS with science key SATISFIED @ `c0e92ea`; only the **human two-key** + R-2 S5 floors remain (per `EXECUTION_STATE.md:3`). The doc currently overstates remaining blockers and understates achieved sign-off.
 3. **Correct the live-arm scoping from "S5/A1/A3 live vs S4/S3/S0 offline" to six primary arms live on `policy_rag_v1`** — DRAFT_ANSWERS 163, SUBMISSION_CHECKLIST 264-265, FACT_CHECK_LIST F26. Post-A8 (`runner.py:196-203`, `campaign.py:26-33`) all six primary arms are in LIVE_KEYS; the RC-1 like-for-like P1 pair (S5 vs S4) exists precisely because S4 is now same-executor.
 4. **Fix FACT_CHECK_LIST internal contradictions (F27/F28/F31-F33 headings vs their own bodies and the F33c/F33d rows)** — F32's heading says "in flight, not merged" while its body says MERGE-OK; F33's heading says A9 "in flight" while F33c (same row) says round-3 complete. This is the doc the submission leans on as the verified backbone, so self-contradiction is worse than staleness.
 5. **(Minor) DEMO_NARRATIVE repro-path inconsistency** (line 6 "repo root" vs line 83 `.worktrees/p08-demo`) — disambiguate so the judge can reproduce the hero run unambiguously.
 
 **Notes:** no file was modified. One observation outside the 5 docs: an untracked `tests/test_r2_preflight.py` (created today 10:33, after the described WIP batch) currently fails 3 of 6 tests (stderr assertion on empty output) — it's not referenced by any application doc, but the WIP batch's "240 tests green" claim holds only for the suite *as described*; the full on-disk suite is 243 passed / 3 failed / 8 skipped until that file is fixed or excluded.