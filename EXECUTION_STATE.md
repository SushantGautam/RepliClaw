# RepliClaw — Execution State (resume cursor)

Status: `WORKING`

## Cursor
- Milestone: M0 (reconnaissance) — 4 parallel read-only investigators launched
- Branch: `repl-claw-dev` (work); `main` = spec/docs baseline, 1 commit
- Upstream ScienceClaw: cloned to `/tmp/scienceclaw-upstream` (head `ab9aba1`); will be vendored as `deps/scienceclaw` submodule

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

## Open questions (recon in flight)
1. Do `scienceclaw.artifacts.artifact/needs/reactor` import cleanly with only core deps? (subagent 1)
2. What can Studio offer us at import-safe cost? (subagent 2)
3. Fastest reliable test command + benchmark patterns in upstream? (subagent 3)
4. Blind commit/reveal leakage / fake-independence critique? (subagent 4)

## Next actions
1. Integrate 4 recon reports → finalize reuse matrix in DECISIONS.md
2. Scaffold package + import-safety probe → commit
3. M1 domain model + vertical smoke

## Verification log (latest first)
- 2026-10-07: LLM endpoint probe — `curl /api/v1/chat/completions` model=default → correct answer, HTTP 200, usage {prompt:71, completion:66}.
- 2026-10-07: git baseline commit of spec docs on `main`.
