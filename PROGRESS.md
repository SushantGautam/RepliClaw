# RepliClaw — Progress Log

Append-only. Each entry: what changed / commands run / observed result / artifacts / next action.

## 2026-10-07 — M0 reconnaissance complete
- What changed: Established durable state (`EXECUTION_STATE.md`), git baseline (branch `repl-claw-dev`), and the reuse matrix + 8 decisions in `DECISIONS.md`.
- Commands/evidence:
  - LLM endpoint probe: `POST https://simulachat.sushant.pp.ua/api/v1/chat/completions` model=`default` → correct t-test answer; `usage {prompt:71, completion:66}`; HTTP 200, <1s.
  - ScienceClaw import probe: `artifacts.artifact`, `artifacts.needs`, `artifacts.reactor` import in 0.09s (stdlib+pydantic only); `core.skill_registry.get_registry()` → 334 skills, 0.58s.
  - `ArtifactStore` hardcodes `~/.scienceclaw` (artifact.py:593); `rank_needs` hardcodes `~/.scienceclaw/artifacts` (pressure.py:199) → run-local subclass required.
  - SimpleAuditStudio = Django + hatchet-sdk + postgres; `audits/agentic/schema_v2.py` absent → OTLP integration target, not a core dependency.
  - `score_need = 2*novelty + 1*centrality + 0.5*depth + 0.2*log1p(age_min)` (pressure.py:197).
- Result: Substrate confirmed import-safe; reuse-first path viable without forking ScienceClaw.
- Artifacts: `/tmp/scienceclaw-upstream` (upstream checkout), `DECISIONS.md`.
- Next: Scaffold `repliclaw` package + vendored ScienceClaw; M1 domain model + vertical smoke.

## 2026-10-07 — M1–M4 core built + 3-way verdict path VERIFIED (offline, hermetic)
- What changed: Full `src/repliclaw/` package (canonical, models, runstore, isolation, scienceclaw_adapter, investigators, evidence, verdict, protocol) + vendored `deps/scienceclaw/{artifacts,core}` + pyproject + 3 known-answer fixtures. Tuned `insufficient_evidence` (a directional+executable piece is sufficient) and the conflict gate (a decisive executable follow-up ADJUDICATES a surviving independent conflict → recovery, AC12).
- Commands/evidence:
  - `python artifacts/dev/e2e_3way.py` (deterministic backend, no network):
    - clean_supported → **SUPPORTED** conf 0.98 (3 support/0 contradict, no conflict).
    - clean_refuted → **REFUTED** conf 0.534 (single directional-executable falsifier is now sufficient; replication need fired).
    - misleading_wrong_test → **REFUTED** conf 0.256 (2 support vs falsifier → independent conflict → falsifier-lens follow-up adjudicates → recovery AC12; conflict surfaced + broken).
  - Confidence ordering well-calibrated: 0.98 > 0.534 > 0.256 (clean > clean-null > recovered-misleading).
  - Earlier (same milestone): commit→reveal→tamper→replay→record-tamper integrity cycle passes (AC04); one-shot reveal blocks re-reveal after rejection (fake-independence hole closed).
- Result: The full blind→commit→reveal→evidence→followup→verdict loop is executable and produces correct, evidence-calibrated verdicts for supported / refuted / misleading paths, fully offline.
- Artifacts: `artifacts/dev/e2e_3way.py`, `tests/fixtures/*.json`, `src/repliclaw/*`.
- Next: formal pytest suite (AC14/15) → M5 strategies baselines → M6 benchmark → M8 CLI → M9 live-LLM demo → M10 harden + COMPLETE.

## 2026-10-07 — M5 baselines + M6 controlled benchmark (committed `c04b2fa`)
- What changed: `src/repliclaw/strategies.py` (5 coordination baselines — single_agent, fixed_dag, isolated_vote, open_debate, repl_claw — on one shared task interface, common `StrategyResult`); 3 more known-answer fixtures (wrong_param_magnitude, data_leakage, cherry_picked_subgroup → 6 tasks, 4 seeded fault modes); `src/repliclaw/benchmark.py` (computed metrics: correctness/FA/FR/inconclusive, cross-strategy error-correlation proxy, recovery, diversity, tokens, latency; CSV/JSON/MD; nothing hard-coded); `tests/test_strategies.py` + `tests/test_benchmark.py` (11 tests → 50 passing).
- Commands/evidence: `python -m repliclaw.cli benchmark --out artifacts` → repl_claw 1.000 correctness / 1.000 recovery / 0 FA / 0 FR / 0 inconclusive (4 agents/run); single_agent & fixed_dag 0.167 correctness / 0.500 false-accept; isolated_vote & open_debate 0.500 correctness but 0.500 inconclusive / 0.000 recovery; error-correlation proxy 0.558. On the misleading fixture: single_agent/fixed_dag false-accept (SUPPORTED), vote/debate abstain, repl_claw recovers (REFUTED).
- Result: differentiation hypothesis supported on controlled known-answer tasks; M5/M6 evidence under `artifacts/benchmark/`.
- Next: M8 CLI `repliclaw verify`.

## 2026-10-07 — M8 cross-team verify() + CLI (committed `5f2e012`)
- What changed: `src/repliclaw/verify.py` (`verify(claim, artifacts=None, config=None)` — str/dict/Claim input, deterministic|llm backends, isolated run dir per call, provenance-linked `verify_report.md`/`.json`); `src/repliclaw/cli.py` (`verify` / `benchmark` subcommands, `main(argv)`); public exports in `__init__.py`; falsifier lens fixed to abstain (uncertain) when no raw events are bundled (previously false-refuted on the fallback CI).
- Commands/evidence: `python -m pytest` → 59 passing; CLI verify: supported data → SUPPORTED 0.980; misleading data → REFUTED 0.256 with emitted falsification need; bare string claim (no data) → INCONCLUSIVE (correct abstention); `repliclaw benchmark` table reproduced.
- Result: AC02/AC13/AC16 surface complete and tested (9 CLI/verify tests).
- Next: M9 live-LLM demo.

