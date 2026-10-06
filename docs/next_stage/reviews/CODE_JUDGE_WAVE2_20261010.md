# CODE JUDGE — Stage-2 Wave 2 (INDEPENDENT) — 2026-10-10

**Judge:** J-CODE W2 (did not author any code under review; read-only)
**Dev worktree:** `/Users/sushantgautam/Documents/RepliClaw-stg2-dev` @ `51ded8b`
**Scope:** W2b (`a9f353d`), W2c (merge after `a9f353d`, `358cc08`/`2e814be`), W2a (`a06f764`), W2g (`51ded8b`)

Status: UNCOMMITTED — for integrator to commit.

---

## 1. Verification commands (actual output, run by this judge)

venv: `/Users/sushantgautam/Documents/ScienceClawHackathon/.venv/bin/python`

| Command | Result |
|---|---|
| `pytest tests/ -q` | **384 passed, 8 skipped, 3 xfailed in 51.18s** (0 failed) |
| `pytest tests/ --tb=no -rXx` | exactly 3 XFAIL lines: `test_module_docstring_documents_case_id_service_embedding`, `test_full_forbidden_set_absent_from_all_artifacts`, `test_replay_determinism_final_verdict_byte_strict` — all match the documented W2a xfail set |
| `mypy src/repliclaw/` | **Success: no issues found in 77 source files** |
| `ruff check src/ tests/` | **Success: no issues found in 77 source files** |
| `shasum -a 256` cluster_bootstrap.py (dev) vs `stg2-worktrees/statistics/cluster_bootstrap.py` | **byte-identical**: both `e14d28add0ceb27bdef73daab268bf07041bd857d34ebd477e2793e0aa96258c` ✔ |
| `pytest tests/benchmarks/test_l5_pin.py tests/benchmarks/test_ground_truth_gate.py` | 11 passed |
| Secret scan of W2g added lines (`git diff a06f764 51ded8b -- \| grep ^+` for `sk-3`, `sushant`, `pp.ua`) | no real key; no real base URL added. W2g files use env vars only (`SIMULACHAT_BASE_URL`/`SIMULACHAT_API_KEY`), `example.test`/`sim.test` placeholders in tests |

---

## 2. W2b — C-SCI-1 scorer-only ground-truth gate (a9f353d)

Files: `src/repliclaw/benchmarks/common/gating.py` (+118), `rcaeval/manifest.py` (+24), `tests/benchmarks/test_ground_truth_gate.py` (+163).

Good:
- Single sanctioned resolve path (`ScorerContext.resolve`) with per-call audit entry; `heldout_ground_truth` wraps it; the resolve path is evaluator-only.
- Static caller-restriction scan (`test_static_caller_restriction_scan`) greps all of `src/repliclaw/` for `heldout_ground_truth|ScorerContext|assert_no_agent_access` outside an explicit 2-file allowlist — real enforcement, and I independently confirmed the scan target is satisfied (the only `root_cause_service` mentions in `src/` are `gating.py` docstring and `rcaeval/manifest.py`).
- `heldout_ground_truth` is NOT exported via `benchmarks/rcaeval/__init__.py`; test pins this.
- Tests use synthetic service names only — no real RCAEval label values in test source (not a label-peek surface).
- Manifest round-trip stays pointer-only.

Findings:

**F-W2-3 (MED)** — `src/repliclaw/benchmarks/rcaeval/manifest.py:230` `heldout_ground_truth` constructs a **fresh `ScorerContext` per call and discards it**, so every resolve's `ResolveAuditEntry` is destroyed with the context. The "audited resolve" guarantee leaves no surviving audit trail for the actual production path; only test-held contexts show audits. Required fix: accept/return a caller-owned context (or append to a persistent audit ledger) so `resolve` calls via `heldout_ground_truth` accumulate somewhere inspectable. Not G2-blocking (the access-restriction property itself holds; audit is a soft guarantee) but a hostile reviewer will catch "audited" with zero persistent audit.

**F-W2-4 (LOW)** — W2b merge commit says "8 tests"; `test_ground_truth_gate.py` has 6. Commit-message/test-count mismatch; correct the message at next integrator checkpoint.

---

## 3. W2c — C-SCI-2 L5 statistics pin (358cc08 / 2e814be)

Files: `common/cluster_bootstrap.py` (+61), `common/power_pin.py` (+93), `tests/benchmarks/test_l5_pin.py` (+106).

