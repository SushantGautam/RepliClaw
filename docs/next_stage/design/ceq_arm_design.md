# C-EQ arm design — intervention-matched adaptive centralized manager

**Status:** DESIGN PROPOSAL (L4, 2026-10-09). Not implemented, not preregistered.
Supersedes nothing; P08 artifacts stay immutable. Feeds V3 prereg (G2 canaries).

**Primary artifact:** one new module `src/repliclaw/experiments/v3/ceq.py`
(+ `src/repliclaw/experiments/v3/__init__.py`) and one test file
`tests/experiments/test_v3_ceq.py`. **No existing module is edited.**
Implementable by one engineer in ~1-2 days: ~450 lines of new code, ~300 lines
of tests, all runnable offline with `FakeLLMClient`.

---

## 1. Context and why S3 was not honest

P08: S3 (the "adaptive central manager", `comparators/managers.py:46`) scored
M1 = 0.050 — the weakest arm — but S3 was confounded (A3 disclosure): it was
the *incumbent RepliClaw protocol* (blind commit/reveal + central follow-up)
running the strategy arms' finding prompts, and it **never executed any
counterfactual intervention** (per `docs/experiments/P1_RESULT_STATEMENT_20261009.md`
section 0.1: S0/S3/S4 never execute I_R/I_P/I_J). C-EQ fixes exactly this: the
central planner **can call the same executor** the decentralized investigators
use, with the same budget, timing and menu. It must be genuinely adaptive —
no fixed script, no pre-coded answers, no oracle.

## 2. Reuse analysis (what exists for the six arms)

| Arm (V3) | P08 predecessor | Existing code | Reuse verdict |
|---|---|---|---|
| **D-E** | S5 `eess` | `EESSLiveS5Arm` (`src/repliclaw/eess_live/arm.py:279`) → `LiveEESSOrchestrator` (`eess_live/orchestrator.py:260`), `EscrowedEscrow` (`eess_live/escrow.py:91`) + `LocalEigPolicy` (`needmarket/policy.py:81`) | **Reuse verbatim.** Only the V3 registry key is renamed D-E in the new registry. |
| **D-N** | A1 `eess_no_escrow` | `EESSLiveA1Arm` (`arm.py:286`) — `PassThroughEscrow` (`eess_live/escrow.py:158`) + `LocalEigPolicy` | **Reuse verbatim.** |
| **D-R** | A3 `eess_random_select` | `EESSLiveA3Arm` (`arm.py:293`) — `EscrowedEscrow` + `RandomPolicy` (`needmarket/policy.py:149`, seeded) | **Reuse verbatim.** |
| **C-EQ** | — (S3 was *not* this) | Executor + case + budget + escrow + evidence plumbing (below) | **New code**, minimal, in `ceq.py`; ~90% composes existing classes. |
| **C-NE** | — | Same as C-EQ with the escrow seam flipped to pass-through | **New code** (thin subclass), same module. |
| **S-I** | — (offline `SingleAgentBaseline` `comparators/managers.py:35` has *no* intervention access; not reusable as S-I) | Same planner loop with 0 investigators | **New code** (thin subclass), same module. |

### 2.1 Components reused verbatim by C-EQ (file:line)

