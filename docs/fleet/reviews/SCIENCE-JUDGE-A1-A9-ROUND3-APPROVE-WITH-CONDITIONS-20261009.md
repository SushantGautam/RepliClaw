# SCIENCE JUDGE — ROUND 3 SIGN-OFF ON A1–A9 (2026-10-09)

> **Verdict: APPROVE-WITH-CONDITIONS (the SCIENCE KEY for the two-key live-run gate).**
> Independent read-only science-judge, agent `713aa9b8-ae26-46ec-8980-0f1b160d764b`, run against
> main tree `repl-claw-dev` (code @ `3491032` = A9 merge; HEAD at review = `80c4dfb`, docs-only
> commits since). M-1 (round-2 BLOCKING) **CONFIRMED genuinely resolved end-to-end** by the
> judge's own independent code inspection + FakeLLMClient six-arm reproduction. No BLOCKING
> findings. MUST (pre-live, registered): (1) fold A9.4/S-1/N-2/R-2 disclosures into the
> application before any P1 result is reported; (2) complete R-2 token-floor measurement +
> commit `floor_r2.json` before the window; (3) human two-key authorization. SHOULD
> (non-blocking): S-1 code comment; optional removal of the `"e.g. 'retrieval'"` example;
> optional full-S5-prompt sha256 pin.

---

All verification complete. Here is the round-3 science sign-off.

---

# ROUND-3 SCIENCE SIGN-OFF — RepliClaw ScienceClaw 2026, Amendments A1–A9

## 1. Verdict

**APPROVE-WITH-CONDITIONS** on A1–A9. **This is the SCIENCE KEY for the two-key live-run gate.**

The crux — whether round-2 BLOCKING **M-1** is **genuinely resolved end-to-end** — is **CONFIRMED**. I verified it by independent code inspection *and* an end-to-end `FakeLLMClient` reproduction (not by trusting the reports): all four P1-relevant arms (S0/S3/S4/S5) now emit non-null `defect_class`/`target_artifact` from **their own findings**, the aggregate reads the full finding dicts (not commitments), both writers emit real values, and the M1 estimator is byte-identical for S5 and S4. A9 introduced **no new scientific invalidity**: the scorer diff is purely additive (0 deletions), the S5 prompt change is honestly accounted, the rule string and estimator are byte-unchanged, the taxonomy is a public menu (not the answer), and no oracle/fault-marker leaks. Residuals are non-blocking operational/reporting conditions.

**Conditions (MUST — pre-live, already registered, do not reopen the science):**
1. **Fold the A9.4 / S-1 / N-2 / R-2 disclosures** (`docs/application/P1_RESULT_DISCLOSURES_DRAFT.md`) into the application/result statement before any P1 result is reported. The draft is gated on "round 3 returns APPROVE" — now satisfied — so it is cleared to fold.
2. **Complete R-2** per `docs/experiments/R2_TOKEN_FLOOR_PREFLIGHT_PROTOCOL.md`: measure S0/S3/S4 live-token floors on the first pre-flight live run, commit `floor_r2.json`, record in `EXECUTION_STATE.md` **before** the window. The backstop (60k/arm hard abort + 10.8M master ceiling + S0 stopping rule) bounds budget even while floors are unknown.
3. **Human two-key authorization** (v1.1 §9.2) remains independently required on top of this science key.

**SHOULD (non-blocking):**
- S-1: add a clarifying code comment at `investigators.py:459-488` (`_deterministic_defect`) that the returned pair is a **fixture stand-in** (not causally justified; inherits the retrieval-vs-judge base-data confound). Application-text disclosure already covers it; the comment is cheap hardening.
- Q4: the shared instruction's `"e.g. 'retrieval'"` target example is **common-mode** (given to every arm incl. S5) and `target_artifact` is `bool()`-only checked (C5), so there is **no differential arm advantage** — but removing the example eliminates any appearance of hinting. Optional.
- Q3: optionally add a **full-S5-prompt sha256** pin. Not a registered A9 requirement (component pins + the explicit A9.2.3 change statement already account for the byte change), but it is stronger provenance.

