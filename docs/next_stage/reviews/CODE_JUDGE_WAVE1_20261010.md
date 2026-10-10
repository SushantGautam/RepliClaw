# CODE JUDGE — WAVE 1 REVIEW

**Judge:** J-CODE (independent Code Judge, RepliClaw Stage 2)
**Reviewed worktree:** `/Users/sushantgautam/Documents/RepliClaw-stg2-dev` @ `99eb764` (branch `dev`)
**Date:** 2026-10-10
**Scratch:** `/Users/sushantgautam/Documents/stg2-worktrees/judge-code-w1/` (read-only probes + tamper test; cleaned)

---

## VERDICT

## **APPROVE-WITH-CONDITIONS**

Wave 1 is high-quality, well-tested, and the mandatory gate suite passes green.
The single **HIGH** finding is a scientific-integrity exposure in the RCAEval
manifest: `root_cause_service` — a **per-case ground-truth root-cause label** —
is both a stratification axis **and** written into the agent-visible
`CaseManifest.strata`. Under the governing rule *"the canonical index for
STRUCTURE is fine, but per-case root-cause labels make the scorer the only
reader,"* the manifest (and its `strata` field) must be gated to scorer-only
access and disclosed in the prereg before G4 freeze. This is fixable without
touching the code under review; it is an access-control / disclosure condition.

No code defect blocks integration. The C-EQ manager has **no covert
information channel** to D-E investigators beyond the *disclosed and tested*
evidence-union; the residual gaps are (i) a static test that proves a subset
rather than completeness, and (ii) a claimed-but-absent prompt-template SHA pin.

---

## 1. Mandatory gate output (ACTUAL)

Environment: `/Users/sushantgautam/Documents/ScienceClawHackathon/.venv/bin/python`
Run from `RepliClaw-stg2-dev` @ `99eb764`.

### pytest (full suite)
```
$ .venv/bin/python -m pytest tests/ -q
352 passed, 8 skipped in ~7s
```
- 23 of the 352 are the C-EQ `tests/experiments/test_v3_ceq_*.py` suite
  (no_fixed_script=3, parity=10, budget=3, capability=7). All green.
- The 8 skips are pre-existing (hardware/network-gated live-LLM paths), not
  introduced by Wave 1.

### mypy
```
$ mypy src/repliclaw/
Success: no issues found in 72 source files
```

### ruff
```
$ ruff check src/ tests/
All checks passed!
```

All three gates pass with the actual output above. The 23 C-EQ tests run in
under a second (static/prompt-structure checks; no live LLM), which is why they
are cheap enough to be CI-resident.

---

## 2. Findings table

