# RCAEval Adapter Contract (L2 / G0–G1)

Status: VERIFIED (G0 pin + G1 pilot reproduction complete)
Author: L2 (RCAEval team), 2026-10-09
Scratch location: `/Users/sushantgautam/Documents/stg2-worktrees/` (nothing committed to the RepliClaw repo except this document)

## 1. Repository pin

| Item | Value |
|---|---|
| Repo | `https://github.com/phamquiluan/RCAEval` |
| Pinned SHA | `259ea4167160256a74ad30004aa3d96a998c846e` (HEAD of `main`, commit dated 2026-09-29 "docs(readme): don't pin the baseline count in the intro") |
| License | MIT (root `LICENSE`, "Copyright (c) 2024 Luan Pham"); per-dependency licenses in `LICENSES/` |
| Python support | 3.8, 3.12, 3.14 (checked in `RCAEval/utility.is_py38/is_py312/is_py314`; `main.py` and `RCAEval/e2e/__init__.py` refuse other versions). RCD additionally requires a separate Python 3.8 env (`pip install -e .[rcd]`). |
| Install for BARO pilot | only `numpy pandas pyarrow scikit-learn tqdm openpyxl requests xlsxwriter networkx` (venv, Python 3.14). Full `requirements.txt` (~200 pkgs) not needed for `baro`. |

## 2. Dataset (Hugging Face)

- Repo: `hf.co/datasets/phamquiluan/RCAEval` — **public, `gated: false`, no token required** (token file exists at `~/.cache/huggingface/token` but was not needed; never printed).
- Mirror: Figshare 31048672, Zenodo 14590730 (zips, ~38 GB extracted; HF parquet preferred).
- Total telemetry on HF: **3,442 MB (3.4 GB)**, matching the README claim.

### Claim vs actual accessible counts

README claims **735 failure cases** (RE1 375 + RE2 270 + RE3 90). Actual HF tree (API, 2026-10-09): **735 case directories, 2,080 files** — the claim is accurate and fully accessible:

| Suite | System | Cases on HF | Bytes | Files per case |
|---|---|---|---|---|
| RE1-OB | Online Boutique | 125 | 31.8 MB | `metrics.parquet`, `inject_time.txt` |
| RE1-SS | Sock Shop | 125 | 15.4 MB | same |
| RE1-TT | Train Ticket | 125 | 73.1 MB | same |
| RE2-OB | Online Boutique | 90 | 922.5 MB | + `logs.parquet`, `traces.parquet` |
| RE2-SS | Sock Shop | 90 | 101.1 MB | + `logs.parquet` (no traces) |
| RE2-TT | Train Ticket | 90 | 1,965.7 MB | + `logs.parquet`, `traces.parquet` |
| RE3-OB | Online Boutique | 30 | 138.1 MB | + `logs.parquet`, `traces.parquet` |
| RE3-SS | Sock Shop | 30 | 32.7 MB | + `logs.parquet` (no traces) |
| RE3-TT | Train Ticket | 30 | 161.4 MB | + `logs.parquet`, `traces.parquet` |

- Index file: `cases.parquet` (29,500 bytes, top-level). **22 columns**: `case, dataset, suite, system, system_name, root_cause_service, fault, fault_description, repetition, inject_time, n_metrics, n_timesteps, time_start, time_end, duration_minutes, normal_timesteps, faulty_timesteps, has_logs, n_logs, has_traces, n_traces, has_root_cause_file`. 735 rows; `groupby("dataset").size()` reproduces the table above.
- Known quirk: `cases.parquet` is written with **parquet-cpp-arrow 25.0.0**; reading it with pyarrow < 25 fails (`OSError: Repetition level histogram size mismatch`). Use pyarrow ≥ 25 (we used 26.0.0 / pandas 3.0.6).
- Layout quirks: 8 RE3 cases also ship `root_cause.txt`; 1 case has metrics+traces but no logs. Case dir names on HF: `re{1,2,3}{ob,ss,tt}_{service}_{fault}_{instance}` (lowercase, no internal underscore between suite letters).
- **TORAI** suites (TORAI-OB/SS/TT, 90 cases each) are listed in the README table but are **not on HF** ("torai data is expected to be local"). They are out of scope for the 735.
- Fault types: RE1 = cpu/mem/disk/delay/loss (5 reps × 5 services × 5 faults); RE2 = +socket (3 reps); RE3 = code-level f1–f5 (note: RE3-SS and RE3-TT have only f1–f4 in practice per index).

## 3. Official evaluator (service ranking)

