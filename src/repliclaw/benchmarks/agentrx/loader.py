"""AgentRx dataset loader — READ-ONLY, no LLM, no judge, no execution.

Loads the 4 pinned HF ``microsoft/AgentRx`` JSONL files (sha256-verified on
load, fail-loud on mismatch), joins raw trajectories with annotations (tau id
prefix drift handled by stripping ``tau_retail_``; magentic ids match
directly), and exposes one typed :class:`AgentRxCASE` per annotated case.

The 14 unannotated raw magentic trajectories are EXCLUDED from the eval set
and counted in the returned manifest notes (contract §4).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .taxonomy import category_code

#: Pinned upstream commit (contract §1) and pinned HF dataset file hashes (§4).
PINNED_REPO_SHA = "7a18c79708e7671be15124460f4f7296107c2a55"

DEFAULT_DATA_DIR = Path("/Users/sushantgautam/Documents/stg2-worktrees/agentrx-data")

#: filename -> (sha256, role)
PINNED_FILES: Dict[str, Tuple[str, str]] = {
    "tau_retail.jsonl": (
        "95729a0f39b1408b0f6d59ccfea758db6f6986218933b812d361cc0a7f49d1a9",
        "annotated_ground_truth_tau_retail",
    ),
    "magentic_one.jsonl": (
        "9bfa562d6928e4cfb56f0f444fee7c916ce28aab35b725538814db6c1bc35187",
        "annotated_ground_truth_magentic_one",
    ),
    "tau_retail_dataset.jsonl": (
        "218529966d5c395ea22a3124aa423a7cb5c3ad4f2f01bf81013b304969bfc7be",
        "raw_trajectories_tau_retail",
    ),
    "magentic_dataset.jsonl": (
        "e2c697a91aa1c1b37d1375547e1da0bcd3190ec68560f019606e837053a2179b",
        "raw_trajectories_magentic_one",
    ),
}

#: Raw-file id prefix stripped for the tau join (contract §4 ID scheme).
TAU_ID_PREFIX = "tau_retail_"

EXPECTED_COUNTS = {"eval_cases": 73, "tau": 29, "magentic": 44, "failure_instances": 334, "unannotated_magentic": 14}

DOMAIN_TAU = "tau_retail"
DOMAIN_MAGENTIC = "magentic_one"


class DatasetHashMismatchError(RuntimeError):
    """Raised when a pinned dataset file does not match its sha256."""


class DatasetLoadError(RuntimeError):
    """Raised for structural problems (bad join, missing root cause, …)."""


@dataclass(frozen=True)
class TrajectoryStep:
    """One step of a raw trajectory (``{index, substeps, ...}``)."""

    index: int
    substeps: Any
    raw: Dict[str, Any] = field(compare=False, repr=False, default_factory=dict)


@dataclass(frozen=True)
class AnnotatedFailure:
    """One annotated failure within a trajectory."""

    failure_id: str
    step_number: int
    step_reason: str
    failure_category: str
    category_reason: str
    failed_agent: str


@dataclass(frozen=True)
class RootCause:
    failure_id: str
    reason: str
    step_number: int
    category: str
    category_code: int


@dataclass(frozen=True)
class AgentRxCASE:
    """One annotated evaluation case: trajectory + annotations + root cause."""

    case_id: str
    domain: str  # "tau_retail" | "magentic_one"
    instruction: str
    steps: Tuple[TrajectoryStep, ...]
    failures: Tuple[AnnotatedFailure, ...]
    root_cause: RootCause
    failure_summary: str
    raw_trajectory_id: str

    @property
    def trajectory_length(self) -> int:
        return len(self.steps)


@dataclass(frozen=True)
class AgentRxEvalSet:
    """The 73-case eval set plus loader bookkeeping."""

    cases: Tuple[AgentRxCASE, ...]
    data_hashes: Dict[str, str]
    unannotated_magentic_ids: Tuple[str, ...]
    notes: str


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_pinned(data_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Read all 4 pinned files, verifying sha256; fail loud on any mismatch."""
    records: Dict[str, List[Dict[str, Any]]] = {}
    for filename, (expected_sha, _role) in PINNED_FILES.items():
        path = data_dir / filename
        if not path.is_file():
            raise DatasetHashMismatchError(f"pinned dataset file missing: {path}")
        actual = _sha256(path)
        if actual != expected_sha:
            raise DatasetHashMismatchError(
                f"{filename}: sha256 {actual} != pinned {expected_sha} "
                f"(refusing to load a tampered or moved dataset)"
            )
        with path.open("r", encoding="utf-8") as fh:
            lines = [json.loads(line) for line in fh if line.strip()]
        records[filename] = lines
    return records


def _to_steps(raw_steps: List[Dict[str, Any]]) -> Tuple[TrajectoryStep, ...]:
    return tuple(TrajectoryStep(index=int(s["index"]), substeps=s.get("substeps"), raw=dict(s)) for s in raw_steps)


def _parse_annotation(ann: Dict[str, Any], domain: str) -> Tuple[AnnotatedFailure, int]:
    """Validate the annotation and return (root-cause failure, root-cause code)."""
    failures = tuple(
        AnnotatedFailure(
            failure_id=str(f["failure_id"]),
            step_number=int(f["step_number"]),
            step_reason=f["step_reason"],
            failure_category=f["failure_category"],
            category_reason=f["category_reason"],
            failed_agent=f["failed_agent"],
        )
        for f in ann["failures"]
    )
    rc_id = str(ann["root_cause"]["failure_id"])
    if str(ann.get("root_cause_failure_id", "")) != rc_id:
        raise DatasetLoadError(
            f"{domain}/{ann['trajectory_id']}: root_cause_failure_id "
            f"{ann.get('root_cause_failure_id')!r} != root_cause.failure_id {rc_id!r}"
        )
    rc_failure = next((f for f in failures if f.failure_id == rc_id), None)
    if rc_failure is None:
        raise DatasetLoadError(f"{domain}/{ann['trajectory_id']}: root cause failure_id {rc_id!r} not in failures")
    code = category_code(rc_failure.failure_category)
    if code is None:
        raise DatasetLoadError(
            f"{domain}/{ann['trajectory_id']}: unnormalisable root-cause category {rc_failure.failure_category!r}"
        )
    return rc_failure, code


