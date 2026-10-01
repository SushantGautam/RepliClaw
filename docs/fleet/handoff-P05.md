# Handoff — P05: matched-budget comparator baselines against the EESS swarm

Branch: `p05/comparators` (base `b5f7bfb`). Worktree: `.worktrees/p05`.
Owner: builder worker (P05 lane = old F01/F03 WIP, per IMPLEMENTATION_PLAN
salvage map).

## Scope / what was built

`docs/fleet/P05.md` does **not** exist in the tree (only P02/P03/P04 tickets
were written). The P05 spec was therefore derived from three authoritative
sources that DO exist:

1. **IMPLEMENTATION_PLAN.md** — P05 row: "fair strong comparators … actual
   open-debate contexts, true vote, **strong equal-concurrency S3 adaptive
   manager, real cost caps, parity proofs**". P08 references the preregistered
   arms **S0/S3/S4/S5**.
2. **docs/design/EESS_CONTRACTS.md** — canonical-JSON + content-hash rules
   (§1), the shared task/verdict-engine identity rule, and the leakage rules.
3. **The mission brief** — "If the ticket names specific managers (e.g.
   adaptive central manager, open-sharing swarm, single-agent baseline),
   implement exactly those with the interfaces it prescribes" + "budget-parity
   mechanism: all arms must consume the same declared token/time budget
   envelope, and tests must assert parity".

Implemented exactly the three named arms the mission lists, mapped onto the
existing shared coordination baselines so the scientific task + verdict engine
are IDENTICAL across arms (only the coordination regime differs):

| Arm name            | Class                    | Wraps strategy | Role |
|---------------------|--------------------------|----------------|------|
| `single_agent`      | `SingleAgentBaseline`    | `single_agent` | S0 — one strong agent, no peers, no aggregation (the floor). |
| `adaptive_central`  | `AdaptiveCentralManager` | `repl_claw`    | S3 — STRONG adaptive central manager (equal concurrency; re-plans from evidence). |
| `open_sharing_swarm`| `OpenSharingSwarm`       | `open_debate`  | S4 — N agents sharing context, each seeing prior conclusions (correlated by construction). |

The **budget-parity mechanism** is the headline deliverable: every arm is
given the SAME frozen `BudgetEnvelope` (max tokens / max wall-s / max agents),
a `BudgetLedger` enforces the caps (raises `BudgetOverflow` on any overrun),
and `assert_budget_parity` proves the comparison is valid by checking (a) all
arms consumed the identical envelope content-hash AND (b) no arm exceeded it.

### Files created (owned paths only)
- `src/repliclaw/comparators/__init__.py`
- `src/repliclaw/comparators/budget.py` — `BudgetEnvelope` (frozen pydantic v2),
  `BudgetRecord`, `BudgetLedger`, `BudgetOverflow`.
- `src/repliclaw/comparators/arms.py` — `ArmSpec`, `ArmResult` (frozen
  dataclass), `ComparatorArm` (runtime-checkable Protocol), `ArmRunner` base.
- `src/repliclaw/comparators/managers.py` — the three named arms.
- `src/repliclaw/comparators/runner.py` — `arm_registry()`,
  `assert_budget_parity()`, `ComparatorHarness`.
- `tests/test_comparators.py` — 19 tests, written RED-first.
- `docs/fleet/handoff-P05.md` — this file.

### Interfaces (as prescribed by the mission)
- `BudgetEnvelope(max_tokens, max_wall_s, max_agents)` — frozen; `.sha256()`
  content hash via `repliclaw.canonical.commit_hash` (reused, not re-implemented).
- `BudgetLedger(envelope).record(BudgetRecord(agent_id, tokens, wall_s, n_agents))`
  — raises `BudgetOverflow` if any cumulative cap is exceeded.
- `ArmResult(arm_name, claim_id, verdict_label, n_agents, total_tokens,
  total_wall_s, envelope_sha256, detail)` — frozen, comparable across arms.
- `ComparatorArm` Protocol: `name() -> str`,
  `run(claim, ledger, spec, work_dir) -> ArmResult`.
- `ComparatorHarness(factory).run(claim, envelope, work_root) -> dict` — runs
  all three arms under one envelope, returns per-arm results + parity report.
- `assert_budget_parity(results, envelope) -> dict` — `{"parity": bool,
  "n_arms", "envelope_sha256", "envelope_hashes", "over_budget_arms"}`.

## Red-first evidence

Tests were written from the acceptance criteria BEFORE the package existed.
First run (package absent) — RED:

```
$ .venv/bin/python -m pytest tests/test_comparators.py
tests/test_comparators.py:30: in <module>
    from repliclaw.comparators import (
E   ModuleNotFoundError: No module named 'repliclaw.comparators'
=========================== short test summary info ============================
ERROR tests/test_comparators.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.58s
```

After the first implementation pass, 6 tests were still red (arms reported the
underlying strategy name `repl_claw`/`open_debate` instead of the arm name
`adaptive_central`/`open_sharing_swarm`, and the agent cap was not enforced
per-arm). Fixed by adding an `arm_label` override to `ArmRunner` and an
`n_agents` field to `BudgetRecord`/`BudgetLedger`. Final: all 19 green.

