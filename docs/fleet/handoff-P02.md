# P02 handoff — SimpleAudit counterfactual intervention package

Branch `p02/simpleaudit-counterfactual`, built on top of the PR-1 lineage
(`repl-claw-dev` @ b5f7bfb). All work is new files; nothing existing was
modified.

## What this delivers (ticket P02.md)

A first-class intervention package that runs **real, executable
SimpleAudit counterfactual interventions** on a frozen scientific case,
discriminating among hypotheses **before any oracle or post-hoc label is
seen**. This is the "actual interventions" capability (contract §5) that
the v1 strategy was faking with scripted strings.

## Files

| Path | Role |
|------|------|
| `src/repliclaw/execution.py` | Reusable execution-honesty record + verification (ported from f02 `src/audit/execution.py`). |
| `src/repliclaw/counterfactual/case.py` | Frozen `CaseSpec` / `InterventionSpec`, factor set, canonical hashing. |
| `src/repliclaw/counterfactual/frozen_backend.py` | Deterministic RAG target + frozen judge client (offline SimpleAudit). |
| `src/repliclaw/counterfactual/executor.py` | `SimpleAuditExecutor`, `InterventionRun`, `run_case` / `run_canonical` / `replay`. |
| `src/repliclaw/counterfactual/__init__.py` | Public API surface (contract §5). |
| `experiments/policy_rag/case.json` | Frozen hero case `policy_rag_v1`. |
| `experiments/policy_rag/interventions.json` | The 5 intervention arms. |
| `experiments/policy_rag/oracle/oracle.json` | **Sealed** ground truth (not read by target/judge). |
| `artifacts/science/p02-hero-canonical/` | Regenerable canonical run + `replay.sh`. |
| `tests/test_execution.py` | 6 red tests for execution-honesty (all green). |
| `tests/test_counterfactual.py` | 6 tests covering ticket items 1–4, 6, 7 (all green). |

## The experiment (one-sentence science)

A returns-policy RAG assistant is seeded with a **retrieval omission**
(stale 14-day snippet served top-1; 30-day snippet absent). Because the
stale retrieval **and** the stale judge rubric agree, the baseline audit
**passes** — the failure is hidden. Counterfactual interventions flip one
factor at a time:

- `I0_baseline` → **pass** (failure hidden)
- `I_R_retrieval_fix` → **critical** (failure exposed; output changed)
- `I_P_policy_conflict` → **pass**, output **byte-identical** to I0 (null result)
- `I_J_judge_fix` → **critical**, output byte-identical (verdict flipped, not output)
- `I_C_retrieval_judge` → **pass** (control: both factors fixed)

**The distinguishing signature** — an intervention changes the verdict
*without* changing the audited output (`I_J`) — is only possible with real
per-factor counterfactual execution. That is the mechanism that separates
RepliClaw's causal diagnosis from a black-box LLM judge.

## Reproduce (from inside this worktree)

```bash
# Full gate — all green.
.venv/bin/python -m pytest                 # 62 passed, 8 skipped (base-branch skips)
.venv/bin/python -m ruff check src tests   # clean
.venv/bin/python -m mypy src               # clean (21 files)

# Regenerate the canonical run byte-identically + verify.
bash artifacts/science/p02-hero-canonical/replay.sh
```

`replay.sh` regenerates every per-arm file, asserts byte-identical
replay, and prints a sha256 summary. The per-arm files contain no
wall-clock timestamps, so the pin is stable across machines.

## Key technical decisions (and why)

1. **SimpleAudit runs OFFLINE.** `ModelAuditor` is constructed with
   `max_turns=1`, a `test_prompt`, and the judge client swapped for a
   deterministic frozen client. No real LLM calls, no network, all token
   counts 0. This keeps the run hermetic while still driving the *real*
   SimpleAudit `run_scenario` → `AuditResult` code path. `engine_metadata()`
   pins `simpleaudit 0.3.3 @ 9783293`.
2. **`run_scenario` is async** in v0.3.3 — call it via `asyncio.run` (the
   earlier p02 prototype wrapped a sync-style call that never fired).
3. **`CallableTarget` lives in `simpleaudit.targets.callable`**, not
   `simpleaudit.targets.base` (where `TargetResponse` is).
4. **Determinism is per-arm, not wall-clock.** The manifest stores
   `started_at`/`finished_at` (for audit honesty) but `replay` compares only
   the `ARM_FILES` (config, target_output, conversation, judgment,
   stdout), which are pure functions of the effective config.
5. **Oracle is sealed and never imported.** Target/judge modules contain no
   `oracle.json` reference (enforced by `test_oracle_not_leaked`); the
   oracle file is committed for reviewers but is not on any code path.
6. **`execution.py` ported, not duplicated.** It is the f02
   execution-honesty module (real subprocess, sha256 artifact hashes,
   protected `verified` field, clean-dir re-run verification) placed under
   `repliclaw.` so P07 can compose it with the protocol.

## What reviewers should attack

- **Is the "counterfactual" just a different prompt?** No — `I_P` and `I_J`
  are the controls: `I_P` changes a factor with **zero** effect on the
  output (proves the harness isn't just re-prompting), while `I_J` changes
  the verdict with a **byte-identical** output (proves the judge is a real
  independent factor, not the target). If the harness were a single
  prompt, you could not produce a byte-identical-output/changed-verdict arm.
- **Does it depend on the oracle?** No — see `test_oracle_not_leaked`.
- **Is SimpleAudit actually being executed?** Yes — `run_case` invokes the
  real `ModelAuditor.run_scenario`; the only substitution is the LLM
  provider (frozen, offline), which is the stated intent for a hermetic
  run. `engine_metadata()` reports the pinned version + git sha.
- **Determinism across machines.** The per-arm files have no timestamps;
  `replay.sh` + sha256 pins prove it. The manifest's wall-clock fields are
  excluded from the byte-comparison by design.

## Known limitations / next steps

- This is a **single canonical case** (`policy_rag_v1`). The second
  (Tox21) case is P06's job.
- The "hypothesis identification" consumer (P03/P07) is not built here;
  this package only produces the `InterventionRun` evidence that P07
  consumes via `hypothesis_from_interventions`.
- Live (real-LLM) scoring of this case is P08's job (requires prereg
  + science-judge approval). Until then, the offline deterministic run is
  the canonical artifact.
