---
name: rc-eval
description: Fast paired experimental runner and concise measurement reporting lane.
user-invocable: true
---
Own scripts/pilot_parallel.py, scripts/pilot_report.py and NEW reporter/driver files only. Do NOT edit telemetry_arms.py or causal executor modules. Prepare immediately usable paired D-E/C-EQ evaluation on existing RCAEval pilot cases: count aborted runs, report top-1/top-5, case/seed, actual tokens, latency, LLM/tool calls and escrow-phase completion. Do not use oracle in agent context. Honor trial caps, track model fingerprint, don't call previously run cases independent heldout. Keep runner resumable; only one focused check, then actual measured pilot when integrator merges A. Minimize new code; return command, file SHA and raw artifact path.