No BLOCKING findings. No invented competitive scores.

---

## 2. Numbered answers (Q1–Q9) with evidence

### Q1. M-1 resolution (the crux) — GENUINELY resolved end-to-end. **PASS.**
- **(a) Equivalent diagnostic access.** One shared constant `DEFECT_ADJUDICATION_INSTRUCTION` (`src/repliclaw/defect_adjudication.py:50-64`) carries the identical field contract (6-class `defect_class` enum + `target_artifact`), identical grounding, and identical role-agnostic clause. It is embedded in **both** the strategy finding prompt (`investigators.py`, hosts S0/S3/S4) **and** the S5 RESOLVE prompt (`eess_live/orchestrator.py`), each wrapped in `# DEFECT DIAGNOSIS (required)`. Byte-identity across hosts + run_metadata sha asserted by `tests/test_a9_defect_adjudication.py:213` (`test_a9_shared_block_byte_identical_s5_and_strategy`).
- **(b) Each arm structurally emits non-null.** Independent reproduction (FakeLLMClient, S0/S3/S4/S5 on `policy_rag`): all four arms wrote `defect_class="retrieval_omission"`, `target_artifact="retrieval"` to `final_verdict.json` (pre-A9 S0/S3/S4 were null-by-construction at `runner.py:376-377`/`588-589`). Structural null eliminated.
- **(c) `_defect_aggregate` reads full finding dicts (C8).** Aggregation source is `StrategyResult.evidence[*].finding` (the full dicts), **not** the commitment payload (the `_commit` fixed-key list does not carry the new keys — reading it would silently re-create M-1). Aggregate computed in `_finalize` → `Verdict` → **both** writers (`runner.py` offline + live). Confirmed by my reproduction reaching non-null in `final_verdict.json` for all arms.
- **(d) M1 estimator identical S5/S4.** `_diagnosis_correct` is byte-unchanged: `defect == oracle.get("true_cause") and bool(target)` (target is `bool()`-only, no exact-match, per C5). A9 diff to `p08/score.py` is **purely additive (0 deletions)**. Re-verified by `tests/test_a9_defect_adjudication.py:184` (`test_a9_m1_diagnosis_correct_unchanged`) and the gate.

### Q2. Canary design — sound. **PASS.**
`_m1_canary`/`_m1_canary_veto` (`score.py`): per-arm state `ok` (≥1 completed run non-null) / `degenerate` (runs exist, all null) / `absent`. The veto fires **only** on S4 (the P1-estimand arm) being all-null, and only as a **pre-bootstrap veto, never a filter** — it sets `P1.decision="m1_interface_degenerate"` (a distinct void state) and records `m1_canary` per-arm; it does **not** drop null runs or recompute the mean/CI. S0/S3 degenerate are reported per-arm, non-vetoing (bearing on RQ3/P3, and fixing the S0→P3-trivially-true issue, N-3).
- **Mask a true signal?** Only the all-S4-null case vetoes — which is *exactly* the M-1 false-positive scenario (S5 non-null vs S4 all-null would otherwise read as a spurious SUPPORTED). Refusing it is correct, not masking. A non-null-but-wrong S4 is **not** degenerate (a valid scientific outcome now that C1 makes "wrong" mean genuinely-wrong cause).
- **False INCONCLUSIVE?** The only path is the LLM *chance*-abstaining on all 20 S4 runs — vanishingly unlikely given the taxonomy forces a pick, and the failure direction is conservative (safe). I reproduced the veto (all-S4-null → `m1_interface_degenerate`, means preserved, CI absent). No scientific harm.