## Gate commands + observed output (final, from worktree root)

### 1. pytest
```
$ .venv/bin/python -m pytest
.........................................................ssssssss....... [ 77%]
.....................                                                    [100%]
85 passed, 8 skipped in 7.37s
```
(Baseline before P05 was `66 passed, 8 skipped`; P05 adds 19 tests → 85.)

### 2. ruff
```
$ .venv/bin/python -m ruff check src tests
All checks passed!
```

### 3. mypy
```
$ .venv/bin/python -m mypy src
Success: no issues found in 21 source files
```

All three gates run from the worktree root (`.worktrees/p05`), NOT the repo
root, per the hard constraint (running from the repo root scans `.venv` and
produces ~2000 false errors).

## Deviations from the ticket / brief
1. **`docs/fleet/P05.md` does not exist.** I derived the spec from
   IMPLEMENTATION_PLAN.md (P05/P08 rows), EESS_CONTRACTS.md, and the mission
   brief, and implemented exactly the three named arms the brief lists. If a
   P05.md is later written with a different arm set (e.g. it names S5 or a
   different S3 definition), the `arm_registry()` in `runner.py` is the single
   place to add/rename arms — the budget-parity mechanism is arm-agnostic.
2. **S3 "adaptive central manager" reuses the `repl_claw` coordination
   regime** (the evidence-driven, re-planning path) rather than a brand-new
   central allocator. Rationale: the EESS design explicitly forbids a central
   role that *ranks scientific options* (EESS_CONTRACTS §4: "the broker
   ENFORCES lease/dedup/budget only — it NEVER ranks scientific options"). The
   fair "strong central" comparator at equal concurrency is the full
   three-investigator pipeline that adapts from evidence — which is what
   `repl_claw` already is. This keeps the comparison honest (same task, same
   verdict engine, same concurrency) and avoids re-implementing the protocol.
3. **S4 "open-sharing swarm" reuses `open_debate`** (N agents, each seeing
   prior conclusions) — the natural correlated "many agents" baseline.
4. **Wall-clock is measured, not faked**, but the offline deterministic
   backend makes it ~0s; the ledger still enforces the wall cap from the
   measured value. Token counts are 0 for the deterministic backend (documented
   in F03: "deterministic backend: 0 tokens — that's fine; parity is about
   equal investigator counts and equal data access"). Parity is therefore
   asserted on the envelope hash + agent count + (trivially) tokens/wall.

## Stubs / integration notes (P07)
- The arms reuse `repliclaw.strategies.run_strategy` and
  `repliclaw.investigators.DeterministicInvestigator` directly (both already in
  the base tree) — no cross-package source was copied.
- The `ComparatorHarness` takes an `investigator_factory` so P07 can wire the
  real P02 SimpleAudit executor / live factory in place of the deterministic
  one without touching the parity mechanism.
- No live LLM, no network, no API keys anywhere in the tests.

## NOT PROVEN
- **Scientific superiority of the EESS swarm.** This ticket builds the
  *matched-budget scaffolding* and the three named comparator arms; it does
  NOT prove the swarm beats them. That is P08's job (preregistered S0/S3/S4/S5
  comparison with real cases, CIs, and honest intervals). The arms currently
  agree on the trivial `clean_supported` fixture; the differentiating
  misleading/faulted cases are exercised by the existing strategy tests, not
  re-asserted here.
- **Real token/time cost parity under a live LLM.** With the deterministic
  backend, token usage is 0 for every arm, so the token cap is trivially
  satisfied. True cost parity (equal token spend at equal wall-clock) is only
  meaningful with a live model and is out of scope for an offline ticket.
- **S3 is "adaptive" in the coordination-regime sense** (re-plans from
  evidence via the `repl_claw` follow-up loop), not a bespoke central
  optimizer. If the judges want a *distinct* central-manager algorithm that
  explicitly re-sequences investigators, that is a P08 refinement.
- **Statistical significance of any arm-vs-arm difference** — no held-out
  set, no bootstrap CIs here (that is F03/P08 territory).
- **Cross-process / multi-worker budget accounting.** The ledger is
  in-process; a distributed budget ledger (shared across OS processes) is not
  implemented and is not required by the P05 brief.

## Attack list (adversarial review prompts)
- Can an arm cheat the parity check by reporting a lower `envelope_sha256`?
  (No — the hash is computed from the envelope the harness actually passed,
  and `assert_budget_parity` compares against the harness's own envelope.)
- Can an arm silently exceed the budget? (No — `BudgetLedger.record` raises
  `BudgetOverflow`; the harness propagates it, so an oversized swarm fails
  loudly rather than being faked as "within budget".)
- Is the comparison confounded by different task code per arm? (No — all arms
  call the same `run_strategy` runner over the same task/verdict engine.)
- Does the agent cap actually bind? (Yes — `test_harness_rejects_oversized_
  envelope_for_swarm` proves a 3-agent swarm overruns a 1-agent envelope.)
