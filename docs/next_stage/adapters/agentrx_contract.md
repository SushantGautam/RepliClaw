# AgentRx Adapter Contract (G0/G1)

**Status:** G0 (repo + dataset pinned, verified) / G1 (partial — LLM stages blocked, see §9)
**Author:** L1 (AgentRx track), RepliClaw Stage 2
**Date:** 2026-10-09
**Paper:** arXiv:2602.02475 (Barke et al., 2026, "AgentRx: Diagnosing AI Agent Failures from Execution Trajectories")
**Repo:** https://github.com/microsoft/AgentRx
**Dataset:** https://huggingface.co/datasets/microsoft/AgentRx (gated)

---

## 1. Repo pin

- **Pinned SHA:** `7a18c79708e7671be15124460f4f7296107c2a55` (`main`, commit date 2026-09-14T15:18:36-07:00, "Merge pull request #38 ... pin-actions")
- **Clone location (scratch only):** `/Users/sushantgautam/Documents/stg2-worktrees/agentrx-upstream`
- **Layout:** `run.py` (CLI entry), `agentrx/` package (`ir/`, `invariants/`, `judge/`, `llm_clients/`, `pipeline/`, `reports/`), `data/` (policies, tool schemas, ground truth), `trajectories/` (sample inputs), `tests/test_judge_encoding.py`.

## 2. License

- **Repo:** MIT (Microsoft Corporation) — `LICENSE.txt`.
- **Dataset:** CC-BY-4.0 (per HF card `license: cc-by-4.0`).

## 3. Dataset access

- HF dataset `microsoft/AgentRx`, **gated (`gated: auto`)**. Access verified 2026-10-09 via user's HF token at `~/.cache/huggingface/token` (HTTP 200 on `api/datasets/microsoft/AgentRx`). **Token-scoped; do not print or commit the token.**
- Local copy: `/Users/sushantgautam/Documents/stg2-worktrees/agentrx-data` (5 files).
- All 5 files independently re-fetched from HF `resolve/main` on 2026-10-09; hashes below **match the re-fetched copies** (verified byte-identical).

## 4. Dataset files — hashes (sha256), counts, roles

| File | sha256 | Records | Role |
|---|---|---|---|
| `tau_retail.jsonl` | `95729a0f39b1408b0f6d59ccfea758db6f6986218933b812d361cc0a7f49d1a9` | **29** | **Annotated ground truth, tau_retail** (domain split) |
| `tau_retail_dataset.jsonl` | `218529966d5c395ea22a3124aa423a7cb5c3ad4f2f01bf81013b304969bfc7be` | **29** | **Raw trajectories, tau_retail** (same 29, unprefixed ids) |
| `magentic_one.jsonl` | `9bfa562d6928e4cfb56f0f444fee7c916ce28aab35b725538814db6c1bc35187` | **44** | **Annotated ground truth, magentic_one** (domain split) |
| `magentic_dataset.jsonl` | `e2c697a91aa1c1b37d1375547e1da0bcd3190ec68560f019606e837053a2179b` | **58** | **Raw trajectories, magentic_one** (14 of 58 unannotated) |
| `README.md` | `2b29f65760747e34364e5f84174573b5741bff2a949d4e136e5da0b50cc1ab5c` | — | HF card |

**Evaluation set = 29 (tau_retail) + 44 (magentic_one) = 73 annotated trajectories.**

### Split structure (HF card)

Two configs: `default` → splits `tau_retail` (tau_retail.jsonl) + `magentic_one` (magentic_one.jsonl); `trajectories` → splits `magentic_dataset` (magentic_dataset.jsonl) + `tau_retail` (tau_retail_dataset.jsonl).

### ID scheme

- **tau_retail:** annotated ids are unprefixed strings (`"2"`, `"3"`, …); raw-file ids are prefixed strings (`"tau_retail_2"`, …). Stripping `tau_retail_` gives 29/29 overlap.
- **magentic_one:** UUID-like strings, 44/44 overlap between raw and annotated.