Good:
- **Byte-identity verified by this judge** (shasum match, §1). `test_pinned_cluster_bootstrap_sha256` re-hashes the in-repo file and asserts the same digest, plus `verify_cluster_bootstrap_pin`.
- Frozen constants (B=10000, PCG64 seed 20261009, percentile 95%, linear) asserted against both `cluster_bootstrap` module constants and `power_pin` constants; RNG construction asserted to be PCG64.
- `test_frozen_self_test_constant` computes the CI **live** on a fixed 24-case input (bit-exact under numpy 1.26.4 and 2.4.6 per the documented cross-check) — stronger than asserting the constant alone.
- Tamper test proves `verify_power_pin` raises `PowerPinError` on a mutated copy.

Findings:

**F-W2-5 (MED)** — `power_pin.py` pins the Monte-Carlo grid generator by sha256 to an **uncommitted scratch file at a machine-specific absolute path** (`/Users/sushantgautam/Documents/stg2-worktrees/statistics/monte_carlo_power.py`). The frozen bytes are therefore NOT reproducible from the repo: the generator's source is outside git, and `test_verify_power_pin_real_scratch` **silently skips** on any machine without that directory (including CI/another operator). A hostile reviewer reads this as "the power grid's code of record is a file on one laptop." Required fix: either commit the frozen generator into the repo (it is small) with the sha pin in-repo, or record the sha256 AND copy its bytes into a git-tracked provenance artifact; at minimum, make the skip explicit in every run summary. Not G2-blocking (the pinned L5 *inference* code is fully in-repo and bit-pinned; only the one-shot grid *generation* is scratch-pinned, and the grid results are already recorded).

---

## 4. W2a — G2 offline canaries (a06f764)

Files: `tests/experiments/test_v3_g2_canaries.py` (+370), `tests/benchmarks/test_rcaeval_leak.py` (+134). Suite: **9 pass + 3 strict xfail** — confirmed by `-rXx` output (§1). All offline (FakeLLMClient, frozen case data, tmp_path); no network/LLM.

**Scrutiny of the 3 xfails — each verified by this judge to actually FAIL without the marker** (run directly against the real code, seed 20261010):