| Component | Location | Used for |
|---|---|---|
| `run_case(case, intervention, seed=0, out_root=...)` + `persist_arm` | `counterfactual/executor.py:296`, `:249` | **The identical executor API** D-E uses (D-E path: `orchestrator.py` `_execute` → `run_case`). C-EQ calls the same function, same seed pinning (0). |
| `load_case` / `load_interventions` / `CaseSpec` / `InterventionSpec` (+ `.sha256()`) | `executor.py:223`, `:229`; `counterfactual/case.py:46`, `:77` | Case + full admissible-intervention menu. No arm gets a filtered menu. |
| `engine_metadata()` | `executor.py:69` | Interface snapshot (executor identity: name/version/git sha). |
| `build_evidence(agent_id, run)` → `EvidenceObservation` | `eess_live/orchestrator.py:227` | Identical observation schema + deterministic obs id (`orchestrator.py:185`) + identical publish timing (only after `run_case` returns). |
| `_evidence_block(evidence, hypothesis_id)` | `orchestrator.py:85` | Identical machine-verified evidence rendering the manager's prompt uses; reuses its `EVIDENCE_FORBIDDEN_SUBSTRINGS` guard (def `orchestrator.py:59`; enforcement loop `:141`). |
| `LiveBudgetLedger` (`record_live_call`, `record_overflow*`, `to_contract_dict`) | `eess_live/accounting.py:70` | Per-call budget accounting; same `p08.budget_ledger/1` artifact schema. |
| `usage_snapshot` / `usage_delta` / `usage_present` / `InvalidUsageError` | `eess_live/budget_calls.py:35`, `:45`, `:54`, `:21` | Snapshot-delta token accounting and never-zero-fill voiding — the same semantics as `orchestrator.py` `_llm_call` (`:320`). |
| `LiveEscrow` interface, `EscrowedEscrow`, `PassThroughEscrow`, `RevealOutcome` | `eess_live/escrow.py:43`, `:91`, `:158`, `:34` | C-EQ commits **one manager pre-outcome forecast packet per round** through the same `EscrowedEscrow` (integrity-checked, revealed before execution) — honest symmetry with D-E's commitment mechanism, centralized. C-NE uses `PassThroughEscrow` (no sealing, no integrity gate), mirroring A1's factor. |
| `PredictionPacket` / `commitment_hash` | `escrow/packet.py:34`, `:84` | The forecast packet schema. C-EQ's packet is `agent_id="manager"`. |
| `DEFECT_ADJUDICATION_INSTRUCTION` | `defect_adjudication.py:55` | Byte-identical defect menu in the manager's diagnosis prompt (same menu D-E's RESOLVE prompt gets, `orchestrator.py` verdict-prompt region ~:580). |
| `BudgetEnvelope` (+ `.sha256()`), `BudgetLedger`, `BudgetRecord`, `BudgetOverflow` | `comparators/budget.py:32`, `:73`, `:59`, `:28` | Envelope + cross-arm parity. |
| `ArmSpec` / `ArmResult` / `ComparatorArm` protocol | `comparators/arms.py:28`, `:37`, `:76` | C-EQ/S-I are `ComparatorArm`s so `assert_budget_parity` (`comparators/runner.py:77`) applies unchanged. |
| `LiveRunResult` | `orchestrator.py:151` | C-EQ's manager returns the same result shape D-E maps to `final_verdict.json`. |
| `write_counterfactuals(orch, result, run_dir)` | `eess_live/arm.py:37` | **Duck-typed reuse**: it only reads `orch.run_cache`; C-EQ builds a namespace with an identically-shaped `run_cache` and the arm's `LiveRunResult`, so the same `p08.counterfactual/1` artifacts are written (pinned in test 15). |
| `FakeLLMClient` (+ `COMMIT_MARKER`/`VERDICT_MARKER`) | `eess_live/fake.py:40`, `:28`, `:29` | Offline tests for *every* arm (canned payload + deterministic usage). |
| `redact_claim_for_arms` | `comparators/runner.py:48` | Same oracle-stripped claim handed to all arms. |
| D-10 frozen-pin pattern (`FROZEN_*`, `--assert-frozen`) | `comparators/runner.py:215-227`, `:287` | The same freeze pattern is copied (not shared) for V3 params in `ceq.py`. |

### 2.2 New code (all in `src/repliclaw/experiments/v3/ceq.py`)

| Item | Est. lines | Notes |
|---|---|---|
| `accounted_call(ledger, client, prompt, purpose, agent_id)` | ~40 | Re-implements the *small* snapshot-delta wrapper of `orchestrator.py` `_llm_call` (`:320-366`) because `_llm_call` is a private method of `LiveEESSOrchestrator`. Composes `budget_calls` + `LiveBudgetLedger`; behavior asserted equivalent in test 11. |
| `PlannerDecision` (pydantic) + `interface_snapshot(case_id, envelope)` | ~50 | Decision = `{action: intervene|abstain|diagnose, intervention_id?, defect_class?, target_artifact?}`. Snapshot = section 3.1. |
| `CEQManager` (the adaptive loop) | ~150 | section 3.2. |
| `CEQArm`, `CNEArm`, `SIArm` (`ComparatorArm` adapters) | ~100 | Thin, share one loop; only flags differ. |
| `v3_arm_registry()` + `CapabilityProfile` matrix | ~60 | section 4. |
| (tests, `tests/experiments/test_v3_ceq.py`) | ~300 | section 6. |

