# Handoff — P06: second, genuinely independent scientific case (Tox21 AR-agonist)

Branch: `p06/secondary-case` · Worktree: `.worktrees/p06` · Base: `b5f7bfb`
Type: CODE + DATA + ARTIFACTS (new case under `src/repliclaw/counterfactual/cases/`,
`tests/`, and `artifacts/science/p06-hero-canonical/`; `pyproject.toml` NOT touched)

> **Spec note:** the ticket file `docs/fleet/P06.md` referenced by the mission
> **does not exist** in this worktree base. The case was specified from the
> mission brief (second, genuinely independent case; offline + deterministic +
> counterfactual arms) and the F05 design (`docs/fleet/F05.md`, which chose the
> Tox21 / molecular secondary case). If a formal P06 ticket later lands and
> diverges, reconcile here.

Purpose: the P02 hero result (`policy_rag_v1`) was a single case. P06 adds a
**second, genuinely independent scientific case** so the counterfactual method
is not single-case: a deterministic, **OFFLINE, no-LLM** molecular experiment
with four counterfactual intervention arms that **actually discriminate**.

---

## 1. Case description (what was built)

**Case:** `tox21_ar_agonist_v1` — *directed aromatic functionalization of a frozen
subset of real Tox21 AR-screen compounds, scored by Crippen logP (RDKit
`MolLogP`).*

**Falsifiable question** (stated in `case.py` docstring): *Does the TYPE of a
single directed aromatic functionalization determine the change in computed
lipophilicity (Crippen logP) of a frozen set of real screened compounds, such
that distinct interventions (hydroxylation, chlorination, methylation) yield
DISTINCT per-arm mean logP shifts — i.e. the arms genuinely discriminate rather
than being relabelled copies of one arm?*

**Data (honest caveat):** 48 real compounds, a deterministic subset of the
Tox21 androgen-receptor (AR) agonist screen (PubChem BioAssay AID 743053,
Tox21 10K library). Provenance: Zenodo record 20269909 (DOI
`10.5281/zenodo.20269909`), CC-BY-4.0, access date 2026-10-08; frozen extract
`experiments/tox21_ar_agonist/data/tox21_ar_7069.tsv` (F05), sha256
`a1056c72…f22` (7,069 unique compounds, 220 active / 3.1%). **This is a
computational structural experiment on a 48-compound subset — NOT an
activity/toxicity prediction on the full extract.** The assay `label` column is
carried for provenance only and is used by no arm or the judge.

**Arms (each perturbs exactly ONE factor = the directed functionalization at a
deterministic site, first aromatic C with an implicit H, lowest atom index):**

| arm | intervention | measured mean ΔlogP |
|---|---|---|
| `I0_baseline` | none | **0.000000** |
| `I1_OH` | aromatic → phenol (C→C–OH) | **−0.294400** |
| `I2_Cl` | aromatic → aryl chloride (C→C–Cl) | **+0.653400** |
| `I3_Me` | aromatic → tolyl methyl (C→C–CH3) | **+0.308420** |

The four observed means are **pairwise distinct** and **direction-consistent**
(baseline 0; hydroxylation lowers logP; chlorination > methylation raise it),
matching real Phase-I chemistry (a polar OH down, hydrophobic Cl/Me up). This
was verified on all 200 candidate molecules before freezing the 48.

**Why it is genuinely independent of P02:** P02 perturbs a *software* failure
(retrieval / judge / policy) in a frozen RAG stack; P06 perturbs a *chemical
structure* in a frozen molecule set and measures a *physical* property. Different
domain, different data, different measurement, different oracle.

---

## 2. Files created (this ticket only)

Case code (owned path `src/repliclaw/counterfactual/cases/`):
- `cases/_base.py` — **case-agnostic runner** (arm-agnostic `Case` ABC, `run_case`/
  `run_canonical`/`replay`, `persist_arm`, `write_case_manifest`, sha256/canonical
  helpers). The P02 `counterfactual` package is not in this base, so this is the
  local abstraction the case plugs into; **real P02 wiring happens at P07**.
