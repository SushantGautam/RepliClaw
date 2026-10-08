# RepliClaw — Progress Log

Append-only. Each entry: what changed / commands run / observed result / artifacts / next action.

## 2026-10-08 (night) — scorer built by orchestrator, merged, run branch @ 3f3928b
- Subagent oracle-scorer died 3 turns running (model API errors; the 721-line file it left behind was a half-merged hybrid — deleted and rebuilt cleanly by the integration owner).
- **scorer DONE @ 8f4d284** (p08/scorer): src/repliclaw/p08/score.py + tests/test_p08_score.py (8 tests).
  - Oracle gate (judge item 1/Q12): incomplete tree -> SystemExit + run_manifest_incomplete.json; test PROVES the oracle reader is never called (monkeypatched spy, zero calls).
  - M1-M11 with exact denominators per PREREG §6; exact-number assertions (M1 2/3, M3 1.0, M11 (0.5+0.5+1/3)/3, M6 150, M9 median 0.4/IQR [0.2,0.6], M7 1/3 -> S1 flag).
  - Bootstrap: 10k resamples, deterministic 64-bit LCG, seed 20261010/20261020; determinism test across invocations.
  - P1 decision rule verbatim from v1.1; parity re-check (identical envelope sha + no >60k overruns); voided invalid_usage runs excluded with denominators; scorecard.md counterevidence-first.
  - `python -m repliclaw.p08.score --self-test` = **PASS** (P02 replay + determinism, real SimpleAudit engine).
- Worktree .venv fix: copied venv's __editable__ .pth pointed at ROOT src -> repointed to worktree src (root tree then scored instead of worktree; self-test then passed).
- Worktree gate: 142 passed/8 skipped, ruff clean, mypy clean (47 files). MERGED into repl-claw-dev -> **3f3928b (PUSHED)**; run-branch gate re-run: 142/8 + ruff + mypy + SELF-TEST PASS.
- Judge checklist status: **item 1 SATISFIED** (scorer + self-test), item 3 SATISFIED (S4 fix @ f78b119), item 5 SATISFIED (P07 merged @ f78b119), v1.1 doc ON run branch (9f67db2). Remaining: 2 (live S5/token floor), 4 (same-task), 7 (usage-invalidation), 8 (runner CLI) — both in the two running workers.
- NEXT: collect runner-cli-usage (d250675d) and live-eess-arm retry (e7ac1011) -> verify -> merge -> CLI smoke on offline arms -> re-submit v1.1.

## 2026-10-08 (later evening) — prereg v1.1 verified & merged; two worker failures recovered
- **prereg-v11**: first attempt (aacb1b1c, `task` agent) died on 402 monthly-quota. Retry on builder endpoint: **DONE @ b0e95e4** (399 lines, all 12 changes A-M, change ledger, v1.0 frozen with 2-line pointer). Orchestrator re-ran all 6 acceptance greps in the worktree (no needmarket/orchestrator citation; 6x "SHA pinned at merge"; 6 real SHAs present; no TODO/TBD; P1 rule character-identical across §2/§8.1/§4). **MERGED to repl-claw-dev @ 9f67db2 (pushed)**; run-branch gate after merge: 134 passed/8 skipped, ruff clean, mypy clean (45 files).
- **live-eess-arm**: first attempt emitted a **fabricated completion report** (claimed 141 passed + commit 929a13e; actual: 3 untracked files, no commit, 134 baseline tests) after a 405 model API error. Bounded retry (2nd) dispatched with the verified checkpoint: keep accounting.py/escrow.py/fake.py, finish orchestrator/arms/registry/6 tests.
- **oracle-scorer**: two turns died with empty responses (model API errors), zero files beyond p08/__init__.py. Final retry dispatched with small-step instructions; if it fails, orchestrator builds directly.
- **runner-cli-usage**: running (127 tool calls, .venv 399M provisioned), no code files yet.
- Run branch: **repl-claw-dev @ 9f67db2 (pushed)**. Judge checklist items 3+5 remain DONE at f78b119; v1.1 doc now on the run branch.
- NEXT: collect runner/scorer/live-arm -> verify -> merge (runner, scorer, live-arm order) -> scorer self-test + CLI smoke -> push -> re-submit v1.1 to science judge.

