# CODE-JUDGE REVIEW — Harness Confound / Leakage (Hotspots 2, 4, 5, 5b, 6, 7)

- **Date:** 2026-10-08 (review run 22:29 +02:00)
- **Branch / SHA:** `repl-claw-dev` @ **`17b37a4`** (task-pinned)
- **HEAD at review time:** `d287149` (drifted during review by parallel workers: `a622058` state/progress; `6eeaaea` prereg v1.2 amendment DRAFT; `f2657d1` A5 honesty framing; `d287149` state — "2 A6 pre-start fix workers dispatched (random-policy, leak-guard)").
- **Drift check (real):** `git diff --stat 17b37a4 d287149 -- <the 10 reviewed files>` → **empty**. All 10 reviewed files are byte-identical at `17b37a4` and `d287149`; only state/docs/prereg-draft files changed in between. Every file:line below is valid at both SHAs.
- **Method:** READ-ONLY. Reviewed COMMITTED sources via `git show HEAD:path` (worktree is dirty: `comparators/managers.py`, `comparators/runner.py`, `needmarket/strategies.py`, `preflight.sh` modified; `slice/case_loader.py`, `tests/test_runner_cli.py` untracked — the runner-CLI worker's separate worktree; **not modified, not built, only read as context**). Offline-only evidence: `.venv/bin/python -m pytest -o addopts="" -q` → **162 passed, 8 skipped, 4 failed** (all 4 failures in untracked WIP `tests/test_runner_cli.py` exercising untracked WIP `runner.py`/`case_loader.py` — outside committed-scope, owned by the runner-CLI worker). Read-only Python reproduction for Item 4 (RandomPolicy double-draw; see the Item 4 section below). **No live LLM keys used; FakeLLMClient/offline only. No source file was modified by this review.**
- **Scope division:** science judge owns prereg-rule adjudication; this review owns the CODE side of hotspots 2, 4, 5, 6, 7 + the same-case loader gap (5b) per `docs/P08_SCIENCE_VALIDITY_HOTSPOTS.md` + `docs/STEER_ACTIVE_ORCHESTRATOR.md`.
- **Correction log:** an earlier message with runner-CLI "recovery evidence" (4 WIP test failures, "fix these in your build") was **misaddressed and does not apply** to this review (user correction 2026-10-08). It is ignored per instruction; only its one in-scope facet (single-envelope-hash propagation) is folded into the item-5b acceptance test, because that IS the C1 same-task property this review must specify. No build was done.

---

## Verdict table (6 items)

| # | Item (hotspot) | Location (committed) | Severity | Affects reported metric (M1–M11)? | Amendment-triggering |
|---|----------------|----------------------|----------|-----------------------------------|----------------------|
| 1 | Post-evidence verdict prompt omits ALL verified evidence (h2) | `eess_live/orchestrator.py:444-452` | **BLOCKER** | **Yes — M1 (primary), M10** | **Y** (pre-start only) |
| 2 | S3 = incumbent full protocol, not a neutral central manager (h4) | `comparators/managers.py:46-61`; `protocol.py:383-406` | **MAJOR** | **Yes — M1 estimand (S5−S3 primary comparison)** | **N** (relabel already in v1.1 Q1/D-1; neutral S3′ = NEXT study, do not build) |
| 3 | `reference_truth` fallback in offline `_verdict` (h5) | `comparators/managers.py:192-194` | **MAJOR** (latent oracle-leak path) | **Yes when merged runner writes `verdict` → M10, secondary-case M1; not policy_rag M1** | **N** (defensive guard + redaction) |
| 4 | RandomPolicy double draw; `utility≠components["rng_draw"]` (h7) | `needmarket/policy.py:167-168` | **MINOR** (with MAJOR trap: naive fix is NOT neutral) | **No** (sole consumer is broker `events.jsonl`, outside M1–M11) | **N — only with the stream-preserving fix (variant C) + regression test; naive single-draw (variant A) WOULD be amendment-triggering** |
| 5 | Effective model treatment not recorded (h6) | `investigators.py:92-97`; `run_metadata.json` writer = WIP runner only | **MINOR** | **Indirect — M5/M6 via 4096-token truncation retries; treatment-matching claim unverifiable from artifacts** | **N** (additive audit metadata; pin model/temp in prereg) |
| 6 (5b) | Offline `EESSArm.run` ignores its claim → same-task (C1) gap | `comparators/managers.py:112-125`; `slice/orchestrate.py:47` | **MAJOR** | **Yes — M1 comparability (RQ1/RQ2) if arms run different cases** | **N** (enforces already-preregistered C1) |

**Top-3 must-fix-before-live:** (1) §1 evidence injection into verdict prompt + amendment + parity rerun; (2) §3 `reference_truth` redaction + INCONCLUSIVE fallback + canary test; (3) §5b same-case acceptance test (identical case_id + claim statement + `envelope_sha256` across all arms). §2 relabel is mandatory but is a reporting fix (v1.1 landed) plus the §5b same-task condition; §4 and §5 are pre-start hygiene, not live blockers.

---

## Item 1 — Post-evidence verdict prompt omits verified evidence (hotspot 2)

**Severity: BLOCKER. Amendment-triggering: Y (pre-start only, amendment + parity rerun).**

### Finding

The RESOLVE-phase verdict prompt is built at `src/repliclaw/eess_live/orchestrator.py:444-452` (committed) as:

```python
prompt = (
    f"{VERDICT_MARKER}\n"
    f"AGENT_ID: {agent_id}\n"
    f"Evidence has been observed for hypothesis "
    f"{packet.hypothesis_id}. Your pre-outcome commitment was: "
    f"{packet.predicted_outcome!r}. Respond with JSON containing "
    f"conclusion (supported|refuted|uncertain), confidence, "
    f"defect_class, target_artifact, statement."
)
```

It contains **exactly four** facts: marker, agent id, hypothesis id, and the agent's pre-outcome commitment. It contains **no** severity, **no** run_id, **no** intervention_id, **no** `target_window_days`, **no** hashes, **no** observation id. The agent is told evidence "has been observed" and asked to produce `defect_class`/`target_artifact` — the exact fields that drive **M1** (`p08/score.py:251-258`: for `policy_rag_v1`, `_diagnosis_correct` = `defect == oracle["true_cause"] and bool(target)`) — with none of that evidence.

**Where the verified evidence actually exists at RESOLVE time** (i.e., it is available and simply not injected):

1. `self.escrow.evidence()` — the published `EvidenceObservation` list. Observations are built by `build_evidence` (`orchestrator.py:128-160`) from the *verified* SimpleAudit run and published per arm during the cycles. Fields: `observation_id` (content-derived, `_deterministic_obs_id(run)`), `case_id`, `producer_id`, `run_id` (the real SimpleAudit run id), `kind="verified_run"`, `summary` (severity + target window + config sha prefix), `data = {intervention_id, severity, target_window_days, target_output, token_counts, hypothesis}`, `provenance = {config_sha256, case_sha256, artifact_hashes, seed, engine}`.
2. `self.run_cache` — `arm_id → verified run` map; the run objects carry the same fields plus `severity` used at verdict time for the hypothesis outcomes.

**Per-agent subset:** for agent `a` with hypothesis `H_a` (from `HYP_BY_AGENT`/`ARM_BY_HYP`), the subset is the single observation whose `data["hypothesis"] == H_a` (equivalently `data["intervention_id"] == ARM_BY_HYP[H_a]`), joined with `self.run_cache.get(ARM_BY_HYP[H_a])` for the run id.

### Oracle-unreachability (required proof)

`build_evidence` (`orchestrator.py:128-160`) constructs the observation **only from `run` attributes** (verified-run outputs and provenance hashes). It never opens the oracle. Repo-wide, the only oracle reader in arm-facing code is `p08/score.py::load_oracle` (`score.py:234-241`, docstring: "The ONLY function that reads one"), called only after the completeness gate (`score.py:198-224`: "Must be called BEFORE any oracle read"). The counterfactual executor has an explicit "no oracle import path" (`counterfactual/executor.py:205`), and `_base.py` strips persisted judgment fields before arm-visible output. **Therefore an evidence block built from `build_evidence`/`escrow.evidence()`/`run_cache` cannot contain `experiments/*/oracle/*` content** — the only fields it can contain are the 13 fields above.

### Metric impact

- **M1 (primary, P1 estimand input):** direct. The LLM's `defect_class`/`target_artifact` are currently a function of (hypothesis id, commitment, model prior) only — M1 is measuring prior-guessing, not evidence use. This is the core of hotspot 2 and the most damaging confound in the live campaign.
- **M10 (verdict stability):** direct — with the same inputs, a "floating" verdict across the 20-run replicates can still vary with sampling; the verdict is not causally tied to the (deterministic) evidence, so stability is under-identified.
- Not affected: M2/M3/M7/M8/M11 (driven by `run_cache`/slots, not the LLM verdict text); M4 (leakage) — M4's scan (`score.py:298-309`) greps for the oracle **path string**, so it cannot detect this omission in either direction.

### Fix spec (diff-level, `eess_live/orchestrator.py`)

Inject the per-agent verified-evidence block into the verdict prompt between the commitment line and the "Respond with JSON" line. Source of the block: `self.escrow.evidence()` filtered by `data["hypothesis"] == packet.hypothesis_id`, plus `self.run_cache` for the run id:

```python
# orchestrator.py, inside the RESOLVE loop, before `prompt = (` at line 444
obs_list = [o for o in self.escrow.evidence()
            if o.data.get("hypothesis") == packet.hypothesis_id]
run = self.run_cache.get(ARM_BY_HYP[packet.hypothesis_id])
if obs_list and run is not None:
    o = obs_list[0]
    ev_block = (
        f"VERIFIED EVIDENCE (SimpleAudit, seed={o.provenance['seed']}):\n"
        f"  run_id: {o.run_id}\n"
        f"  observation_id: {o.observation_id}\n"
        f"  intervention_id: {o.data['intervention_id']}\n"
        f"  severity: {o.data['severity']}\n"
        f"  target_window_days: {o.data['target_window_days']}\n"
        f"  target_output: {o.data['target_output']}\n"
        f"  config_sha256: {o.provenance['config_sha256']}\n"
        f"  case_sha256: {o.provenance['case_sha256']}\n"
        f"  artifact_hashes: {o.provenance['artifact_hashes']}\n"
        f"Evidence has been observed for hypothesis {packet.hypothesis_id}. "
    )
else:
    ev_block = f"Evidence has been observed for hypothesis {packet.hypothesis_id}. "
prompt = (
    f"{VERDICT_MARKER}\n"
    f"AGENT_ID: {agent_id}\n"
    f"{ev_block}"
    f"Your pre-outcome commitment was: {packet.predicted_outcome!r}. "
    f"Base your conclusion ONLY on the VERIFIED EVIDENCE above. Respond with JSON "
    f"containing conclusion (supported|refuted|uncertain), confidence, "
    f"defect_class, target_artifact, statement, and the run_id you used."
)
```

Constraints: (a) build the block **only** from the `EvidenceObservation`/run fields listed — no new data sources, so the oracle-unreachability proof holds unchanged; (b) keep the field set identical across agents (same template, per-agent subset) so the only between-agent variance is the data; (c) if the arm's observation or run is missing, fall back to the current wording rather than inventing content (prevents a partial-evidence run from silently changing the prompt shape).

### Test spec (negative-path regression — to be added in `tests/test_eess_live.py`)

`test_verdict_prompt_carries_verified_evidence_not_oracle`:

1. Build one committed escrow packet per agent (real `CommitmentPacket` from a completed commit phase with `FakeLLMClient`), frozen.
2. Build TWO verified-evidence views over that same packet: view A = observation for the agent's arm with `severity="critical"`, real `run_id` R1 (full provenance); view B = same shape with `severity="no_defect"`, real `run_id` R2. (Same committed packet, different verified evidence.)
3. Assert:
   - prompts for A and B are **identical outside the evidence block** (diff is exactly the block — compare with the block normalized to a placeholder);
   - prompt A contains `R1` and not `R2`; prompt B contains `R2` and not `R1` (both contain real run IDs from `run_cache`);
   - **neither** prompt contains any oracle field value: `"true_cause"`, the oracle's `true_cause` value, keys `supports_hypothesis`/`expected_arm_outcomes`/`fault_marker`/`seeded_fault` (the full `oracle.json` key set is `['case','expected_arm_outcomes','fault_marker','hypothesis','schema','seeded_fault','supports_hypothesis','true_cause']`), nor the oracle path string `experiments/policy_rag/oracle/oracle.json` (the same string M4 greps, `score.py:299-307`);
   - the returned verdict JSON schema still accepts a `run_id` echo, and the harness records which run id each agent cited.

**Amendment status: Y.** The verdict prompt is the measured behavior of the primary live arm; changing it changes the estimand's inputs. Per the hotspot preamble ("material behavioral change requires prereg amendment + parity rerun") this must be a **versioned prereg amendment applied PRE-START (before the live window opens)**, with the 20-run replicates re-seeded under the amended prompt — and the A3/S4 parity fixtures regenerated, because the frozen A3 seed (20261010) pins prompt-driven outputs.

---

## Item 2 — S3 is not a neutral central manager (hotspot 4)

**Severity: MAJOR (reporting/estimand confound). Amendment-triggering: N (relabel already mandated+landed in v1.1 Q1/D-1; neutral S3′ is a NEXT study).**

### What `AdaptiveCentralManager` actually does

`comparators/managers.py:46-61` (committed): `strategy = "repl_claw"`, `n_agents = 3`, `arm_label = "adaptive_central"`. Its `run` delegates to `run_repl_claw` → `RepliClawProtocol` (`protocol.py:89+`): initial multi-role investigation, then per-cycle, when a need is open, `_fulfill_need` (`protocol.py:383-406`) **deterministically** dispatches `FALSIFIER` if `need.kind == FALSIFICATION` else `STATISTICIAN` (`protocol.py:401-404`), recomputes from the bundled claim data, and updates the plan.

### Full confound list

1. **Different intervention space.** S3 runs re-analysis *lenses* (falsifier/statistician recomputation over the claim's bundled data). S5 runs SimpleAudit *counterfactual arms* (`I_R`/`I_P`/`I_J`/`I0`). The action spaces differ, so "S5 vs S3" is not a selection-mechanism comparison over the same actions.
2. **Central-vs-escrow confound.** `repl_claw` contains blind commit/reveal (an escrow-like mechanism). Comparing S5 (escrow + decentralized market) against S3 conflates "central vs decentralized" with "escrow regime". This is exactly what science-judge Q1 flags: "central vs decentralized is overstated."
3. **Dispatch is deterministic, not adaptive choice.** The "adaptive" label comes from re-planning which *lens* to apply; the role choice itself is a fixed function of `need.kind` (`protocol.py:401-404`) — there is no utility ranking over candidate actions.
4. **M1 structural weakness (WIP-path, load-bearing).** The committed comparator path produces an `ArmResult` with `verdict_label` but no `defect_class`/`target_artifact`; the P08 `final_verdict.json` writer exists only in the WIP runner, which writes `defect_class=None, target_artifact=None` for offline arms. If S3 is scored through that path, `score.py:257` (`defect == oracle["true_cause"] and bool(target)`) is **structurally 0** for S3, making the P1 difference (S5 − S3 on M1) a function of S5 alone. The merged CLI must make S3's `defect_class`/`target_artifact` either populated from its own verdict or the arm declared non-comparable for M1 — one of the two, chosen pre-start.
5. **Cost/token mismatch.** S3's call pattern (initial roles + one follow-up per cycle) does not match S5's (3-agent market + up to `max_cycles` offers + counterfactual slots); matched-budget claim (docstring) holds only at wall/call-count level, not per-decision.

### Feasibility + cost of a neutral same-intervention-space central manager (NEXT study — do NOT build)

A neutral S3′ would: (a) run the **same** SimpleAudit arms (`I_R`/`I_P`/`I_J`/`I0`) via `counterfactual.executor.run_case`/`verify_run` (the call pattern is already in `eess_live/orchestrator.py`'s cycle loop — no new case, no new oracle, no new engine); (b) replace the decentralized need-market with a **central scheduler** that allocates arms (e.g., evidence-ranked or sequential) with a broker it owns; (c) run **without blind commit/reveal** (or with a distinct, declared escrow regime) so centralization is the only difference. Feasibility: **HIGH** — it reuses executor + escrow + verdict code; estimated **~150-300 LOC + 2-4 tests (parity, budget, determinism)**, roughly 1-2 engineer-days. Cost in study terms: it is a **new preregistered arm/study** (its own envelope, its own noise floor) — it cannot be bolted into P08 without breaking the same-task/versioned-protocol claim, and it cannot be the v1.2 S3 retroactively.

### Exact label the prereg/tables must use

Per `docs/experiments/PREREG-2026-10-v1.1.md:74` (S3 row, `[v1.1: Q1]`) and `docs/fleet/reviews/SCIENCE-JUDGE-PREREG-P08-2026-10-08.md:20` (Q1), every table/figure/caption must read:

> **"incumbent RepliClaw full protocol (blind commit/reveal + central adaptive follow-up)"**

— never "neutral central manager" or "central adaptive manager (same intervention space)". Registry keys (`adaptive_central`) and code comments may stay; the *reported* label must carry the parenthetical. S3 must additionally run the same task/case/oracle as S5 (C1 — see item 6).

**Amendment status: N.** The relabel + same-task condition are already versioned in prereg v1.1 (and the v1.2 draft keeps them); no metric definition changes. The neutral S3′, when built, gets its own prereg.

---

## Item 3 — `reference_truth` fallback in offline `_verdict` (hotspot 5)

**Severity: MAJOR (latent oracle-leak path; defensive branch). Amendment-triggering: N.**

### When it fires

`comparators/managers.py:171-194` (committed). `EESSArm._verdict` first maps the offline slice's per-hypothesis outcomes: if `predictions_outcome(claim)` yields any determined `supported`/`refuted` outcomes, it returns a majority label (lines 175-191). Only if **no determined outcomes exist at all** does control reach:

```python
# managers.py:192
truth = getattr(claim, "reference_truth", None)
mapping = {"supported": "SUPPORTED", "refuted": "REFUTED"}
return mapping.get(truth if isinstance(truth, str) else "", "INCONCLUSIVE"), 0.5
```

The docstring asserts the offline slice "always yields some" determined outcome, so this is a defensive path — but it **reads the claim's ground-truth label** and converts it into the arm's verdict. The live S5 arm has no such fallback (its hypothesis outcomes come from `run_cache` severities in the orchestrator, and its `final_verdict.json` writer at `eess_live/arm.py:199-215` has no `reference_truth` field — the live path is clean).

### Can it reach a scored artifact?

- **Committed tree:** NO scored artifact exists for offline arms (the committed `comparators/runner.py` returns `ArmResult` only; no `final_verdict.json` writer). So today the fallback value reaches only `ArmResult.verdict_label`.
- **Once the WIP runner-CLI is merged:** YES. The WIP runner writes `final_verdict.json` with `"verdict": str(result.verdict_label).lower()`. `score.py` reads `"verdict"` for (a) **secondary-case M1** (Tox21 stance match, `score.py:258-265`) and (b) **M10** (modal-verdict stability across replicates). For `policy_rag_v1`, M1 uses `defect_class`/`target_artifact` (both `None` for offline arms), so the fallback does **not** flip policy_rag M1 — but it **would** flip M10 and secondary M1 if it ever fires. A ground-truth leak into a reported verdict, even via a dead branch, is a BLOCKER-class property; it is MAJOR here only because the branch is currently dead in normal operation.

### Fix spec (diff-level)

1. **Harness redaction (primary guard):** in the runner-CLI claim construction (and in any test harness that builds a `Claim` for arms), **redact before arm construction**:
   ```python
   claim.reference_truth = None   # and any oracle-derived fields
   claim.seeded_fault = None
   ```
   applied to the shared claim passed to every arm, so no arm object can carry ground truth, committed or offline.
2. **Policy-level guard (defense in depth):** `managers.py:192-194` must NOT consult `claim.reference_truth` at all:
   ```python
   # managers.py — replace lines 192-194
   return "INCONCLUSIVE", 0.5
   ```
   (Drop the `truth`/`mapping` lines entirely. An undetermined offline slice is INCONCLUSIVE by definition; there is no legitimate source for the label.)

### Test spec (canary, negative-path)

`test_reference_truth_fallback_canary` (in `tests/test_comparators.py` or the comparators suite):

1. `claim_leaky = Claim(..., reference_truth="supported")`; `claim_clean = Claim(..., reference_truth=None)` — otherwise identical.
2. Force the defensive branch: monkeypatch `predictions_outcome` (or feed a slice report with all outcomes `not_run`/`inconclusive`) so `_verdict` reaches the fallback.
3. Assert: `EESSArm(...).run(claim_leaky, ...)` and `run(claim_clean, ...)` return **identical** `verdict_label == "INCONCLUSIVE"` (proves the leak channel is closed — same output regardless of the claim's reference truth).
4. Canary assertion: the string `"supported"` (the leaky claim's `reference_truth` value) does not appear in the returned `ArmResult.verdict_label`/detail, and `"reference_truth"` appears in **no** artifact file written by the arm.
5. Post-merge extension (runner-CLI): same test with a WIP-runner claim whose `reference_truth` is set → assert it is `None` at arm-construction time (redaction executed).

**Amendment status: N.** It closes a latent path without changing any normal-operation behavior or metric definition.

---

## Item 4 — RandomPolicy double draw (hotspot 7)

**Severity: MINOR — with a MAJOR trap: the task's stated "one-line fix" (single draw for both) is NOT selection-neutral. The only neutral fix is the stream-preserving variant C, proven below.**

### Confirmation (committed `needmarket/policy.py:164-176`)

```python
rng = random.Random(f"{rng_seed}|{agent_id}|{evidence_snapshot_sha}")   # :163
actions = [
    RankedAction(
        need_id=n.need_id,
        utility=float(rng.random()),            # :167  draw #1
        components={"rng_draw": float(rng.random())},   # :168  draw #2
        ...
```

**Confirmed: `utility` = draw #1, `components["rng_draw"]` = draw #2** — two independent draws from the same MT19937 stream. Reproduced at the pinned A3 seed (20261010, agent `alpha`, 4 needs, fixed snapshot): committed output `utility=0.9798352996452436`, `components["rng_draw"]=0.3521824001063546` — distinct, as expected.

### Why the naive "single draw for both" is NOT selection-neutral (correction to the task premise)

The task premise: "the first draw is unchanged, so ranked order is identical for a fixed seed/agent/snapshot/needs." **False.** `random.Random` is a stateful stream; draw #2 advances the stream. `rank()` is called **per agent, per evidence snapshot, per cycle** with a fresh `rng` seeded by `(seed, agent, snapshot_sha)` — and `evidence_snapshot_sha` changes after every cycle (new open-need list / new evidence). Within one `rank` call there are `2k` draws (k needs); after the fix there are `k`. For any needs-list processed after the first one in a session (i.e., cycle 2+ for every agent), draw #1 of need i under the fixed code is draw #1 of need i+k*0… concretely, the value that was draw #1 of need 1 in cycle 2 becomes a *different position in the stream* once the per-need draw count changes — so every later cycle's first-draw vector shifts, and the ranking shifts.

**Empirical proof (this review, offline, committed `RandomPolicy` imported from the worktree file which is byte-identical at 17b37a4 and d287149):**

- Sweep of **2000 seeds** (fixed agent/snapshot/needs), comparing full ordering + utility list vs committed:
  - **Variant A** (naive: `u = rng.random(); utility=u; components={"rng_draw": u}` — drop draw #2): **2000/2000 changed**. At the pinned A3 seed the committed order is `[N3, N0, N2, N1]`; variant A gives `[N0, N3, N1, N2]`.
  - **Variant C** (stream-preserving, see below): **0/2000 changed** — byte-identical ordering and utility lists.

Variant A is therefore an *experiment-changing* edit (it re-runs the A3 arm under a different selection distribution) and would be amendment-triggering; it must NOT be used.

### Recommended fix — variant C (stream-preserving), diff-level

`needmarket/policy.py:167-168` becomes (inside the list comprehension's per-need body — either inline or via a small helper for testability):

```python
u = float(rng.random())   # draw #1 — the utility (unchanged)
_ = rng.random()          # draw #2 — consumed and discarded: keeps the
                          # stream position identical to the committed code
RankedAction(
    need_id=n.need_id,
    utility=u,
    components={"rng_draw": u},   # now consistent with utility; the stream
                                  # (not this field) is what downstream cycles
                                  # depend on, and it is unchanged
    ...
)
```

**Why variant C is behavior-identical for the frozen A3 seed (and every other seed/agent/snapshot):** the fixed stream is `MT19937(seed=sha256(f"{rng_seed}|{agent_id}|{evidence_snapshot_sha}"))`. Variant C consumes the **exact same 2k values in the exact same order** as the committed code for every `rank` call (draw #1 → utility, draw #2 → discarded); it only changes what is *recorded* in `components`. Hence: (a) every `utility` value is bit-identical → `_stable_order` (the tie-broken sort at `policy.py:77-78`) produces an identical ranking for every cycle, for the pinned A3 seed (20261010) and all others (proven 0/2000); (b) every downstream `evidence_snapshot_sha`-seeded stream is fed the same preceding state; (c) the only observable delta is `components["rng_draw"]` in the choice trace. "Reuse draw #1 for `components` while consuming draw #2 as a discarded no-op" is exactly variant C.

### Consumer grep — no reported metric is touched

`grep -rn rng_draw src/ tests/` (committed) → **one hit**: the producer itself, `policy.py:168`. The sole *consumer* path is `needmarket/worker.py:68-71` `_ranking_view` (`{"need_id", "utility", "components"}` per ranked action), emitted as `choice_ranked`/`choice_changed` broker events into the broker's `events.jsonl` (broker rooted at the run dir, `orchestrator.py:199` / `arm.py:121`). `p08/score.py` **never reads** `needs/events.jsonl` or `components` for any of M1–M11 (it reads `final_verdict.json`, `run_metadata.json`, `budget_ledger.json`, `counterfactuals/*`, `traces.jsonl` for trace types). M4's artifact scan (`score.py:299-307`) greps that same file for the oracle **path string** only — a float is not that string. **Conclusion: the double-draw mismatch affects NO reported metric; the fix (variant C) changes NO reported metric.**

### Test spec (regression)

`test_random_policy_single_draw_regression` (in `tests/test_needmarket.py`):

1. **Consistency invariant:** for a fixed (seed, agent, snapshot, needs), assert `utility == components["rng_draw"]` for **every** `RankedAction` (the committed code fails this — the test is red before the fix, green after).
2. **Pinned-order neutrality:** pin the A3 seed (20261010, agent `alpha`), a fixed snapshot sha, and a fixed needs list; record the ordering fields `(need_id, rank)` sequence for cycles 1..N (run the worker loop offline, as `test_eess_live.py` already does with `FakeLLMClient`). Assert the sequence is **byte-identical** to the committed code's sequence (pre-fix fixture captured from the committed build, e.g., `[N3, N0, N2, N1]` for the single-snapshot case). This test is what *makes* the fix safe: a variant-A implementation fails it; variant C passes.
3. **Stream-preservation sweep (cheap property):** for 100 random seeds, assert the full `(need_id, round(utility,12))` list equals the committed-code list captured in the fixture.

**Amendment status: N — conditional.** Condition: the fix MUST be variant C and MUST land with the pinned-order regression test. If variant A were used, the A3 arm's selection distribution would change → amendment-triggering + A3 parity rerun. State this condition in the amendment/v1.2 notes so the pre-start fix worker (dispatched per `d287149` subject line) is pinned to variant C.

---

## Item 5 — Effective model treatment not recorded (hotspot 6)

**Severity: MINOR (observability/audit; indirect metric exposure). Amendment-triggering: N (additive metadata; model/temperature pinning is a prereg condition, not a code change).**

### Exact request fields sent (committed `investigators.py:92-97`)

```python
resp = client.chat.completions.create(
    model=self.cfg.model,                              # :93
    messages=[{"role": "system", "content": system},
              {"role": "user", "content": prompt}],    # :94
    max_tokens=max_tokens or self.cfg.max_tokens,      # :95  (default 4096, :40)
    temperature=self.cfg.temperature,                  # :96
)
```

Exactly **four** fields: `model`, `messages`, `max_tokens`, `temperature`. `grep -rn reasoning_effort src/` → **0 hits** (no `reasoning_effort`, no `enable_thinking`, no provider-specific knobs anywhere in the request path). Consequence: whatever reasoning mode the provider applies by default is **unrecorded and unverifiable from artifacts**, and `max_tokens=4096` can truncate long chain-of-thought output, triggering the one-shot JSON retry (`investigators.py:114-124`) — i.e., truncation is a silent treatment effect and a token-count effect.

### Where `run_metadata.json` must gain the effective-treatment block

The committed `run_metadata.json` writer exists **only in the WIP runner-CLI** (`comparators/runner.py` WIP, ~lines 300-319: writes `model`, `temperature`, `endpoint` (base_url), `offline_arm`, `harness_seed`, `envelope`, `tree_sha`). The committed `eess_live/arm.py::_write_artifacts` (`arm.py:190-215`) writes `final_verdict.json`/`budget_ledger.json`/`traces.jsonl`/counterfactuals but NOT `run_metadata.json`, and neither does the committed orchestrator. Neither arm.py nor orchestrator.py knows the *effective* LLM config (arms receive an opaque `client_factory`), so **the correct writer is the runner-CLI** — it is the composition root that owns `LLMConfig`/`base_url`.

Spec: the runner-CLI's `run_metadata.json` writer gains, for every arm (live and offline — offline arms get the same shape with the offline marker), an `effective_treatment` block:

```json
"effective_treatment": {
  "model": "<LLMConfig.model as sent to the API>",
  "endpoint_host": "<host parsed from base_url>",
  "temperature": 0.0,
  "max_tokens": 4096,
  "reasoning_effort": null
}
```

- `reasoning_effort: null` is written **explicitly** (JSON `null`) to document that no reasoning control was sent (negative audit field).
- `endpoint_host` from the configured `base_url` (e.g., `api.openai.com`) — host only, no API keys or paths.
- The same block is written for offline arms with `"model": "offline"` semantics already present via `offline_arm`, so all arms are comparable on treatment fields.
- The v1.2 sign-off gate should verify, before live start, that every arm's `run_metadata.json` carries the block and that `model`/`temperature` match the prereg-pinned values.

### Metric impact

No M1–M11 is *computed* from these fields, so there is no direct metric change. Indirect: (a) **M5/M6** — 4096-token truncation → JSON retry → inflated token counts and a changed effective output; (b) the prereg's "matched model/treatment across arms" claim is currently **unverifiable from artifacts** (a provider silently applying different reasoning defaults or a mid-campaign model substitution would be invisible). Hence MINOR: an audit gap that can mask a treatment change, not a metric mismeasurement by itself.

**Amendment status: N.** Additive metadata + pre-start verification; the model/temperature values themselves must be *pinned in the prereg* (science side), not changed in code.

---

## Item 6 (5b) — Same-case loader gap: `EESSArm.run` ignores its claim (hotspot 5b)

**Severity: MAJOR. Amendment-triggering: N (enforces already-preregistered C1; no metric definition change).**

### Finding (committed `comparators/managers.py:112-125`)

```python
def run(self, claim, ledger, spec, work_dir) -> ArmResult:
    from ..slice import run_slice
    work_dir = Path(work_dir)
    t0 = time.monotonic()
    report = run_slice(work_dir / "eess")      # <-- claim NEVER used
```

The `claim` parameter is accepted and **discarded**. `run_slice` → `slice/orchestrate.py` is rooted to the canonical case: `CASE_ID = "policy_rag_v1"` (`slice/orchestrate.py:47`), with fixed hypotheses and the policy-rag data pipeline. So if the harness ever hands the offline EESS arm a claim for a *different* case (e.g., Tox21, or a mutated policy_rag claim), the arm silently executes `policy_rag_v1` — a **C1 same-task violation** that would invalidate the RQ1/RQ2 M1 comparisons (and the S5-offline parity arm's meaning). There is no committed guard: no check that the claim's case matches the slice's root, no recorded proof of which case was actually executed.

The WIP (separate worktree, **do not touch**): untracked `slice/case_loader.py` + an uncommitted `managers.py` diff adding `case_loader.assert_same_task(...)` in `EESSArm.run` (rooting the slice to the loaded case), and untracked WIP `runner.py` writing `case_id`/`envelope` into `run_metadata.json`. Read-only observation of the WIP: the WIP guard compares the constructor-injected claim (`self._claim`) while `run(claim)` receives the harness's claim as a parameter, and the committed registry path (`ComparatorHarness`, `comparators/runner.py`) constructs arms with a single `investigator_factory` argument — no claim — so the WIP guard is skipped on that path (`if self._claim is not None:`). That is the runner-CLI worker's workstream to close; this review does not modify it and lists the acceptance contract below that the **merged** CLI must pass.

### Acceptance test the merged runner-CLI must pass (C1 property)

`test_all_arms_same_case_and_envelope` (CLI-level, offline, FakeLLMClient):

1. Run the merged CLI for one campaign over all arms (S0/S3/S4/S5 [+ eess_offline]) with ONE claim (case `policy_rag_v1`, fixed statement text).
2. Collect every arm's `run-*/run_metadata.json`.
3. Assert:
   - **identical `case_id`** across all arms: `len({m["case_id"] for m in metas}) == 1` — this intercepts the *actually-loaded* case id per arm (the offline EESS arm must prove it ran the same case, not just share the claim metadata);
   - **identical claim statement** across all arms: each `run_metadata.json` carries `claim_statement_sha256` (or the statement verbatim) and all arms share one value; the offline EESS arm's recorded case must equal the slice root it actually executed (`slice/orchestrate.CASE_ID` at execution time);
   - **identical `envelope_sha256`** across all arms (`envelope_mismatch` flag in `p08/score.py:180-188` stays False; the scorer's re-check is the second line of defense);
   - negative arm: point the CLI at a claim for a *different* case (Tox21) while the offline EESS arm still roots to `policy_rag_v1` → the CLI must **fail loudly (non-zero exit, clear message), not silently run the wrong case**.
4. The negative arm is the discriminating half of the test: a CLI that only stamps shared claim metadata (without verifying what each arm actually executed) passes 3a/3b/3c and fails 4.

**Amendment status: N.** C1 (same task/case/oracle across compared arms) is already a preregistered condition (v1.1 Q1(b), cross-cutting C1); this test enforces it mechanically.

---

## Cross-cutting notes

- **M-metric map used above (committed `p08/score.py`):** M1 `_diagnosis_correct` (251-265); M2 falsification discipline (traces); M3 counterfactual yield (293-297, `counterfactuals/*` + slots); M4 leakage = count of oracle **path-string** hits in `*.json/.jsonl/.md/.txt` under the run dir (298-309); M5 tokens; M6 tokens/correct; M7 abort rate; M8 integrity rejections; M9 wall; M10 modal-verdict stability (reads `"verdict"`); M11 correct-falsified rate.
- **Baseline check (real):** `.venv/bin/python -m pytest -o addopts="" -q` → **162 passed, 8 skipped, 4 failed** at review start; all 4 failures in the untracked WIP `tests/test_runner_cli.py` (out of committed scope). No committed-test regression exists; the fixes above are spec'd, not applied, by this review.
- **Oracle-isolation invariant (re-verified):** the sole oracle reader is `p08/score.py::load_oracle` (234-241) behind the completeness gate (198-224); the executor declares no oracle import path; therefore any data path composed of `EvidenceObservation`/verified-run fields (items 1, 6) is oracle-free by construction.
- **Parallel state:** `d287149` notes two A6 pre-start fix workers dispatched (random-policy, leak-guard). The specs in §4 (variant C + pinned-order test) and §3 (redaction + INCONCLUSIVE + canary) are the acceptance criteria those fixes must meet; the random-policy worker must be pinned to variant C — a variant-A implementation fails the pinned-order regression and would be amendment-triggering.

## Top-3 must-fix-before-live

1. **Item 1 (BLOCKER):** inject the per-agent verified-evidence block (escrow observation + run id) into the RESOLVE verdict prompt (`orchestrator.py:444-452`), amendment-triggering, pre-start only, with the negative-path regression test (see the Item 1 test spec). Without it, M1 measures prior-guessing, not evidence use — the P08 headline is invalid.
2. **Item 3 (MAJOR, cheap):** redact `claim.reference_truth`/`seeded_fault` before arm construction (harness) + replace the `managers.py:192-194` fallback with `"INCONCLUSIVE"` + canary test. Closes the only remaining path by which a ground-truth label could reach a reported verdict (M10, secondary M1) once the merged runner writes `final_verdict.json`.
3. **Item 6/5b (MAJOR):** the merged runner-CLI must pass the same-case acceptance test — identical `case_id` + claim statement + `envelope_sha256` across all arms, plus the fail-loudly negative arm. Without it, RQ1/RQ2 compare arms that may have run different cases.

Also required before live but below the top-3: **Item 2** — tables use the exact v1.1 label "incumbent RepliClaw full protocol (blind commit/reveal + central adaptive follow-up)" and S3 runs same-task (rides on item 3); decide pre-start whether S3's offline `defect_class`/`target_artifact` are populated or S3 is declared M1-non-comparable. **Item 4** — variant-C fix + regression (prevents a future "one-line" edit from silently changing A3's selection distribution). **Item 5** — runner-CLI writes the `effective_treatment` block with explicit `"reasoning_effort": null` and the v1.2 sign-off gate verifies treatment fields.