**No edits** to `eess_live/*`, `comparators/*`, `counterfactual/*`, `escrow/*`,
`needmarket/*`. If a private helper (e.g. `_evidence_block`) is imported, it is
imported — not copied — and a test pins its byte behavior.

---

## 3. C-EQ design

### 3.1 Identity, agents, and interface snapshot

C-EQ = **1 manager (LLM planner) + 3 investigators (LLM)**, 4 distinct agents,
so D-E's 3 investigators are matched *as a subset of the same 4-agent cap*
(P08 envelope: 60,000 tokens / 900 s / 4 agents — identical `BudgetEnvelope`,
so `envelope_sha256` parity holds). The manager may consult investigators
(one prompt each, accounted) but **all intervention choice is the manager's**.
Investigator prompts are byte-for-byte the D-E investigator *finding* prompts
(the same workers, centrally scheduled) — keeps prompting budget symmetric
(risk R1).

`interface_snapshot(case_id, envelope)` = canonical JSON dict of:
`case.sha256()` (`case.py:64`), sorted `(intervention_id,
InterventionSpec.sha256())` pairs (`case.py:105`),
`sha256(DEFECT_ADJUDICATION_INSTRUCTION)`, `engine_metadata()`, and
`envelope.to_dict()`. This is the tool-interface hash the harness records in
`run_metadata` and compares across arms.

### 3.2 Loop (per case, single run)

```
1.  claim = redact_claim_for_arms(claim)          # runner.py:48 — no oracle fields
2.  escrow.open(case_id)                           # EscrowedEscrow (C-NE: PassThrough)
3.  FORECAST: manager LLM emits one PredictionPacket
    (working hypothesis set, predicted dominant defect, refutation
     criterion) -> escrow.commit("manager", packet) -> begin_reveal ->
     reveal -> enter_execute.  (C-NE/S-I: step 3 is a no-op.)
4.  for round in 1..MAX_PLANNER_ROUNDS (frozen; proposed 4):
      evidence_view = wall-free escrow.evidence()  # same records D-E sees
      decision = LLM(planner_prompt(case, hypothesis set,
                                    evidence block via _evidence_block,
                                    allowed intervention ids + declared
                                    changed factors, DEFECT_ADJUDICATION
                                    menu, budget-so-far))
      decision in {intervene(I), abstain, diagnose(defect_class,
                                                   target_artifact)}
      - intervene: I must be in load_interventions(case_id) ids; cached by
        intervention_id (exactly orchestrator.run_cache semantics,
        orchestrator.py:701); run_case(case, I, seed=0); build_evidence ->
        escrow.publish_evidence  (timing: only after execution completes)
      - diagnose: final; break
      - abstain: continue (or final-abstain if rounds exhausted)
5.  escrow.resolve(); FINAL diagnosis prompt (evidence blocks +
    DEFECT_ADJUDICATION_INSTRUCTION) -> defect_class / target_artifact /
    confidence; LiveRunResult mapped to final_verdict.json via the same
    contract fields (verdict, defect_class, target_artifact, hypotheses,
    agent_verdicts).
```

**No pre-coded answers:** the planner prompt contains only (a) case id +
redacted claim, (b) its own sealed forecast, (c) verified evidence lines,
(d) intervention ids + their *declared changed factors* (from
`InterventionSpec.changed_factors`, `case.py:89` — the action vocabulary, not
outcomes), (e) the defect menu, (f) budget-so-far. It contains **no**
schedule, no hint of which intervention fires, no oracle content. The
full-prompt forbidden-substring guard (`orchestrator.py:59` def, `:141` enforcement loop, applied as in
the D-E verdict prompt ~:573) runs on *every* manager/investigator prompt,
fail-loud.

**Adaptive by construction:** the manager observes every result before each
decision, can change the plan round-to-round, can abstain, and can call any
admissible intervention in any order (cache makes repeats idempotent). There
is no per-case branching anywhere in `ceq.py`; test 13 forbids case-id- and
defect-specific literals.

### 3.3 Prompting parity (honest strength, not starved prompting)

- Manager diagnosis prompt = D-E RESOLVE prompt structure
  (`orchestrator.py` verdict region ~:557-597) with roles centralized: same
  evidence-block format, same defect-menu block, same required JSON fields.