### Annotation schema (annotated files; matches repo `data/ground_truth/*.json`)

Top level: `trajectory_id` (str), `failure_summary` (str), `num_failures` (int), `failures` (list), `root_cause` (dict), `root_cause_failure_id` (str), `root_cause_reason` (str).
Each `failures[i]`: `failure_id` (**str** in HF / **int** in repo GT — content identical), `step_number` (int), `step_reason` (str), `failure_category` (str), `category_reason` (str), `failed_agent` (str).
`root_cause`: `{failure_id, reason_for_root_cause}`.

Raw files: `trajectory_id`, `instruction`, `steps` (list of `{index, substeps, ...}`).

### Dataset-vs-repo GT reconciliation

Repo `data/ground_truth/tau_ground_truth.json` (29 entries) and `magentic_one_ground_truth.json` (44 entries) have **identical content** to the HF annotated files modulo: (a) int vs str typing of `trajectory_id`/`failure_id`, (b) HF adds derived fields `num_failures`, `root_cause_failure_id`, `root_cause_reason`. No semantic drift. A second repo file `data/ground_truth/tau_retail.json` (24 entries) is a **subset/older variant** (also the path the judge's default `--ground_truth_file ground_truth_tau_retail.json` expects, via `analyze_metrics.DOMAIN_GROUND_TRUTH_PATHS["tau"]`); treat the 29-entry file/HF split as the authoritative evaluation set unless the paper specifies otherwise.

## 5. Taxonomy (v-pinned)

**10 categories**, pinned by `FailureCase` enum in `agentrx/judge/judge.py` (L253-264) and `FAILURE_CASE_TO_CATEGORY` in `agentrx/reports/analyze_metrics.py` (L20-27). These are the canonical metric-level names:

| # | Canonical category (code) |
|---|---|
| 0 | NO_ERROR_PREDICTED (enum-only; treated as wrong prediction, not a GT category) |
| 1 | Instruction Adherence Failure |
| 2 | Invention of New Information |
| 3 | Invalid Invocation |
| 4 | Misinterpretation of Tool Output |
| 5 | Intent Plan Misalignment |
| 6 | Underspecified User Intent |
| 7 | Intent Not Supported |
| 8 | Guardrails Triggered |
| 9 | System Failure |
| 10 | Inconclusive (judge may attach a `custom_category` label) |

### Discrepancies (documented, NOT remapped)

1. **README (repo) table** renders slightly different strings: "Instruction/Plan Adherence Failure", "Intent-Plan Misalignment", "Invention of New Information" — the judge normalizes these via `normalize_category()` (substring matching on "instruction"+"adherence", "invention", etc.) into the canonical names above. **Never match on README strings; match on canonical names or enum ints.**
2. **Annotated data uses 3 inconsistent spellings:**
   - `tau_retail.jsonl`: "Instruction Adherence Failure" (no slash; 6), plus Misinterpretation of Tool Output (8), Invalid Invocation (4), Underspecified User Intent (10), Intent Plan Misalignment (8), Intent Not Supported (2), System Failure (1). No categories 2, 8, 10 present.
   - `magentic_one.jsonl`: "Instruction/Plan Adherence Failure" (197), "Invention of new information" (lowercase n; 8), "Intent Plan Misalignment" (19), "Intent not supported" (22), "Misinterpretation of Tool Output" (23), "Guardrails Triggered" (24), "Invalid Invocation" (1), "System Failure" (1). No categories 6, 10 present.
   - **Total annotated failure instances: 39 (tau) + 295 (magentic) = 334.** (Integrator-verified 2026-10-09 by direct recount of both JSONL files; the original "73 (tau)" miscounted annotated *trajectories* as *failure instances* — the per-file category sums 39 + 295 are internally consistent and are authoritative.)
3. **README says 10 categories; blog reportedly said 9** — the code is authoritative: 10 (incl. Inconclusive). The paper's "3 domains" = tau (Tau-bench retail), magentic (Magentic-One), **flash** (incident management) — but **flash has no ground truth and no dataset in the release** (GT path `symbolic_invariants/pipeline/flash_dataset.json` does not exist in the repo). So the reproducible benchmark is 2 domains / 73 trajectories, not 3.
4. The "115 trajectories" figure in the paper does **not** match the public release: 58 + 29 = 87 raw trajectories, 73 annotated. (115 may include the unreleased flash set; cannot be verified from the release.)

## 6. Official baseline (run commands)

Setup:
```bash
cd AgentRx && python3 -m venv .venv && .venv/bin/pip install -e .
cp .env.example .env   # fill endpoint
export AZURE_TOKEN_CREDENTIALS=dev   # skip ManagedIdentity IMDS probe
```

Full pipeline (per trajectory JSON; outputs → `runs/<run_name>/`):
```bash
python run.py <trajectory.json> --domain tau --run-name <name>
# stages: ir → static → dynamic → check → judge → report
# --stage <s> runs one stage; --from-stage <s> resumes
# --endpoint {copilot,azure,trapi} (default: copilot = GitHub Copilot CLI)
# --ground-truth <path> for judge comparison
```

Judge standalone:
```bash
python agentrx/judge/judge.py --domain tau --log_file <traj.json> --mode combined \
  --ground_truth_file data/ground_truth/tau_ground_truth.json --with_ground_truth --iterations 1
# --mode {baseline, checklist, examples, combined}; --exec_mode {violations-after, stepbystep, violations-before}
```

Aggregation:
```bash
python agentrx/reports/analyze_metrics.py <run_output_dir> --domain tau   # + --calculate_manually
python agentrx/reports/analyze_run_metrics.py ...                          # cross-run std dev
```

**LLM requirements:** every stage after IR (static, dynamic, check-on-LLM-content, judge) calls an LLM via one of 3 clients:
- `copilot` (default): local GitHub Copilot CLI, model from `AGENT_VERIFY_COPILOT_MODEL` (example: `claude-opus-4.6`). No API key — uses the CLI's own auth.
- `azure`: Azure OpenAI (`AGENT_VERIFY_ENDPOINT/DEPLOYMENT/MODEL_NAME/API_VERSION`), **Azure AD auth** (`az login` / Managed Identity).
- `trapi`: Microsoft Research internal — not available externally.

## 7. Metric schema (exact, from `judge.py` summary writer + `analyze_metrics.py`)

Judge writes `runs/<n>/<model>_<timestamp>.json` = `{"summary": {...}, "detailed_results": [...]}`.

**Summary fields (exact keys):** `model_name`, `api_version`, `Correct cases` (int), `Incorrect cases` (int), `Average distance for correct cases`, `Average distance for incorrect cases`, `Overall average distance`, `Normalized average distance for correct cases`, `Normalized average distance for incorrect cases`, `Normalized overall average distance`, `Correct step number predictions` (int), `Incorrect step number predictions` (int), `Step number accuracy` (float 0-1), `Step accuracy within +-1` … `+-5` (floats 0-1), `total_prompt_tokens`, `total_output_tokens`, `total_tokens`, `total_execution_time_sec`.

**Denominators (code-verified):**
- Root-cause accuracy = `Correct cases / (Correct cases + Incorrect cases)`; a case is **correct iff the predicted `failure_case` int equals the GT root-cause failure's category int** (`str(most_common_failure) == str(gt_failure_case)`).
- Step metrics: `step_mean` = mean of predicted step numbers for the task; exact = `round(step_mean) == gt_step_number`; ±k = `abs(round(step_mean) - gt_step) <= k`; denominators = same `total_cases`.
- Distance = `abs(step_mean - gt_step)`; normalized = distance / `trajectory_length`.
- GT root-cause step/category = failure entry whose `failure_id == root_cause.failure_id`.
- `analyze_metrics.py` cross-run: mean + population std dev (ddof=0) over per-run accuracies; category variants **any_failure / earliest / terminal** (predicted category ∈ {all|first|last GT failure categories by `step_number`}).

**detailed_results per-task fields (used by analysis):** `gt_failure_case`, `most_common_failure`, `step_mean`, `step_median`, `step_std_dev`, `step_mae`, `gt_step_number`, `trajectory_length`, `step_error_distribution`.

## 8. Verification performed (2026-10-09, this environment)

- venv install `pip install -e .` — OK (Python 3.11).
- `run.py trajectories/tau-retail/instruction_adherence_failure.json --domain tau --stage ir` — **OK, LLM-free**: produces `trajectory_ir.json` (list of `{trajectory_id, instruction, steps}`), 0.0s.
- Full pipeline with `--endpoint copilot` — **reached the LLM call, then failed**: Copilot CLI returned quota message (see §9).
- Dataset counts, hashes, ID joins, taxonomy string audit — as documented above (recomputed, not assumed).

## 9. BLOCKERS

1. **B1 — No working LLM provider for baseline reproduction (hard).**
   - `copilot` endpoint (no paid API needed, local CLI v1.0.92 present): **monthly quota exhausted** — probe `copilot --prompt '...'` returns "You have exceeded your monthly quota (Request ID: D4AB:2E3DC8:E4EA85:F5BA5A:6AC94D41)". Therefore `static/dynamic/check/judge` all fail (`Static invariants JSON parse failed: Expecting value: line 1 column 1`); pipeline is resumable with `--from-stage static` once credits refresh. Exact failing command: `.venv/bin/python run.py trajectories/tau-retail/instruction_adherence_failure.json --domain tau --run-name tiny_baseline` (endpoint default `copilot`).
   - `azure` endpoint: requires Azure OpenAI resource + Azure AD identity (`AGENT_VERIFY_ENDPOINT`, `AGENT_VERIFY_DEPLOYMENT`, `az login`/Managed Identity) — **not available here**.
   - `trapi`: Microsoft-internal — **not available externally**.
   - No fabricated baseline numbers are reported; paper numbers must be re-derived once an endpoint is available.
2. **B2 — Flash domain absent.** Paper's 3rd domain (flash, incident management) has GT path `symbolic_invariants/pipeline/flash_dataset.json` that does not exist in the repo, and no flash files in the HF release. Baseline reproduction is limited to tau + magentic (73 trajectories).
3. **B3 — Minor schema drift** (HF str ids vs repo int ids; `data/ground_truth/tau_retail.json` 24-entry subset vs 29-entry authoritative file; `DOMAIN_GROUND_TRUTH_PATHS["tau"]` points to a nonexistent `ground_truth_tau_retail.json` filename relative to repo root). Adapter must pass `--ground_truth_file data/ground_truth/tau_ground_truth.json` explicitly and coerce id types (str()) on join.

## 10. Reproduction plan (when an LLM endpoint is available)

1. `pip install -e .`, set endpoint env, `export AZURE_TOKEN_CREDENTIALS=dev`.
2. Tiny smoke (2 trajs, 1 iteration): run judge on `trajectories/tau-retail/*.json` with `--with_ground_truth --ground_truth_file data/ground_truth/tau_ground_truth.json`.
3. Full eval: iterate the 29 tau raw trajectories (`data/tau_retail/tau_dataset_failed.json` / HF `tau_retail_dataset.jsonl`) and 44 annotated magentic raws (`data/magentic_dataset/*.json` subset matching `magentic_one.jsonl` ids), 3+ iterations per domain for std dev; aggregate via `analyze_metrics.py --domain {tau,magentic}` with GT `data/ground_truth/{tau_ground_truth,magentic_one_ground_truth}.json`.
4. Report schema fields from §7 verbatim; do not rename.
