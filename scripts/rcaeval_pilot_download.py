"""T0+1: download the frozen G3 pilot telemetry (10 cases) from HF (public, no token).

Frozen case list = docs/next_stage/design/g3_pilot_spec_draft.md \u00a72 (merged I2.9).
The sorted-id sha256 (955a4621\u2026) is asserted before any byte is fetched. No
telemetry labels (fault_description / root_cause prose) are read here; files land on
disk with per-file sha256 into download_manifest_pilot.json (S7 pattern).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from typing import Any

import pandas as pd

# Fallback local HF mirror (original host). Fresh hosts should pass --index
# pointing at the in-repo pinned data/cases.parquet (default below).
RCACAL_HF = "/Users/sushantgautam/Documents/stg2-worktrees/rcacal-hf"
CASES_SHA = "c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb"
REPO_DEFAULT_INDEX = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "cases.parquet"
)
BASE = "https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/main"
FILES = ["metrics.parquet", "logs.parquet", "traces.parquet", "inject_time.txt", "root_cause.txt"]

# Frozen pilot set — g3_pilot_spec_draft.md \u00a72 (10 cases, one per stratum, rep 1).
PILOT_CASES = [
    "re1ob_adservice_cpu_1",
    "re1ob_cartservice_cpu_1",
    "re1ob_adservice_delay_1",
    "re1ob_cartservice_delay_1",
    "re2ob_checkoutservice_delay_1",
    "re2ob_currencyservice_delay_1",
    "re2ob_emailservice_delay_1",
    "re2ob_productcatalogservice_delay_1",
    "re3ob_cartservice_f1_1",
    "re3ob_adservice_f3_1",
]
IDS_SHA = "955a462175200909577c8c71db64e3fc8f879c83f1a9028e307926c471503a02"

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".artifacts", "rcaeval", "pilot")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", default=REPO_DEFAULT_INDEX,
                    help="pinned cases.parquet index (default: in-repo data/cases.parquet)")
    ap.add_argument("--tree", default=None,
                    help="optional HF tree_full.json for size hints; without it, "
                         "files are fetched directly and 404s are recorded as skipped")
    args = ap.parse_args()

    idx_path = os.path.normpath(args.index)
    with open(idx_path, "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == CASES_SHA, "cases.parquet hash mismatch"
    idx = pd.read_parquet(idx_path)
    ids = sorted(PILOT_CASES)
    ids_sha = hashlib.sha256("\n".join(ids).encode()).hexdigest()
    assert ids_sha == IDS_SHA, f"pilot id-set hash mismatch: {ids_sha}"
    missing = set(PILOT_CASES) - set(idx["case"])
    assert not missing, f"ids not in index: {missing}"

    tree: dict[str, int] = {}
    if args.tree:
        tree = {
            e["path"]: e["size"]
            for e in json.load(open(args.tree))
            if e["type"] == "file"
        }

    out = os.path.normpath(OUT)
    os.makedirs(out, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    skipped: list[str] = []
    for case in PILOT_CASES:
        case_dir = os.path.join(out, case)
        os.makedirs(case_dir, exist_ok=True)
        for fn in FILES:
            key = f"{case}/{fn}"
            if tree and key not in tree:
                skipped.append(key)
                continue
            dst = os.path.join(case_dir, fn)
            if not os.path.exists(dst):
                url = f"{BASE}/{key}"
                size_hint = f" ({tree[key] // 1024} KiB)" if key in tree else ""
                print(f"GET {url}{size_hint}", flush=True)
                try:
                    urllib.request.urlretrieve(url, dst)
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        skipped.append(key)
                        continue
                    raise
            with open(dst, "rb") as f:
                sha = hashlib.sha256(f.read()).hexdigest()
            manifest.append({"file": key, "bytes": os.path.getsize(dst), "sha256": sha})

    doc = {
        "cases": PILOT_CASES,
        "sorted_ids_sha256": IDS_SHA,
        "files": manifest,
        "skipped_not_in_dataset": sorted(skipped),
    }
    with open(os.path.join(out, "download_manifest_pilot.json"), "w") as f:
        json.dump(doc, f, indent=2, sort_keys=True)
    total = sum(m["bytes"] for m in manifest)
    print(
        f"done: {len(manifest)} files, {total // (1024 * 1024)} MiB, "
        f"skipped: {sorted(skipped)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