| xfail | Judge reproduction (marker removed, assertion executed) | Honest? |
|---|---|---|
| (a) `test_full_forbidden_set_absent_from_all_artifacts` (oracle-set over-artifact scan) | Assertion **fails**: 31 artifact files carry full-set tokens (intervention ids, `policy_rag_v1`, case id, defect classes) across `counterfactuals/`, `escrow/`, `runs/` on both arms. | **Honest.** The strict-xfail pins that a zero-occurrence claim over the *full* derived set would be a *wrong* canary (those tokens are the arms' own menu vocabulary in a scripted-fake run), and it states what to do if it ever XPASSes (re-derive the split). The real guarantee — oracle vocabulary (`true_cause`/`load_oracle`/`oracle`) absent from **all** artifacts of **both** arms — is carried by `test_oracle_tokens_absent_from_all_artifacts`, which **passes**. Not disguised weakening: the strengthening direction is pinned by the passing test; the xfail is a tripwire. Residual: in a LIVE run, defect-taxonomy values in agent-visible artifacts would be indistinguishable from this scripted-fake baseline; the oracle-token set is the defense. |
| (b) `test_replay_determinism_final_verdict_byte_strict` (final_verdict wall_s) | Assertion **fails**; the ONLY differing key between two replays is `wall_s` (0.131995 vs 0.059277). All other fields byte-stable. | **Honest.** The companion test `test_replay_determinism_final_verdict_and_counterfactuals` enforces byte-identity on counterfactuals and content-identity on final_verdict modulo `wall_s` — and passes. Reason string is precise (names the exact field and its nature). Note: `run_metadata.json` start/end_ts are also wall-clock (acknowledged in the xfail text) but no modulo-timestamp test pins that file — see F-W2-7. |
| (c) `test_module_docstring_documents_case_id_service_embedding` (rcaeval manifest docstring) | Assertion **fails**: current `rcaeval/manifest.py` module docstring contains neither "embed" nor "opaque" (verified directly). | **Honest tracked gap** — BUT see F-W2-6: the same wave (W2b) already edited this exact docstring and could have closed it. |

Verdict on xfail scrutiny: **no disguised test-weakening.** All three are `strict=True`, each has a specific reason, each was independently re-proven to fail, and each names its passing counterpart that carries the real guarantee.

Findings:

**F-W2-6 (MED)** — W2b's `manifest.py` docstring edit (`a9f353d`) added a C-SCI-1 paragraph but did NOT add the upstream case-id service-embedding fact + opaque-id runtime requirement that xfail (c) tracks. A hostile reviewer will ask: the wave that touched this docstring left a same-wave-tracked documentation gap open. Required fix: two sentences in the module docstring (the schema `case_id` note already has the wording to copy), then remove the xfail. Cheap to close now.

**F-W2-7 (LOW)** — (i) No modulo-timestamp replay test for `run_metadata.json` (xfail reason mentions its wall-clock fields; untested). (ii) `test_reset_into_existing_out_root_fails_loud_and_preserves` correctly pins that rerun-into-existing-out_root **fails** with `DuplicateCommitment` — but that pinned "behavior" is an operational gap in `ceq.py` (no out_root reuse/resume path; only P08 replay). It is honestly documented in the test docstring; carry it as a follow-up ticket rather than treating it as acceptable-by-design at G4.

---

## 5. W2g — SimulaChat provider wiring (51ded8b / 49ff077)

Files: `agentrx/simula.py` (+306), `agentrx/agentrx_patch.py` (+317), `scripts/agentrx_simula_smoke.py` (+122), `tests/test_agentrx_simula_client.py` (+227, 13 offline tests), `agentrx/__init__.py`, contract doc update.

### 5.1 Secret hygiene (scanned ALL added lines of the diff)

- **Real key `sk-3…`: NOT present** in any committed code, test, or doc (repo-wide grep; W2g added lines grep). Tests use `sk-test-key`/`sk-env` placeholders only. Clean.
- **Real base URL `https://simulachat.sushant.pp.ua/api/v1`: NOT added by any Wave-2 diff hunk** (W2g files use `"<host>/api/v1"` placeholders and env vars). **However**, the URL is present verbatim in PRE-EXISTING committed files: `src/repliclaw/investigators.py:25` (`DEFAULT_BASE_URL` default), `docs/experiments/PREREG-2026-10.md:163`, `docs/experiments/PREREG-2026-10-v1.1.md:224`, `docs/PI_MODELS_TEMPLATE.json:4` — the latter committed on the **public main branch** (`7591195`). Per the review rubric, verbatim committed base URL is a CRITICAL exposure, even though Wave 2 did not introduce it.

**F-W2-1 (CRITICAL)** — `src/repliclaw/investigators.py:25`, `docs/PI_MODELS_TEMPLATE.json:4`, `docs/experiments/PREREG-2026-10.md:163`, `PREREG-2026-10-v1.1.md:224`: the real SimulaChat base URL is committed verbatim, including on public main. Provenance: pre-existing (not a Wave-2 regression; Wave-2 diff hunks are clean). Problem: the endpoint location for the human-authorized private LLM provider is disclosed in the repo; a hostile reviewer (or anyone with repo access) learns the live endpoint. Required fix: scrub to env-var-only configuration (`REPLICLAW_LLM_BASE_URL` with no hardcoded default, or a `localhost` placeholder), redact the PREREG docs ("the P03-verified endpoint, see env of record"), rotate/none (URL is not a credential, but the disclosure stands), and note the scrub in `DECISIONS.md` with date. **Blocks G2** only in the sense that G2 artifacts cite this endpoint; integrator must decide (scrub vs. explicit documented decision that the URL is non-sensitive) before G2 sign-off.

### 5.2 Monkeypatch approach (`agentrx_patch.py`)

Good:
- No upstream file on disk is ever written (in-memory attribute patching of the pinned read-only checkout at 7a18c797 — verified against the checkout's seam locations: `pipeline/globals.py:61-70`, `judge/judge.py:1088-1089,1831`, `run.py` stage functions).
- `SimulaPatchState.undo()` exists and the smoke script calls it in `finally`.
- `CALLS_SERVED` records every factory/completion with real token usage — token provenance is auditable.
- Judge routing preserves AgentRx's own `get_llm_judge_class` logic verbatim and only swaps the transport (try/finally restores `copilot_mod.LLMAgent`/`ENDPOINT_USED` around the class build).

Findings:

**F-W2-2 (MED)** — `agentrx_patch.py:247-250` `undo()` performs `import run as run_py` (and `import agentrx.ir.trajectory_ir`) at the **top of the function, outside any try/except**, before any restoration. If `run.py` is not importable at undo time (different cwd than at apply, or `run.py` was importable at apply but the process moved), `undo()` raises `ImportError` **before restoring anything**, leaving the process still patched. Consequence for a later official run: any in-process AgentRx pipeline call would still route `trapi_mk_client`/`copilot_mk_client` to `_serve` (SimulaChat) — silently, with no model-substitution label, i.e. exactly the corruption mode the review rubric asks about. Contained today (smoke script runs apply+undo in one process at the AgentRx root), but it is a landmine. Required fix: make `undo()` best-effort and idempotent — wrap the imports in try/except ImportError, restore each attribute in independent try/except, and raise a single summary error only after attempting all restorations. Non-G2-blocking (no live G2 run uses it) but must be fixed before any G4 live-run script reuses this module in a long-lived process.

**F-W2-8 (MED)** — No pin-integrity pre-check in `apply_simula_patch`: it does not verify the checkout is actually agentrx@7a18c797 (no git HEAD/sha check) and does not `hasattr`-verify the four client-factory seams it rebinds (only the `run.py` stages are `hasattr`-guarded). A drifted or mis-checked-out upstream would either fail obscurely or — worse — silently not be patched, letting a real `copilot`/`azure`/`trapi` client be used while metadata says `endpoint: simulachat`. Required fix: at apply time, assert the checkout commit (e.g. read `.git/HEAD` against the pinned sha, or a marker), and `hasattr`-fail-loud on each seam before rebinding.

**F-W2-9 (LOW)** — `_EndpointChoice.__hash__` is a constant `hash("simula-choice")`; if that value ever lands in a dict/set alongside other endpoint strings it silently collides. Unused today (argparse `in`/`==` path only); either hash by `str(self)` or document the hazard.

### 5.3 Model-substitution label enforcement

`MODEL_SUBSTITUTION_LABEL` is exact-string tested; `stamp_model_substitution_metadata` merges (never weakens) `state.json` and sets `official_baseline: false`. The one real run's artifacts are stamped correctly (verified `w2-simula/.artifacts/agentrx/simula_tiny_smoke/state.json`: label present, `official_baseline: false`, real token usage 21,460).

**F-W2-10 (MED)** — The label is **stampable but bypassable by construction**: nothing in the patched pipeline writes the label automatically; it is mandatory only by doc. A script that calls `apply_simula_patch` and runs AgentRx without calling `stamp_model_substitution_metadata` produces a full unlabeled run whose artifacts look official except for the `llm_provenance` stamp being absent (not contradicted). Required fix: enforce in code — e.g. `_serve()`/the routed factories require a pre-registered run_dir and stamp `state.json` themselves, or the patch state refuses to serve completions until `stamp_model_substitution_metadata` has been called for the active run_dir. Before G4 live runs this must be mechanical, not documentary.

### 5.4 Smoke result honesty (1/2)

- Actual artifacts: `summary.json` shows `Correct cases: 1, Incorrect cases: 1` → **1/2 root-cause-correct; the EXECUTION_STATE claim "1/2 root-cause correct, 21.4K tokens" matches the artifacts exactly.** The "1/2" number is honestly scoped and reproducible from the artifacts. ✔
- **F-W2-11 (MED)** — Coverage overclaim: contract §9 status-change (line 155) says the wiring makes "the **full official pipeline** (IR→static→dynamic→check→judge→report) **runnable** against SimulaChat". The executed smoke covered **judge (1 iteration, 2 trajs) + hand-written LLM-free tau IR only** — `static`/`dynamic`/`check` were never executed, and the smoke's IR path (`load_trajectories`/`tau_bench_ir`) does not even invoke the patched `llm_ir`. "Runnable" is unverified for 3 of 6 stages. Required fix: either run a one-stage smoke for static/dynamic/check (they are cheap, single-stage runs) or rewrite the contract line to "judge stage + LLM-free IR executed; static/dynamic/check wiring in place, unexecuted." A hostile reviewer comparing the claim to the artifacts will catch this.
- **F-W2-12 (LOW)** — `summary.json` (AgentRx's own writer) reports `total_tokens: 0 / total_execution_time_sec: 0.0` while the stamped `state.json` reports 21,460 real tokens. The two token records in the same run dir disagree in appearance; add a note in `state.json` (or the contract) that AgentRx's summary writer does not capture usage and that `simula_run_extra.real_token_usage` is the record of truth.

---

## 6. Findings table (G2 impact)

| ID | Sev | File:line | Problem (one line) | Required fix | Blocks G2? |
|---|---|---|---|---|---|
| F-W2-1 | CRITICAL | investigators.py:25; PI_MODELS_TEMPLATE.json:4; PREREG-2026-10.md:163; PREREG-2026-10-v1.1.md:224 | Real SimulaChat base URL committed verbatim (pre-existing, incl. public main) | Scrub to env-only / redact docs / decide-sensitivity + DECISIONS.md note | **Yes** (integrity/sensitivity decision before G2 sign-off) |
| F-W2-2 | MED | agentrx_patch.py:247-250 | `undo()` import outside try/except can abort before any restore → process left patched (silent SimulaChat routing of a later official run) | Best-effort idempotent undo, per-attribute try/except | No (fix before any G4 live script) |
| F-W2-3 | MED | rcaeval/manifest.py:230 | Per-call `ScorerContext` in `heldout_ground_truth` discards the audit log — "audited" path leaves no surviving audit | Caller-owned context or persistent audit ledger | No |
| F-W2-4 | LOW | commit `a9f353d` message | "8 tests" vs actual 6 in test_ground_truth_gate.py | Correct count at next checkpoint | No |
| F-W2-5 | MED | power_pin.py:41-44 | MC grid generator pinned by sha256 to uncommitted scratch file on one machine; verification test silently skips off-machine | Commit generator bytes into repo/provenance artifact; make skip explicit | No |
| F-W2-6 | MED | rcaeval/manifest.py docstring | W2b edited the docstring but left the xfail-tracked service-embedding/opaque-id gap open | Two sentences added + drop xfail (c) | No (cheap, do before G2) |
| F-W2-7 | LOW | test_v3_g2_canaries.py | run_metadata.json replay modulo-timestamps untested; out_root reuse failure is a real operational gap pinned as behavior | Add modulo-timestamp test; file follow-up ticket for resume path | No |
| F-W2-8 | MED | agentrx_patch.py:137-170 | No checkout-sha / seam-existence pre-check — drifted upstream could patch nothing silently | Assert pinned commit + hasattr-fail-loud on each seam | No (before G4 live runs) |
| F-W2-9 | LOW | agentrx_patch.py:66 | `_EndpointChoice.__hash__` constant — latent dict/set collision | Hash by `str(self)` or document | No |
| F-W2-10 | MED | agentrx_patch.py / smoke script | Model-substitution label mandatory by doc only — pipeline runs unlabeled if `stamp_model_substitution_metadata` is skipped | Enforce stamp in `_serve`/patch state | No for G2; **must be mechanical before any G4 live run** |
| F-W2-11 | MED | agentrx_contract.md:155 | "Full official pipeline runnable" overclaims — only judge + LLM-free IR were executed (static/dynamic/check unexecuted) | Run one-stage smokes or reword claim to executed scope | No |
| F-W2-12 | LOW | smoke `summary.json` vs `state.json` | 0 tokens in summary vs 21,460 in state — appearance conflict | Note in state.json/contract which record is truth | No |

### xfail scrutiny verdict (W2a)
All 3 xfails are **honest tracked findings, not disguised weakening**: each `strict=True`, each independently re-proven to fail by this judge with the marker removed (31-file token hits; single-key `wall_s` diff 0.131995 vs 0.059277; docstring lacks both required facts), each names its passing counterpart that carries the real guarantee, and each documents the XPASS-resolve procedure.

---

## 7. VERDICT

**APPROVE-WITH-CONDITIONS**

Conditions:
1. **F-W2-1 (CRITICAL):** integrator must resolve the committed base-URL exposure before G2 sign-off — scrub/redact the four pre-existing locations (or record an explicit human decision that the endpoint URL is non-sensitive) with a DECISIONS.md note. Wave-2 diff itself is clean.
2. **F-W2-6:** close the manifest docstring gap (two sentences) and drop xfail (c) — same wave touched the file; leaving it open is a visible process gap.
3. **F-W2-11:** reword or extend the contract §9 "full pipeline runnable" claim to match executed evidence (judge + LLM-free IR).
4. **F-W2-2, F-W2-8, F-W2-10:** must be fixed (code-enforced label, fail-loud seam checks, safe undo) before any G4 live-run script reuses `agentrx_patch` — not G2-blocking.
5. Remaining MED/LOW (F-W2-3, F-W2-5, F-W2-7, F-W2-9, F-W2-12) tracked as follow-up tickets.

### Per-branch status
- **W2b (a9f353d):** PASS — gate + static caller scan solid; MED: discarded per-call audit (F-W2-3); LOW: test count (F-W2-4).
- **W2c (358cc08/2e814be):** PASS — byte-identity verified; MED: scratch-pin portability gap (F-W2-5).
- **W2a (a06f764):** PASS — 9 pass + 3 honest strict xfails, all re-verified; MED: docstring gap W2b could have closed (F-W2-6); LOW: F-W2-7.
- **W2g (51ded8b):** PASS-WITH-CONDITIONS — no key/URL in diff hunks; MED: undo landmine (F-W2-2), missing seam/pin checks (F-W2-8), bypassable label (F-W2-10), coverage overclaim (F-W2-11); CRITICAL inherited from pre-existing committed URL (F-W2-1).