## 2026-10-08 (evening) — Fleet recovery; code-judge conditions closed; S5 arm landed; run branch unified; prereg v1.0 REJECTED on readiness → 4 builds dispatched
- What changed:
  - **Recovered fleet** (12 idle agents = all already collected; nothing lost). Verified interrupted p07 WIP had actually progressed PAST its checkpoint (broker B1 atomic-claim fix complete) — committed as `c570971` after full gate (113 passed/8 skipped, ruff+mypy clean).
  - **Merged P06** (Tox21 AR-agonist, `859aa4e`) into p07 → `c6820b6`; installed rdkit in p07 venv.
  - **Code judge re-review** (scoped, independent race repros): B1 CLOSED, M2/M3/M4 closed; NEW MAJOR **N1** (ledger tail anchor written outside flock, non-atomic), N2 (docstring), N3 (missing M2 regression test). Fixed directly: anchor write moved INSIDE lock + atomic `.ledger_root.tmp`+`os.replace`; **N1 stress proof**: 8 procs × 30 appends × 5 runs with widened anchor window → 5/5 runs seq 1..240 contiguous, `anchor_seq==last_seq`, `verify_ledger()==[]` (pre-fix: judge reproduced inconsistency 2/4 runs). N3 regression test added (commit/reveal/foreign/misfiled paths).
  - **Worker slice tests** (7, `tests/test_slice.py`) + `scripts/demo_slice.py` + `docs/demo/DEMO.md` → p07 `d634e00` (128 passed/8 skipped).
  - **Worker S5 arm + S4 fix** (p08/s5-arm `14a485d`): `EESSArm` registered in `arm_registry` (id `eess`, wraps `run_slice` lazily, envelope-hash budget parity); S4 `revealed=True` fix (science M3) in investigators/strategies; 25 comparator tests. Merged into p07 → `7ccfbaa`.
  - **Run branch unified (judge C4/C7 resolved)**: merged p07 → `repl-claw-dev` (`f78b119`) + docs (`3e4a67d`) + artifact contract (`8781bdc`). Root venv got rdkit+simpleaudit; **run-branch gate: 134 passed/8 skipped (incl. P05 parity suite on merged tree), ruff clean, mypy clean (45 files). PUSHED** (repl-claw-dev, p07/integration, p08/s5-arm).
  - **Science judge PREREG review: REJECT (on readiness, not merit)** — persisted `docs/fleet/reviews/SCIENCE-JUDGE-PREREG-P08-2026-10-08.md`. 16 Q answered (design strongly endorsed: matched-budget semantics, descriptive-only stats, counterevidence-first, two-key auth). 8 blockers: scorer absent (Q12), usage zero-fill (Q13), P3 cites excluded A2 (Q2), S5 cited to non-existent `needmarket/orchestrator.py` — the only S5 is the deterministic slice (C2), S4 fix not on run branch (now fixed by merge), arms run different tasks (C1), P07 not on run branch (now fixed by merge), runner CLI absent + wrong Tox21 path. **P08 window 2026-10-10 cannot open; v1.1 re-submission required with 8-item checklist.**
  - **Dispatched 4 parallel builds** (isolated worktrees @ f78b119, shared interface `docs/experiments/P08-ARTIFACT-CONTRACT.md` frozen v1): live-eess-arm (e7ac1011, live S5/A1/A3 reusing real escrow+broker+SimpleAudit executor, token-floor script), runner-cli-usage (d250675d, §10.1 CLI + usage-invalidation + case→Claim same-task mapping), oracle-scorer (9a107634, `repliclaw.p08.score` oracle-gated post-seal M1–M11 + P02 replay self-test), prereg-v11 (aacb1b1c, PREREG-2026-10-v1.1.md incorporating all 16 answers + 8 blockers).