## 2026-10-07 — M9 live-LLM demo: two silent LLM-path bugs found & fixed
- What changed (bugs surfaced by real model runs, AC18-safe — kept the bad intermediate outputs as evidence in git history of this doc):
  1. `verify._llm_factory` re-wrapped an `LLMClient` as its config → `LLMClient(LLMClient)`; every LLM investigator raised `AttributeError`; the protocol swallowed per-agent exceptions and the run "succeeded" with zero findings → uniform INCONCLUSIVE 0.05. Fixed: factory receives `LLMConfig`; `LLMClient.__init__` now raises `TypeError` on a client; `RepliClawProtocol.run` hard-fails (`RuntimeError`) when ALL investigators fail (0 findings is no longer a silent success); regression test `test_llm_factory_wraps_config_not_client`.
  2. `InvestigationContext.to_prompt_block()` omitted `claim.data` → the live model (correctly) reported "no bundled data provided" and abstained. Fixed: prompt block serializes `claim.data`; `LLMInvestigator` now includes per-role quantitative methods mirroring the deterministic lenses (analyst: Cohen's d; statistician: two-sample t vs alpha; falsifier: raw-event RR + log-normal 95% CI vs baseline_rr).
- Commands/evidence:
  - Post-fix live probe: `run_strategy("single_agent", misleading_fixture, llm_factory)` → verdict INCONCLUSIVE, 460 real tokens, 2.6s, 0 errors.
  - `repliclaw demo --out artifacts/demo-llm --backend llm` (real Qwen3.8-27B via OpenAI-compatible endpoint): genuine-supported case → **SUPPORTED** conf 0.980; misleading case → **REFUTED** conf 0.980 (all 3 roles independently refuted → no unresolved conflict → no follow-up needed, 2780 real tokens, 8.0s); full baseline table in `artifacts/demo-llm/demo_summary.md`; transcript shows hash-only pre-reveal commitments from the event log.
  - Live run note (kept, not spun): on the LLM backend the raw-event reading is straightforward enough that all three roles agree; the evidence-conditional follow-up branch fires only on actual conflict (shown by the deterministic run). Demo interpretation section is now derived from the computed tables, not a fixed narrative.
- Result: AC18 demo path works end-to-end with real generated outputs; `artifacts/demo-llm/` committed.
- Next: M10 — README (AC17) + AC01–18 evidence map + final verification + COMPLETE.

## 2026-10-07 — M10 README (AC17) + AC evidence map + final hardening
- What changed:
  - `README.md` (new, AC17): scientific hypothesis, architecture (6 phases + module table), why-not-a-fixed-DAG, install/test (AC01), cross-team surface (AC13, example verified verbatim → REFUTED 0.256), 5 baselines, benchmark table, demo guide, AC01–AC18 evidence map.
  - `verify.py`: artifacts carrying a `data` block are merged into `claim.data` so cross-team `--artifact file.json` feeds the analytical lenses (new test `test_verify_artifact_with_data_block`).
  - Fixtures (D12): mean direction now matches "treatment increases" in clean_supported/misleading_wrong_test/wrong_param_magnitude/data_leakage + test/README examples. Zero deterministic regression (lenses are magnitude-based): 61 tests, demo 0.980/0.256, benchmark table identical.
  - `investigators.py`: `max_tokens` default 1024→4096 + one retry-with-terse-prompt in `chat_json` (live model was truncating verbose JSON → ValueError); LLMClient double-wrap guard; protocol hard-fail on zero findings (all from D10).
  - `demo.py`: Case-2 heading + interpretation are now derived from run outputs (code-review fixes): follow-up described as "fulfilled" only when actual follow-up evidence exists; pre-reveal table shows only initial-round commitments (events before `revealing` phase).
  - Repo hygiene: `artifacts/benchmark/_work/` and `artifacts/verify/` untracked + gitignored (churny byproducts); canonical evidence = benchmark reports + `artifacts/demo*/`; `.egg-info` gitignored.
- Commands/evidence:
  - Clean-env install (AC01): `python3 -m venv /tmp/repliclaw-venv && pip install -e ".[dev]" && pytest` → **61 passed** in fresh venv.
  - `python -m pytest` (system env) → **61 passed in ~1.5s** (hermetic, no network).
  - `python -m compileall -q src/repliclaw tests` → OK (AC15 static check).
  - `repliclaw demo --backend deterministic` → supported SUPPORTED 0.980; misleading REFUTED 0.256 with 1 emitted+fulfilled follow-up (AC12); baselines: single_agent/fixed_dag false-accept, vote/debate abstain.
  - `repliclaw demo --backend llm` (real Qwen3.8-27B, ~60s, ~19k real tokens) → supported SUPPORTED 0.980; misleading REFUTED 0.980 (all 3 roles independently executable-refute → no conflict → 0 needs, stated as such); full run dirs under `artifacts/demo-llm/`.
  - `repliclaw verify` README example verbatim → REFUTED 0.256 (matches documented output).
  - Independent code review (code-review subagent): 2 HIGH narrative issues found → both fixed (data-driven heading/interpretation, fulfillment gated on evidence); re-review scope = no blocking issues.
- Result: All 18 ACs have concrete, committed evidence (map in README §Acceptance-criteria evidence map).
- Next: final state-file pass → status COMPLETE.
