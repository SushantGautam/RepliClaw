# Mechanism smoke — lane-mechanism (mechanism v2)

**Mandatory label:** MECHANISM SMOKE (v2, lane-mechanism) — **ACCESS-MATCHED
OBSERVATIONAL diagnosis** (the RCAEval telemetry sandbox exposes
observational queries only — system_context, top_anomalies, service_metrics,
service_logs, service_traces — **NO executable interventions**);
MODEL-SUBSTITUTION (SimulaChat default, Qwen3.8-27B); **EVOLVING INSTRUMENT:
non-comparable to prior ledgers** (R1–R3 / Oct-12 fast-finish campaign);
exploratory smoke on a single REUSED pilot case (already exposed to earlier
experiment tuning — not a fresh heldout). No confirmatory, statistical, or
causal-intervention claim is supported by any artifact here.

## What changed (mechanism v2)

* **D-E-TELEM (changed):** investigators operate INDEPENDENTLY — no shared
  reasoning channel (the phase-2 cross-consultation is removed; raw
  observational tool access is shared, inferences are not). Each
  investigator has bounded tool/query turns (`DE_PHASE1_TOOL_CAP`, default
  6, CLI `--de-tool-cap`) and MUST escrow a ranked candidate-cause packet
  (phase "phase1") **before any reveal/synthesis** (escrow:
  `repliclaw.canonical` hashes, `PhaseGate` COMMIT→REVEAL, transitions in
  the ledger). Synthesis is the deterministic committee ranking over the
  revealed packets, submitted via the arm's own fresh sandbox.
* **BEST-EVIDENCE COMMIT (both arms):** budget exhaustion (tool cap / token
  envelope / wall cap) no longer masks the outcome — the arm still commits
  a best-evidence ranking (flagged `abort_reason="budget_exhausted:..."` +
  warning); a non-commit is a recorded FAILURE
  (`abort_reason="non_commit:..."`, `status != completed`).
* **C-EQ-TELEM (kept strong, not crippled):** identical tool set, identical
  per-run token envelope, same sealed-forecast/planner/findings flow, plus
  equivalent parallelism — the manager may batch up to
  `CEQ_MANAGER_BATCH_MAX=3` tool calls per turn (`tool_calls` action,
  disclosed to the manager only).
* **Commit validation (both arms, identical):** an invalid (hallucinated)
  service name triggers up to 2 bounded correction asks (one tool call may
  be served per episode); still-invalid → recorded non-commit failure.

## Runs (chronological; all preserved, including failures)

| run dir | git sha | D-E-TELEM | C-EQ-TELEM | notes |
|---|---|---|---|---|
| `smoke_RCA-P-05_seed0_20261012T160430Z` | 7abb21e | crashed (invalid-service submit) | crashed (invalid-service submit) | first live run; exposed the hallucinated-service crash; fixed by commit validation |
| `smoke_RCA-P-05_seed0_20261012T161022Z` | f8fe440 | **non-commit FAILURE** (abort_reason `non_commit:inv-c…`; 2/3 escrowed) | completed — 10,659 tok, 14.4 s, acc@5 HIT (true=checkoutservice), top-1 MISS, prompt-volume canary breach disclosed (0.244) | honest negative for D-E at the low cap; motivated the bounded-correction refinement (2673e9e) |
| `smoke_RCA-P-05_seed0_20261012T161240Z` | 2673e9e | completed — 39,267 tok (exceeded 30K envelope → best-evidence commit path, flagged `budget_exhausted`), 26.3 s, 25 LLM calls, 18 tools, 3/3 escrowed, acc@5 HIT, top-1 MISS | completed — 10,659 tok, 12.2 s, 13 LLM calls, 8 tools, 1 escrowed (sealed forecast), acc@5 HIT, top-1 MISS, prompt-volume canary breach disclosed (0.244) | **final instrument run: 2/2 completions, 2/2 acc@5 hits, 0/2 top-1 hits, pair tokens 49,926** — single case, exploratory, no statistical claim |
| see `smoke_report.json` of each run | | | | |

Fixed caps for all runs: 30,000 tokens per run per arm (pair ≤ 60K of the
120K smoke budget), wall 600 s, D-E per-investigator tool cap 6, case
RCA-P-05 (case sha256 in each report), seed 0, model `default`
(backend echo `Qwen/Qwen3.8-27B-FP8`), scorer = official service-level
accuracy@5 (+ top-1), ground truth resolved scorer-side only.

## Reproduce

```bash
cd <repo>   # worktree/checkout of branch lane-mechanism (or dev after merge)
REPLICLAW_LLM_API_KEY="$(cat ~/.config/simulachat.key)" \
SIMULACHAT_BASE_URL="https://simulachat.sushant.pp.ua/api/v1" \
  uv run python scripts/mechanism_smoke.py \
    --case RCA-P-05 --tokens-per-run 30000 --de-tool-cap 6 --wall-cap-s 600
```

Each run writes `<run_root>/smoke_report.json` (provenance + per-arm
status/tokens/wall/LLM calls/tool calls/escrow commitments/score/failures)
plus per-arm `status.json`, `audit_llm.json`, `audit_sandboxes.json`,
escrow ledger, and `score.json` (completed runs only).