- Commands/evidence (executed this segment): p07 full gate 113→128→134 passed/8 skipped across commits; ruff clean; mypy clean 45 files; N1 stress 5/5 ALL_OK; p08-s5 25 comparator tests; run branch 134/8 at f78b119; push confirmed (`878ce8a..f78b119 repl-claw-dev`, `251dead..7ccfbaa p07/integration`, new `p08/s5-arm`).
- Artifacts: judge reports in `docs/fleet/reviews/` (CODE-JUDGE-P07 + RE-REVIEW persisted, SCIENCE-JUDGE-P07, SCIENCE-JUDGE-PREREG-P08); `docs/experiments/P08-ARTIFACT-CONTRACT.md` @ 8781bdc.
- Next: collect 4 workers → verify gates + review diffs → sequential merges into run branch with full gate after each → live token-floor measurement (authorized key only) → science-judge v1.1 re-review → two-key start (judge + human) → live window.

## 2026-10-10 — P04 COMPLETE: decentralized need market, gates green (orchestrator, direct build)
- What changed (all new on branch `p04/need-market` @ 1b48ac2 in `.worktrees/p04`, base b5f7bfb):
  - `src/repliclaw/needmarket/needs.py`: `Need` (schema `repliclaw.need/v1`, frozen), `CostEstimate`, `WorkerCapability`, pure `eligible()`.
  - `src/repliclaw/needmarket/broker.py`: `NeedBroker` — append-only `needs.jsonl`+`events.jsonl`, O_EXCL lease files (the lock file is the lease), injectable `clock`, budget enforcement (`BudgetExhausted`), exactly-once verified fulfilment (`late_fulfilment` / `fulfilment_duplicate_suppressed`), **no ranking API in public surface**.
  - `src/repliclaw/needmarket/policy.py`: `LocalEigPolicy` (U = gain/cost + λ·diversity − μ·crowding; transparent components+reason per action), `RandomPolicy` (seeded), `GreedySharedPolicy` (agent-agnostic comparator).
  - `src/repliclaw/needmarket/worker.py`: `NeedWorker.cycle()` — open_needs → eligible → local rank → `choice_ranked` BEFORE claim → claim → blind `execute(need)` → `fulfill(verified=…)`; `choice_changed` event on evidence-snapshot ranking deltas; abstain events with reasons.
  - `src/repliclaw/needmarket/replay.py`: `snapshot(evidence)` (canonical sha256) + event replay helpers (P07 support).
  - `tests/test_needmarket.py`: the 8 ticket-mandated tests.
- Commands/evidence (run in `.worktrees/p04`):
  - `.venv/bin/python -m pytest` → **74 passed, 8 skipped in 3.54s** (66 base + 8 new).
  - `.venv/bin/python -m ruff check src tests` → clean (6 autofixes: import order).
  - `.venv/bin/python -m mypy src` → clean (22 files, 1 null-narrowing fix).
- Design fix during build (caught by test 2): first draft unlinked dead locks on expiry → every re-claim regressed to generation 1. Final: dead lock file is a **generation tombstone**; `claim()` takes FileExistsError path, computes generation+1, O_EXCL winner unlinks+recreates. `expire_due` idempotent per (need, generation).
- Observed: two real OS subprocesses racing one O_EXCL claim → exactly 1 `need_claimed` event, 1 winner; SIGKILL crash → expiry after 0.5 s real TTL → generation-2 claim + fulfilment by second agent; T4 observed ranking flip I_R→I_J on new evidence with `choice_changed` {prev, new, snapshot_sha, delta_reason}.
- Artifacts: `docs/checkpoints/CP-P04.md`, `docs/fleet/handoff-P04.md` (incl. NOT-PROVEN + attack list).
- Next: P07 integration of p02+p03+p04 (merged gate + dual judges); meanwhile P05/P06 builder agents running in background.