def _build_case(raw_id: str, raw: Dict[str, Any], ann: Dict[str, Any], domain: str) -> AgentRxCASE:
    rc_failure, rc_code = _parse_annotation(ann, domain)
    failures = tuple(
        AnnotatedFailure(
            failure_id=str(f["failure_id"]),
            step_number=int(f["step_number"]),
            step_reason=f["step_reason"],
            failure_category=f["failure_category"],
            category_reason=f["category_reason"],
            failed_agent=f["failed_agent"],
        )
        for f in ann["failures"]
    )
    return AgentRxCASE(
        case_id=str(ann["trajectory_id"]),
        domain=domain,
        instruction=raw["instruction"],
        steps=_to_steps(raw["steps"]),
        failures=failures,
        root_cause=RootCause(
            failure_id=rc_failure.failure_id,
            reason=ann["root_cause"]["reason_for_root_cause"],
            step_number=rc_failure.step_number,
            category=rc_failure.failure_category,
            category_code=rc_code,
        ),
        failure_summary=ann["failure_summary"],
        raw_trajectory_id=raw_id,
    )


def load_agentrx_eval_set(data_dir: Optional[Path] = None) -> AgentRxEvalSet:
    """Load and join the 4 pinned files into the 73-case eval set.

    Join rules (contract §4): tau annotated ids are unprefixed strings; raw
    tau ids are ``tau_retail_<n>`` — strip the prefix to match. Magentic ids
    are UUID strings matching directly. Raw magentic trajectories with no
    annotation are excluded and counted.
    """
    data_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    records = _read_pinned(data_dir)

    tau_ann = {str(d["trajectory_id"]): d for d in records["tau_retail.jsonl"]}
    mag_ann = {str(d["trajectory_id"]): d for d in records["magentic_one.jsonl"]}
    tau_raw = {d["trajectory_id"]: d for d in records["tau_retail_dataset.jsonl"]}
    mag_raw = {d["trajectory_id"]: d for d in records["magentic_dataset.jsonl"]}

    cases: List[AgentRxCASE] = []

    missing_raw = sorted(tid for tid in tau_ann if f"{TAU_ID_PREFIX}{tid}" not in tau_raw)
    if missing_raw:
        raise DatasetLoadError(f"tau annotated ids with no raw trajectory: {missing_raw}")
    for tid in sorted(tau_ann, key=lambda t: int(t)):
        cases.append(_build_case(f"{TAU_ID_PREFIX}{tid}", tau_raw[f"{TAU_ID_PREFIX}{tid}"], tau_ann[tid], DOMAIN_TAU))

    missing_raw_mag = sorted(tid for tid in mag_ann if tid not in mag_raw)
    if missing_raw_mag:
        raise DatasetLoadError(f"magentic annotated ids with no raw trajectory: {missing_raw_mag}")
    for tid in sorted(mag_ann):
        cases.append(_build_case(tid, mag_raw[tid], mag_ann[tid], DOMAIN_MAGENTIC))

    unannotated_mag = sorted(set(mag_raw) - set(mag_ann))
    total_failures = sum(len(c.failures) for c in cases)
    n_tau = sum(1 for c in cases if c.domain == DOMAIN_TAU)
    n_mag = sum(1 for c in cases if c.domain == DOMAIN_MAGENTIC)
    if (len(cases), n_tau, n_mag, total_failures, len(unannotated_mag)) != (
        EXPECTED_COUNTS["eval_cases"],
        EXPECTED_COUNTS["tau"],
        EXPECTED_COUNTS["magentic"],
        EXPECTED_COUNTS["failure_instances"],
        EXPECTED_COUNTS["unannotated_magentic"],
    ):
        raise DatasetLoadError(
            f"eval-set counts drifted: cases={len(cases)} tau={n_tau} magentic={n_mag} "
            f"failures={total_failures} unannotated={len(unannotated_mag)}"
        )

    notes = (
        f"14 raw magentic trajectories have no annotation and are EXCLUDED from the eval set "
        f"(ids: {', '.join(unannotated_mag)}). "
        f"Eval set = {len(cases)} annotated trajectories ({n_tau} tau_retail + {n_mag} magentic_one), "
        f"{total_failures} annotated failure instances. "
        f"Trajectories are stored observational traces; this adapter performs no execution, "
        f"no LLM calls, and no causal intervention."
    )
    data_hashes = {name: _sha256(data_dir / name) for name in PINNED_FILES}
    return AgentRxEvalSet(
        cases=tuple(cases),
        data_hashes=data_hashes,
        unannotated_magentic_ids=tuple(unannotated_mag),
        notes=notes,
    )


__all__ = [
    "AgentRxCASE",
    "AgentRxEvalSet",
    "AnnotatedFailure",
    "DEFAULT_DATA_DIR",
    "DatasetHashMismatchError",
    "DatasetLoadError",
    "DOMAIN_MAGENTIC",
    "DOMAIN_TAU",
    "EXPECTED_COUNTS",
    "PINNED_FILES",
    "PINNED_REPO_SHA",
    "RootCause",
    "TAU_ID_PREFIX",
    "TrajectoryStep",
    "load_agentrx_eval_set",
]