### Q3. A9.2.3 — S5 prompt change honestly accounted. **PASS** (one SHOULD).
S5 RESOLVE bytes **did** change (appended defect block). Accounting: (a) the A9 delta (shared block) is sha256-pinned (`defect_instruction_sha256()` = `5c7192eb…`) and asserted byte-identical in both hosts (`test_a9_defect_adjudication.py:213`); (b) the pre-existing A4 evidence span is pinned via footer substrings (`evidence_cited (…)`, `Respond with JSON containing conclusion`) and the test asserts the defect block is **AFTER** the footer (`test_a9_defect_adjudication.py:228-231`) — evidence span preserved. A9.2.3 explicitly states "S5's RESOLVE prompt bytes DO change … gains the registered defect taxonomy" — an honest C2-corrected change statement, not a false non-change. **Nothing else in S5 changes** (evidence build, first-non-null rule, guard, extraction unchanged — verified in the diff). SHOULD: no *full*-prompt sha pin exists (only component pins) — not a registered requirement; optional hardening.

### Q4. New risks from A9. **No new invalidity.**
- **Dilution/contamination of S4's primary role:** S4's primary job *is* causal diagnosis; the defect block is the same task made machine-extractable — not a competing role. The clause is appended **after** the numeric role-method section, independently marked, and C6(i) instructs the agent to answer the defect question *regardless* of whether the numeric method found data. Placement is adequate (C6).
- **Leakage:** The instruction's only example is `"e.g. 'retrieval'"` — a generic component name, **not** the fault_marker. The sealed fault_marker `14-day-stale-top1` has **0 occurrences** in `defect_adjudication.py`. The taxonomy is a public **menu**, not the answer (A9.4.3). Guards: A4 `EVIDENCE_FORBIDDEN_SUBSTRINGS` applied to **both** hosts (`test_a9_defect_adjudication.py:285` `test_a9_strategy_prompt_oracle_leak_guard` + `test_prompt_evidence.py:361` `test_evidence_block_guard_fails_loud_on_oracle_substring`). No leak. (The "retrieval" example is common-mode + `bool()`-only → no differential advantage; SHOULD to remove.)

### Q5. Re-pinned tests — justified, non-weakening. **PASS.**
All four are *direct consequences* of A9 turning S4's null into a real value; each strengthens, none weakens:
- `test_a8_scorer_refuses_mixed_executor_p1` — S4 control now non-null-but-wrong (`policy_conflict`) so the canary stays `ok`; the mixed/root parity refusal path is untouched.
- `test_a8_six_arm_primary_runset_is_scoreable` — adds non-null + canary-ok asserts.
- `test_a8_s5_s0_mixed_does_not_flip_parity_ok` — S4 → `retrieval_omission`.
- `test_prompt_evidence` value canary — re-pinned `retrieval_omission`→`14-day-stale-top1` (fault_marker is oracle-only, absent from public data); taxonomy added to `_public_identifiers` so menu values don't trip the leak canary. Confirmed, consistent with the code-judge.

### Q6. N-1 / N-2 / N-3.
- **N-1** (run_metadata LLMConfig + instruction sha256): **implemented** — `test_a9_defect_adjudication.py:317`/`:338`; my reproduction's run_metadata carried model, max_tokens, max_calls, timeout, temperature, `a9_defect_instruction_sha256`.
- **N-2** (strategy `budget_ledger.json` single-synthetic-call granularity): **disclosure-only, adequate** — tracked in `P1_RESULT_DISCLOSURES_DRAFT.md`; non-blocking.
- **N-3** (S0 shares M1-null → P3 trivially true): **addressed** — S0 is now non-null-surfaced and its degenerate state is reported per-arm by the canary.