- `cases/tox21_ar_agonist/__init__.py` — exports `Tox21ArAgonistCase`, `load_case`.
- `cases/tox21_ar_agonist/case.py` — the ARM. Data load, `measure_arm` (RDKit logP
  before/after the single directed substitution), `effective_config` (single-factor),
  `engine_metadata`, `case_sha256`. **Contains no reference to the sealed oracle.**
- `cases/tox21_ar_agonist/judge.py` — the JUDGE. **The ONLY module that reads the
  sealed oracle.** Scores the measured mean ΔlogP against the frozen expected value
  within a tight tolerance.
- `cases/tox21_ar_agonist/__main__.py` — canonical-run entrypoint
  (`python -m repliclaw.counterfactual.cases.tox21_ar_agonist <out>`).
- `cases/tox21_ar_agonist/data/molecules.json` — the frozen 48-compound subset
  (sha256 `19da2bb7…`, full provenance + selection rule + RDKit version).
- `cases/tox21_ar_agonist/oracle/oracle.json` — the **sealed ground truth**
  (schema `repliclaw.sealed_oracle/v1`): per-arm expected mean ΔlogP, tolerance,
  hypothesis. Read only by `judge.py`.
- `cases/tox21_ar_agonist/oracle/freeze_oracle.py` — one-shot generator that
  froze `oracle.json` from a real offline RDKit run (kept as ground-truth
  provenance).

Tests:
- `tests/test_secondary_case.py` — 7 contract tests (see §3).

Canonical artifacts (generated by a REAL run, committed):
- `artifacts/science/p06-hero-canonical/manifest.json`
- `artifacts/science/p06-hero-canonical/replay.sh`
- `artifacts/science/p06-hero-canonical/interventions/{I0_baseline,I1_OH,I2_Cl,I3_Me}/
  {config.json, target_output.json, stdout.log, judgment.json, hashes.json}`

Handoff: this file.

No other files changed. `git status` is clean apart from these (plus the
git-ignored `.venv/`).

---

## 3. The 7 tests (`tests/test_secondary_case.py`) — all PASS

1. `test_arms_discriminate` — the four arms give **distinct OBSERVED** mean ΔlogP
   shifts AND are direction-consistent (`baseline≈0, OH<0<Me<Cl`); each judged
   within tolerance.
2. `test_determinism` — same seed → **byte-identical** per-arm artifacts (and
   `hashes.json`) across two fresh run dirs.
3. `test_oracle_not_leaked` — the arm-side runtime modules (`case.py`, `__init__.py`,
   `__main__.py`) never reference the oracle file; the oracle's ground-truth
   literals appear in **no** canonical artifact.
4. `test_judge_is_sole_reader` — only `judge.py` names the oracle file.
5. `test_single_factor_at_a_time` — each arm's effective config differs from baseline
   in exactly the one intervention factor (`functionalization`+`element`).
6. `test_tamper_detection` — genuine run replays `True`; flipping one byte of a
   stored artifact makes `replay` return `False`; restoring replays `True` again.
7. `test_canonical_artifacts` — the committed canonical run exists, pins the engine
   (RDKit version) + per-arm artifact hashes, and replays genuinely.

---

## 4. Commands run & exit codes (worktree venv, run from worktree root ONLY)

- `.venv/bin/pip install 'opentelemetry-api>=1.20' 'opentelemetry-sdk>=1.20'
  'openinference-semantic-conventions>=0.1'` → 0 (needed by pre-existing
  `tests/test_observability.py`; not a P06 dependency)
- `.venv/bin/python -m repliclaw.counterfactual.cases.tox21_ar_agonist
  artifacts/science/p06-hero-canonical` → 0 (generated the committed artifacts)
- `bash artifacts/science/p06-hero-canonical/replay.sh` → 0 →
  `[replay] byte-identical verification: True` (regenerates + two-pass verify +
  per-arm sha256 summary)
- **`.venv/bin/python -m pytest` → 0 → `73 passed, 8 skipped in 2.87s`**
  (the 8 skips are pre-existing, unrelated to P06)