- Each investigator gets the identical finding prompt D-E investigators get.
- Prompt-volume canary (test 5) asserts C-EQ's planner+investigator prompt
  volume is not *less* than D-E's per-agent volume for the same case state —
  guards against the "weaker prompting budget" cripple (R1).

## 4. Arm registry and capability matrix

`v3_arm_registry()` in `ceq.py` returns `{arm_name: constructor}`; constructors
take the same `client_factory` signature as `live_arm_registry()`
(`arm.py:300`). Each arm class carries a `CapabilityProfile` (frozen
dataclass) so tests can assert capabilities without running the arm:

| Capability | D-E | C-EQ | D-N | D-R | C-NE | S-I |
|---|---|---|---|---|---|---|
| Counterfactual executor (`run_case`, seed 0) | Y | Y | Y | Y | Y | Y |
| Full 5-intervention menu (I0..IC) | Y | Y | Y | Y | Y | Y |
| Pre-outcome sealed forecast (`escrow.commit`) | Y per-agent | Y (manager, 1) | N | Y per-agent | N | N |
| Verified-evidence view (integrity-gated) | Y | Y | N (raw) | Y | N (raw) | N (own obs) |
| Decentralized per-agent selection | Y (EIG) | N | Y (EIG) | Y (seeded rand) | N | N |
| Investigators (distinct agents) | 3 | 3 + manager | 3 | 3 | 3 + manager | 1 |
| Adaptive replanning after each observation | Y | Y | Y | Y (seeded) | Y | Y (single) |
| Oracle read (any prompt/artifact) | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| Fixed/canned intervention script | FORBIDDEN | FORBIDDEN | n/a (seeded, not script) | n/a (seeded, not script) | FORBIDDEN | FORBIDDEN |

Mechanism differences, precisely:
- **D-E vs C-EQ**: selection locus (3 independent local EIG policies via
  `LocalEigPolicy`/`NeedWorker` (`policy.py:81`, `needmarket/worker.py:46`)
  vs one central planner) and commitment locus (3 agent packets vs 1 manager
  packet). Identical: executor, menu, timing, envelope, defect menu.
- **D-E vs D-N**: escrow seam only (`EscrowedEscrow` vs `PassThroughEscrow`).
- **D-E vs D-R**: policy seam only (`LocalEigPolicy` vs `RandomPolicy`).
- **C-EQ vs C-NE**: escrow seam only (sealed manager forecast +
  integrity-gated view vs pass-through raw view) — mirrors A1's single factor.
- **S-I**: same planner loop, `n_investigators=0`; parallelism difference is
  an intrinsic architectural effect, disclosed per V3.

## 5. Parity contract (what is PARITY-CHECKED and how)

All checks are deterministic, offline (FakeLLMClient + frozen `policy_rag_v1`
case), no LLM, no network.

1. **Interface snapshot equality.** **Test:** snapshots for D-E and C-EQ (and
   every V3 arm) are byte-identical (test 1).
2. **Budget parity.** One shared `BudgetEnvelope` instance per harness; every
   arm's `ArmResult.envelope_sha256` equal and `assert_budget_parity`
   (`runner.py:77`) returns `parity: True` over all six arms (test 2).
3. **Information timing.** Evidence is publishable only after `run_case`
   returns (both arms call `build_evidence` at the same point). **Test:**
   instrumented FakeLLMClient records every prompt; in the C-EQ run *no*
   planner prompt before the first executor completion contains
   `evidence_id=`, and after k executed interventions the next planner prompt
   contains exactly the same set of `evidence_id=` lines D-E's next reasoning
   prompt contains (tests 6-7).
4. **Defect menu.** The diagnosis prompt of both arms embeds
   `DEFECT_ADJUDICATION_INSTRUCTION` byte-identically (test inside 6: extract
   block from recorded prompts, assert equal).
5. **Executor identity.** Both arms obtain runs through `run_case` at seed 0;
   for the same case+intervention, `config_sha256` and `target_output` in
   D-E's and C-EQ's `counterfactuals/<arm>.json` are identical (test 14 spy +
   snapshot check).
