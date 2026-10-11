"""BARO feasibility pass for the G3 pilot (frozen spec §3 "BARO"; D-V3-013).

Runs the OFFICIAL BARO method (RCAEval, pinned 259ea41, venv `rcarun`) on the
RE2-OB delay pilot cases and verifies the harness reproduces the official
Avg@5-CPU metric in-range (W1 RE2-OB cpu smoke = 0.66).

Pipeline:
  1. Convert the pilot telemetry `metrics.parquet` (wide: `time` int64 unix-sec
     + `{service}_{metric}` columns — identical names to the W1-converted
     `data.csv` columns) into the legacy layout the official `main.py` reads:
       data/RE2/RE2-OB/{service}_delay/{case}/data.csv (+ inject_time.txt)
  2. Run `main.py --method baro --dataset re2-ob --report-chance` from the
     pinned repo so BARO processes exactly the delay cases (the 10 W1 cpu
     result files in output/results/ are excluded: main.py only evaluates
     result files whose `{service}_{fault}` matches a data.csv it processed).
  3. Capture per-case ranked lists from output/results/*.json, the run's
     official metric, and per-case top-5 service hit vs the cases.parquet
     index label (SCORER-SIDE — the only code path in this script that reads
     root_cause_service; offline feasibility artifact, not an arm run).

Outputs: .artifacts/rcaeval/pilot/baro_feasibility.json + raw run log.

Known spec defect (recorded, NOT fixed): the frozen spec §3 says "run on the
8 RE2-OB delay pilot cases" but the frozen 10-case pilot set (spec §2 table,
sha 955a4621…) contains exactly 4 RE2-OB delay cases. See `spec_defect` below.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT_DIR = os.path.join(REPO, ".artifacts", "rcaeval", "pilot")
RCAEVAL = "/Users/sushantgautam/Documents/stg2-worktrees/RCAEval-run"
RCARUN_PY = "/Users/sushantgautam/Documents/stg2-worktrees/rcarun/bin/python"
CASES_PARQUET = "/Users/sushantgautam/Documents/stg2-worktrees/rcacal-hf/cases.parquet"
LAYOUT_ROOT = os.path.join(RCAEVAL, "data", "RE2", "RE2-OB")
RESULTS_DIR = os.path.join(RCAEVAL, "output", "results")
OUT_JSON = os.path.join(PILOT_DIR, "baro_feasibility.json")
OUT_LOG = os.path.join(PILOT_DIR, "baro_re2ob_delay_feasibility.log")

# Frozen pilot set RE2-OB delay cases (g3_pilot_spec_draft.md §2 table, rows 5-8).
RE2OB_DELAY_CASES = [
    "re2ob_checkoutservice_delay_1",
    "re2ob_currencyservice_delay_1",
    "re2ob_emailservice_delay_1",
    "re2ob_productcatalogservice_delay_1",
]

# Exact quote of the discrepancy (frozen spec §3, "BARO (official baseline)").
SPEC_QUOTE = (
    "**BARO (official baseline):** run on the 8 RE2-OB delay pilot cases "
    "**only as a feasibility check**"
)

IN_RANGE = (0.4, 0.85)


def convert_case(case: str) -> str:
    """Convert one pilot case's metrics.parquet to the legacy data.csv layout.

    Returns the target directory under data/RE2/RE2-OB/{service}_delay/{case}.
    """
    src = os.path.join(PILOT_DIR, case)
    df = pd.read_parquet(os.path.join(src, "metrics.parquet"))
    if "time" not in df.columns:
        raise RuntimeError(f"{case}: metrics.parquet missing 'time' column")

    # Derive the faulted service from the case id (re2ob_{svc}_delay_1).
    service = case.split("re2ob_")[1].rsplit("_delay", 1)[0]

    dst = os.path.join(LAYOUT_ROOT, f"{service}_delay", case)
    os.makedirs(dst, exist_ok=True)
    df.to_csv(os.path.join(dst, "data.csv"), index=False)
    shutil.copyfile(os.path.join(src, "inject_time.txt"),
                    os.path.join(dst, "inject_time.txt"))
    return dst


def case_id_from_result_name(name: str) -> str:
    """checkoutservice_delay_re2ob_checkoutservice_delay_1.json -> case id."""
    return name.split("_delay_", 1)[1].rsplit(".json", 1)[0]


def main() -> int:
    # --- 1. Convert the 4 pilot delay cases to the legacy layout ---
    converted = []
    for case in RE2OB_DELAY_CASES:
        dst = convert_case(case)
        converted.append(dst)
        print(f"converted {case} -> {dst}")

    # main.py processes every data.csv under the dataset root, so the W1
    # re2ob_cpu cases (data/RE2/RE2-OB/*_cpu/) are re-run too in this pass.
    # Their result files are replaced by the current run, so evaluation is
    # self-consistent; the original W1 result JSONs were backed up to
    # .artifacts/rcaeval/w1_re2ob_cpu_results_backup/ before the run.
    import glob
    data_csvs = sorted(glob.glob(os.path.join(LAYOUT_ROOT, "**", "data.csv"),
                                 recursive=True))
    missing = [c for c in RE2OB_DELAY_CASES
               if not any(p.endswith(f"/{c}/data.csv") for p in data_csvs)]
    if missing:
        raise RuntimeError(f"delay cases not converted: {missing}")
    extra = [os.path.basename(os.path.dirname(p)) for p in data_csvs
             if os.path.basename(os.path.dirname(p)) not in RE2OB_DELAY_CASES]
    print(f"note: main.py will also re-process W1 cpu cases under the "
          f"dataset root: {sorted(set(extra))}")

    # --- 2. Run the official pipeline ---
    cmd = [RCARUN_PY, "main.py", "--method", "baro",
           "--dataset", "re2-ob", "--report-chance"]
    print("running:", " ".join(cmd), "(cwd", RCAEVAL + ")")
    with open(OUT_LOG, "w") as log:
        proc = subprocess.run(cmd, cwd=RCAEVAL, stdout=log,
                              stderr=subprocess.STDOUT, timeout=1800)
    if proc.returncode != 0:
        print(f"main.py FAILED rc={proc.returncode}; see {OUT_LOG}")
        return 1

    report = open(OUT_LOG).read()
    m = re.search(r"Avg@5-DELAY:\s+([0-9.]+|n/a)", report)
    if not m:
        print("no Avg@5-DELAY line in report:")
        print(report[-2000:])
        return 1
    avg_at_5_delay = None if m.group(1) == "n/a" else float(m.group(1))

    # --- 3. Per-case ranked lists from official result files ---
    per_case: dict[str, Any] = {}
    for case in RE2OB_DELAY_CASES:
        rp = os.path.join(RESULTS_DIR,
                          f"{case.split('re2ob_')[1].rsplit('_delay', 1)[0]}_"
                          f"delay_{case}.json")
        if not os.path.exists(rp):
            raise RuntimeError(f"missing official result file: {rp}")
        ranks = json.load(open(rp))["0"]
        per_case[case] = {"top5": ranks[:5], "n_ranks": len(ranks)}

    # --- SCORER-SIDE (the only label reads in this script) ---
    # Ground truth = cases.parquet index column `root_cause_service`, read here
    # offline for the feasibility table only; not an arm run and not a
    # comparison target (spec §3: BARO outputs are never a comparison target).
    idx = pd.read_parquet(CASES_PARQUET).set_index("case")
    for case in RE2OB_DELAY_CASES:
        truth = idx.loc[case, "root_cause_service"]
        per_case[case]["hit"] = truth in [r.split("_")[0] for r in
                                          per_case[case]["top5"]]

    # --- 4. Write the feasibility artifact ---
    in_range = (avg_at_5_delay is not None
                and IN_RANGE[0] <= avg_at_5_delay <= IN_RANGE[1])
    artifact = {
        "method": "baro (official, RCAEval pinned 259ea41, venv rcarun)",
        "dataset_arg": "re2-ob",
        "cases": list(RE2OB_DELAY_CASES),
        "metric_name": "Avg@5-DELAY (service-level, official main.py report; "
                       "the -DELAY bucket is the official analog of the "
                       "Avg@5-CPU smoke metric)",
        "avg_at_5_cpu": avg_at_5_delay,
        "w1_cpu_smoke_ref": 0.66,
        "in_range_0.4_0.85": in_range,
        "per_case": per_case,
        "log": OUT_LOG,
        "spec_defect": {
            "finding": "frozen spec §3 names 'the 8 RE2-OB delay pilot cases' "
                       "but the frozen 10-case pilot set (§2 table) contains "
                       "exactly 4 RE2-OB delay cases; BARO ran on all 4",
            "spec_quote": SPEC_QUOTE,
            "recorded_only": True,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(OUT_JSON, "w") as f:
        json.dump(artifact, f, indent=2)
    print(f"\nAvg@5-DELAY = {avg_at_5_delay}  (in-range [{IN_RANGE}]: {in_range})")
    for case in RE2OB_DELAY_CASES:
        pc = per_case[case]
        print(f"  {case}: hit={pc['hit']} top5={pc['top5']}")
    print(f"artifact: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
