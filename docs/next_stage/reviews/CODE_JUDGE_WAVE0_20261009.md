# CODE JUDGE — WAVE 0 REVIEW (J-CODE)

- **Reviewer**: J-CODE (independent Code Judge; wrote none of this code)
- **Date**: 2026-10-09
- **Worktree**: `/Users/sushantgautam/Documents/RepliClaw-stg2-dev` @ `a8e2b0e725bb6eb1c106d975663c1de0ee188f56` (branch `dev`, verified `git rev-parse HEAD`)
- **Scratch (judge-owned)**: `/Users/sushantgautam/Documents/stg2-worktrees/judge-code/`
  - `adversarial_validation.py` — 41 adversarial schema/validator cases
  - `adversarial_resume.py` — 17 state-machine + records probes

---

## VERDICT: **APPROVE-WITH-CONDITIONS**

The shared benchmark infrastructure is solid, adversarially resistant at the
dataclass layer, and the state machine is correct. All 4 git SHA pins and every
file hash I could recompute verify byte-for-byte. No secrets in any deliverable.
Conditions below must be closed before G2: 1 doc-citation fix-up (M1), 2 schema
hardening gaps (M2), and 3 docstring consistency items (L1–L3).

---

## 1. ACTUAL test / lint output

```
$ /Users/sushantgautam/Documents/ScienceClawHackathon/.venv/bin/python -m pytest tests/ 2>&1 | tail -3
................................ssssssss................................ [ 70%]
........................................................................ [ 94%]
.................                                                        [100%]
297 passed, 8 skipped in 36.69s          (exit code 0)

$ /Users/sushantgautam/Documents/ScienceClawHackathon/.venv/bin/python -m pytest tests/benchmarks/ -q
................................................                         [100%]
48 passed in ~4s                        (exit code 0)

$ /Users/sushantgautam/Documents/ScienceClawHackathon/.venv/bin/ruff check src/ tests/
All checks passed!                    (exit code 0)
```

Test count claim "48 tests in tests/benchmarks/" is **accurate**:
12 (`test_common_provenance.py`) + 21 (`test_common_records.py`) +
15 (`test_common_resume.py`) = 48.

---

## 2. Adversarial probes I ran

### 2.1 Validator (41 cases, `adversarial_validation.py`)

38/41 behaved as the schemas intend. The 3 deviations are documented in
Findings F2/F3/F5 — none are exploitable through the dataclass API, but two
create gaps for raw-JSON consumers of the schemas.

**Verified rejects (all worked):** zero-filled usage with `usage_present=false`;
completed-with-abort_reason; aborted-with-empty abort_reason; `+02:00` and no-`Z`
timestamps; `seed=bool` / `seed=1.0` / `seed=-1`; negative tokens/wall_s; unknown
top-level and nested properties; wrong `schema` const; bad `run_id` pattern;
63-hex and uppercase provenance SHA; `wall_s` bool/str; empty tool names;
string tool counts; 8-hex `pinned_sha`; empty `data_hashes`; bad data hashes;
`repliclaw_git_sha: "unknown"`; 64-hex repliclaw SHA; non-Zulu `captured_at`;
8-hex upstream SHA; uppercase scorer metric.

**Verified accepts (correct per draft 2020-12):** 64-hex `pinned_sha`;
valid provenance; permissive scorer `allOf`; if/then with absent key (trivially
passes).

### 2.2 State machine + records (17 probes, `adversarial_resume.py`) — **all pass**

- `begin()` idempotent on running (attempts 1→2) ✓
- `begin()` on finished → `RunAlreadyFinished` ✓ (**double-open impossible**)
- `mark_finished(same payload)` → idempotent no-op ✓
- `mark_finished(different payload)` → `StateConflict` ✓ (**double-record impossible**)
- `mark_finished` before `begin` → `RunStateError` ✓
- record/state run_id mismatch → `RunStateError` ✓
- corrupt JSON state file → `RunStateError` ✓; wrong-schema and wrong-run_id
  state files → `RunStateError` ✓
- atomic write: no `*.tmp` leftover, final file valid JSON+`\n`, fresh-process
  reload sees finished state with `attempts=2` and round-trips the record ✓
- `RunRecord` round-trip incl. abort/tool/intervention fields ✓
- wrong schema string in `from_dict` → `ValueError` ✓
- `intervention_counts.by_kind` sum mismatch → `ValueError` ✓
- `TokenUsage` zero-fill guard ✓; `absent()` round-trip ✓; bool token count
  → `ValueError` ✓