- **`.venv/bin/python -m ruff check src tests` → 0 → `All checks passed!`**
- **`.venv/bin/python -m mypy src` → 0 → `Success: no issues found in 22 source files`**

### Canonical run output (real)
```
I0_baseline  mean_delta_logp=+0.000000 severity=pass
I1_OH        mean_delta_logp=-0.294400 severity=pass
I2_Cl        mean_delta_logp=+0.653400 severity=pass
I3_Me        mean_delta_logp=+0.308420 severity=pass
manifest: artifacts/science/p06-hero-canonical/manifest.json
```

### Real sha256 — committed canonical artifacts (`artifacts/science/p06-hero-canonical/`)
```
c0b7c24bd5a26cd6fdcc57a72b72331c614e3f30c8a6f9f8e8add1407dd1c663  manifest.json
ef72d1c39129e74cca9ddfe372977f4a331ada9013d5ca18484488b7b721dfd4  replay.sh
  I0_baseline  config.json      894bd7e396ad3956a40e0afb13545e1bdbd78894ec2b5bfb34fca891d5714efe
  I0_baseline  target_output.json 8755e08cddc82d841992288db5361970b24dfd422a64040e946ee929870762f1
  I0_baseline  judgment.json    7dacda361c687bf40f2586fa41f28d049c0714baec4d5de50573cf4f9e129832
  I0_baseline  stdout.log       9876d9fabb64a0cabec1aefd6401d6705d4f18271ac0292877ae31a5a99334eb
  I0_baseline  hashes.json      2b0016129f2741bc87ad76d2389fea58db1c66f0018984bd8107272a184205c6
  I1_OH        config.json      473c1d54a1495630f95db7465728b6708c6d5102321a23aeda586fa8b77da2a2
  I1_OH        target_output.json 75bde8710fedd9e5fb47b14090f94303ec1822a3ea89314202b814fa4c194159
  I1_OH        judgment.json    7ed381d765e5b25d193edb21c1d878573b7eef9869b693a690a56d4300d16d3a
  I1_OH        stdout.log       d83a81bd069a1114377b4ac71f4e97a45bad919dd3011604f9406a8c85aae18a
  I1_OH        hashes.json      e03fa2ed51dd7db7d05188c08323582ea193db2517f39d994a6ebaf44cb87438
  I2_Cl        config.json      e83b1382d52b6cb83146e56e46ae368ce94cde8783a9680b824edaebf9fdd708
  I2_Cl        target_output.json 517640606a38dc0c1dcf11baede9dfbf0c2bedc6325bfc9794cc82abfa6bfc69
  I2_Cl        judgment.json    c0247aba9a7c17d3f0169d5c7621285cfd708ca983eb5a7f9dc41598b2297f81
  I2_Cl        stdout.log       9fea29e664a3da9acf6c43236801bd130ba9f5896b0f8a3874e017f0d1686edb
  I2_Cl        hashes.json      8b73ed0ecae676f96ff262f18aa8fe4657b03e75048fb31816ed75d15a7dffaf
  I3_Me        config.json      deab566f0751f80aba1514b581188fd09815b4429c1746aaff80e8a839d26db4
  I3_Me        target_output.json 3377331f846f717bddb8972e8c106fd0ec1d92e7123964251cc6a6c94e48bfb3
  I3_Me        judgment.json    973bd7191da0ce8a79e22a266cf49a5f7fb3118bc6b88e71f4bb8d00442dfb62
  I3_Me        stdout.log       f8c1cb23778d7385926dcfb48f71fee0d5b0b2429899db4862f035288063f65a
  I3_Me        hashes.json      1ae4fb0a40156eaa1505e55fddc243ce7dc982e19b910c3dc3feeaefcab0ff0d
```

