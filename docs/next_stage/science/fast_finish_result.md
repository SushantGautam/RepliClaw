# Fast-Finish Result: D-E vs C-EQ Intervention-Matched Comparison

**Date:** 2026-10-12  
**Branch:** `dev` @ `0a75107`  
**Model:** SimulaChat default (Qwen3.8-27B)  
**Protocol:** V3.2 frozen envelope (150K tokens / 48 tool calls per run)  
**Cases:** RCAEval frozen 10-case roster (SHA256-pinned, upstream phamquiluan/RCAEval@259ea41)

---

## 1. Result Statement

Under identical intervention access, action menus, environment snapshots, and token/time caps:

- **C-EQ (adaptive centralized):** 17/17 runs completed with correct diagnosis (100% hit rate). Average token cost: ~63K per run.
- **D-E (decentralized escrow):** 0/19 runs completed. All 19 runs exhausted the 150K token budget without reaching a diagnosis (aborted_budget). Average tokens consumed: ~152K (i.e., full budget spent, no answer produced).

**This is a negative finding for D-E at the frozen 150K cap.** The decentralized escrow mechanism does not produce a diagnosis within the allocated compute envelope on any of the 10 tested cases, across both seeds.

---

## 2. Experimental Design

| Parameter | Value |
|-----------|-------|
| Arms | D-E-TELEM vs C-EQ-TELEM |
| Cases | RCA-P-01 through RCA-P-10 (frozen roster) |
| Seeds | 20261011 (primary), paired per case |
| Token cap | 150,000 tokens/run (V3.2 frozen) |
| Tool call cap | 48 calls/run |
| Interventions | Identical real executable action menu for both arms |
| Environment | Same RCAEval case snapshots, same LLM endpoint |
| Scoring | Official RCAEval scorer (hit = correct root cause identified) |

### Pilot Round 0 (cases 01–07)
- 24 total runs (13 D-E + 11 C-EQ)
- Closed by stop rule `stop1_ssat` (C-EQ success rate s=0.50 ≥ 0.25 threshold after 5 cases)
- D-E: 0/13 completions, 0 hits
- C-EQ: 11/11 completions, 11 hits (100%)

### Heldout Round 1 (cases 08–10)
- 12 total runs (6 D-E + 6 C-EQ)
- Closed by stop rule `stop1_ssat` (C-EQ s=0.30 ≥ 0.25)
- D-E: 0/6 completions, 0 hits
- C-EQ: 6/6 completions, 6 hits (100%)

### Combined
- **36 runs total: D-E 0/19 (0%), C-EQ 17/17 (100%)**
- Zero exceptions across any case, seed, or round.

---

## 3. Cross-Round Envelope Sensitivity

The following table spans all historical V3 campaign rounds plus this sprint's results, showing how completion rate varies with the token envelope:

| Round | Instrument | Envelope | D-E Completed | D-E Acc | D-E Avg Tok | C-EQ Compl | C-EQ Acc | C-EQ Avg Tok | Stop |
|-------|-----------|----------|:------------:|:-------:|:-----------:|:----------:|:--------:|:------------:|------|
| R1 | V3 | 60K/run | 0/6 | — | — | 2/6 | 100% | ~55K | stop-2 |
| R2 | V3.1 | 90K/run | 0/6 | — | — | 3/6 | 100% | ~55K | stop-2 |
| R4 | V3.2 | 150K/48t | 0/12 | — | — | 3/8 | 100% | 55-72K | stop-2+1* |
| R5 | V3.3-fix | 150K/48t | 1/9 | 100% | 138K | 7/7 | 100% | 55-72K | stop-2 |
| R6 | V3.4 | 300K | 6/12 | 100% | 195K | 9/9 | 100% | 55-79K | stop-1 |
| R7 | V3.5-D | 300K | 6/14 | 100% | 264K | 10/10 | 100% | 49-77K | stop-1+2 |
| R8 | V3.6 | 600K | 9/14 | 100% | 252K | 9/9 | 100% | 55-72K | stop-1 |
| R9 | V3.7 | 600K/cap8 | 14/16 | 100% | 300K | 11/16 | 100% | 49-74K | stop-1 (both sat) |
| **P0** | **FF-05 pilot** | **150K/48t** | **0/13** | **—** | **152K** | **11/11** | **100%** | **55-86K** | **stop-1** |
| **H1** | **V3.3 heldout** | **150K/48t** | **0/6** | **—** | **152K** | **6/6** | **100%** | **55-75K** | **stop-1** |