6. **Prompt volume (anti-cripple).** For the same case state, sum of prompt
   tokens across C-EQ's agents >= sum across D-E's agents (fake
   tokenization: len(prompt)//4) (test 5).
7. **Leakage.** No arm module or prompt touches oracle fields:
   `EVIDENCE_FORBIDDEN_SUBSTRINGS` guard active on every prompt (fail-loud,
   test 4); static test greps `ceq.py` for `oracle` / `true_cause` /
   `load_oracle` — must be absent (test 13).

## 6. Test plan (`tests/experiments/test_v3_ceq.py`, all offline)

Helpers: `_fake_factory(**payloads)` → `FakeLLMClient` factory
(`fake.py:40`); `_env()` → `BudgetEnvelope(max_tokens=60_000, max_wall_s=900,
max_agents=4)`; `_claim()` → fixture claim (via `redact_claim_for_arms`);
`tmp_path` work dirs.

1. **`test_interface_snapshot_identical_all_arms`** — `interface_snapshot`
   byte-equal for D-E, C-EQ, D-N, D-R, C-NE, S-I (same case + envelope).
2. **`test_envelope_parity_six_arms`** — run all six arms (fake clients);
   `assert_budget_parity(results, env)["parity"] is True`; every
   `envelope_sha256` == `env.sha256()`.
3. **`test_ceq_rejects_unregistered_intervention`** — fake planner payload
   returns `intervention_id="I_X_bogus"` → arm does **not** call the
   executor, records a `rejected_intervention` trace event, run completes
   with `counterfactual_slots_executed == 0`.
4. **`test_ceq_forbidden_substring_guard`** — monkeypatch an evidence record
   to contain `"true_cause"` → arm raises `RuntimeError` (guard from
   `orchestrator.py:59/141`), run does not complete.
5. **`test_prompt_volume_parity_ceq_vs_de`** — sum of prompt volume in C-EQ
   >= sum in D-E for an identical 2-execution fake trace.
6. **`test_information_timing_ceq`** — planner prompt #1 contains no
   `evidence_id=`; after first `run_case`, planner prompt #2 contains exactly
   that run's `obs_` id; D-E (S5 arm) shows the same before/after split;
   both arms' post-execution prompt evidence blocks are equal.
7. **`test_information_timing_de`** — S5 arm: no `evidence_id=` in any
   COMMIT prompt; first appears only in post-evidence prompts.
8. **`test_ceq_adaptivity_offline`** — fake planner: round 1 → `abstain`;
   round 2 (after I0 evidence present) → `intervene I_R_retrieval_fix`;
   round 3 → `diagnose`. Assert 3 planner calls, exactly 1 executor run,
   choice trace shows the plan *changed because of evidence* (round-2 prompt
   contains the obs id from round 1).
9. **`test_reset_determinism_ceq`** — run CEQArm twice (fresh `tmp_path`,
   identical fake payloads, same seed) → `run_cache` entries
   (`config_sha256`, `target_output`, `severity`) and all published
   `EvidenceObservation` dicts (wall-clock field stripped, cf.
   `_wall_free_evidence`, `orchestrator.py:220`) equal;
   `counterfactuals/*.json` byte-equal.
10. **`test_capability_matrix`** — for each arm class: assert its
    `CapabilityProfile` matches the section 4 table row (allowed/forbidden
    flags); runtime: for D-N, C-NE, S-I the instrumented escrow records
    **zero** `commit` calls; for D-E/D-R/C-EQ, >=1.
11. **`test_ceq_budget_enforcement`** — fake client `per_call=(50_000, 0)`
    with a 60k-token envelope → 2nd call aborts: `result.status ==
    "aborted_budget"`, `ledger.overflow_events` non-empty, tripping call
    present with real usage (never zero-filled); parent ledger never over-cap.
12. **`test_ceq_agent_cap`** — `max_agents=4`: C-EQ (manager+3) completes;
    `max_agents=3`: C-EQ aborts on 4th distinct agent with
    `distinct_agents == 4` recorded; S-I under `max_agents=1` completes.
13. **`test_no_fixed_script`** — static: source of `ceq.py` contains no
    `"I_R_retrieval_fix"`, `"I_P_policy_conflict"`, `"I_J_judge_fix"`,
    `"policy_rag_v1"`, `"retrieval_omission"`, `load_oracle`, or `true_cause`
    literals (menu ids come only from `load_interventions`; defect classes
    only from the shared instruction string).
14. **`test_ceq_uses_same_executor_api`** — monkeypatch
    `repliclaw.counterfactual.executor.run_case` with a spy; run D-E and
    C-EQ; the spy must fire for C-EQ with the same argument types and
    `seed=0`; assert C-EQ's calls go through the imported `run_case` (no
    re-implementation).