`RCAEval/benchmark/evaluation.py`, class `Evaluator(max_k=5)`; driven by `main.py`. Two granularities: **service-level** (entities, coarse) and **fine-grained** (entity+metric nodes, "metric-level" in main.py reports). Per-case input: full ranked list of `Node(entity, metric)`; `add_case(ranks, answer, n_candidates, answer_in_candidates=True)`.

Exact metric names and formulas (method names are the contract):

| Metric (code) | Formula |
|---|---|
| `accuracy(k)` → printed `AC1/AC3/AC5` | `AC@k = (1/N) Σᵢ 1[answer ∈ ranksᵢ[:k]]` |
| `average(k)` → printed `Avg@k` | `Avg@k = (1/k) Σⱼ₌₁..k AC@j` |
| `accuracy_service(k)`, `average_service(k)` | same, on service entities (dedup of repeated services in ranking done by caller in `main.py`) |
| `retrieval(budget)` | `Retrieval@K = accuracy(K)`; `retrieval(None)` = fraction of cases whose answer is anywhere in the returned ranking (the method's own candidate set) |
| `rerank(k, budget)` | `Rerank@k = accuracy(k) / retrieval(budget)` (among cases retrieved, fraction with answer in top k). Invariant: `accuracy(k) = retrieval(budget)·rerank(k,budget)` |
| `chance_accuracy(k)`, `chance_average(k)` | random-ranking floor: per case `min(k,n)/n` (`0` if answer not in candidates); `None` if any case lacks `n_candidates` |
| `lift(k)` | `average(k) − chance_average(k)` |

`main.py` CLI flags: `--report-chance` (prints `Chance@5`, `Lift@5`), `--report-decomposition K|all` (prints `Retrieval@K`, `Rerank@1`). Per-fault slices (cpu/mem/io/delay/loss/socket) plus `overall_*` rows; RE1 `disk` faults are scored against `latency` (RE1 telemetry has no diskio metric — RE1 was recorded before blkio export existed). `--length` (minutes, default 20 → window = length·60//2 seconds each side of `inject_time`), `--tdelta` (detection delay simulation), `--test` (first 2 cases only).

## 4. Pilot selection rule (predeclared, no label peeking)

**Rule**: stratum = `dataset == "RE1-OB" AND fault == "cpu"` (smallest metric-only stratum, metric-based methods, cheap to download). Select **2 cases per root-cause service** (5 services → 10 cases), lowest `repetition` first. Selection uses only the public `cases.parquet` index (`root_cause_service` is an index column — inherent to any stratified design; no telemetry or labels beyond the index were read before running the baseline).

Stratum size: 25 cases (5 services × 5 reps). **Pilot = 10 cases** (repetitions 1–2 each):

| case | root_cause_service | n_metrics | n_timesteps |
|---|---|---|---|
| re1ob_adservice_cpu_1 / _2 | adservice | 49 | 4201 |
| re1ob_cartservice_cpu_1 / _2 | cartservice | 49 | 4201 |
| re1ob_checkoutservice_cpu_1 / _2 | checkoutservice | 49 | 4201 |
| re1ob_currencyservice_cpu_1 / _2 | currencyservice | 49 | 4201 |
| re1ob_productcatalogservice_cpu_1 / _2 | productcatalogservice | 49 | 4201 |

Manifest: `stg2-worktrees/rcacal-hf/pilot_manifest.json` (sha256 `2d3075f4…5428e61`, 2,056 B).

## 5. Download manifest (what was actually fetched)

Location: `stg2-worktrees/rcacal-hf/`. Download size: **4,151,409 bytes (~4.0 MB)** telemetry (10 `metrics.parquet` + 10 `inject_time.txt` @ 10 B each) + 29,500 B index.

| File | bytes | sha256 |
|---|---|---|
| `cases.parquet` | 29,500 | `c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb` |
| `hf/re1ob_adservice_cpu_1/metrics.parquet` | 368,024 | `464dcc215afe145d37f8b107ea291df7ffc0691756d375c54ddc1c09d0a2ac74` |
| `hf/re1ob_adservice_cpu_1/inject_time.txt` | 10 | `392017698b9b1df43c5b9a5e96dfb9c19676348d67d2ee6a4ad2061abe729112` |
| `hf/re1ob_adservice_cpu_2/metrics.parquet` | 385,594 | `efc09980ca1386b6ace770364272201ef8eb055444f804cca9f0be8c15199483` |
| `hf/re1ob_adservice_cpu_2/inject_time.txt` | 10 | `d6819c7dc9a5eef5aa2c0ee4ae2494c29ad5c68e2be6bfff450e1e3999c9529b` |
| `hf/re1ob_cartservice_cpu_1/metrics.parquet` | 379,137 | `0f4df7e0eca4c9db7fcbdf2dab29065e14c3ed770c6a70d4a70b8784eb0c0199` |
| `hf/re1ob_cartservice_cpu_1/inject_time.txt` | 10 | `72b74f590a5fdeb7f0df289b7afaa56a73108248600c824ac3e8ba99b13f5a6c` |
| `hf/re1ob_cartservice_cpu_2/metrics.parquet` | 377,747 | `796a22185159f8cb8b34279f77cd293546ed71a081825a0724976dc2aa7af8f9` |
| `hf/re1ob_cartservice_cpu_2/inject_time.txt` | 10 | `6f5008f7377bcaf563d5ee626408c8cf8cbbfaff10184d103e98a798dc3cd46c` |
| `hf/re1ob_checkoutservice_cpu_1/metrics.parquet` | 364,727 | `4590756f037b2ca254b8beb42247883c99712e83fd736d075ace7369bee1f692` |
| `hf/re1ob_checkoutservice_cpu_1/inject_time.txt` | 10 | `5d562cc312d14c858401638bf38ddc3ad35e2f2f873e3e0357fd28030c842f8a` |
| `hf/re1ob_checkoutservice_cpu_2/metrics.parquet` | 547,230 | `91f2117fae29c11799dd54eaaf0651cb94bb205b1f07b44b173caff65dadab4c` |
| `hf/re1ob_checkoutservice_cpu_2/inject_time.txt` | 10 | `9fec8c9f8d87af51dd64a330259dd166077d8b49cd4905c64764b4ee421f317a` |
| `hf/re1ob_currencyservice_cpu_1/metrics.parquet` | 446,967 | `8e9005e50adbf3509d39ddac02b9c09d6f2f167c67ba9fd1d2d4f74dc08e1f19` |
| `hf/re1ob_currencyservice_cpu_1/inject_time.txt` | 10 | `d2a0c0ecc8d8959dc9440e2acf891ca1507da20763eb1741292d3aa01e330bc5` |
| `hf/re1ob_currencyservice_cpu_2/metrics.parquet` | 553,868 | `175f0af6df109004ab25f19ab45246372beff7ef7be1dacb38e98282a099e319` |
| `hf/re1ob_currencyservice_cpu_2/inject_time.txt` | 10 | `3704b2d5df1dd50474cafc4d8de4f9e33a3f286c6358de000ffa24b5afb45da5` |
| `hf/re1ob_productcatalogservice_cpu_1/metrics.parquet` | 359,575 | `7d6322b6de321ced64d5af25f12084ecb96d90a28e59620247158f51b3a72618` |
| `hf/re1ob_productcatalogservice_cpu_1/inject_time.txt` | 10 | `ed6d4733ce0cce697b747316cf01448ca78f62c152f469f6c580b907b39eca84` |
| `hf/re1ob_productcatalogservice_cpu_2/metrics.parquet` | 368,440 | `920ddec1219d9bf714d9e11f6f91b21c20086badfba1ff4a419abe2deff5ed90` |
| `hf/re1ob_productcatalogservice_cpu_2/inject_time.txt` | 10 | `894e9b338721dd92fd7061676231d1355bb5f903cee0efeac9914b880f0c6f90` |

Canonical list of record: `stg2-worktrees/rcacal-hf/sha256_cases.txt` (generated by `shasum -a 256` over all 21 files; the table above is transcribed from it).

## 6. BARO baseline reproduction (evidence)

**Status: REPRODUCED end-to-end, offline, CPU-only, no paid services.**

- BARO (`RCAEval/e2e/baro.py`): window = `length·60//2` seconds (default 20 min → 600 s) before and after `inject_time`; preprocess (drop constant cols, mem→MB); per-metric score = `max` of `RobustScaler` z-scores of the faulty window against the normal window; rank all metrics descending; `ranks` = ordered metric names (service = first token).
- Environment: Python 3.14.8 (homebrew), venv `stg2-worktrees/rcarun` (numpy 2.5.3, pandas 3.0.6, pyarrow 26.0.0, scikit-learn 1.9.1, tqdm, openpyxl, networkx). Clean copy of the repo at pinned SHA: `stg2-worktrees/RCAEval-run` (`git status` clean).
- Layout conversion: `metrics.parquet` → legacy `data/online-boutique/{service}_{fault}/{case}/data.csv` (+ `inject_time.txt`), because `main.py --dataset re1-ob` reads `data/online-boutique/**/data.csv` (CSV layout is what `main.py` expects; the HF parquet layout is read by `RCAEval.utility.read_metrics`, not by `main.py` directly).
- Command (exact):
  ```
  cd /Users/sushantgautam/Documents/stg2-worktrees/RCAEval-run
  ../rcarun/bin/python main.py --method baro --dataset re1-ob --report-chance
  ```
  (`data/online-boutique` pre-populated with the 10 pilot cases; the auto-download is a no-op because the dir already exists.)
- Actual output (verbatim, saved to `stg2-worktrees/rcacal-hf/baro_pilot_output.txt`):
  ```
  100%|██████████| 10/10 [00:00<00:00, 24.33it/s]
  --- Evaluation results ---
  Avg@5-CPU:   1.0
  Chance@5-CPU: 0.23
  Lift@5-CPU:  0.77
  ---
  Avg speed: 0.04
  ```
- Per-case check: in all 10 cases the true root-cause service's `_cpu` metric is rank 1 or 2 (AC1 at service level = 1.0). Example: `re1ob_adservice_cpu_1` → top5 = `['adservice_cpu', 'redis_mem', 'checkoutservice_latency', 'emailservice_mem', 'adservice_mem']`.
- Result artifacts: `stg2-worktrees/RCAEval-run/output/results/*.json` (10 files, one per case, keys `{"0": [ranked metrics]}`). Full-SHA list via `shasum -a 256` in that directory (spot: `adservice_cpu_re1ob_adservice_cpu_1.json` = `804fd7af1caf4b9c601fcbc841d4ceef33d6ea200da5769c28fd395824d06bbe`).
- Known non-finding: `main.py` defines `report_path = output/report.xlsx` but at pinned SHA it **never writes the xlsx** (no `to_excel` call in main.py at 259ea41); the per-fault `eval_data` table is built but discarded. Not a blocker — all metrics are re-derivable from the JSON result files + `Evaluator`.
- Wall time: ~0.4 s for 10 cases (BARO is trivially cheap).

### Blockers (for full-suite / other baselines)

- **Full RE1**: 120 cases per system, ~120 MB (OB); trivially extendable from the pilot path. No blocker.
- **Full RE2-TT**: 1.97 GB alone (340–376 metrics/case, ~10 min to evaluate per README CI timing). Feasible but must be scheduled; CPU-only.
- **RCD/MMRCD**: require Python 3.8 + `pip install -e .[rcd]` (pinned old deps) — not yet set up; treat as a G2 task.
- **TORAI suites**: not on HF (local data only) — unavailable; out of scope.
- `cases.parquet` requires pyarrow ≥ 25 (documented above).
- `main.py` is version-sensitive: Python 3.8/3.12/3.14 only.

## 7. Observational-failure caveat

All RCAEval failure cases are **recorded, observational incident data** (telemetry captured in live microservice systems with fault injection; ground truth = annotated injected root cause). They are **not counterfactual replay**: the benchmark provides no re-injection interface, no mutable environment, and no ability to intervene and observe the system's counterfactual response. Any counterfactual/what-if capability claimed by a RepliClaw method must be evidenced outside this benchmark; on RCAEval we can only measure ranking quality against recorded annotations.

## 8. Reproduction script

```bash
# from /Users/sushantgautam/Documents/stg2-worktrees
git clone https://github.com/phamquiluan/RCAEval RCAEval && cd RCAEval && git checkout 259ea4167160256a74ad30004aa3d96a998c846e
python3.14 -m venv rcarun && ./rcarun/bin/pip install numpy pandas pyarrow scikit-learn tqdm openpyxl requests xlsxwriter networkx
python3 -m venv rcaenv && ./rcaenv/bin/pip install pyarrow pandas   # pyarrow>=25 to read cases.parquet
cd rcacal-hf && ./rcaenv/bin/python -c "import pandas as pd; idx=pd.read_parquet('cases.parquet'); (idx[(idx.dataset=='RE1-OB')&(idx.fault=='cpu')].groupby('root_cause_service',group_keys=False).head(2)).to_json('pilot_manifest.json',orient='records',indent=2)"
# download pilot: for each case in manifest: resolve {case}/metrics.parquet and {case}/inject_time.txt
# convert: data/online-boutique/{service}_{fault}/{case}/{data.csv,inject_time.txt}
cd RCAEval-run && ../rcarun/bin/python main.py --method baro --dataset re1-ob --report-chance
```
