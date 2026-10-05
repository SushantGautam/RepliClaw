# P09 — Hero Demo Narrative (one-page, rubric-aligned)

**One command, fully OFFLINE** (no live LLM, no network, no API key). It reproduces the
hero flow end-to-end and prints `DEMO OK`.

```
/Users/sushantgautam/Documents/ScienceClawHackathon/.venv/bin/python scripts/demo_hero.py
```

Run from the **repo root on the run branch** (`repl-claw-dev`; the committed demo runs from the
repo root — no worktree involved). It reuses **existing** components only
(`run_slice`, `demo_slice._reverify`, the `repliclaw.comparators.runner` CLI) — no new
science, no new claims, no changes to `src/`.

---

## What the one command does (stage by stage)

| Stage | What happens | Rubric point it proves |
|---|---|---|
| **0. Pin** | Prints the run-branch SHA + commit SHA; records whether the tree is dirty. The committed SHA is what the generated artifacts pin. | 10 execution — real, reproducible provenance |
| **1. Vertical slice** | `run_slice` drives one real claim (`policy_rag_v1`) through: **3 independent investigations** (alpha/beta/gamma, distinct hypotheses H_R/H_P/H_J) → **hash-only prediction commitments** (escrow, `commit` before any outcome) → **sealed reveal vs outcome** → **evidence-derived need-market reallocation** → a provenance-linked, uncertainty-aware verdict. | 20 decentralization (private beliefs + local bids/leases) · 25 collective (competing hypotheses) |
| **2. Re-verification** | Re-executes every persisted arm in a clean temp dir and compares the **pinned** `hashes.json` (same `verify_run` semantics `demo_slice` uses). Prints `PASS`/`FAIL`. Never self-attested. | 10 execution — independently validated, not LLM-reported |
| **3. Comparator arms (C1)** | Runs **two offline arms** via the runner CLI (`--client-factory fake`): `S0` (single-agent) and `eess_offline` (RepliClaw rooted slice), same case, same envelope. Asserts their `envelope_sha256` are **identical** → matched-budget, same-task comparison structure is available. | 25 collective — matched-budget same-task structure |
| **4. Determinism** | Digs the seeded **science subtree** (`runs/**`) and shows it is bit-for-bit reproducible and **identical between the slice and the `eess_offline` arm** (same rooted slice → provenance link). | 20 impact — reproducible, reusable artifact |
| **5. Honest summary** | Prints what is real offline and what is **not** demonstrated. | rubric-honesty; anti-"pretty dashboard" trap |

**Expected headline numbers (stable across runs):**
- `stop_reason = all_needs_fulfilled`, `revealed_verified = 3/3`, `revealed_mismatch = 0`, `published_evidence = 4`.
- Prediction verdicts: `alpha H_R → supported`, `beta H_P → refuted`, `gamma H_J → supported`.
- Choice-change trace: `cycle 2: beta  need_I_R_retrieval_fix_alpha → need_I0_baseline_alpha`.
- C1 `envelope_sha256` identical for S0 and eess_offline.
- **Honest disagreement (displayed, not hidden):** `S0 → inconclusive` vs `eess_offline → supported` on the same task/budget.

---

## Which artifacts are produced

Under `artifacts/demo-hero/run-<ts>/`:
- `demo_report.json` — machine-readable summary: branch/commit SHA, slice result fields,
  both arms' `envelope_sha256`, verification status, and the honest-limits list.
- `slice/` — the full P07 slice: `ledger/` (commitments, revealed packets, evidence,
  `events.jsonl` hash chain), `market/` (needs + lease/choice events), `runs/**` (seeded
  SimpleAudit outputs + pinned `hashes.json`), `slice_result.json`.
- `arms/S0/run-01/` and `arms/eess_offline/run-01/` — runner-contract artifacts
  (`final_verdict.json`, `budget_ledger.json`, `traces.jsonl`, `run_metadata.json`,
  plus `eess/runs/**` for the offline EESS arm).

Existing `artifacts/demo/` and `artifacts/demo-llm/` are **left untouched** (not overwritten).

---

## What is real (demonstrated offline, reproducible)

- **Offline deterministic substrate:** the seeded SimpleAudit counterfactual runs (`runs/**`)
  and their pinned `hashes.json` are bit-for-bit reproducible run-to-run, and identical
  between the slice and the `eess_offline` arm (a genuine provenance link).
- **Escrow integrity:** hash-only prediction commitments are sealed and reveal-verified
  against the committed `commitment_sha256` (3/3 verified, 0 mismatch).
- **Independent re-verification:** persisted arms are re-executed and the pinned artifact
  hashes re-derived and compared — never self-attested.
- **Matched-budget same-task structure (C1):** two offline arms share one envelope hash
  under `--client-factory fake`.

## What is NOT demonstrated offline (not faked)

- **No live-LLM performance claims.** No live model / API key / network. The live arm
  (S5/A1/A3) and any live-vs-offline performance gap are out of scope here. (The live
  matched-budget result remains `[PENDING: P08 live]` per `docs/application/`.)
- **No bulk S5 (full EESS) campaign run** — only the offline `eess_offline` rooted slice.
- **Whole-run-dir byte-identity across runs is NOT claimed.** The escrow *bookkeeping*
  (per-run UUID packet ids, wall-clock timestamps, the `prev_event_sha256` hash chain, and
  the derived `evidence_snapshot_sha256` + per-cycle `snapshot_sha`) intentionally differs
  run-to-run; only the science subtree + pinned `hashes.json` are reproducible.
- **No third-party / other-team `verify()` integration** (collaboration label bonus unachieved).
- The slice yields **per-hypothesis** supported/refuted outcomes (not a single calibrated
  confidence score). Where the two arms disagree, the disagreement is shown, not smoothed.

---

## How to reproduce (exact commands + expected outputs)

```bash
cd /Users/sushantgautam/Documents/ScienceClawHackathon   # repo root, run branch `repl-claw-dev`
PY=/Users/sushantgautam/Documents/ScienceClawHackathon/.venv/bin/python

# Baseline slice (should print DEMO OK):
$PY scripts/demo_slice.py

# The one-command hero demo (should print DEMO OK, exit 0):
$PY scripts/demo_hero.py
```

Run it **twice**; both runs must exit 0, print `DEMO OK`, print
`Independent re-execution verification (slice): PASS`, and assert
`C1 … envelope_sha256 identical = True`. The two runs are **identical in every
reproducible metric** (science subtree digest, pinned `hashes.json`, both arms'
`envelope_sha256`, `stable_science` fields, arm verdicts, C1, re-verification) and differ
only by the run timestamp dir name and the per-run escrow `snapshot_sha` (by design).

Machine-readable confirmation per run: `artifacts/demo-hero/run-<ts>/demo_report.json`.
The committed artifacts were regenerated at `945986f` (see
`artifacts/demo-hero/run-20261009-083159/` and `artifacts/demo-slice/run-20261009-083156/`).
