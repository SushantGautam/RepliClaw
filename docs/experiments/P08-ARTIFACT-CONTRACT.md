# P08 Artifact Contract v1 (frozen interface for scorer, arms, and runner CLI)

This file is the **single interface contract** between the three P08 builds
(live EESS arms, oracle-gated scorer, runner CLI) and the prereg §10.3 layout.
Any deviation requires a version bump here and a prereg v1.1 note.

Status: DRAFT-v1 written by the integration owner 2026-10-08 after the
science judge REJECT (see `docs/fleet/reviews/SCIENCE-JUDGE-PREREG-P08-2026-10-08.md`).

## 1. One run = one directory

The runner CLI writes exactly these files into `<runs-dir>/<arm>/run-<NN>/`:

| File | Written by | Contents |
|------|-----------|----------|
| `final_verdict.json` | arm | Arm's own output only. **No oracle fields.** |
| `budget_ledger.json` | arm (via `BudgetLedger`) | Per-call usage + envelope + overflow events. |
| `traces.jsonl` | arm | Ordered trace events, one JSON per line. |
| `counterfactuals/` | arm (S5/A1/A3) | One file per executed slot: the single-factor diff + verdict effect. |
| `run_metadata.json` | runner CLI | Tree SHA, seed, model, temperature, endpoint, envelope sha256, start/end wall. |

## 2. `final_verdict.json` (exact keys)

```json
{
  "schema": "p08.final_verdict/1",
  "arm": "S5",
  "case_id": "policy_rag_v1",
  "run_id": "S5/run-07",
  "harness_seed": 20261010,
  "envelope_sha256": "<64 hex>",
  "n_agents": 3,
  "total_tokens": 0,
  "wall_s": 0.0,
  "status": "completed | aborted_budget | invalid_usage",
  "verdict": "supported | refuted | uncertain",
  "defect_class": "<arm's diagnosed defect class or null>",
  "target_artifact": "<arm's diagnosed target artifact or null>",
  "confidence": 0.0,
  "hypotheses": [
    {"id": "H_R", "statement": "...", "falsifiable": true,
     "attempted_falsification": true, "outcome": "supported | refuted | not_run",
     "counterfactual_slot": "I_R_retrieval_fix | null"}
  ],
  "counterfactual_slots_granted": 0,
  "counterfactual_slots_executed": 0,
  "integrity_rejections": 0,
  "agent_verdicts": [{"agent_id": "alpha", "verdict": "refuted", "confidence": 0.8}]
}
```

Rules:
- **Oracle isolation:** this file must never contain `reference_truth`,
  oracle ids, or anything read from an `oracle/` directory. M4 re-grep covers
  it.
- `defect_class`/`target_artifact` use the case's controlled vocabulary
  (policy_rag_v1: classes include `retrieval_omission`; the oracle defines
  the target artifact). Arms may emit `null` when they cannot diagnose.
- `status` = `invalid_usage` is set by the harness (usage-invalidation,
  judge item 7) when a call's usage fields are missing — the run is void,
  excluded from M1, reported in the voided-run table.

## 3. `budget_ledger.json` (exact keys)

```json
{
  "schema": "p08.budget_ledger/1",
  "envelope": {"max_tokens": 60000, "max_wall_s": 900.0, "max_agents": 3,
                "sha256": "<64 hex>"},
  "calls": [
    {"seq": 1, "agent_id": "alpha", "prompt_tokens": 0, "completion_tokens": 0,
     "total_tokens": 0, "wall_s": 0.0, "usage_present": true}
  ],
  "totals": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
             "llm_calls": 0, "wall_s": 0.0},
  "overflow_events": []
}
```

`usage_present=false` on any call ⇒ the harness must mark the run
`invalid_usage` (never zero-fill — judge item 7 / Q13).

## 4. `traces.jsonl` event types (T1–T10)

`trace, commitment, reveal, need_registered, offer, choice,
intervention_start, intervention_end, evidence_published, verdict`.
Each line: `{"seq": <int>, "ts": <iso8601>, "agent_id": "<id|null>", "type": "...", "payload": {...}}`.
Metric M4 (leakage) is computed by re-grep, not by traces; M2/M3/M8/M11
read `final_verdict.json` + `counterfactuals/`.

## 5. Oracle

- policy_rag_v1: `experiments/policy_rag/oracle/` (sealed, P02 layout).
- tox21_ar_agonist: `src/repliclaw/counterfactual/cases/tox21_ar_agonist/oracle/oracle.json`.
- **Only the scorer** (`repliclaw.p08.score`) may read an oracle, and only
  after every run directory's artifacts exist (post-seal). Arm-side code
  reading an oracle path is a leakage incident (M4 > 0 ⇒ campaign stop S5).

## 6. Scorer output (`<runs-dir>/scores/`)

- `scores.json` — M1–M11 per arm + bootstrap CIs (10,000 resamples,
  seeded `20261010` primary / `20261020` secondary) + parity re-check
  (identical envelope hash across arms, no overruns) + voided/abort tables.
- `per_run.csv` — one row per run: arm, run, status, M1, tokens, wall_s,
  slots, integrity_rejections.
- `scorecard.md` — human table, counterevidence-first ordering when
  P1 is falsified (prereg §8.2).

## 7. Envelope and seeds

- Primary: 60,000 tokens / 900 s / 3 agents, seed `20261010`.
- Secondary: same class, seed `20261020`. (Re-derivation against the live
  S5 token floor is a prereg v1.1 condition, judge Q6.)
- Arms: `S0 single_agent`, `S3 adaptive_central`, `S4 open_sharing_swarm`,
  `S5 eess`, `A1 eess_no_escrow`, `A3 eess_random_select` (CLI accepts both
  the S/A label and the registry key).
