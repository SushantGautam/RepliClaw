# R-2 Pre-flight Protocol — S4/S3/S0 live-token floors (round-2 REQUIRED item)

> **STATUS: READY TO EXECUTE — gated.** Execute ONLY after (1) science round 3 on
> A1–A9 = APPROVE and (2) human two-key authorization is recorded in
> the run-state record. Execute BEFORE the live campaign window opens. This is
> measurement, not a campaign run: 3 arms × 1 run each, oracle never read.

## Why (round-2 science verdict)
The S5-only live-token floor (1,358–1,380 tokens, `scripts/measure_live_token_floor.py`
→ `artifacts/p08/live_token_floor/floor.json`) was measured before A8 put **six**
arms on live-LLM. With S0/S3/S4 live, their per-run token floors are **unknown**.
R-2 requires measured S4/S3/S0 floors recorded pre-window.

## Frozen settings (prereg v1.1 §3.1/§3.2, D-10 — same for every arm)
- harness seed **20261010**; λ=μ=0.5; max_cycles=6; offer TTL=120 s
- envelope 60,000 tokens / 900 s / 4 agents per arm (A8); master ceiling 10.8M
- case `policy_rag_v1` (primary — all six arms live; case-conditional,
  `runner.py:186-207`)

## Commands (main tree, post-gates)
```bash
cd /Users/sushantgautam/Documents/ScienceClawHackathon
RUN=artifacts/p08/token_floor_r2_$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$RUN"

for ARM in open_sharing_swarm adaptive_central single_agent; do
  .venv/bin/python -m repliclaw.comparators.runner \
    --arm "$ARM" --case policy_rag \
    --client-factory live --harness-seed 20261010 \
    --assert-frozen \
    --out "$RUN/$ARM"
done
```

## Extraction + recording
For each arm read `$RUN/<arm>/run-01/budget_ledger.json` (and `run_metadata.json`
for the R-1 tree_sha + N-1 LLMConfig + `a9_defect_instruction_sha256` — recorded
automatically since A9). Write `$RUN/floor_r2.json`:

```json
{
  "schema": "p08.token_floor_r2/1",
  "date": "<UTC>",
  "pin": "<git rev-parse HEAD at execution>",
  "harness_seed": 20261010,
  "case_id": "policy_rag_v1",
  "arms": {
    "S4_open_sharing_swarm": {"tokens": null, "wall_s": null, "llm_calls": null, "status": null},
    "S3_adaptive_central":   {"tokens": null, "wall_s": null, "llm_calls": null, "status": null},
    "S0_single_agent":       {"tokens": null, "wall_s": null, "llm_calls": null, "status": null}
  },
  "headroom": {
    "per_arm_ceiling": 60000,
    "master_ceiling": 10800000,
    "max_arm_usage_fraction": null,
    "verdict": "OK|CHECK — if any arm > 60k the run is aborted_budget (envelope); record actual"
  }
}
```

## Acceptance + backstops
- Each arm `status` ∈ {completed, aborted_budget} with `total_tokens > 0`.
- **60,000-token/arm envelope** aborts any single-arm overrun (hard backstop).
- **10.8M master ceiling** bounds the whole campaign.
- **S0 stopping rule**: S0 stops at the first budget-exhausting cycle (its arm
  contract) — the floor may legitimately be the envelope.
- Any arm whose floor exceeds **60%** of the per-arm ceiling → flag in
  the run-state record + reconsider per-run counts BEFORE the window (do not
  silently proceed).

## After execution
1. Commit `floor_r2.json` (tracked artifact) — the floor record the live window
   relies on.
2. Update the run-state record: R-2 CLOSED + floors.
3. Update `docs/application/FACT_CHECK_LIST.md` (new fact row citing
   `floor_r2.json` + this protocol) and `P1_RESULT_DISCLOSURES_DRAFT.md` §7.
4. Proceed to the live campaign ONLY with both keys green.
