"""Round-trippable dataclasses for the shared benchmark infrastructure layer.

Each dataclass maps 1:1 onto one JSON Schema document in ``schemas/`` (draft
2020-12). ``to_dict()`` emits the exact wire shape (canonical key order is
irrelevant — ``repliclaw.canonical.canonical_json`` sorts keys before
hashing); ``from_dict()`` accepts that shape and enforces schema string
identity. ``validate()`` runs the dependency-free validator in
:mod:`repliclaw.benchmarks.common.validation`.

Token-usage convention (shared with ``repliclaw.eess_live.accounting``):
when ``usage_present`` is False the numeric fields are ``None`` — never
zero-filled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .validation import SCHEMA_FILES, validate_record

RUN_RECORD_SCHEMA = SCHEMA_FILES["run_record"][1]
CASE_MANIFEST_SCHEMA = SCHEMA_FILES["case_manifest"][1]
PROVENANCE_SCHEMA = SCHEMA_FILES["provenance"][1]
SCORER_OUTPUT_SCHEMA = SCHEMA_FILES["scorer_output"][1]

RUN_STATUSES = ("completed", "aborted_budget", "aborted_error", "invalid_usage")


def _check_schema(obj: dict, expected: str, kind: str) -> None:
    if obj.get("schema") != expected:
        raise ValueError(f"{kind}: schema string {obj.get('schema')!r} != {expected!r}")


# ---------------------------------------------------------------------------
# run_record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenUsage:
    """Per-arm actual token usage; numeric fields are None when usage_present is False."""

    input: Optional[int]
    output: Optional[int]
    cached: Optional[int]
    total: Optional[int]
    usage_present: bool
    llm_calls: int = 0

    def __post_init__(self) -> None:
        if not self.usage_present:
            if any(v is not None for v in (self.input, self.output, self.cached, self.total)):
                raise ValueError(
                    "TokenUsage with usage_present=False must carry all-null numerics (never zero-filled)"
                )
        else:
            if self.input is None or self.output is None or self.total is None:
                raise ValueError(
                    "TokenUsage with usage_present=True requires input/output/total; "
                    "use TokenUsage.absent() when the provider reported no usage"
                )

    @classmethod
    def absent(cls, llm_calls: int = 0) -> "TokenUsage":
        """Usage the provider never reported (never zero-filled)."""
        return cls(input=None, output=None, cached=None, total=None, usage_present=False, llm_calls=llm_calls)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": self.input,
            "output": self.output,
            "cached": self.cached,
            "total": self.total,
            "usage_present": self.usage_present,
            "llm_calls": self.llm_calls,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TokenUsage":
        for key in ("input", "output", "cached", "total"):
            value = d[key]
            if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
                raise ValueError(f"TokenUsage.{key} must be int or null, got {value!r}")
        return cls(
            input=d["input"],
            output=d["output"],
            cached=d["cached"],
            total=d["total"],
            usage_present=bool(d["usage_present"]),
            llm_calls=int(d.get("llm_calls", 0)),
        )


@dataclass(frozen=True)
class RunRecord:
    """One completed or aborted benchmark run for (case, arm, seed)."""

    run_id: str
    arm: str
    case: str
    seed: int
    model: str
    provider: str
    started_at: str
    finished_at: str
    status: str
    token_usage: TokenUsage
    tool_call_counts: Dict[str, int] = field(default_factory=dict)
    intervention_counts: Dict[str, int] = field(default_factory=dict)
    wall_s: float = 0.0
    abort_reason: Optional[str] = None
    provenance_sha256: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in RUN_STATUSES:
            raise ValueError(f"RunRecord.status {self.status!r} not in {RUN_STATUSES}")
        if (self.status == "completed") != (self.abort_reason is None):
            raise ValueError(
                "abort_reason must be set for aborted/invalid runs and null for completed runs"
            )

    def to_dict(self) -> Dict[str, Any]:
        intervention: Dict[str, Any] = {"total": sum(self.intervention_counts.values())}
        if self.intervention_counts:
            intervention["by_kind"] = dict(self.intervention_counts)
        return {
            "schema": RUN_RECORD_SCHEMA,
            "run_id": self.run_id,
            "arm": self.arm,
            "case": self.case,
            "seed": self.seed,
            "model": self.model,
            "provider": self.provider,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "token_usage": self.token_usage.to_dict(),
            "tool_call_counts": dict(self.tool_call_counts),
            "intervention_counts": intervention,
            "wall_s": self.wall_s,
            "abort_reason": self.abort_reason,
            "provenance_sha256": self.provenance_sha256,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RunRecord":
        _check_schema(d, RUN_RECORD_SCHEMA, "run_record")
        intervention = d.get("intervention_counts") or {}
        by_kind = intervention.get("by_kind", {})
        if by_kind and intervention.get("total") != sum(by_kind.values()):
            raise ValueError("intervention_counts.total must equal sum(by_kind)")
        return cls(
            run_id=d["run_id"],
            arm=d["arm"],
            case=d["case"],
            seed=int(d["seed"]),
            model=d["model"],
            provider=d["provider"],
            started_at=d["started_at"],
            finished_at=d["finished_at"],
            status=d["status"],
            token_usage=TokenUsage.from_dict(d["token_usage"]),
            tool_call_counts=dict(d.get("tool_call_counts") or {}),
            intervention_counts=dict(by_kind),
            wall_s=float(d["wall_s"]),
            abort_reason=d.get("abort_reason"),
            provenance_sha256=d.get("provenance_sha256"),
        )

    def validate(self):
        return validate_record("run_record", self.to_dict())


# ---------------------------------------------------------------------------
# case_manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GroundTruthPointer:
    """EVALUATOR-ONLY pointer to ground truth. Never embeds the content."""

    pointer: str
    sha256: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"pointer": self.pointer}
        if self.sha256 is not None:
            d["sha256"] = self.sha256
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GroundTruthPointer":
        return cls(pointer=d["pointer"], sha256=d.get("sha256"))


@dataclass(frozen=True)
class CaseManifest:
    """Pins one benchmark case to its exact upstream bytes and strata."""

    case_id: str
    source_benchmark: str
    pinned_sha: str
    data_hashes: Dict[str, str]
    strata: Dict[str, str] = field(default_factory=dict)
    heldout: bool = False
    ground_truth: Optional[GroundTruthPointer] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "schema": CASE_MANIFEST_SCHEMA,
            "case_id": self.case_id,
            "source_benchmark": self.source_benchmark,
            "pinned_sha": self.pinned_sha,
            "data_hashes": dict(self.data_hashes),
            "strata": dict(self.strata),
            "heldout": self.heldout,
        }
        if self.ground_truth is not None:
            d["ground_truth"] = self.ground_truth.to_dict()
        if self.notes is not None:
            d["notes"] = self.notes
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CaseManifest":
        _check_schema(d, CASE_MANIFEST_SCHEMA, "case_manifest")
        gt = d.get("ground_truth")
        return cls(
            case_id=d["case_id"],
            source_benchmark=d["source_benchmark"],
            pinned_sha=d["pinned_sha"],
            data_hashes=dict(d["data_hashes"]),
            strata=dict(d.get("strata") or {}),
            heldout=bool(d["heldout"]),
            ground_truth=GroundTruthPointer.from_dict(gt) if gt is not None else None,
            notes=d.get("notes"),
        )

    def validate(self):
        return validate_record("case_manifest", self.to_dict())


# ---------------------------------------------------------------------------
# provenance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UpstreamRepo:
    url: Optional[str] = None
    sha: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"sha": self.sha}
        if self.url is not None:
            d["url"] = self.url
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "UpstreamRepo":
        return cls(url=d.get("url"), sha=d["sha"])


@dataclass(frozen=True)
class Environment:
    python_version: str
    platform: str
    os_version: Optional[str] = None
    os_release: Optional[str] = None
    timezone: Optional[str] = None
    vars: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"python_version": self.python_version, "platform": self.platform}
        for key in ("os_version", "os_release", "timezone"):
            value = getattr(self, key)
            if value is not None:
                d[key] = value
        if self.vars:
            d["vars"] = dict(self.vars)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Environment":
        return cls(
            python_version=d["python_version"],
            platform=d["platform"],
            os_version=d.get("os_version"),
            os_release=d.get("os_release"),
            timezone=d.get("timezone"),
            vars=dict(d.get("vars") or {}),
        )


@dataclass(frozen=True)
class Provenance:
    """Reproducibility record for a run directory."""

    run_id: str
    captured_at: str
    repliclaw_git_sha: str
    repliclaw_dirty: bool
    dependency_pins: Dict[str, str]
    environment: Environment
    upstream_repos: Dict[str, UpstreamRepo] = field(default_factory=dict)
    dataset_sha256s: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "schema": PROVENANCE_SCHEMA,
            "run_id": self.run_id,
            "captured_at": self.captured_at,
            "repliclaw_git_sha": self.repliclaw_git_sha,
            "repliclaw_dirty": self.repliclaw_dirty,
            "dependency_pins": dict(self.dependency_pins),
            "environment": self.environment.to_dict(),
        }
        if self.upstream_repos:
            d["upstream_repos"] = {k: v.to_dict() for k, v in self.upstream_repos.items()}
        if self.dataset_sha256s:
            d["dataset_sha256s"] = dict(self.dataset_sha256s)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Provenance":
        _check_schema(d, PROVENANCE_SCHEMA, "provenance")
        return cls(
            run_id=d["run_id"],
            captured_at=d["captured_at"],
            repliclaw_git_sha=d["repliclaw_git_sha"],
            repliclaw_dirty=bool(d["repliclaw_dirty"]),
            dependency_pins=dict(d["dependency_pins"]),
            environment=Environment.from_dict(d["environment"]),
            upstream_repos={k: UpstreamRepo.from_dict(v) for k, v in (d.get("upstream_repos") or {}).items()},
            dataset_sha256s=dict(d.get("dataset_sha256s") or {}),
        )

    def validate(self):
        return validate_record("provenance", self.to_dict())


# ---------------------------------------------------------------------------
# scorer_output
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScorerCaseRow:
    case_id: str
    value: Any
    eligible: Optional[bool] = None
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"case_id": self.case_id, "value": self.value}
        if self.eligible is not None:
            d["eligible"] = self.eligible
        if self.note is not None:
            d["note"] = self.note
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ScorerCaseRow":
        return cls(case_id=d["case_id"], value=d["value"], eligible=d.get("eligible"), note=d.get("note"))


@dataclass(frozen=True)
class ScorerOutput:
    """One scored metric plus its raw per-case table."""

    metric: str
    value: Optional[float]
    denominator: Optional[int]
    formula_version: str
    per_case: Tuple[ScorerCaseRow, ...] = ()
    numerator: Optional[float] = None
    scored_at: Optional[str] = None
    run_ids: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "schema": SCORER_OUTPUT_SCHEMA,
            "metric": self.metric,
            "value": self.value,
            "denominator": self.denominator,
            "formula_version": self.formula_version,
            "per_case": [row.to_dict() for row in self.per_case],
        }
        if self.numerator is not None:
            d["numerator"] = self.numerator
        if self.scored_at is not None:
            d["scored_at"] = self.scored_at
        if self.run_ids:
            d["run_ids"] = list(self.run_ids)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ScorerOutput":
        _check_schema(d, SCORER_OUTPUT_SCHEMA, "scorer_output")
        rows = tuple(ScorerCaseRow.from_dict(r) for r in d.get("per_case") or [])
        case_ids = [r.case_id for r in rows]
        if case_ids != sorted(case_ids):
            raise ValueError("scorer_output.per_case must be sorted by case_id")
        return cls(
            metric=d["metric"],
            value=d["value"],
            denominator=d["denominator"],
            formula_version=d["formula_version"],
            per_case=rows,
            numerator=d.get("numerator"),
            scored_at=d.get("scored_at"),
            run_ids=tuple(d.get("run_ids") or ()),
        )

    def validate(self):
        return validate_record("scorer_output", self.to_dict())


__all__ = [
    "RUN_RECORD_SCHEMA",
    "CASE_MANIFEST_SCHEMA",
    "PROVENANCE_SCHEMA",
    "SCORER_OUTPUT_SCHEMA",
    "RUN_STATUSES",
    "TokenUsage",
    "RunRecord",
    "GroundTruthPointer",
    "CaseManifest",
    "UpstreamRepo",
    "Environment",
    "Provenance",
    "ScorerCaseRow",
    "ScorerOutput",
]