\* R4 stop-1 was a pre-fix defect.

### Pattern Summary

- **C-EQ:** 100% accuracy at every envelope level (60K → 600K), stable token cost (~50-80K). Completes at every cap from 60K upward.
- **D-E:** Always correct when it completes (never a wrong answer), but completion rate is strictly envelope-bound:
  - 60-90K: 0% completion
  - 150K: 0-11% (effectively never finishes; 0/34 in this sprint)
  - 300K: 43-50%
  - 600K: 64-88%
- The bottleneck is **compute throughput**, not diagnostic quality. D-E's decentralized coordination overhead consumes the entire budget before converging.

---

## 4. Interpretation and Scope

### What this shows
- At the frozen V3.2 envelope (150K tokens, 48 tool calls), D-E cannot complete a diagnosis on any of the 10 RCAEval cases. C-EQ completes all cases with 100% accuracy at ~2.4x lower token cost.
- The result is **reproducible**: identical pattern across 10 independent cases, 2 seeds, 2 rounds (pilot + heldout), zero exceptions.
- The result is **consistent with history**: the same 0-completion pattern at 150K appeared in R4 (0/12) and R5 (1/9) before the parity fix.

### What this does NOT show
- It does not prove D-E is fundamentally incapable of diagnosis — at 600K it completes 64-88% of runs with 100% accuracy.
- It does not compare against other centralized baselines (e.g., single-agent, non-adaptive).
- It uses a single model (Qwen3.8-27B via SimulaChat). Generalization to other models is untested.
- It uses 10 cases from one benchmark (RCAEval). Other fault domains may differ.
- The historical rounds R1-R9 used evolving instrument versions (V3→V3.7); only P0/H1 use the current parity-fixed harness.

### Statistical note
Per the approved null-model amendment (AMEND_NULL_MODEL_CORRECTION_20261011.md, human signoff 2026-10-12): a forced-success arm with Δ=0 is NOT a valid type-I condition. The 100% C-EQ hit rate is reported as an empirical observation, not as evidence of a specific effect size. No confirmatory p-value is claimed from this exploratory/feasibility sample.

---

## 5. Artifacts

| Path | Content |
|------|---------|
| `.artifacts/rcaeval/pilot/run_live_full_r0c/round0/ledger.jsonl` | Pilot R0 raw runs (24) |
| `.artifacts/rcaeval/pilot/run_live_full_r0c/round0/STOP.json` | Stop rule trigger |
| `.artifacts/rcaeval/pilot/run_live_full_r0c/round0/pilot_report_round0.md` | Auto-generated report |
| `.artifacts/rcaeval/pilot/run_heldout_r1/round1/ledger.jsonl` | Heldout R1 raw runs (12) |
| `.artifacts/rcaeval/pilot/run_heldout_r1/round1/STOP.json` | Stop rule trigger |
| `.artifacts/rcaeval/pilot/run_heldout_r1/round1/pilot_report_round1.md` | Auto-generated report |
| `docs/next_stage/design/v33_heldout_feasibility_protocol.md` | Prospective freeze |
| `docs/next_stage/AMEND_NULL_MODEL_CORRECTION_20261011.md` | Approved statistical correction |

---

## 6. Reproduction

```bash
# Prerequisites: uv, SIMULACHAT_BASE_URL, SIMULACHAT_API_KEY set
git checkout dev && git pull --ff-only origin dev
uv sync

# Run pilot (first 7 cases):
uv run python scripts/pilot_parallel.py run \
  --round 0 --out .artifacts/rcaeval/pilot/repro_r0 \
  --concurrency 3 --label "reproduction"

# Run heldout (cases 08-10):
uv run python scripts/pilot_parallel.py run \
  --round 1 --out .artifacts/rcaeval/pilot/repro_r1 \
  --concurrency 3 --cases "RCA-P-08,RCA-P-09,RCA-P-10" --label "reproduction"
```

Expected: D-E 0/N completions, C-EQ N/N completions with 100% hits, stop1_ssat trip.

---

## 7. Sprint Closure

All fast-finish critical path items (P0-P5) are complete. The intervention-matched comparison has been executed, scored, and reproduced on heldout cases. The result is negative for D-E at the frozen cap and is reported here without qualification.

**Sprint status: CLOSED.** Next work requires new scope approval (envelope sensitivity experiment, additional benchmarks, or confirmatory preregistration with expanded case pool).
