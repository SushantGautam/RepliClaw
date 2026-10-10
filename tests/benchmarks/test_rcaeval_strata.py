"""W1 / J-SCI A6: RCAEval strata + label-mask-safe heldout candidate manifest.

Requires pyarrow >= 25 and pandas (contract §2 quirk: cases.parquet is written
with parquet-cpp-arrow 25 and is unreadable by older pyarrow).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from repliclaw.benchmarks.rcaeval import (
    CASES_PARQUET_SHA256,
    QUOTA_TABLE,
    build_heldout_manifest,
    select_heldout_cases,
    verify_cases_index,
)

DATA = Path(__file__).resolve().parents[2] / "data" / "cases.parquet"

# Frozen expected selection (contract-verified 2026-10-09): 42 cases spanning
# RE1 (10), RE2 (20), RE3 (6) — the A6 requirement is the RE2/RE3 rows.
EXPECTED_COUNTS = {"RE1-OB": 10, "RE2-OB": 20, "RE3-SS": 12}
EXPECTED_TOTAL = 42
SUITE_COUNTS = {"RE1": 375, "RE2": 270, "RE3": 90}


@pytest.fixture(scope="module")
def index() -> pd.DataFrame:
    assert DATA.exists(), f"fixture {DATA} missing — copy the pinned cases.parquet"
    return pd.read_parquet(DATA)


def test_cases_parquet_hash_matches_contract(index: pd.DataFrame) -> None:
    assert verify_cases_index(str(DATA)) == CASES_PARQUET_SHA256
    assert hashlib.sha256(DATA.read_bytes()).hexdigest() == CASES_PARQUET_SHA256


def test_index_counts_match_contract(index: pd.DataFrame) -> None:
    assert len(index) == 735
    assert index.groupby("suite").size().to_dict() == SUITE_COUNTS
    assert index.groupby("dataset").size()["RE1-OB"] == 125


def test_selection_counts_and_strata(index: pd.DataFrame) -> None:
    cases = select_heldout_cases(index)
    assert len(cases) == EXPECTED_TOTAL
    assert len(set(cases)) == len(cases), "no duplicate cases"
    by_ds = index.set_index("case").loc[cases, "dataset"]
    assert by_ds.value_counts().to_dict() == EXPECTED_COUNTS
    # A6: every suite must be present in the heldout
    assert set(index.set_index("case").loc[cases, "suite"]) == {"RE1", "RE2", "RE3"}


def test_selection_covers_all_quota_rows(index: pd.DataFrame) -> None:
    cases = set(select_heldout_cases(index))
    for suite, system, fault, per_service in QUOTA_TABLE:
        sub = index[
            (index["dataset"] == f"{suite}-{system}")
            & (index["fault"] == fault)
        ]
        in_sel = [c for c in cases if c in set(sub["case"])]
        # per-service cap respected
        per_svc = index.set_index("case").loc[in_sel, "root_cause_service"].value_counts()
        assert (per_svc <= per_service).all(), (suite, system, fault, per_svc.to_dict())
        assert len(in_sel) == per_service * sub["root_cause_service"].nunique()


def test_selection_lowest_repetition_first(index: pd.DataFrame) -> None:
    cases = select_heldout_cases(index)
    by = index.set_index("case")
    for case in cases:
        ds, fault, svc = by.loc[case, "dataset"], by.loc[case, "fault"], by.loc[case, "root_cause_service"]
        stratum = index[
            (index["dataset"] == ds) & (index["fault"] == fault) & (index["root_cause_service"] == svc)
        ]
        # every selected case's repetition must be one of the lowest `per_service`
        # repetitions in its stratum
        sel_rep = int(by.loc[case, "repetition"])
        allowed = sorted(stratum["repetition"].tolist())[:2]
        assert sel_rep in allowed, (case, sel_rep, allowed)


def test_label_mask_invariance(index: pd.DataFrame) -> None:
    """Selection output must be identical when the label/annotation columns
    are masked to NaN — the proof that selection never reads them.

    Mask `fault_description` (the annotation text column) plus every column
    that is NOT a stratum/ordering axis, so the strongest plausible leakage
    surface is covered. Also perturb the masked values with per-case distinct
    strings to rule out coincidence on all-NaN input.
    """
    base = select_heldout_cases(index)

    stratum_axes = set(
        ("case", "suite", "system", "system_name", "root_cause_service", "fault", "repetition", "dataset")
    )
    mask_cols = [c for c in index.columns if c not in stratum_axes]
    assert "fault_description" in mask_cols, "annotation column must be masked in this test"

    # Variant 1: every non-stratum column masked to NaN
    masked = index.copy()
    for c in mask_cols:
        masked[c] = pd.NA
    assert select_heldout_cases(masked) == base

    # Variant 2: masked columns carry per-case distinct opaque strings
    masked2 = index.copy()
    for c in mask_cols:
        masked2[c] = [f"MASK_{i}" for i in range(len(masked2))]
    assert select_heldout_cases(masked2) == base
    # and also with the annotation column shuffled independently
    shuffled = index.copy()
    shuffled["fault_description"] = shuffled["fault_description"].sample(frac=1.0, random_state=0)
    assert select_heldout_cases(shuffled) == base


def test_determinism_under_row_and_column_order(index: pd.DataFrame) -> None:
    base = select_heldout_cases(index)
    assert select_heldout_cases(index) == base, "same index → same selection"
    # row order must not matter
    reshuffled = index.sample(frac=1.0, random_state=20261009).reset_index(drop=True)
    assert select_heldout_cases(reshuffled) == base
    # column order must not matter
    permuted = index[index.columns[::-1].tolist()]
    assert select_heldout_cases(permuted) == base


def test_manifest_records_roundtrip(index: pd.DataFrame) -> None:
    cases = select_heldout_cases(index)
    # synthetic data hashes: real ones live in the W1 download manifest
    data_hashes = {c: {"metrics.parquet": "0" * 64} for c in cases}
    manifests = build_heldout_manifest(index, data_hashes)
    assert len(manifests) == EXPECTED_TOTAL
    for m in manifests:
        assert m.heldout is True
        assert m.source_benchmark == "rcaeval"
        assert m.ground_truth is not None, "evaluator-only ground-truth pointer required"
        assert set(m.strata) == {"suite", "system", "fault_type", "quota_service_order", "repetition"}
        result = m.validate()
        assert not result.errors, [str(e) for e in result.errors]
        # wire round-trip preserves identity
        assert type(m).from_dict(m.to_dict()) == m


def test_manifest_strata_leak_free(index: pd.DataFrame) -> None:
    """J-CODE W1 F1 (HIGH): agent-visible manifest fields must carry NO ground truth.

    root_cause_service names and fault_description text are answers; they may
    be used to DEFINE the quota (pre-experiment) but must never appear in
    strata or evaluation_scope.

    Documented upstream fact (not fixable here): the official RCAEval case
    identifiers embed the affected service (``re1ob_adservice_mem_1``) and
    data files are named by case id. The V3 agent runtime must therefore
    present cases by opaque random id — see case_manifest.schema.json notes.
    This test asserts the structured fields, which are under our control.
    """
    cases = select_heldout_cases(index)
    data_hashes = {c: {"metrics.parquet": "0" * 64} for c in cases}
    manifests = build_heldout_manifest(index, data_hashes)
    service_names = set(index["root_cause_service"].astype(str))
    for m in manifests:
        for field in (m.strata, m.source_benchmark):
            assert "root_cause_service" not in str(field)
            serialized = str(field)
            for svc in service_names:
                if svc:
                    assert svc not in serialized, (
                        f"ground-truth service {svc!r} leaked into {field!r}"
                    )
        assert m.ground_truth.pointer == f"hf://phamquiluan/RCAEval/cases.parquet#case={m.case_id}"


def test_manifest_rejects_missing_data_hashes(index: pd.DataFrame) -> None:
    cases = select_heldout_cases(index)
    with pytest.raises(ValueError, match="no data hashes"):
        build_heldout_manifest(index, {c: {} for c in cases})