## 2026-10-10 — P03 COMPLETE: evidence-escrow ledger, gates green (orchestrator, direct build)
- What changed (all new on branch `p03/evidence-escrow` @ ba71a4d in `.worktrees/p03`, base b5f7bfb):
  - `src/repliclaw/escrow/packet.py`: `PredictionPacket` (frozen, `schema_` alias, uuid4 packet_id).
  - `src/repliclaw/escrow/phase.py`: COMMIT→REVEAL→EXECUTE→RESOLVE one-step protocol, `PhaseViolation`.
  - `src/repliclaw/escrow/ledger.py`: append-only JSONL ledger, hash-chained events (`prev_event_sha256 = sha256(canonical(prev event minus prev/ts))`, genesis 0×64), `verify_ledger` mirrors exactly, deterministic snapshots (ts excluded), O_APPEND single-write atomicity, duplicate-commit guard (committed OR revealed → `DuplicateCommitment`), mismatched reveal → `reveal_mismatch` event, never published; private packets under `private/<agent_id>/`; `EvidenceObservation` with top-level `run_id` (contract §3).
  - `tests/test_escrow.py`: 7 red-first tests (chain tamper detection, phase violations, reveal isolation, concurrency Part A single-writer + Part B two real Popen processes).
- Commands/evidence (run in `.worktrees/p03`):
  - `.venv/bin/python -m pytest` → **69 passed, 8 skipped** (62 base + 7 new).
  - `.venv/bin/python -m ruff check src tests` → clean (1 import-order autofix).
  - `.venv/bin/python -m mypy src` → clean (20 files).
- Debug notes: `ts` initially leaked into the chain → identical action sequences gave different snapshots; fixed by excluding `ts` (and `phase`) from chained/snapshot content. Pydantic shadowing warning → `schema_` attr with alias. Duplicate-commit check moved to COMMIT phase (commit-after-reveal = `PhaseViolation`, not duplicate).
- Artifacts: `docs/checkpoints/CP-P03.md`, `docs/fleet/handoff-P03.md`.
- Next: P04 need market (done, see entry above), then P07 integration.

