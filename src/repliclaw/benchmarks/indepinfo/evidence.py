"""Evidence representation and per-source partitioning (indepinfo Part A).

The core construct of the independent-information experiment: evidence is a
set of named SOURCES, and each investigator receives exactly ONE partition
(:func:`partition_for_source`) — a self-contained, content-hashed subset.

There is deliberately NO aggregate/global score vector anywhere in this
module: the only derived quantity is the per-partition ``snapshot_sha256``,
computed from that source's records alone. An investigator holding a
partition has no reference to, and no bytes of, any other source.
"""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from repliclaw.canonical import canonical_json, sha256_hex


class UnknownSourceError(KeyError):
    """Raised when a source_id is not present in the evidence."""


class EvidenceRecord(BaseModel):
    """One atomic piece of evidence inside a source."""

    record_id: str
    data: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}


class EvidenceSource(BaseModel):
    """A named evidence source (one per investigator in the design)."""

    source_id: str
    name: str
    description: str = ""
    records: List[EvidenceRecord] = Field(default_factory=list)

    model_config = {"frozen": True}


class Evidence(BaseModel):
    """The full case evidence: a set of named sources.

    NOTE: by design this model has NO aggregate score vector, no global
    summary, and no cross-source rollup. The only derived quantity in this
    module is the per-partition snapshot hash.
    """

    case_id: str
    case_brief: str = ""
    sources: List[EvidenceSource] = Field(min_length=1)

    model_config = {"frozen": True}


class EvidencePartition(BaseModel):
    """The complete, self-contained view of ONE source for one investigator.

    ``snapshot_sha256`` is the content hash of this partition alone
    (case_id + source_id + that source's records). It is the value an
    investigator must record as ``prior_evidence_snapshot_sha256`` in its
    escrow packet — never a hash of any aggregate/global vector.
    """

    case_id: str
    source_id: str
    source_name: str
    source_description: str
    records: List[EvidenceRecord] = Field(default_factory=list)
    snapshot_sha256: str

    model_config = {"frozen": True}


def partition_for_source(evidence: Evidence, source_id: str) -> EvidencePartition:
    """Return ONLY ``source_id``'s subset of ``evidence``.

    The result is self-contained: an investigator holding the partition has
    no reference to, and no bytes of, any other source.
    """
    src = next((s for s in evidence.sources if s.source_id == source_id), None)
    if src is None:
        raise UnknownSourceError(
            f"source {source_id!r} not in evidence for case {evidence.case_id!r}"
        )
    body = {
        "case_id": evidence.case_id,
        "source_id": src.source_id,
        "records": [r.model_dump() for r in src.records],
    }
    return EvidencePartition(
        case_id=evidence.case_id,
        source_id=src.source_id,
        source_name=src.name,
        source_description=src.description,
        records=list(src.records),
        snapshot_sha256=sha256_hex(canonical_json(body)),
    )


__all__ = [
    "Evidence",
    "EvidencePartition",
    "EvidenceRecord",
    "EvidenceSource",
    "UnknownSourceError",
    "partition_for_source",
]
