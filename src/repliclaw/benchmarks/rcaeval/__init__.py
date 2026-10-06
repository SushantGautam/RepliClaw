"""RCAEval lane — observational track O-R only (see README.md for caveats).

Predeclared strata + label-mask-safe heldout CANDIDATE manifest builder
(J-SCI A6 remediation; see docs/next_stage/adapters/rcaeval_contract.md).
"""
from repliclaw.benchmarks.rcaeval.manifest import (
    CASE_FILES,
    CASE_MANIFEST_COLUMNS,
    CASES_PARQUET_SHA256,
    PINNED_SHA,
    QUOTA_TABLE,
    SEED,
    SOURCE_BENCHMARK,
    STRATUM_COLUMNS,
    build_heldout_manifest,
    default_ground_truth_pointer,
    load_manifest_records,
    select_heldout_cases,
    verify_cases_index,
)

__all__ = [
    "CASE_FILES",
    "CASE_MANIFEST_COLUMNS",
    "CASES_PARQUET_SHA256",
    "PINNED_SHA",
    "QUOTA_TABLE",
    "SEED",
    "SOURCE_BENCHMARK",
    "STRATUM_COLUMNS",
    "build_heldout_manifest",
    "default_ground_truth_pointer",
    "load_manifest_records",
    "select_heldout_cases",
    "verify_cases_index",
]
