"""RepliClaw domain model.

Small, stable dataclasses + pydantic records for the verification protocol.
Kept deliberately dependency-light (pydantic only) so the core is hermetic.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def commit_payload(finding: Dict[str, Any]) -> Dict[str, Any]:
    """The exact, canonical content an investigator commits to AND reveals.

    Commit and reveal MUST hash the same object, so both go through here.
    Doctored reveals change one of these fields and fail the hash check.
    """
    try:
        conf = float(finding.get("confidence", 0.5) or 0.5)
    except (TypeError, ValueError):
        conf = 0.5
    return {
        "conclusion": str(finding.get("conclusion", "uncertain")),
        "statement": str(finding.get("statement", "")),
        "plan": str(finding.get("plan", "")),
        "evidence": finding.get("evidence", {}) or {},
        "confidence": conf,
        "executable": bool(finding.get("executable", False)),
    }


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------
class Claim(BaseModel):
    """A structured scientific claim to be verified."""

    claim_id: str = Field(default_factory=lambda: _uid("claim"))
    statement: str
    domain: str = "general"
    subclaims: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    # Optional structured data/code context bundled with the claim.
    data: Optional[Dict[str, Any]] = None
    source_artifacts: List[str] = Field(default_factory=list)  # artifact ids
    reference_truth: Optional[str] = None  # "supported"|"refuted"|None (benchmark only)
    seeded_fault: Optional[str] = None  # fault-mode tag (benchmark only)
    created_at: str = Field(default_factory=_now)


class Subclaim(BaseModel):
    claim_id: str
    text: str
    index: int = 0


# ---------------------------------------------------------------------------
# Investigator identity / context
# ---------------------------------------------------------------------------
class InvestigatorRole(str, Enum):
    ANALYST = "analyst"
    STATISTICIAN = "statistician"
    FALSIFIER = "falsifier"
    CRITIC = "critic"


@dataclass
class InvestigatorConfig:
    agent_id: str
    role: InvestigatorRole
    # Which evidence sources / tools this investigator may access.
    allowed_sources: List[str] = field(default_factory=list)
    # Model/tool differentiation is allowed; keep it explicit for comparability.
    model: str = "default"
    seed_note: str = ""  # descriptive note of the investigator's stance


# ---------------------------------------------------------------------------
# Commitment
# ---------------------------------------------------------------------------
class CommitmentPhase(str, Enum):
    BLIND = "blind"  # pre-reveal; conclusion/plan not yet visible to peers
    COMMITTED = "committed"  # tamper-evident record persisted
    REVEALED = "revealed"  # content revealed + verified against commitment
    REJECTED = "rejected"  # reveal did not match commitment


@dataclass
class Commitment:
    commitment_id: str
    claim_id: str
    agent_id: str
    role: str
    # Canonicalized content being committed (hypothesis/conclusion + plan + evidence meta).
    content: Dict[str, Any]
    content_hash: str
    phase: CommitmentPhase = CommitmentPhase.BLIND
    timestamp: str = field(default_factory=_now)
    # Integrity/provenance extras
    model: str = "default"
    evidence_refs: List[str] = field(default_factory=list)
    revealed_content: Optional[Dict[str, Any]] = None
    reveal_timestamp: Optional[str] = None
    reveal_verified: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commitment_id": self.commitment_id,
            "claim_id": self.claim_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "content_hash": self.content_hash,
            "phase": self.phase.value,
            "timestamp": self.timestamp,
            "model": self.model,
            "evidence_refs": self.evidence_refs,
            "revealed_content": self.revealed_content,
            "reveal_timestamp": self.reveal_timestamp,
            "reveal_verified": self.reveal_verified,
            "content": self.content,
        }


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------
class EvidenceRelation(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    REPLICATES = "replicates"
    FAILS_TO_REPLICATE = "fails_to_replicate"
    DEPENDS_ON = "depends_on"
    NEUTRAL = "neutral"


@dataclass
class Evidence:
    evidence_id: str
    claim_id: str
    agent_id: str
    relation: EvidenceRelation
    # The revealed conclusion/findings this evidence carries.
    finding: Dict[str, Any]
    # Provenance: the commitment that produced it + artifact lineage.
    commitment_id: Optional[str] = None
    artifact_ids: List[str] = field(default_factory=list)
    # Executable evidence is weighted more heavily than opinion.
    executable: bool = False
    quality: str = "ok"  # ok | empty | suspicious
    confidence: float = 0.5  # 0..1, investigator-reported
    timestamp: str = field(default_factory=_now)
    # Independence / provenance assertions
    independent_of: List[str] = field(default_factory=list)  # evidence_ids
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "claim_id": self.claim_id,
            "agent_id": self.agent_id,
            "relation": self.relation.value,
            "finding": self.finding,
            "commitment_id": self.commitment_id,
            "artifact_ids": self.artifact_ids,
            "executable": self.executable,
            "quality": self.quality,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "independent_of": self.independent_of,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Needs (plannerless follow-up)
# ---------------------------------------------------------------------------
class NeedKind(str, Enum):
    REPLICATION = "replication"
    FALSIFICATION = "falsification"
    COUNTERFACTUAL = "counterfactual"
    DATA_QUALITY = "data_quality"


@dataclass
class FollowUpNeed:
    need_id: str
    claim_id: str
    kind: NeedKind
    query: str
    rationale: str
    # Which prior evidence triggered this need (provenance).
    triggered_by: List[str] = field(default_factory=list)
    artifact_type: str = "analysis_result"
    status: str = "open"  # open | fulfilled | dropped
    fulfilled_by_artifact_id: Optional[str] = None
    # Deterministic urgency (mirrors ScienceClaw pressure scoring).
    priority: float = 0.0
    created_at: str = field(default_factory=_now)


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
class VerdictLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class Verdict:
    claim_id: str
    label: VerdictLabel
    confidence: float  # 0..1 calibration-ish
    # Transparent decomposition of how the verdict was reached.
    n_support: int = 0
    n_contradict: int = 0
    n_replicate: int = 0
    n_fail_replicate: int = 0
    independent_evidence_count: int = 0
    unresolved_conflicts: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    reasoning: str = ""
    error_correlation: Optional[float] = None  # -1..1 proxy
    timestamp: str = field(default_factory=_now)
    # A9 (PREREG v1.2 A9.2.2 / M-1 fix): the arm-neutral defect adjudication
    # aggregate for THIS arm's run, computed in strategies._finalize (or
    # run_repl_claw) from the FULL finding dicts (evidence[*].finding, C8) and
    # carried here so the artifact writers (comparators/runner.py) record the
    # arm's REAL diagnosis instead of hard-coded nulls. Both are None when no
    # finding in the arm supplied a non-null value (e.g. the offline
    # deterministic legs on non-policy-rag cases).
    defect_class: Optional[str] = None
    target_artifact: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "label": self.label.value,
            "confidence": self.confidence,
            "n_support": self.n_support,
            "n_contradict": self.n_contradict,
            "n_replicate": self.n_replicate,
            "n_fail_replicate": self.n_fail_replicate,
            "independent_evidence_count": self.independent_evidence_count,
            "unresolved_conflicts": self.unresolved_conflicts,
            "evidence_refs": self.evidence_refs,
            "reasoning": self.reasoning,
            "error_correlation": self.error_correlation,
            "timestamp": self.timestamp,
            "defect_class": self.defect_class,
            "target_artifact": self.target_artifact,
        }


# ---------------------------------------------------------------------------
# Run metadata (resource/comparability)
# ---------------------------------------------------------------------------
@dataclass
class ResourceUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tool_calls: int = 0
    llm_calls: int = 0
    wall_clock_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
            "llm_calls": self.llm_calls,
            "wall_clock_s": self.wall_clock_s,
        }


@dataclass
class RunMetadata:
    run_id: str = field(default_factory=lambda: _uid("run"))
    claim_id: str = ""
    strategy: str = "repl_claw"  # one of the 5 baselines
    protocol_version: str = "v1"
    model: str = "default"
    n_investigators: int = 0
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    completed_at: Optional[str] = None
    usage: Optional[ResourceUsage] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "claim_id": self.claim_id,
            "strategy": self.strategy,
            "protocol_version": self.protocol_version,
            "model": self.model,
            "n_investigators": self.n_investigators,
            "config": self.config,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "usage": self.usage.to_dict() if self.usage else None,
        }
