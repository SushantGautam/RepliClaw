---
name: rc-telemetry
description: Fast D-E observational telemetry engineering lane; independent parallel investigators, bounded commitments, escrow integrity.
user-invocable: true
---
Own src/repliclaw/experiments/v3/telemetry_arms.py and direct focused regression tests ONLY. Examine phase-1 loop at _run_inner(): three investigators are currently sequential and a single repeated-tool chain blocks reveal. Implement concurrent independent investigators with separated state and shared arm-level enforcement; bounded calls/tokens/time per investigator and explicit best-evidence commit or honest failure. Preserve escrow ordering, reveal, phase2, scorer-only labels, total token accounting and baseline parity. Do not alter C-EQ to make D-E look good; do not alter frozen results. First diff within 30 min; focused check and handoff. No broad refactor or new test suite.
