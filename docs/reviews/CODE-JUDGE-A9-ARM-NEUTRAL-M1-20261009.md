# CODE JUDGE — A9 Arm-Neutral Defect-Adjudication Surface (`p08/arm-neutral-m1` @ `edd0def`, base `f6c9362`)

> **VERDICT: MERGE-OK** — M-1 genuinely fixed end-to-end. No BLOCKERs, no MUSTs. All of C1–C9, R-1, N-1 SATISFIED. The four re-pins are direct A9 consequences, none a weakening. Two NITs + one non-blocking disclosure note (S-1: the offline deterministic arm's `_deterministic_defect` is a fixture stand-in — disclosure lands in A9.4 application text). Source: RepliClaw Code Judge agent `e0a8b838-43b1-41fa-9439-8178247a2400` (read-only, gate re-run independently in the worktree). Integrated @ `3491032` on `repl-claw-dev` (2026-10-09) after main-tree gate re-run.

# CODE JUDGE — A9 Arm-Neutral Defect-Adjudication Surface (`p08/arm-neutral-m1` @ `edd0def`, base `f6c9362`)

**VERDICT: MERGE-OK**

M-1 is genuinely fixed end-to-end. No BLOCKERs, no MUSTs. All of C1–C9, R-1, N-1 are SATISFIED. The four re-pins are direct, mechanically-justified A9 consequences and none is a weakening. The score.py diff is purely additive, docs/ is untouched, no scope creep, no oracle/prompt leak, no new correctness bug. Two NITs + one scientific-disclosure note (non-blocking) below.

---

## 1. Gate commands (run by me in the worktree)

| Check | Result (verbatim tail) |
|---|---|
| `python -m pytest -o addopts="" -q` | **`235 passed, 8 skipped in 15.26s`** (re-run: `235 passed, 8 skipped in 14.52s` — stable) |
| `ruff check src tests scripts` | **`All checks passed!`** |
| `mypy src` | **`Success: no issues found in 56 source files`** |
| `PYTHONPATH=$PWD/src …/.venv/bin/python -m repliclaw.p08.score --self-test` | **`"replay_ok": true, "determinism_ok": true … SELF-TEST: PASS`** |

**Preflight note (which I chose):** the worktree has **no `.venv`** (confirmed). I did **not** create the builder's temp symlink; I ran the self-test via `PYTHONPATH=$PWD/src` using the main tree's `.venv` interpreter — the same documented approach as A8 (code-judge MINOR#4 / carryover). `pytest` is immune via `conftest.py`. No gap in gate completeness. This is a known A8 carryover, not an A9 defect.

Worktree hygiene: `git status --short` is **clean** — I modified nothing; `git rev-parse HEAD` = `edd0def…`.

---

## 2. Findings

**BLOCKER:** none.

**MUST:** none.

**SHOULD**
- **(S-1) Scientific-disclosure nuance (offline deterministic arm).** `investigators.py:459-488` `_deterministic_defect` returns `("retrieval_omission","retrieval")` for the policy_rag claim shape from **base data alone** (compares `base_retrieval` window vs `policy_docs` window). This is the exact retrieval-vs-judge confound the design (Q2(b)/C7) states is *not* validly disambiguable from base data (both point at 14 days). It is **registered** (A9.2.2 "offline deterministic path returns registered non-null defect fields") and is **not exercised in the primary live P1** (A8 makes S0/S3/S4 live-LLM; the deterministic arm is offline/fixture-only, and the secondary tox21 case has no RAG data → abstain). Defense-in-depth: even if a live P1 pair were mis-configured offline, the A8 parity guard would void it. This is a **disclosure** obligation (application text, A9.4/C7 — out of scope for this code PR, which correctly leaves docs/ untouched), not a code defect. Recommend one clarifying comment that the deterministic diagnosis is a fixture stand-in, not a causally-justified result. *(Downgraded from MUST: does not affect the primary live P1.)*

**NIT**
- **(N-1) Canary "ok" is OR-semantics on null-ness.** `score.py:493-499` marks a run "ok" if `defect_class is not None OR target_artifact is not None`. A run with only `target_artifact` non-null (class null) counts as "ok". Defensible partial-answer state, but worth a one-line comment. Also correctly treats the string `"none"` (a valid answer) as "ok", distinct from `None` (no answer) — that distinction is correct and important.
- **(N-2) C9 three-way sha identity is transitive, not a single direct hash-equality.** `tests/test_a9_defect_adjudication.py` asserts the identical marker string is a substring of *both* the S5 RESOLVE prompt and the strategy finding prompt (byte-identical ⇒ same sha), plus `defect_instruction_sha256()` is 64-hex, plus a *separate* test pins `run_metadata.a9_defect_instruction_sha256 == defect_instruction_sha256()`. The three-way identity (S5 block = strategy block = run_metadata) holds transitively. A single `sha256(s5_block)==sha256(strategy_block)==run_metadata` assertion would be marginally more explicit. C9 is satisfied either way.
- **(N-3) Carryover:** no `.venv` in worktree → self-test needs `PYTHONPATH` (A8 MINOR#4). No action required.

**Re-pin scrutiny (each is a direct A9 consequence; none weakens):**
- **`test_a8_scorer_refuses_mixed_executor_p1` (control):** S4 `(None,None)`→`("policy_conflict","returns-policy")`. **The mixed part (root) is untouched** and still fires `executor_parity_violation` (I reproduced: MIXED → `executor_parity_violation`). Only the *control* (root2) changed, and it had to: with the canary, an all-null S4 is now the degenerate state, so an all-null control would flip from "proceeds to normal branch" to `m1_interface_degenerate`. Using a **non-null-but-wrong** class keeps Δ=+1.0 (S5 M1=1.0, S4 M1=0.0) → SUPPORTED, exactly as the pre-A9 control intended. Reproduced: MATCHED(wrong) → `SUPPORTED`, ci95 `[1.0,1.0]`; MATCHED(all-null S4) → `m1_interface_degenerate`. **Meaningful, not weakened** (still asserts `decision == decision_branch(ci95)`, parity ok, and now also `canary S4 == "ok"`).
- **`test_a8_six_arm_primary_runset_is_scoreable` extension:** adds non-null `defect_class`/`target_artifact` for S0/S3/S4/S5 + canary "ok" for all + `!= m1_interface_degenerate`. Pure additions (A9.3a re-pin). Not a weakening.
- **`test_a8_s5_s0_mixed_does_not_flip_parity_ok`:** S4 `(None,None)`→`("retrieval_omission","returns-policy")` so the P1 canary is "ok" and doesn't mask the RQ3 S5/S0 assertion. Adds `!= m1_interface_degenerate` + `canary S4 == "ok"`. Direct consequence, not a weakening.
- **`test_prompt_evidence.py` value-canary re-pin `retrieval_omission` → `14-day-stale-top1`:** **(a) still catches oracle CONTENT leakage?** Yes. `14-day-stale-top1` is the oracle's `fault_marker` **value** (`oracle.json:7`), a sealed value that is **not** taxonomy vocabulary and is **oracle-only** (I grepped: absent from public case data). The test still asserts every forbidden substring is absent from the prompt, so value-level leak coverage is preserved with a genuinely-sealed value. **(b) is `taxonomy ∩ forbidden = ∅` meaningful?** Yes — it asserts the C1 property that the registered public menu is *not* sealed content; if a taxonomy label were ever added to `EVIDENCE_FORBIDDEN_SUBSTRINGS`, the S5 RESOLVE guard (which now embeds the taxonomy) would raise and break the run, so the assertion is a real invariant. The re-pin is a **direct** consequence: post-A9, `retrieval_omission` is legitimately in the prompt (it is the taxonomy menu), so keeping it as a "forbidden value" would be wrong. **Not a weakening.**

---

## 3. Condition-by-condition verdict table

| Cond. | Verdict | Evidence (file:line) |
|---|---|---|
| **C1** taxonomy in shared block, both arms, + sha fn | **SATISFIED** | `defect_adjudication.py:55` instruction embeds `retrieval_omission \| policy_conflict \| judge_stale \| generation_error \| data_error \| none` (l.67-68); `DEFECT_TAXONOMY` l.82; `defect_instruction_sha256()` l.94; imported by `investigators.py:22` and `orchestrator.py:33`. Leaf module (only `hashlib` import) ⇒ no cycle. |
| **C2** S5 RESOLVE gains shared constant; evidence build / first-non-null / guard / extraction unchanged | **SATISFIED** | Block appended `orchestrator.py:573-574` **after** the footer. `_evidence_block` (l.550) untouched; first-non-null `if not defect_class and payload.get(...)` (l.588-592) untouched; guard loop (l.580-584) untouched (now also covers the block — taxonomy ∩ forbidden = ∅, so it can't trip); `payload = self._llm_call(...)` (l.586) untouched. |
| **C3** canary VETOs on **S4 specifically**; S0/S3 reported, not vetoing; all-null S4 + non-null S3 MUST veto | **SATISFIED** | `_m1_canary_veto` = `canary.get("S4")=="degenerate"` (`score.py:504-506`); all-arms recorded `score.py:574-575`. Regression case: `test_a9_canary_degenerate_s4_vetoes_p1` + `test_a9_canary_s4_specific_not_any_of`(i). I reproduced all-null-S4/non-null-S3 → `m1_interface_degenerate` (never SUPPORTED). |
| **C4** pre-bootstrap VETO, never a filter; means identical | **SATISFIED** | `s5m/s4m` computed over full `clean` at `score.py:563-564`, **before** canary (l.574) and bootstrap (l.612). `test_a9_canary_veto_never_filter` asserts `s4_m1_mean==0.0` and `s5_m1_mean==1.0` in both degenerate and healthy sets. I reproduced: a FILTER would give `s4_m1_mean=None`; here it's `0.0` (full 3-run set) ⇒ veto, not filter. |
| **C5** `_diagnosis_correct` byte/behavior-unchanged, no exact-match of target | **SATISFIED** | `score.py:255` `defect == oracle.get("true_cause") and bool(target)`. score.py diff has **zero deletions** (purely additive). Behavior-pin `test_a9_m1_diagnosis_correct_unchanged`: `m1("retrieval_omission","returns-policy") is True` (different target still scores ⇒ no exact-match), `m1("retrieval_omission_extra","retrieval") is False`. |
| **C6** independent role-agnostic section after numeric role-method + "answer even if insufficient" + guard on strategy prompt | **SATISFIED** | `investigators.py:231 # ROLE METHOD`, `:233 # OUTPUT`, `:249-250 # DEFECT DIAGNOSIS (required)` (block is last). "answer … even when … insufficient data" in `defect_adjudication.py:60,72`. Guard `investigators.py:261-267` (lazy import + loop). |
| **C7** application-text disclosure | **N/A for code** (docs/ untouched by design); lands on A9.4 application text. See S-1 for the one related code-side nuance. |
| **C8** aggregate from full finding dicts (not commitment payload); per-strategy rules; computed in `_finalize`/`run_repl_claw`; both writers emit real values (null only when incomplete) | **SATISFIED** | `_defect_aggregate` (`strategies.py:120`) reads `e.finding` (full dict from `_ev` l.94); repl_claw reads `raw_findings`=`protocol.findings` (full findings, `protocol.py:203,350`) with `commit_payload` (`models.py:35-42`) confirmed to drop the new keys. Per-strategy: single_agent / fixed_dag final stage (l.154-155) / isolated_vote+open_debate `sorted by agent_id` (l.159) / repl_claw followup+committed. Attached in `_finalize` (l.178) and `run_repl_claw` (l.337). Writers `runner.py:380-381` (offline) + `609-610` (live) emit `result.defect_class if completed else None`. **`completed` gate is sound:** `completed = status=="completed"` (l.328/559) matches the canary's `status=="completed"` filter (score.py:491) — completed⇒real value, incomplete⇒null+excluded. |
| **C9** shared-sha256 identity (S5 vs strategy vs run_metadata); pinned S5 footer substrings green | **SATISFIED** | `test_a9_shared_block_byte_identical_s5_and_strategy` (marker byte-identical in both hosts + footer-before-block + 64-hex sha); `test_a9_run_metadata_records_llmconfig_and_instruction_sha` (run_metadata sha == `defect_instruction_sha256()`). Footer pins: `_BLOCK_HEADER`, `Respond with JSON containing conclusion` (via `_block_lines` index at l.164-165), `evidence_cited (…)` all green (41 passed across the 4 test files). |
| **R-1** `run_metadata.tree_sha` = `git rev-parse HEAD` of run tree, all arms; tests present | **SATISFIED** | `_tree_sha` (`runner.py:242-255`) runs `git rev-parse HEAD` cwd=`root=Path.cwd()` (l.641); written at l.833. Tests `test_r1_tree_sha_records_actual_head_real_git` (offline S0 + live S4, real git) and `test_r1_tree_sha_is_run_tree_head_at_write_time` (mechanism + cwd assertion). |
| **N-1** run_metadata records LLMConfig fields + instruction sha256 | **SATISFIED** | `_live_client_identity` now returns all 6 (`runner.py:451-475`); metadata `max_tokens/max_calls/timeout/temperature` (l.839-849) + `a9_defect_instruction_sha256` (l.849). Tests `test_a9_run_metadata_records_llmconfig_and_instruction_sha` (live) + `…_offline_arm_records_sha_and_nulls` (nulls offline). |

---

## 4. Hard non-changes (verified)

- **M1 definition** — `_diagnosis_correct` byte-identical (no deletions in score.py diff). ✅
- **A1.3 P1 rule string** — I computed: **`len 1224`, sha256 `766f4eb9ac2c97a7c2bbef531492c5ffbbdc274a430eabed5077dd2020e0c988`** = the registered pin (`766f4eb9…20e0c988`). `test_p1_rule_string_is_canonical` asserts `rule == CANONICAL_P1_RULE_V1_2` and `len==1224`; green. ✅
- **A8 executor-parity guard + precedence over canary** — `score.py:576` `if _pair_executor_mismatch(...)` precedes `:596 elif _m1_canary_veto(...)`. Reproduced: a mixed pair fires `executor_parity_violation` even when S4 is non-null ⇒ parity guard wins. ✅
- **Envelope/budget caps, seeds, counts** — diff adds none (grep of `+` lines for `60_000/10_800_000/20261010/20261020/BOOTSTRAP_RESAMPLES/max_wall_s` ⇒ NONE). ✅
- **S5 evidence construction** — `_evidence_block` untouched. ✅
- **Oracle read-path** — diff adds **no** src oracle reader; `load_oracle`/`oracle.json`/`DEFAULT_ORACLES` additions are test-file only. Score.py remains the sole sealed-oracle reader. ✅
- **docs/ untouched** — `git diff --name-only` touches only `src/` + `tests/`. ✅
- **`ProtocolResult.findings`** — additive optional field (`default_factory=dict`); read only at `strategies.py:335-339` (the A9 repl_claw aggregate). No other consumer. ✅

---

## 5. Independent read: is M-1 genuinely fixed end-to-end?

**Yes.** Tracing the full chain: **writer → artifact → scorer M1 input → canary.**

1. **Source of diagnosis:** Every arm's investigator prompt now carries the identical registered defect block (`# DEFECT DIAGNOSIS (required)` + `DEFECT_ADJUDICATION_INSTRUCTION`) — S5 RESOLVE (`orchestrator.py:573`) and all strategy finding prompts (`investigators.py:249`), so every arm can *emit* `defect_class`/`target_artifact`. The strategy path's `Finding` schema and the S5 RESOLVE payload both accept the two fields.
2. **Threading to the artifact:** `_ev`/`findings` carry the full dicts (C8); `_defect_aggregate` computes per-arm first-non-null; `_finalize`/`run_repl_claw` attach it to `StrategyResult.verdict`; `ArmResult` carries it (`arms.py:168-172`); **both** writers (`runner.py:380-381`, `609-610`) write the real value (null only if incomplete). The pre-A9 hard-coded `None` (`runner.py:376-377`, `588-589`) is gone. I confirmed via the six-arm CLI run that `final_verdict.json` for S0/S3/S4/S5 now carries non-null fields and the canary reads "ok".
3. **Scorer M1 input:** `M1` (`score.py:273`) reads `final_verdict.defect_class/target_artifact` via `_diagnosis_correct` — no longer structurally null for comparators, so `M1(S4)` *can* be non-zero.
4. **Canary as last line of defense:** if a regression reintroduced all-null S4, `_m1_canary` (S4-specific) + `_m1_canary_veto` set `P1.decision = "m1_interface_degenerate"` (distinct void state) **before** the bootstrap, without filtering `s4m/s5m`. I reproduced the exact regression (all-null S4, non-null S3) → vetoed, never SUPPORTED — the precise false-positive M-1 forbade.

The structural task-interface asymmetry (comparators unable to emit the field) is closed; the residual "S4 can't *win*" is now a genuine scientific outcome (non-identifiability from base data, per Q2(b)), not a lexical/interface artifact, and the canary guards the interface regression. **M-1 is fixed.**

**Recommendation: merge.** No correctness bugs, no regressions, no oracle/prompt-leak findings. Address S-1 as an application-text disclosure and the two NITs as optional polish. (Read-only review — I did not modify, merge, or push anything.)
