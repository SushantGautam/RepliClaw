# RepliClaw — Execution State (resume cursor)

Status: `WORKING`

## Cursor
- Milestone: **M1–M4 core built + 3-way verdict path VERIFIED offline.** Core package `src/repliclaw/` complete: canonical, models, runstore (one-shot tamper-proof commit/reveal), isolation (PhaseGate+ContextEnforcer), scienceclaw_adapter, investigators (LLM + Deterministic), evidence (graph, conflicts, AC11 correlation), verdict (evidence-weighted + decisive-followup adjudication), protocol (blind→commit→reveal→evidence→followup→verdict).
- Branch: `repl-claw-dev`
- **Core code NOT yet committed** (only 2 baseline doc commits on branch).
- Next: formal pytest suite (AC14/15) → M5 strategies baselines → M6 benchmark (known-answer, no hard-coded scores) → M8 CLI `repliclaw verify` → M9 live-LLM demo → M10 harden (README AC17, map AC01–18 to evidence, commit, COMPLETE).

## Confirmed facts (evidence-backed)
- Hackathon repo was EMPTY of code (only 4 markdown docs, no commits) → RepliClaw is a new package here.
- Toolchain: Python 3.11.7 (anaconda), `uv` available, networkx/pydantic/openai/anthropic already in env.
- LLM access: Open WebUI at `https://simulachat.sushant.pp.ua` (OpenAI-compatible `/api/v1/chat/completions`), key = env `CUSTOM_SIMULACHAT_KEY`, model `default` (base Qwen3.8-27B) verified: correct t-test answer, <1s, usage tokens returned. Also listed: `glm-5-2-fp8`, `Qwen3.8-27B`.
- No standard ANTHROPIC/OPENAI/GEMINI keys in environment.
- SimpleAudit + SimpleAuditStudio checkouts exist in `~/Documents/` (we own Studio).
- ScienceClaw upstream core is light: `requirements.txt` = openai, anthropic, requests, pydantic, biopython, bs4, pyyaml, psutil, tooluniverse.

## Key decisions (details in DECISIONS.md)
- Python package `repliclaw` in this repo; ScienceClaw = git submodule under `deps/` + thin adapter (`repliclaw/scienceclaw_adapter/`) — NO upstream fork edits this round.
- SimpleAuditStudio: evaluate via recon; default = NOT a hard dependency for core ACs (Hatchet/Postgres infra too heavy); document in reuse matrix; possible OTel ingest hook.
- Isolation: per-investigator OS subprocesses with sealed context envelopes (structural, not prompt-level).
- Commit/reveal: SHA256 over canonical JSON (sorted keys, no floats-as-text, no timestamps); persisted run store + event log.
- Tests hermetic via `ProcessInvestigator` (deterministic offline); live-LLM runs are the demo/benchmark path (real outputs, AC18-safe).
- OTel: in-memory exporter + `repliclaw.*` namespaced attributes; SDK optional (no-op fallback).

## Confirmed facts (evidence-backed, updated)
- `deps/scienceclaw/{artifacts,core}` import cleanly with stdlib+pydantic only (0.09s); `get_registry()` discovers 334 skills (0.58s). Upstream `ArtifactStore`+`rank_needs` hardcode `~/.scienceclaw` → run-local subclass required (done: `RunLocalArtifactStore`).
- Upstream `score_need = 2*novelty + 1*centrality + 0.5*depth + 0.2*log1p(age_min)` (reused via `pressure_score`).
- 3-way offline e2e (`artifacts/dev/e2e_3way.py`) VERIFIED:
  - clean_supported → `SUPPORTED` conf 0.98 (3 support / 0 contradict, no conflict).
  - clean_refuted → `REFUTED` conf 0.534 (single directional-executable falsifier sufficient; replication need fired).
  - misleading_wrong_test → `REFUTED` conf 0.256 (2 support vs falsifier → independent CONFLICT → falsifier-lens follow-up ADJUDICATES → recovery AC12; conflict surfaced + broken).
- Confidence ordering is well-calibrated: clean supported (0.98) > clean refuted (0.534) > recovered-misleading (0.256).

## Next actions
1. Formal pytest suite (hermetic): isolation pre-reveal, commit/reveal integrity + one-shot, conflict/follow-up, verdict provenance (AC14/15).
2. M5 `strategies.py` (5 baselines, same task interface + common result schema).
3. M6 benchmark: known-answer fixtures (wrong_stat_test, leakage, wrong_param), metrics (correctness, FA/FR, inconclusive, error-correlation, recovery, diversity, latency, cost), CSV/JSON/MD — NO hard-coded scores (AC18).
4. M8 CLI `repliclaw verify --claim ... [--artifact ...]` + Python `verify()`.
5. M9 live-LLM demo path; M10 README + AC01–18 evidence map + commit + COMPLETE.

## Verification log (latest first)
- 2026-10-07: 3-way offline e2e — SUPPORTED/REFUTED/REFUTED-recovery all correct (see Confirmed facts).
- 2026-10-07: verdict engine tuned — `insufficient_evidence` now requires a directional+executable piece; conflict gate now lets a decisive executable follow-up adjudicate (AC12).
- 2026-10-07: vertical loop proven: commit→reveal→tamper→replay→record-tamper integrity (AC04); one-shot reveal blocks re-reveal after reject.
- 2026-10-07: LLM endpoint probe — `curl /api/v1/chat/completions` model=default → correct answer, HTTP 200, usage {prompt:71, completion:66}.
- 2026-10-07: git baseline commit of spec docs on `main`.