### Real sha256 — case source / data / oracle
```
19da2bb7303be82b124323f846f6bcbd2ad42e0e2440e8345bf42e8966c75f88  cases/tox21_ar_agonist/data/molecules.json  (= case_sha256)
8c83dd9e6c2c0d9f53ebc9b0946220338092fca2348e116012ad9e068766be90  cases/tox21_ar_agonist/oracle/oracle.json
d9a5b1697ddcef7c4a987de40950b3a755bcf86c2654a6e97ed3913244ca4621  cases/tox21_ar_agonist/case.py
336052022ab3d25753b3a9061884dd0dca4235360a897ddcb56a5880a940e145  cases/tox21_ar_agonist/judge.py
6b3ec3ddcd626c64de85ad54e53c2f6120388186a4b191d50fd025571809151c  cases/_base.py
739d26e7f49a6589c67ed4e7bf03005108391a19b5cc4e1fff3d1bf00deed1b2  tests/test_secondary_case.py
```

---

## 5. Design decisions worth flagging

- **Sealed-oracle pattern, made structural, not just textual.** The arm code
  (`case.py`) and package `__init__`/`__main__` contain no reference to the
  oracle file; only `judge.py` names it. `test_oracle_not_leaked` +
  `test_judge_is_sole_reader` enforce this at the source level, and a grep over
  the committed artifact tree enforces it at the artifact level.
- **§6 leakage: the oracle's ground-truth VALUE never appears in a public
  artifact.** `persist_arm`/`write_case_manifest` strip `expected_mean_delta_logp`
  and `oracle_schema` from the PERSISTED `judgment.json` and the manifest's
  per-arm entry. The in-memory judgment keeps them (for internal validation);
  the public artifacts carry only the arm's own MEASURED value + pass/fail.
  (Verified: a grep for the expected deltas finds them only as the measured
  values, and never under `expected_*`/`oracle_*` keys.)
- **`_base.py` is deliberately case-agnostic** so P07 can mount both cases on one
  runner without editing P02's code. It lives under `cases/_base*` per the
  mission to avoid colliding with the P02 branch's `counterfactual/__init__.py`.

---

## 6. NOT PROVEN / honest limitations (do not overclaim)

- **P02/P07 wiring is NOT integrated.** The P02 `counterfactual` package
  (`CaseSpec`/`InterventionSpec`/`SimpleAuditExecutor`) is not in this base; this
  case runs on the local `cases/_base.py` abstraction. Integration is P07's job.
- **Byte-identity across MACHINES is unproven.** Same-machine, same-seed,
  same-RDKit-version reproduction is proven (replay + tests). RDKit Crippen logP
  is a deterministic fragment sum, so cross-machine byte-identity is *expected*
  given the pinned RDKit version (2026.03.6, recorded in the manifest), but was
  not exercised on a second machine.
- **RDKit is a lazy, not-declared dependency.** It is NOT in `pyproject.toml`
  (that file is outside my owned paths and I did not edit it). The run venv has
  RDKit installed; the arm raises a clear, actionable error if RDKit is absent.
  Tests `pytest.importorskip("rdkit")` for the case-specific tests.
- **The oracle is a deterministic chemical constant, not independent external
  truth.** The expected per-arm mean ΔlogP was frozen from the same deterministic
  RDKit chemistry the arms use (on the frozen 48). It is sealed from the arms,
  but the *derivation* is not an independent measurement — the judge checks
  internal consistency + direction, not ground-truth from an outside source.
- **logP is a physicochemical PROXY, not bioactivity/toxicity.** This is a
  structural property experiment on a 48-compound subset. It does not predict
  Tox21 assay outcomes on the full 7,069 extract; the assay `label` is unused.
- **Small subset.** 48 of 7,069 compounds (the smallest subset that keeps every
  molecule editable by all three substitutions and gives a clean, constant
  per-molecule ΔlogP per arm). 1 positive / 47 negative labels carried for
  provenance only.
- **`git_sha` in the engine metadata is empty** (best-effort; the venv python
  does not expose it). Engine NAME + VERSION (rdkit 2026.03.6) are pinned.

---

## 7. How to reproduce

```
cd .worktrees/p06
bash artifacts/science/p06-hero-canonical/replay.sh
# -> "[replay] byte-identical verification: True" + per-arm sha256 summary
```