| # | Severity | File:line | Evidence | Required fix / condition |
|---|----------|-----------|----------|--------------------------|
| F1 | **HIGH** | `src/repliclaw/benchmarks/rcaeval/manifest.py` (`STRATUM_COLUMNS`, `build_heldout_manifest`); `data/cases.parquet` | `cases.parquet` (29KB, 735×22, sha `c49a2889…`) **contains per-case ground truth**: `root_cause_service` (the true root-cause service) and `fault` (fault type). `select_heldout_cases` stratifies **by** `root_cause_service`, and `build_heldout_manifest` copies `root_cause_service` + `fault_type` into `CaseManifest.strata`. The module comment's *"stratum axis, not a label"* framing is contestable: for `root_cause_service` the stratum axis **is** the ground-truth answer. | Gate the heldout manifest (file + `strata`) to **scorer-only access** at G4 freeze; agents must never receive the manifest/strata while solving. Disclose `root_cause_service`-stratification in the prereg. `select_heldout_cases` correctly never reads `fault_description` (verified by code read), so the *selection* is label-mask-safe; the exposure is purely the *written manifest*. |
| F2 | **MEDIUM** | `tests/experiments/test_v3_ceq_no_fixed_script.py` (`FORBIDDEN_LITERALS`) | The literal list covers `I_R_retrieval_fix`, `I_P_policy_conflict`, `I_J_judge_fix`, `policy_rag_v1`, `retrieval_omission`, `load_oracle`, `true_cause`, `oracle` + the `H_R/H_P/H_J/CASE_ID` checks. Constructed slip-throughs that contain **zero** forbidden literals yet are fixed scripts: (a) arm ids `I0_baseline` and `I_C_retrieval_judge` are absent; (b) 5 of 6 defect classes (`data_error`, `generation_error`, `judge_stale`, `none`, `policy_conflict` as a literal) are absent — only `retrieval_omission` is listed; (c) index-based scripts (`sorted(self.interventions)[k]`, `changed_factors[0]`, position-based diagnosis) are literal-free by construction. | Either extend `FORBIDDEN_LITERALS` to **all 5 arm ids** and **all 6 defect classes**, or add an explicit comment + design-doc rationale documenting that the list is an intentional *detectable-canary subset*, not a completeness proof (the runtime adaptivity test already proves the *fake* script can be conditioned on evidence; it does not prove the real planner has no hidden ordering). |
| F3 | **MEDIUM** | `src/repliclaw/experiments/v3/ceq.py` L118 (docstring) vs tests | Module docstring claims the `PROMPT_VOLUME_CEIL=1.25` / `FLOOR=0.6` band was *"calibrated against frozen planner/final-diagnosis prompt templates (the templates are sha-pinned at prereg time)."* **No test pins any prompt-template SHA.** `grep sha256` over the 4 test files finds only `obs_id` computation. The `CEQ_PLANNER_DECISION` template marker literal occurs exactly once in `ceq.py` (a valid pin target), but nothing freezes it. Until the pin lands, `1.25` is an **asserted constant with no calibration test** — the anti-starve assertion is therefore only partially independent (see F5). | Before V3 prereg freeze: add a test that hashes the exact planner-decision + final-diagnosis prompt templates (e.g. `sha256` of the `CEQ_PLANNER_DECISION` template string) and asserts the `0.6..1.25` band was calibrated against that hash. This makes the canary two-sided *and* reproducible. |
| F4 | **LOW** | `tests/experiments/test_v3_ceq_parity.py` (test 6) | The design doc §5.3 promised the manager sees *"exactly the same set of `evidence_id=` lines"* as a D-E investigator would at the matching point. Test 6 verifies **timing only** (no `evidence_id` before the first run; an `obs` id first appears in planner prompt #2). It does not assert *content-equality* of the manager's evidence set against a D-E investigator's at the same step. The manager sees the **union of all 3 hypotheses'** evidence blocks (+baseline); each D-E agent sees own-hyp + baseline. That union is *disclosed* in design §4 and bounded by the F5 volume ceiling, so it is not covert — but the §5.3 equality claim is over-stated relative to what is actually tested. | Add a content-level assertion: at the first consult, the set of `evidence_id=` strings in the manager's evidence block equals the D-E investigator's (own-hyp) set, modulo the documented union-of-others delta. Or soften §5.3 wording to "superset of, and volume-bounded against." |
| F5 | **LOW** | `tests/experiments/test_v3_ceq_parity.py` (test 5, token canary) | The anti-starve assertion is `manager_vol + worker_vol >= de_total` **plus** `0.6 <= manager_vol/de_total <= 1.25`. These overlap (the floor on the manager-only ratio already implies a large chunk of the total), so the two-sidedness is only partial. Separately, `ceq.prompt_volume_ratio()` sums the **whole** dict passed in, while test 5 inlines a **manager-only** ratio — a minor semantic drift between the helper and the test. The remaining unproven claim ("1.25 is not a starve-tolerance in disguise") rests on the template calibration that F3 shows is not yet tested. | After F3's template pin lands, add an explicit sub-assertion that the *worker-side* contribution (consults) alone keeps the investigators from starving, independent of the manager ratio. Reconcile `prompt_volume_ratio()` helper vs the inlined manager-only ratio (pick one source of truth). |
| F6 | **LOW** | `src/repliclaw/eess_live/orchestrator.py` (`_execute`) vs `ceq.py` (run_cache) | Undisclosed behavioral deltas between C-EQ and D-E: (a) D-E can **retry a failed need** in a later cycle (re-executing a hash-mismatched intervention); C-EQ caches failed verifies in `run_cache` → effectively no retry. (b) D-E checks per-agent `max_cycles` / `_deadline_exceeded`; C-EQ relies on the token envelope only. Both are almost certainly immaterial (verify failures are engine-deterministic/rare), but they are not documented. | Add a one-line note to the design doc's risk table (R-section) listing these two deltas as intentional / immaterial, so a future parity reviewer isn't forced to rediscover them. |
| F7 | **LOW** | `src/repliclaw/benchmarks/agentrx/loader.py` (`DEFAULT_DATA_DIR`) | `DEFAULT_DATA_DIR` hardcodes the absolute local path `/Users/sushantgautam/Documents/stg2-worktrees/agentrx-data`. Correct on the author's machine (and the suite passes), but a provenance/portability hazard for any other runner. | Make the data dir an explicit required argument or an env-var with a clear error on missing, rather than a machine-specific default. Not a Wave-1 blocker. |

### Verified-positives (no action required)

| Item | Result |
|------|--------|
| **P08 legacy reproducibility (mandatory check d)** | **Behavior-identical.** `git show 9ae6fe1 -- src/repliclaw/comparators/runner.py src/repliclaw/eess_live/arm.py` = +24/−5: `runner.py` extracts an inline `write_text` into the shared `write_run_metadata()` (byte-identical: `json.dumps(..., indent=2, sort_keys=True)`); `arm.py` retypes `write_counterfactuals` from `LiveEESSOrchestrator` to a `_RunCacheHolder` Protocol and adds an inert `self._orch = orch`. `git diff 5a7833f 99eb764 --stat -- eess_live/ comparators/ needmarket/ slice/` confirms these are the **only** legacy-path changes in Wave 1. The four "P08 arm bug fixes" (evidence-block union, `n_investigators`, void-arm budget recording, S-I escrow) are **all new code in `ceq.py`** — they do not touch the legacy arm path. A future P08 re-run reproduces. |
| **AgentRx fail-loud (mandatory check)** | **Works.** Scratch tamper test (in `judge-code-w1`): a single-byte tamper of a `tau_retail.jsonl` copy → `DatasetHashMismatchError` raised on load. Untampered load → 73 cases, with the **14 unannotated** magentic rows excluded (verifiable via the `EXPECTED_COUNTS` raw−annotated set-difference assertion). |
| **AgentRx `normalize_category` (mandatory check)** | **Verbatim copy.** Behavioral diff vs `agentrx@7a18c797 …/reports/analyze_metrics.py:47-76` across 18 test inputs = **0 diffs**. Upstream has no `NO_ERROR` sentinel; the judge-side sentinel is correctly excluded from the parity claim. |
| **RCAEval label-mask invariance (mandatory check)** | **Real.** `test_label_mask_invariance` masks non-stratum columns to `NaN` + `MASK_i` + a shuffled `fault_description`, calls `select_heldout_cases`, and asserts identical selection across 3 masking variants. `select_heldout_cases` never reads `fault_description` (verified by code read). |
| **`data/cases.parquet` (mandatory check)** | **29KB canonical index, correct hash.** 735 rows × 22 cols, 29500 bytes, `sha256 = c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb` (matches `CASES_PARQUET_SHA256`). It is the index, not the full dataset. (It does contain `root_cause_service`/`fault` — see F1.) |
| **No restricted data / secrets** | Grep over the new benchmark files finds **no** keys/tokens/secret patterns (the only `sk-` hits are the substring in "label-**mask**-safe"). The committed parquet is the 29KB index only. |

---

## 3. C-EQ information-asymmetry audit (highest-value question)

**Question (a): is there ANY path where the manager gets information the
decentralized investigators don't — timing, extra observations, retry of failed
interventions, knowledge of the investigators' hypotheses — that the parity
tests don't catch?**

Read `ceq.py` in full (1113 LOC). Findings:

1. **Evidence union (the real asymmetry — disclosed, volume-bounded, timing-tested
   but not content-tested).** The manager's planner sees `_evidence_block_union`
   — the **union of all three hypotheses'** evidence blocks plus baseline. Each
   D-E investigator sees **own-hypothesis + baseline** only. This is *disclosed*
   in design §4 ("the manager owns all hypotheses") and bounded by the `0.6..1.25`
   volume canary, so it is not a covert channel. **Gap:** parity test 6 checks
   **timing**, not the content-equality promised by §5.3 → **F4**.

2. **Retry of failed interventions.** D-E's `_execute` can re-run a
   hash-mismatched intervention in a later cycle; C-EQ's `run_cache`
   de-duplicates it (no retry). Behavioral delta, almost certainly immaterial,
   **undisclosed** → **F6**.

3. **Per-agent wall-deadline / max-cycles.** D-E enforces `max_cycles` and
   `_deadline_exceeded` per agent; C-EQ enforces only the token envelope.
   Behavioral delta, immaterial, **undisclosed** → **F6**.

4. **`producer_id` = "manager" vs D-E's proposer agent id** — cosmetic, no
   informational advantage.

**No covert timing leak was found:** the escrow opens, one sealed manager packet
is escrowed *before* any run, the planner loop (≤4 rounds) never receives an
`evidence_id` before the first run is executed (test 6), and consults happen
**after** the planner loop with `CONSULT_CAP_PER_CASE=1` so investigator outputs
cannot feed planner decisions. The manager does not receive knowledge of which
hypothesis any *specific* investigator holds — it sees the union of the three
*pre-declared* hypothesis evidence blocks, which is the arm's intended design,
not a leak.

**Question (b): does the no-fixed-script static test's literal list cover the
risk, or only a subset? — Construct a slip-through.**

It covers **only a subset** → **F2**. A fixed script that slips past it
(containing none of `I_R_retrieval_fix`/`I_P_policy_conflict`/`I_J_judge_fix`/
`policy_rag_v1`/`retrieval_omission`/`load_oracle`/`true_cause`/`oracle`/
`H_R`/`H_P`/`H_J`/`CASE_ID`):

```python
# Fixed script, zero forbidden literals, still a fixed script:
def plan(self, history):
    order = ["I0_baseline", "I_C_retrieval_judge"]   # arm ids not in the list
    return order[min(len(history), len(order) - 1)]
def diagnose(self, history):
    return "none"                                     # defect class not in the list
```

Index/position-based selection (`sorted(self.interventions)[k]`,
`changed_factors[0]`) is likewise literal-free. The static test is a
**canary detector, not a completeness proof**. Recommend either broadening the
list to all arm ids + defect classes, or documenting the subset rationale (F2).

**Question (c): is `1.25` a starve-tolerance in disguise? Is the anti-starve
assertion independent? — F3 + F5.**

The docstring claims the `0.6..1.25` band is calibrated against **SHA-pinned
frozen prompt templates**. **No such SHA pin exists in the test suite** (only
`obs_id` hashes are present). Until the template pin lands, `1.25` is an
asserted constant with no reproducible calibration — so the ceiling's
legitimacy is currently *unproven*, not just undocumented. And the two-sided
canary's two assertions overlap (FLOOR on the manager ratio + total ≥ D-E),
so independence is partial. The fix is the template pin (F3) plus an explicit
worker-side anti-starve sub-assertion (F5).

**Question (d): do the four P08 arm bug fixes change P08 ARM BEHAVIOR? —
See verified-positives.** No. All four fixes are new `ceq.py` code; the legacy
arm path is byte-behavior-identical (only the inert `write_run_metadata`
extraction and a Protocol retyping touched `runner.py`/`arm.py`). A future P08
re-run reproduces; **no gating behind the V3 registry is required** because the
legacy path was not changed.

---

## 4. Recommended conditions (blockers before V3 prereg / G4)

1. **(F1, HIGH)** At G4 freeze, restrict the heldout manifest (file +
   `CaseManifest.strata`) to **scorer-only** access and disclose
   `root_cause_service`-stratification in the prereg. This is the governing
   "scorer must be the only reader of per-case root-cause labels" rule.
2. **(F3, MEDIUM)** Land the planner/final-diagnosis **prompt-template SHA pin**
   test and tie the `0.6..1.25` band to it, so `1.25` is a calibrated canary,
   not an asserted constant.
3. **(F2, MEDIUM)** Broaden `FORBIDDEN_LITERALS` to all arm ids + defect
   classes, or document the intentional-subset rationale in the design doc.

F4/F5/F6/F7 are low-severity and can be tracked as follow-ups; none blocks
integration. Scratch probe artifacts were removed from `judge-code-w1`.
