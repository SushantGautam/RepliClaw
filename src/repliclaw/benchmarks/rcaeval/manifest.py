"""RCAEval (observational track O-R) predeclared strata + heldout CANDIDATE manifest.

J-SCI A6 remediation (SCIENCE_JUDGE_WAVE0_20261009.md, finding F7): the heldout
must span RE1/RE2/RE3 so that the official BARO baseline does not saturate the
whole track. Everything here is frozen BEFORE any telemetry of a heldout case
is inspected; the manifest is a CANDIDATE pending freeze at gate G4.

Label-mask safety
-----------------
``select_heldout_cases`` touches ONLY stratum-defining index columns
(:data:`STRATUM_COLUMNS` + ``dataset``/``repetition`` for ordering).
``CASE_MANIFEST_COLUMNS`` is the annotation column family a scorer may read to
resolve ground truth, and selection never reads it.
``tests/benchmarks/test_rcaeval_strata.py`` proves the selection output is
identical when the label column is masked to NaN.

J-SCI C-SCI-1 (S1): the single evaluator-only resolve path is
:func:`heldout_ground_truth`, which reads labels exclusively THROUGH
``repliclaw.benchmarks.common.gating.ScorerContext`` (audited). No
agent-facing code may import or call it; the static caller-restriction scan
in ``tests/benchmarks/test_ground_truth_gate.py`` pins this.

Case-id and strata confidentiality (G2)
---------------------------------------
(i) Upstream RCAEval case ids embed the root-cause service (e.g.
    ``re1ob_adservice_mem_1`` names ``adservice``), so the upstream id is
    itself a ground-truth identifier.
(ii) Agents only ever receive OPAQUE case ids at runtime — the upstream id
    stays evaluator-side (the ground-truth pointer and the pinned index are
    scorer-only). The V3 runtime must present cases by opaque random id; see
    the ``case_id`` note in ``case_manifest.schema.json``.
(iii) The agent-visible ``strata`` exclude ALL ground-truth identifiers,
    including derived ordinals. A ``quota_service_order`` ordinal was removed
    pre-G4 (J-CODE W1 F1 follow-up) because it was the alphabetical rank of
    the root-cause service within the fault stratum — decodable from the
    public index, hence a ground-truth channel, not a non-informative one.
    The strata now carry only (suite, system, fault_type, repetition), which
    never uniquely determine the service (pinned by
    ``tests/benchmarks/test_rcaeval_leak.py::test_strata_do_not_decode_root_cause_service``).
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from repliclaw.benchmarks.common.gating import (
    ResolveAuditLedger,
    ScorerContext,
    get_resolve_audit_ledger,
)
from repliclaw.benchmarks.common.records import CaseManifest, GroundTruthPointer

SOURCE_BENCHMARK = "rcaeval"

# Upstream repo pinned per docs/next_stage/adapters/rcaeval_contract.md §1.
PINNED_SHA = "259ea4167160256a74ad30004aa3d96a998c846e"

# Contract §2: cases.parquet content hash (pyarrow >= 25 required to read it).
CASES_PARQUET_SHA256 = "c49a288920dbba2e8e724679a14636d5c7eb2b45426bba14007ef79a6c0ab1bb"

# Frozen random tie-break seed (seed allocation: W1/RCAEval heldout selection;
# distinct from the statistical bootstrap seed of statistical_protocol_v3).
SEED = 20261009

# Only these columns may ever influence case selection. Root-cause service is
# the one index column inherent to any stratified RCA design (also used by the
# official per-fault evaluator slices); it is a stratum axis, not a label.
STRATUM_COLUMNS: Tuple[str, ...] = (
    "case",
    "suite",
    "system",
    "system_name",
    "root_cause_service",
    "fault",
)

# Ground-truth / annotation columns. Only the scorer may read these, and only
# after selection is frozen. `fault` (the fault-type NAME) is a stratum axis,
# not a label; `fault_description` is the annotation text and is excluded from
# selection by construction.
CASE_MANIFEST_COLUMNS: Tuple[str, ...] = ("fault_description",)

# Data files present per case on HF (contract §2 layout).
CASE_FILES: Tuple[str, ...] = (
    "metrics.parquet",
    "logs.parquet",
    "traces.parquet",
    "inject_time.txt",
    "root_cause.txt",
)

# Predeclared stratification and heldout CANDIDATE quota table (frozen
# 2026-10-09, W1 / J-SCI A6). Rows are (suite, system, fault_type,
# per_service_cap). Within each (dataset, fault_type, root_cause_service)
# stratum the lowest `repetition` values are taken first (case-name order
# breaks ties). Quotas were chosen from the public index so each (suite,
# system) has a bounded HF download (~220 MB total) and every suite appears in
# the heldout:
#
#   RE1 (metrics-only, easier)  : RE1-OB / mem        5 services x 2 = 10
#   RE2 (logs+traces, harder)   : RE2-OB / cpu        5 services x 2 = 10  <- BARO smoke stratum
#                                 RE2-OB / mem        5 services x 2 = 10
#   RE3 (code-level faults)     : RE3-SS / f1         3 services x 2 = 6
#                                 RE3-SS / f3         3 services x 2 = 6
#
# 42 heldout candidate cases total. RE2-OB cpu doubles as the RE2 feasibility
# smoke (RE2-OB is the largest-case RE2 system; the 1.97 GB RE2-TT is deferred).
QUOTA_TABLE: Tuple[Tuple[str, str, str, int], ...] = (
    ("RE1", "OB", "mem", 2),
    ("RE2", "OB", "cpu", 2),
    ("RE2", "OB", "mem", 2),
    ("RE3", "SS", "f1", 2),
    ("RE3", "SS", "f3", 2),
)


def verify_cases_index(cases_path: str) -> str:
    """Return sha256 of cases.parquet; raise ValueError if it differs from the contract."""
    sha = hashlib.sha256()
    with open(cases_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            sha.update(chunk)
    digest = sha.hexdigest()
    if digest != CASES_PARQUET_SHA256:
        raise ValueError(f"cases.parquet hash mismatch: {digest} != {CASES_PARQUET_SHA256}")
    return digest


def _dataset(su: str, sy: str) -> str:
    return f"{su}-{sy}"


def _select_stratum(index: pd.DataFrame, dataset: str, fault: str, per_service: int) -> List[str]:
    """Cases for one (dataset, fault) quota row, lowest repetition first.

    Uses only :data:`STRATUM_COLUMNS` + ``repetition`` for ordering.
    Deterministic: repeated calls on the same index return the identical
    ordered list. ``SEED`` is reserved for any future random tie-break; the
    current ordering is total, so no RNG draws are consumed.
    """
    sub = index[(index["dataset"] == dataset) & (index["fault"] == fault)]
    if sub.empty:
        raise ValueError(f"quota row ({dataset}, {fault}) selects 0 cases — index changed?")
    services = sorted(sub["root_cause_service"].unique())
    picked: List[str] = []
    for svc in services:
        stratum = sub[sub["root_cause_service"] == svc].sort_values(["repetition", "case"])
        if len(stratum) < per_service:
            raise ValueError(
                f"stratum ({dataset}, {fault}, {svc}) has {len(stratum)} cases < cap {per_service}"
            )
        picked.extend(stratum["case"].head(per_service).tolist())
    return picked


def select_heldout_cases(index: pd.DataFrame) -> List[str]:
    """Frozen stratified selection rule. Returns case ids in selection order.

    Label-mask invariance: output depends only on :data:`STRATUM_COLUMNS`
    plus ``repetition``, so masking :data:`CASE_MANIFEST_COLUMNS` (or any
    other annotation column) to NaN cannot change the result.
    """
    for col in list(STRATUM_COLUMNS) + ["dataset", "repetition"]:
        if col not in index.columns:
            raise ValueError(f"index missing required column {col!r}")
    cases: List[str] = []
    for suite, system, fault, per_service in QUOTA_TABLE:
        cases.extend(_select_stratum(index, _dataset(suite, system), fault, per_service))
    if len(set(cases)) != len(cases):
        raise ValueError("selection produced duplicate case ids")
    return cases


def default_ground_truth_pointer(case_id: str) -> GroundTruthPointer:
    """EVALUATOR-ONLY locator: the case row in the pinned cases.parquet.

    The scorer (and only the scorer) may read the row's annotation columns
    (:data:`CASE_MANIFEST_COLUMNS` / ``fault`` detail) after this manifest is
    frozen; no lane code dereferences it.
    """
    return GroundTruthPointer(pointer=f"hf://phamquiluan/RCAEval/cases.parquet#case={case_id}")


def build_heldout_manifest(
    index: pd.DataFrame,
    data_hashes: Dict[str, Dict[str, str]],
    *,
    ground_truth_pointers: Optional[Dict[str, GroundTruthPointer]] = None,
) -> List[CaseManifest]:
    """Build CaseManifest records for :func:`select_heldout_cases`.

    ``data_hashes`` maps case id -> {filename: sha256} for every downloaded
    case file (from the W1 download manifest). ``ground_truth_pointers`` maps
    case id -> GroundTruthPointer (default: the index-row locator above).
    """
    cases = select_heldout_cases(index)
    missing = [c for c in cases if not data_hashes.get(c)]
    if missing:
        raise ValueError(f"no data hashes for selected cases: {missing[:5]}…")

    by_case = index.set_index("case")
    manifests: List[CaseManifest] = []
    for case in cases:
        row = by_case.loc[case]
        # J-CODE Wave 1 F1 (HIGH): strata are AGENT-VISIBLE. The index row's
        # root_cause_service is ground truth and MUST NOT appear in the
        # manifest (it would disclose the answer before the diagnosis).
        # Quota stratification uses it internally in _select_stratum only.
        #
        # J-CODE W1 F1 follow-up (pre-G4): the earlier "non-informative"
        # quota_service_order ordinal was REMOVED. It was the alphabetical
        # rank of the root-cause service within the (dataset, fault) stratum,
        # which is decodable from the public index (an attacker recomputes the
        # rank and maps it back to the service) — a ground-truth channel, not
        # a non-informative one. The strata now carry only
        # (suite, system, fault_type, repetition), which never uniquely
        # determine the service (pinned by
        # tests/benchmarks/test_rcaeval_leak.py::test_strata_do_not_decode_root_cause_service).
        strata = {
            "suite": str(row["suite"]),
            "system": str(row["system"]),
            "fault_type": str(row["fault"]),
            "repetition": str(int(row["repetition"])),
        }
        notes = (
            "O-R heldout CANDIDATE (frozen 2026-10-09, W1/J-SCI A6); pending "
            "freeze at G4. Observational recorded failure — NOT counterfactual "
            f"replay. Selection seed={SEED} (reserved; ordering is deterministic). "
            "Strata exclude ground-truth identifiers (J-CODE W1-F1): "
            "root_cause_service is scorer-only."
        )
        gt = (ground_truth_pointers or {}).get(case) or default_ground_truth_pointer(case)
        manifests.append(
            CaseManifest(
                case_id=case,
                source_benchmark=SOURCE_BENCHMARK,
                pinned_sha=PINNED_SHA,
                data_hashes=dict(data_hashes[case]),
                strata=strata,
                heldout=True,
                ground_truth=gt,
                notes=notes,
            )
        )
    return manifests


def heldout_ground_truth(
    case_id: str,
    index: pd.DataFrame,
    *,
    caller_tag: str = "rcaeval_scorer",
    ledger: Optional[ResolveAuditLedger] = None,
) -> str:
    """EVALUATOR-ONLY: resolve one case's ground-truth root-cause service.

    Reads ``root_cause_service`` from the pinned cases index strictly through
    :class:`~repliclaw.benchmarks.common.gating.ScorerContext`, so the resolve
    is audited and there is exactly one code path by which a label can be
    read (J-SCI C-SCI-1). Lane / agent-facing code MUST NOT import or call
    this function; the static scan in
    ``tests/benchmarks/test_ground_truth_gate.py`` enforces the allowed-caller
    set. ``caller_tag`` identifies the resolving scorer run for the audit log.

    The resolve context is constructed and discarded per call; the audit
    entry therefore also goes to a persistent :class:`ResolveAuditLedger`
    (F-W2-3). When ``ledger`` is omitted, the module-level default ledger
    from :func:`get_resolve_audit` is used, so production resolves leave a
    surviving trail. Tests may inject a fresh ledger for isolation.
    """
    scorer = ScorerContext(index=index, label_column="root_cause_service", ledger=ledger or get_resolve_audit_ledger())
    return scorer.resolve(case_id, caller_tag=caller_tag)


def get_resolve_audit() -> ResolveAuditLedger:
    """Return the persistent resolve-audit ledger for RCAEval holds.

    DOCUMENTED USE: evaluator/QA inspection only. Never import this from
    agent/lane-facing code to act on audit contents.
    """
    return get_resolve_audit_ledger()


def load_manifest_records(manifests: Sequence[CaseManifest]) -> List[Dict[str, Any]]:
    """Wire-shape dicts for archival (canonical key order irrelevant)."""
    return [m.to_dict() for m in manifests]