### Q7. R-1 / R-2.
- **R-1** (pin to actual HEAD): **sound.** `_tree_sha(".")` == `git rev-parse HEAD` at write time; preflight prints the real HEAD. Covered by `test_a9_defect_adjudication.py:363` (`…real_git`) and `:394` (`…head_at_write_time`).
- **R-2** (S4/S3/S0 live-token floors pre-window): **still open** — `docs/experiments/R2_TOKEN_FLOOR_PREFLIGHT_PROTOCOL.md` registers the protocol. Backstop is **adequate for the window**: 60k/arm hard `aborted_budget` abort (line 63), 10.8M master ceiling (line 64), S0 stopping rule = stops at first budget-exhausting cycle (line 65), 60%-of-ceiling flag (line 67). It is a REQUIRED pre-live operational item (MUST #2), not a science-sign-off blocker.

### Q8. GATE-paragraph compliance. **Every item satisfied.**
A1+A2+A3+A4+A7+A8 approved in round 2 (NOT-APPROVE was solely M-1, now fixed; RC-1/Q1 confirmed PASS); **A9** approved by this verdict. A4 PR + A1.7 scorer PR + A6 tests merged/green (rounds 1–2 + this round). **A8** executor-parity PR merged/green (round 2). **A9** PR **merged @ `3491032`** to `repl-claw-dev`, tests green. Preflight FakeLLMClient six-arm parity re-run complete with recorded payloads (tooling, C7). Live-arm contract suite green incl. restored `test_cli_tox21_offline_arms_complete` (**1 passed**, just re-run). `p08.score --self-test` + `test_p08_score` green. The file-SHA-256-in-run_metadata step is a run-time action, not a sign-off blocker. **Two-key start** (v1.1 §9.2) unchanged and still required.

### Q9. Novelty/framing. **Correct, no overclaim.**
The P1 claim ("counterfactual interventions yield causal diagnosis that base-data access cannot") is attributed to the **counterfactual-intervention identifiability mechanism, not autonomy** — mandated by A9.4 item 1 (`PREREG-2026-10-v1.2-AMENDMENT.md:341`) and mirrored in `P1_RESULT_DISCLOSURES_DRAFT.md:24,55` ("does **not** establish 'decentralized autonomy improves diagnosis'"; "no 'autonomy beats central workflows' claim"). `DRAFT_ANSWERS.md:193` ("we do **not** claim firstness") and the prior-art survey (`F16`) treat AutoScientists / Co-Scientist / Robin / AgentRx / Dubova as prior art — **no firstness claimed**. A firstness/autonomy-overclaim scan of `docs/application/*`, `PREREG-2026-10-v1.2-AMENDMENT.md`, and `src/` found **no** "first to / first ever / no prior work / autonomy beats" phrasing (only benign "the first pass" and the negative statements above). No overclaim in the live application text.

---

## 3. Findings summary

- **BLOCKING:** none.
- **MUST (pre-live, registered):** (1) fold A9.4/S-1/N-2/R-2 disclosures into the application/result statement; (2) complete R-2 token-floor measurement + commit `floor_r2.json` before the window; (3) human two-key authorization (independent of this science key).
- **SHOULD (non-blocking):** S-1 code comment at `_deterministic_defect` (`investigators.py:459-488`); optionally drop the `"e.g. 'retrieval'"` example from the shared instruction; optionally add a full-S5-prompt sha256 pin.

---

## 4. Confirmed gate outputs (real, re-run this session on the MAIN tree, `.venv`, code `3491032` = HEAD~1; commits since `3491032` are **docs-only**)

| Gate | Result |
|---|---|
| `pytest -o addopts="" -q` | **235 passed, 8 skipped** (expected 235/8) |
| `repliclaw.p08.score --self-test` | **SELF-TEST: PASS** (replay_ok, determinism_ok) |
| `bash experiments/policy_rag/preflight.sh` | **ALL 5 GATES PASS**, pin = **actual HEAD** (R-1) |
| `ruff check src tests scripts` | **All checks passed!** |
| `mypy src` | **Success: no issues found in 56 source files.** |
| `test_cli_tox21_offline_arms_complete` (frozen RQ4/P4 secondary) | **1 passed** |

**Deterministic-vs-real-world distinction (for the record):** the 235/8 suite, the self-test, the preflight, and my `FakeLLMClient` six-arm reproduction are all **deterministic fixtures** proving structure, arm-neutrality, canary/veto semantics, byte-identity, and no-leakage — they are **not** a live scientific finding. The live LLM runs (the actual P1/P2/P3 evidence) have **not** been executed (F27: SCHEDULED, window 2026-10-10→23, gated on this key + human key). No live result is claimed.
