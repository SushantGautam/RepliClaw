# RepliClaw — Execution State (resume cursor)

Status: `COMPLETE`

## Cursor
- Milestone: **COMPLETE — M1–M10 all built, committed, and verified. Every acceptance criterion AC01–AC18 has concrete evidence (map in README).**
- Branch: `repl-claw-dev`
- Commits: `2a7d1e9` (spec) → `e7c4a3b` (M1–M4 core + tests) → `c04b2fa` (M5 baselines + M6 benchmark) → `5f2e012` (M8 verify/CLI) → `acaefbb` (M9 live-LLM demo + M10 README/AC map) → `c010481` (lint/type gate + benchmark re-run reproducibility fix, D13).
- Tests: **62 passing, hermetic** (`python -m pytest`); **`ruff check` 0 errors + `mypy` no issues in 15 files** (AC15 full static gate, D13); clean-venv install verified (AC01).
- Canonical committed evidence: `artifacts/benchmark/` (reports), `artifacts/demo/` (deterministic, incl. AC12 recovery), `artifacts/demo-llm/` (live model outputs, AC16/AC18).

## Verified facts (this segment)
- **61 hermetic tests passing** (`python -m pytest`, ~1.5s, no network).
- Deterministic benchmark (6 known-answer tasks × 5 strategies, computed not hard-coded):
  repl_claw 1.000 correctness / 1.000 recovery / 0 FA / 0 FR / 0 inconclusive;
  single_agent & fixed_dag 0.167 correctness / 0.5 FA; isolated_vote & open_debate 0.500 but 0.5 inconclusive, 0 recovery. Error-correlation proxy 0.558. (artifacts/benchmark/)
- Deterministic demo (`artifacts/demo/`): supported→SUPPORTED 0.98; misleading→REFUTED 0.256 via conflict→falsification follow-up→adjudication (AC12). Transcript shows pre-reveal commitments from event log (`committed` events = hash-only view).
- **LLM-path bug #1 (fixed)**: `_llm_factory` received an `LLMClient` and re-wrapped it (`LLMClient(LLMClient)`) → every LLM investigator silently failed; protocol swallowed the errors and "succeeded" with 0 findings. Fix: pass `LLMConfig`; added `TypeError` guard in `LLMClient.__init__`; added hard-fail in protocol when ALL investigators fail; regression test `test_llm_factory_wraps_config_not_client`.
- **LLM-path bug #2 (fixed)**: `InvestigationContext.to_prompt_block()` never included `claim.data`, so the live model correctly reported "no bundled data" and abstained for all. Fix: prompt block now serializes `claim.data`; `LLMInvestigator` prompt now carries per-role quantitative methods (analyst: Cohen's d; statistician: two-sample t; falsifier: raw-event RR + log-normal CI vs baseline_rr) mirroring the deterministic lenses.
- Live LLM endpoint works through the strategy path post-fix: `single_agent` on misleading fixture → INCONCLUSIVE, 460 real tokens, 2.6s, no errors.
- Full live demo (pre-prompt-fix) took 47s wall clock, ~8k real tokens across 5 strategies × 2 cases.

## Next actions
- None — task complete. For a future session: `python -m pytest` reproduces everything offline; `repliclaw demo --backend auto` reproduces the demo (llm if a key is present, else deterministic).

## Verification log (latest first)
- 2026-10-07: **AC15 strengthened (D13).** Added ruff+mypy gate; fixed 26 ruff + 10 mypy findings (incl. a real `List[str]`→`List[Dict[str,Any]]` bug on `Verdict.unresolved_conflicts`). Result: ruff 0 errors, mypy clean (15 files). Regenerated canonical `artifacts/benchmark/` (committed CSV was stale: `n_needs=4`→`1`, table story unchanged).
- 2026-10-07: **Benchmark reproducibility bug found + fixed.** `RunStore.append_need` is append-mode, so re-running the benchmark into a dirty `_work/` inflated `n_needs` (the root cause of the stale `4`). Fix: `run_benchmark` now wipes each per-run `run_dir` before running; proven by running twice into one dir (both `n_needs=1`) + new regression test `test_benchmark_is_deterministic_across_reruns`. Suite now **62 tests**, ruff+mypy clean, canonical artifact == clean `acaefbb` regen (cols 1–14).
- 2026-10-07: LLM demo second run exposed missing claim.data in prompt (uniform abstention) — fixed with data block + per-role methods.
- 2026-10-07: LLM demo first run exposed double-wrapped client (all-investigator failure masquerading as success) — fixed + guarded + hard-fail + regression test.
- 2026-10-07: M8 committed (`5f2e012`); falsifier lens fixed to abstain when no raw events bundled (was false-refuting on fallback CI).
- 2026-10-07: M5+M6 committed (`c04b2fa`); benchmark table reproduced identically after lens fix (all 6 fixtures carry data).
- 2026-10-07: M1–M4 core + 39 tests committed (`e7c4a3b`); 3-way e2e: SUPPORTED 0.98 / REFUTED 0.534 / REFUTED-recovered 0.256.
- 2026-10-07: LLM endpoint probe verified (model=default, usage returned).

## Confirmed facts (carried)
- Python 3.11.7 (anaconda), networkx/pydantic/openai in env; ScienceClaw vendored at `deps/scienceclaw` (reused via thin adapter, no fork edits).
- LLM: OpenAI-compatible `https://simulachat.sushant.pp.ua/api/v1`, key env `CUSTOM_SIMULACHAT_KEY`, model `default` (Qwen3.8-27B base); usage tokens returned.
- Upstream `NeedItem.rationale` ≥20 chars; `score_need` has wall-clock age term (near-determinism tolerance in tests).
- runstore: `_SEAL_EXCLUDE` = revealed fields + seal_hash; REJECTED phase terminal (one-shot reveal); mismatch re-seals.
- PhaseGate: blind→committed→revealing→revealed→followup→verdict; blind reads metadata-only.