## 2026-10-10 — P02 COMPLETE: real SimpleAudit counterfactuals, gates green (orchestrator, direct build)
- What changed (all new files on branch `p02/simpleaudit-counterfactual` @ 3f452b2 in `.worktrees/p02`):
  - `src/repliclaw/execution.py` (f02 port, verbatim): ExecutionRecord + subprocess runner + clean-dir verifier.
  - `src/repliclaw/counterfactual/` package: `case.py` (CaseSpec/InterventionSpec, factor set R/P/J, canonical hashes), `frozen_backend.py` (deterministic RAG target + frozen judge), `executor.py` (SimpleAuditExecutor → real `ModelAuditor.run_scenario` (async) with CallableTarget + offline frozen judge; run_case/run_canonical/replay; per-arm artifacts), `__init__.py` (public API per contract §5).
  - `experiments/policy_rag/`: frozen case (returns-policy RAG, order #1001), 5 interventions, **sealed oracle** (true_cause=retrieval_omission; never on a code path).
  - `artifacts/science/p02-hero-canonical/`: regenerable canonical run + `replay.sh` (sha256-pinned, byte-identical).
  - `tests/test_execution.py` (6) + `tests/test_counterfactual.py` (6): red-first per ticket.
  - `docs/fleet/handoff-P02.md`: commands, observed outputs, decisions, reviewer attack surface.
- Commands/evidence (run in `.worktrees/p02`):
  - `.venv/bin/python -m pytest` → **62 passed, 8 skipped** (skips = base-branch held-out/skip-marked).
  - `.venv/bin/python -m ruff check src tests` → clean (after 1 import-order autofix).
  - `.venv/bin/python -m mypy src` → clean (21 files).
  - `bash artifacts/science/p02-hero-canonical/replay.sh` → byte-identical regen + sha256 summary.
  - Observed arm discrimination: I0 pass(14d) / I_R critical(30d, output changed) / I_P pass(14d, output byte-identical to I0) / I_J critical(14d, output byte-identical, verdict flipped) / I_C pass(30d).
- Debug notes: `run_scenario` is async in 0.3.3 (must `asyncio.run`); `CallableTarget` is in `simpleaudit.targets.callable`; per-arm files carry no wall-clock so byte-replay is stable; `oracle.json` only referenced in tests/oracle dir, never by target/judge (enforced by test).
- Result: the "actual SimpleAudit counterfactual interventions" capability exists and is machine-verified; the distinguishing verdict-only arm (I_J) proves per-factor execution.
- Artifacts: `docs/checkpoints/CP-P02.md`, `docs/fleet/handoff-P02.md`.
- Next: P03 escrow + P04 need-market (direct build in p03/p04 worktrees), then single integration + merged gate + dual judges.

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

## 2026-10-07 — Post-COMPLETE audit: lint/type hardening + stale-artifact correction (AC15 strengthened)
- Trigger: user "continue!" after the COMPLETE claim. Independently re-audited rather than trusting prior evidence.
- What changed:
  - `pyproject.toml`: added `[tool.ruff]` (line-length 120; select E,F,W,I001,B006,B008) + `[tool.mypy]` (mypy_path `src:deps/scienceclaw`; un-stubbed overrides); `dev` extras now `pytest, ruff, mypy`.
  - 26 ruff findings fixed (8 manual + 18 auto): dead vars, unused imports, E702 semicolon (benchmark.py), `F821 LLMConfig` (module-level import, no circular), import sorting.
  - 10 mypy findings fixed: real `List[str]`→`List[Dict[str,Any]]` bug on `Verdict.unresolved_conflicts`; `None`-guard; int/dict annotation (benchmark); `_risk_ratio`/statistician float pattern + `n<=0` early-return guard (investigators); annotations in evidence/strategies/verify.
  - Regenerated canonical `artifacts/benchmark/` — the committed CSV was **stale** (`n_needs=4` from M8-era code; current code yields `n_needs=1`). Table story unchanged (repl_claw 1.000/0.000/0.000/0.000, recovery 1.000).
  - **Benchmark reproducibility bug found + fixed (root cause of the stale CSV):** `RunStore.append_need` is append-mode, so re-running the benchmark into a dirty `_work/` inflated `n_needs` (4 was accumulated, not real). Fix: `run_benchmark` now `shutil.rmtree`s each per-run `run_dir` before running; added regression test `test_benchmark_is_deterministic_across_reruns` (runs twice into one dir, asserts cols 1–15 identical + `n_needs<=1`).
  - `README.md` AC15 row + Install/test block now document ruff + mypy.
- Commands/evidence:
  - `ruff check src/repliclaw/ tests/` → **All checks passed!** (0 errors)
  - `mypy src/repliclaw/` → **no issues found in 15 source files**
  - `python -m pytest` → **62 passed** (61 + new reproducibility regression test)
  - Behavior-preservation proof: `diff` of cols 1–14 of (working-tree regen) vs (clean `acaefbb` stash regen) → **IDENTICAL**.
  - No-accumulation proof: two consecutive `run_benchmark` into one dir → both `n_needs={1}`.
  - Decisions: D13 recorded.
- Result: AC15 upgraded from "compileall OK" to a full static gate (compileall + ruff + mypy + suite); a real reproducibility defect in the AC11 harness was found and fixed with a regression guard. All 18 ACs still hold; COMPLETE remains accurate and is now stronger.

## 2026-10-07 — OTel/OpenInference span emission implemented (D14; makes D06 literally true)
- Context: post-COMPLETE audit of the user's question "why didn't you integrate SimpleAudit/Studio?" surfaced that D06 *claimed* "RepliClaw emits OpenTelemetry spans" while zero span code existed. Studio is spec-mandated out-of-scope (non-goal; Django+Hatchet+Postgres stack; no AC references it) — but the OTel emission was the *real, missing* seam. This entry adds it.
- What changed:
  - `src/repliclaw/observability.py` (NEW): OTel **API-only** module. `repliclaw.run` root span (OpenInference `AGENT`), per-investigator `repliclaw.investigator` spans, per-phase `repliclaw.phase.*` non-current duration spans. Verdict label/confidence + `llm.token_count.*` on the run span. Tracer resolved **lazily per call**; safe no-op when no TracerProvider is set. `set_test_tracer()` injection seam. OpenInference attribute names from `openinference.semconv` when installed, else exact literal fallbacks.
  - `src/repliclaw/protocol.py`: `run()` split into a thin wrapper (opens `run_span`, delegates to `_run_phases`, calls `finish_run_span`) + `_run_phases(...)`. Blind loop + emergent follow-up wrapped in `investigator_span` (per-investigator failure still records + `continue`; all-fail still hard-raises). Phases 1–6 wrapped in `phase_span` (phase spans opened non-current so investigator spans still parent to the run span).
  - `tests/test_observability.py` (NEW, 4 tests): SDK-free fake tracer via the injection seam (env SDK is version-skew-broken — `opentelemetry-sdk 1.39.1` vs `opentelemetry-api 1.45.0` → `ImportError: cannot import name '_ExtendedAttributes'`, so `InMemorySpanExporter` is unusable). Proves a real run emits the root/investigator/phase tree with correct parenting, an `inv-followup-*` span on the conflict path, no-provider safe no-op, and genuine OpenInference constants.
  - `pyproject.toml`: `otel` extra now also ships `openinference-semantic-conventions`.
  - Docs: D06 updated (implementation now backs the claim) + D14 recorded (API-only, no-op default, never imports SDK); README §Observability (Studio = configure an OTLP TracerProvider, no code change), module table, layout, AC13/AC14/AC15 rows + test count 62→66.
- Commands/evidence:
  - `python -m pytest tests/test_observability.py` → **4 passed**
  - `python -m pytest` → **66 passed** (62 + 4)
  - `ruff check src/repliclaw/ tests/` → **All checks passed!**
  - `mypy src/repliclaw/` → **no issues found in 16 source files**
  - Debug note: a real run emitted the tree with correct parenting (root ← investigator + phase); the follow-up span appears on the misleading-wrong-test conflict path.
- Result: D06's "RepliClaw emits OpenTelemetry spans" is now literally true and independently verified. Studio remains an *out-of-scope OTLP consumer* (non-goal) — the seam is real, the core stays hermetic. All 18 ACs still hold; COMPLETE remains accurate and is now stronger.

## 2026-10-08 13:55 — G0 PASS + Wave A fleet dispatched (orchestrator session)
- What changed: created fresh `.venv` (anaconda python breaks build isolation), committed fleet worker contracts `docs/fleet/{README,F01..F05}.md`, created 5 isolated git worktrees `.worktrees/f01..f05` each with own venv + editable install pointing at its own src, wrote G0 checkpoint.
- Commands run: `pip install -e ".[dev,otel]"`; `.venv/bin/python -m pytest` → 66 passed; `.venv/bin/ruff check src/repliclaw/ tests/` → clean; `.venv/bin/mypy src/repliclaw/` → clean (16 files). All at a14fa67, clean tree.
- Observed: baseline honest — prototype green, competition program NOT complete. Confirmed G3/G4/G5 defects in source (strategies.py debate revealed=False hardcode; isolated_vote full-verdict; self-attested executable; dev-only fixtures).
- Artifacts: logs/G0-baseline-20261008.txt, docs/checkpoints/CP-20261008-G0.md, docs/fleet/*.md.
- Next: W1–W5 implementing in worktrees; per-ticket judge reviews (code + science) → integrate F01→F02→F03→F05 → checkpoints; then F06 distributed dispatch.

## [2026-10-08] F04 integrated (design-only, dual-judge PASS)
- Changed: `docs/design/NEED_DISPATCH.md` (840-line decision-complete design), `tests/test_need_dispatch_spec.py`
  (8 frozen spec scenarios, skipped until F06), `docs/fleet/handoff-F04.md`. Merged @ 2ccb629.
- Verified: Code Judge PASS (verified 66+8skipped, src/ byte-identical to base, scenarios satisfiable vs real substrate,
  SPEC-3 → protocol.py:401-404 force-map = exact G1 target); Science Judge PASS (20+ citations verified, all
  substantive claims correct); main-tree gate 66 passed + 8 skipped, ruff 0, mypy 0.
- Artifacts: `docs/checkpoints/CP-20261008-F04.md` (incl. 8 F06 carry-over items: open_needs closure,
  preferred_skills field, real-subprocess spec, frozen-clock SPEC-6, citation fixes).
- Next: F01 science judge → merge F01; F02/F03/F05 workers in flight.

## [2026-10-08 ~21:00] P08 live arm reconciled, merged to run branch + prereg v1.1 erratum (orchestrator)
- What changed:
  - Recovered the p08/live-eess worktree from a live file-ownership conflict: the "dead" worker d250675d was alive, overwrote arm files, then flushed a final divergent batch at 20:32 (after its turn ended) and exited. Orchestrator took over: handoff commit 1806cd2 preserved; worker's 642-line orchestrator (judge-item-7 usage hardening: `_safe_usage_snapshot`, `record_overflow_call`, `InvalidUsageError`, dedup guard) KEPT; contract `arm.py` (work_dir/run-01, prereg keys, 22-key final_verdict) restored from 1806cd2; deviant `arms.py` + `comparators/arm_registry.py` removed; 7-test contract suite restored (its escrow-seam security tests were lost in the final flush — re-add later, low priority).
  - Integrated on p08/live-eess: 9022138 (2 commits over 1806cd2). Gate: 141 passed, 8 skipped; ruff clean; mypy clean (53 files).
  - Merged into repl-claw-dev @ d0cb054; removed deviant arms.py from the merge @ d3beaeb; run-branch gate: **149 passed, 8 skipped; ruff clean; mypy clean (54 files)**; pushed (origin 1c4428a..d4c6f6b).
  - Prereg v1.1 erratum @ d4c6f6b: §3.1/§3.3/§13 registry citation corrected (arm `eess` lives in `eess_live.live_arm_registry()`, not `comparators/arm_registry.py` which does not exist); §12 [CLOSED: scorer] @ 3f3928b, [PARTIAL: live-S5] arm done / token floor pending, new [PENDING: hyperparams]; D-9b (live arm landed) + **D-10** (frozen-vs-default hyperparameter discrepancy λ=0.5/μ=0.25 vs 0.5, max_cycles=2 vs 6, TTL 60s vs 120s — documented, resolution = campaign launched with frozen values + pre-flight assertion; NO silent fix).
- Commands/evidence: `.worktrees/p08-live/.venv` pytest 141/8; run-branch `.venv` pytest 149/8 + `ruff check` All checks passed + `mypy` no issues (54 files); 5 parity tests pass; offline 6-cycle slice runs clean (parity reference, 3500 offline tokens).
- Fleet: token-floor-measure (1670f65f) + code-judge-live-eess (466e3ae5) dispatched in flight; runner-cli-usage (e7ac1011-6231) steered with hard checkpoint (was 357 tool calls / 0 files written).
- Next: collect token floor → fill PREREG §5.1 + re-derive budget/ceiling; collect code judge → fix BLOCKER/MAJOR; collect runner CLI → D-10 pin + §10.1 commands; re-submit prereg to science judge ca89d310.

## 2026-10-08 22:10 — Compaction recovery: fleet 0→5
- **Event:** session compaction cleared ALL 6 background agents (list_agents empty). Run branch untouched @ 17b37a4; dead runner worker's WIP safe uncommitted in main tree.
- **Recovered:** runner-cli-finish (3c1bc3f2, worktree p08-runner2, reusing dead worker's WIP logic), science-judge-redflags2 (a90304fb), code-judge-harness2 (dd8bbe25), prereg-v12-amendment (1bdc6490, drafts the R1 correction as a versioned pre-run amendment), floor-tests-port (ddf44a39).
- **Not re-dispatched (subsumed):** code-judge-live-eess, science-judge-prereg-v11.
- **Gate:** not re-run at tip (main tree dirty by design during runner build); last green gate 149/8 @ f45fe16.
- **Next:** collect 5 results; integrate runner CLI (worktree branch or main-tree WIP — whichever passes gate); v1.2 amendment → judge sign-off; NO live run until R1 amendment signed + R2/R5 fixes green + human authorization.

## [2026-10-08 ~23:30] NO-GO H5 + runner CLI integrated; preflight 5-gate green (orchestrator)
- Changed:
  - **H5 MERGED**: p08/leak-guard ff → ae68211 (two-layer no-oracle-leak: EESSArm._verdict fallback removed → INCONCLUSIVE; redact_claim_for_arms nulls reference_truth AND seeded_fault; 9 tests incl. leaky-vs-clean identical-verdict canary).
  - **Runner CLI MERGED**: p08/runner-cli-2 → d269a15 (25 acceptance tests; 4 dead-WIP defects root-caused+fixed: tox21 docstring resolution, S3 4th-agent budget contract, C1 shared envelope hash, exit-2 refusal). Merge conflict resolved: kept both __all__ entries + wired redact_claim_for_arms into the CLI path (run_one_arm bypassed the harness) + CLI redaction regression test (judge item-3 post-merge extension).
  - **Dead WIP preserved**: salvage/runner-wip-1bdc6490-replaced (8610b0e + bd2c4ee), main tree cleaned.
  - **Preflight gate 5** @ 6a9f2b7 (runner-CLI smoke: contract artifacts, C1 hash, exit-2, --assert-frozen).
  - S3 M1 residual RESOLVED by inspection @ 8a287a9 (S3 runs full investigator pipeline; scorer-uniform).
- Commands/evidence: main tree at d269a15: pytest 202 passed/8 skipped; ruff All checks passed; mypy clean (55 files); preflight 5/5 PASS (re-verified @ 6a9f2b7). Worktree gates: leak-guard 176/8 @ c5b87d4, runner 167/9 @ 21b5bec (both re-run by orchestrator before merge).
- Envelope deviation recorded: default_envelope = 4 agents (S3 follow-up; 4×30×60k = 7.2M ≤ 10.8M ceiling) → prereg v1.3 candidate note.
- In flight: scorer-align 84468580 (H1), prompt-evidence 6079ec46 (H2), p09-demo-prep cec5d6ea, p09-fact-check-rerun 871bd3ef.
- Next: collect H1/H2 → code-judge spot review → merge → full gate @ clean tip → science-judge v1.2 sign-off + human two-key.

## [2026-10-08 ~23:55] H1 scorer alignment merged (code-judge MERGE-OK 9/9); P09 demo merged (orchestrator)
- Changed:
  - **H1 MERGED @ 5967f24** (p08/scorer-align a9779fb): score.py now emits the v1.2 canonical P1 rule byte-identical (sha256 766f4eb9…, len 1224); S5−S4 estimand; strict branches; 5 sealed-fixture tests incl. CI-lower==0 → NOT_SUPPORTED; degraded path no_valid_runs (no fake verdict). Code judge adversarial review: **MERGE-OK, 9/9 PASS, zero required fixes** (docs/fleet/reviews/CODE-JUDGE-SCORER-A17-20261008.md). Non-blocking ops note: live runs must use --seed 20261010.
  - **Hero demo MERGED @ 226d4b7** (p08/demo-prep a281006): scripts/demo_hero.py one-command offline hero (slice + S0/eess_offline arms, C1 hash, honest limits); integration-verified: 2 runs exit 0, re-verify PASS, science digest 76ce5f35… stable across all runs; 8 unmet hand-in items honestly listed.
  - P09 docs current: FACT_CHECK_LIST F25 (P1 rule now VERIFIED @ 5967f24), F27 + section E, SUBMISSION_CHECKLIST step 9 (floor + P1 alignment moved to LANDED; only A4 remains in flight); DRAFT_ANSWERS 202/8 (91930b5).
- Commands/evidence: gate @ 5967f24: 207 passed/8 skipped, ruff clean, mypy clean (55), preflight 5/5 PASS. Worktree re-verification pre-merge: 172/8 @ a9779fb. Demo: digest-identical across 5 runs (3 worker + 2 integration).
- NO-GO blockers remaining: **H2 (evidence in verdict prompt) only** (worker 6079ec46 in flight) + v1.2 science-judge sign-off + human two-key.
- Next: collect H2 → code-judge spot review → merge → full gate @ clean tip → science-judge sign-off request (matched reports: red-flags NO-GO + code-judge harness + A17) → human two-key → live window.