- `ScorerOutput` unsorted `per_case` → `ValueError` at dataclass layer ✓

**Conclusion on the state machine: it is correct.** "No double-record of a
finished run" holds without caller-side bookkeeping, exactly as claimed in the
module docstring.

---

## 3. Findings table

| ID | Severity | Location | Evidence | Required fix |
|----|----------|----------|----------|--------------|
| F1 | **MEDIUM** | `docs/next_stage/design/ceq_arm_design.md:45` | Cites `EVIDENCE_FORBIDDEN_SUBSTRINGS` at `orchestrator.py:47`; actual definition is **line 59** (line 47 is `LEASE_TTL_S`). Same doc cites `orchestrator.py:47-56` (line 133) and `:47` (line 234) for the same constant. | Correct all three to the actual span (def at 59; enforcement loop at 141). |
| F2 | **MEDIUM** | `docs/next_stage/design/ceq_arm_design.md:55` | Cites `COMMIT_MARKER` `fake.py:26` / `VERDICT_MARKER` `fake.py:27`; actual: `COMMIT_MARKER` **line 28**, `VERDICT_MARKER` **line 29** (26 is an import, 27 blank). Same doc cites fallback payload at `fake.py:101-114` (line 293); actual `return json.dumps(` at **line 104** (101 is a comment). | Correct to `fake.py:28`, `fake.py:29`, `fake.py:104-…`. |
| F3 | **MEDIUM** | `docs/next_stage/design/ceq_arm_design.md:41, 90, 91` | Cites `_execute` at `orchestrator.py:306`; actual `def _execute` is **line 701** (line 306 is `__init__` body). Cites `case.sha256()` at `case.py:64` — actual `def sha256` is **line 64** ✓ but the decorator is 63 (acceptable); however `InterventionSpec.sha256` at `case.py:105` → actual def at **line 105** ✓. The `:306` error is the material one — off by ~395 lines. | Find the correct `_execute` reference (701) or reword; re-verify the two `case.py` lines against the final frozen file. |
| F4 | **MEDIUM** | `src/repliclaw/benchmarks/common/schemas/run_record.schema.json` (allOf #2) + `validation.py` if/then | Schema's aborted-branch `then: {properties: {abort_reason: {type: "string", minLength: 1}}}` does **not** fire when the `abort_reason` key is absent (my case 5: `aborted_budget` with no `abort_reason` key → **accepted**, expected reject). The `abort_reason` description promises "Required non-null iff status starts with 'aborted_'". Dataclass `RunRecord.__post_init__` catches this — but a raw-JSON scorer/ingest path bypasses it. | Either (a) add a `required: ["abort_reason"]` branch keyed on aborted statuses, or (b) explicitly document in the schema + `records.py` that the schema is a *subset* of the dataclass invariants and schema-only consumers must additionally run the dataclass load. |
| F5 | **MEDIUM** | `src/repliclaw/benchmarks/common/schemas/run_record.schema.json` (token_usage.allOf) | Symmetric gap: no branch for `usage_present=true` → null numerics is accepted by the schema (my case 3). The module docstring (P08 Q13 never-zero-fill) says the schema should forbid it. Dataclass catches it. Same scope decision as F4. | Same as F4: harden the schema (add inverse if/then) or document the subset relationship explicitly. |
| F6 | **LOW** | `src/repliclaw/benchmarks/common/provenance.py:123-140` (docstring) vs code 154-160 | Docstring claims "if a clone is unavailable only its URL is recorded and the SHA is filled in later via verify_provenance re-capture — capture itself never fails on an unreachable repo." **Code contradicts this**: any upstream pin with an unresolvable clone raises `ProvenanceError` (URL-only is not recorded at all). `verify_provenance` has no "fill in later" path. | Fix the docstring to match the actual fail-loud behavior (which is the correct behavior for this program). |
| F7 | **LOW** | `src/repliclaw/benchmarks/common/validation.py:108` `_equal` | `const 1` rejects `1.0` (`type(1) is type(1.0)` is False); official `jsonschema` **accepts** `1.0` for `const 1`. Impl is stricter than reference on int/float const — safe direction, but the module docstring claims "the two agree on this keyword subset", which is now technically false. | Add a one-line note in the docstring: "const/enum compare with strict Python type identity, so `1` ≠ `1.0` (stricter than `jsonschema`)". |
| F8 | **LOW** | `src/repliclaw/benchmarks/common/resume.py:56-70` `_atomic_write_json` | The docstring's atomicity claim covers file tear, but the directory fsync happens **after** `os.replace`. On a crash between rename and dir-fsync the new file is durable but the directory entry may be lost. Minor durability gap on macOS ext4/HFS+. | Move the dir fsync to before `os.replace` (write tmp, fsync, fsync dir, replace) or document the chosen tradeoff. |
| F9 | **LOW** | `src/repliclaw/benchmarks/common/records.py:386-395` + `scorer_output.schema.json` | `ScorerOutput.from_dict` enforces sorted `per_case` (raises), but the schema does not express it (my case 36: unsorted rows pass the schema). Dataclass-only invariant, same class as F4/F5. | Either encode a note in the schema description or fold into the F4/F5 "subset" documentation. |
| F10 | **INFO** | `src/repliclaw/benchmarks/common/resume.py` | No cross-process locking (two concurrent `begin()` on the same dir could interleave). The module docstring already states single-writer-per-run-dir is the lane design and cross-process safety belongs to the escrow ledger. | No fix required — noted for the record; keep the docstring as-is. |

---

## 4. Verification evidence per checklist item

### 4.1 Schema/validator correctness — DONE (§2.1)
See F4/F5/F7. The claimed keyword subset (`type`, `required`, `properties`,
`additionalProperties` false/object, `pattern`, `propertyNames`, `minLength`,
`minimum`, `minProperties`, `const`, `enum`, `allOf`, if/then/else, boolean
schemas) is implemented **correctly** for its stated draft 2020-12 semantics,
including the subtle `if`-with-absent-key case and strict bool/int exclusion.

### 4.2 records.py round-trip / fail-loud / never-zero-fill / Zulu — DONE (§2.2)
All 8 relevant probes pass. Zulu enforcement is at the schema pattern
`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$` on `started_at`, `finished_at`,
`captured_at`, `scored_at` — verified rejects for offset and missing-Z forms.
The Zulu shape is schema-enforced but **not** enforced in `RunRecord.__post_init__`
(a malformed string passes construction, fails `.validate()`); acceptable
since every writer path calls `validate()` before persist (provenance.py:186,
resume persists only validated records via the dataclass), but worth knowing.

### 4.3 Resume state machine — DONE (§2.2)
Correct. Atomic write is tmp+fsync+`os.replace`+dir-fsync (see F8 minor).

### 4.4 Contract docs SHA pins & file hashes — **ALL VERIFIED**

| Claim | Verified against | Result |
|---|---|---|
| AgentRx repo `7a18c79708e7671be15124460f4f7296107c2a55` | `git -C stg2-worktrees/agentrx-upstream rev-parse HEAD` (= agentrx-repo) | ✅ exact match, commit message/date match |
| `tau_retail.jsonl` `95729a0f…f49d1a9`, 29 records | `shasum -a 256` + JSONL parse | ✅ hash + count (29) |
| `tau_retail_dataset.jsonl` `21852996…fc7be`, 29 | same | ✅ (28 newlines but 29 records — final line un-terminated; parse count authoritative) |
| `magentic_one.jsonl` `9bfa562d…5187`, 44 | same | ✅ |
| `magentic_dataset.jsonl` `e2c697a9…b`, 58 | same | ✅ |
| `README.md` `2b29f657…ab5c` | same | ✅ |
| RCAEval repo `259ea4167160256a74ad30004aa3d96a998c846e` | `git -C stg2-worktrees/RCAEval rev-parse HEAD` | ✅ exact match, commit msg/date match |
| `pilot_manifest.json` `2d3075f4…5428e61` | `shasum -a 256` | ✅ |
| All 21 rcacal-hf files (table rows 85-105) | vs `rcacal-hf/sha256_cases.txt` + direct re-hash of 5 files | ✅ all 21 identical |
| Result `adservice_cpu_re1ob_adservice_cpu_1.json` `804fd7af…d06bbe` | `shasum -a 256` in `RCAEval-run/output/results/` | ✅ (dir has exactly 10 files as claimed) |
| AIOpsLab repo `ccf08d0d1d5fa5b30f120e2e8549662d44411b35` | `git -C stg2-worktrees/AIOpsLab rev-parse HEAD` | ✅ exact match, commit msg matches |
| Submodule `aiopslab-applications` @ `8038be6b4989c647126f27715acc591c47133c2d` | `git submodule status` + `.gitmodules` lines 2-4 | ✅ (uninitialized `-` prefix, SHA exact) |
| `actions/detection.py:18` `submit(has_anomaly)` | `sed -n 18p aiopslab/orchestrator/actions/detection.py` | ✅ exact line |

### 4.5 Secret scan — CLEAN
`grep -rniE "bearer |sk-[a-z0-9]{8,}|hf_[a-z0-9]{20,}|ghp_[a-z0-9]{20,}|api[_-]?key\s*[:=]"`
over all six deliverable areas returned **zero secret hits**. Only hits were
benign false positives (`submit(has_anomaly)` contains "has_a"; an existing
*science* judge report in `docs/next_stage/reviews/` — not a Wave-0 deliverable).
Both contracts explicitly state the HF token was never printed/committed.

### 4.6 ceq_arm_design.md citation audit — 49 citations checked programmatically
**43/49 accurate to the exact line.** 6 wrong (F1–F3 above):
`orchestrator.py:47` → actual 59 (×3 in doc), `orchestrator.py:306` → actual
701, `fake.py:26/27` → actual 28/29, `fake.py:101-114` → actual starts 104.
All other citations (arm.py, escrow.py, executor.py, case.py, packet.py,
budget.py, arms.py, runner.py, accounting.py, budget_calls.py, policy.py,
worker.py, defect_adjudication.py) verified exact.

### 4.7 Ground-truth leak paths — NONE FOUND
- `GroundTruthPointer` stores **pointer + optional sha only**, never content
  (records.py:183-200); schema description reiterates "Never embeds the content".
- `ceq_arm_design.md` line 169: oracle read is FORBIDDEN across all six arms;
  lines 211-214: static grep test (test 13) asserts `oracle`/`true_cause`/
  `load_oracle` are absent from `ceq.py`; `redact_claim_for_arms` applied to
  every arm prompt (line 99).
- R6 (line 293) explicitly acknowledges the `FakeLLMClient` fallback
  leakage risk and mandates `offline: true` labeling + report-generator
  refusal of fixture rows — the one real leak vector is identified and
  mitigated by design.
- Contracts describe GT locations for evaluator use only; no GT content is
  inlined in any doc (rcaeval names columns like `root_cause_service`
  as dataset metadata, which is the dataset's own structure, not a leak).

### 4.8 statistical_protocol_v3.md
Status header correctly marks it **DRAFT / NOT PREREGISTERED / not signed
off** with a no-authorization-until-frozen clause (§9 dual-sign). Unit-of-
inference (case, not rollout) and ITT scoring are internally consistent with
the arms defined in the design doc. (Deep scientific review is the Science
Judge's scope; flagged only that it references companion
`EXPERIMENT_PROTOCOL_V3_DRAFT.md`, which is not among the six reviewed
deliverables.)

---

## 5. Conditions for G2 (blocking)

1. **F1–F3**: fix the 6 wrong line citations in `ceq_arm_design.md` and re-run
   the citation check; the `:306`→701 error is a real pointer, not drift.
2. **F4/F5**: close the if/then absent-key schema gaps — either harden the
   `run_record` schema (add `required` branches) or add an explicit
   "schema is a subset of dataclass invariants" note in both the schema
   description and `records.py`, plus one regression test per gap proving
   the dataclass catches what the schema doesn't.

## 6. Non-blocking (fix in Wave 1)

- F6 provenance docstring contradiction (doc says never-fails on unreachable
  clone; code fails loud — align doc to code).
- F7 `_equal` int/float const strictness note.
- F8 dir-fsync ordering in `_atomic_write_json`.
- F9 schema-vs-dataclass sort invariant note.

---

## 7. Verdict rationale

Strong, honest, adversarially-tested infrastructure. The parts I pushed
hardest on — double-record, zero-fill, corrupt state, tampered pins, secret
leakage, ground-truth exfiltration — all held. The blocking items are small
and mechanical: 6 wrong line numbers in one doc, and 2 schema holes that the
dataclass layer already covers but which would silently bite any raw-JSON
consumer. No fabricated evidence found; every number I rechecked was real.

**APPROVE-WITH-CONDITIONS** — G2 may proceed on the code; the two doc/schema
conditions above must land before any lane ships a run record through the
schema-only path.

*— J-CODE, 2026-10-09*