15. **`test_write_counterfactuals_ducktyping`** — CEQArm's
    `counterfactuals/<arm>.json` files parse as `p08.counterfactual/1` and
    are key-for-key equal to what `write_counterfactuals`
    (`arm.py:37`) produces for D-E on the same runs (minus arm/hypothesis
    fields).

All tests pass offline: fake clients, frozen case data, tmp_path artifacts.
Estimated total runtime < 20 s.

## 7. Risks (cripple modes) and canaries

| # | Risk (how C-EQ could be accidentally weakened) | Canary / mitigation |
|---|---|---|
| R1 | Hidden fixed script: planner effectively follows a canned I0→I_R→diagnose order (prompt-tuned toward the known P08 answer) | Test 13 (no case/defect literals in `ceq.py`); test 8 (choice provably depends on observed evidence); prereg freeze of planner prompt template sha; independent Code Judge review of the prompt template before G2. |
| R2 | Weaker prompting budget (manager gets a thinner prompt than D-E's agents, so it *cannot* reason as well) | Test 5 (prompt volume); prompt-structure spec section 3.3 (same evidence-block + defect-menu blocks); any prompt change is a versioned, pre-freeze amendment. |
| R3 | Information timing asymmetry (C-EQ sees results before D-E, or vice versa) | Tests 6-7; single publish point `build_evidence` reused verbatim for both arms. |
| R4 | Executor divergence (C-EQ calls a different code path → different observations) | Test 14 (spy on `run_case`); `interface_snapshot` includes `engine_metadata()`. |
| R5 | Envelope drift (e.g. different wall cap silently) | One shared `BudgetEnvelope` object; test 2; `--assert-frozen`-style check copied from `runner.py:287`. |
| R6 | Fake-LLM answer leakage: `FakeLLMClient`'s fallback payload (`fake.py:104-…`) returns the case-consistent defect, so an *offline* C-EQ can "succeed" trivially — must never be read as a measurement | S-1-style disclosure (as in P08 section 2.5): offline results labeled `offline: true` in `run_metadata`; report generator refuses fixture rows in results tables. |
| R7 | Escrow confound re-introduction (C-EQ/C-NE flip-flopped, or D-N accidentally escrowed) | Test 10 pins the section 4 table at class level *and* runtime (commit-call counts). |
| R8 | Agent-cap asymmetry (C-EQ starved by counting the manager as an agent while D-E's agents are counted differently — or the reverse) | Test 12; both arms count *distinct agent ids* through the same `LiveBudgetLedger` path; the 4-agent cap is explicit in the prereg and both arms' typical deployments (3 vs 4) are declared. |
| R9 | Wall-clock / parallelism advantage unmeasured (C-EQ parallelizes, S-I serial) | Envelope wall cap enforced identically; per-arm concurrency recorded in `run_metadata` and disclosed per V3 ("parallelism is an intrinsic architectural effect"); no wall-time advantage claim without the measurement. |
| R10 | Verdict aggregation differs (C-EQ single voice vs D-E plurality) making `verdict` non-comparable | Both arms emit the full `agent_verdicts` list + identical `defect_class`/`target_artifact` extraction (first-non-null, `orchestrator.py` ~:596-601); primary metric M1 uses `defect_class == oracle.true_cause`, not `verdict`, so aggregation locus cannot bias M1; test asserts both arms populate the same `final_verdict.json` keys. |

## 8. Out of scope / open items (for V3 prereg, not for this module)

- AIOpsLab adapter (track I live environment) — L1-L3; `ceq.py` is
  case-agnostic via `case_id` param, but the V3 pilot runs on the frozen
  `policy_rag_v1` case first (feasibility, not confirmatory).
- `C-OracleSelection` — evaluator-side only, never in `ceq.py`.
- Pilot N/seeds, bootstrap RNG pin, multiplicity — prereg document.
- Whether C-EQ's manager may *delegate* an intervention to an investigator
  agent id (affects agent-cap counting): default **no** (manager executes
  under its own agent id `"manager"`); keep it a frozen parameter.
