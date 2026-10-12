"""indepinfo: independent-information evidence escrow (Parts A + C).

Part A — evidence-partitioning boundary:
    Evidence / EvidenceSource / EvidenceRecord / EvidencePartition,
    partition_for_source, PartitionVault, InvestigatorView,
    IsolationViolation, UnknownSourceError

Part C — real LLM investigators inside the boundary (driven by
:mod:`repliclaw.investigators.LLMClient`):
    PartitionedInvestigator, InvestigatorConfig, InvestigatorReceipt,
    CallRecord, InvestigatorRunError, run_case

Sealing/reveal is delegated to :mod:`repliclaw.escrow` (not reimplemented).
"""
from .evidence import (
    Evidence,
    EvidencePartition,
    EvidenceRecord,
    EvidenceSource,
    UnknownSourceError,
    partition_for_source,
)
from .investigator import (
    RECEIPT_SCHEMA,
    CallRecord,
    InvestigatorConfig,
    InvestigatorReceipt,
    InvestigatorRunError,
    PartitionedInvestigator,
)
from .isolation import InvestigatorView, IsolationViolation, PartitionVault
from .runner import run_case

__all__ = [
    "Evidence",
    "EvidencePartition",
    "EvidenceRecord",
    "EvidenceSource",
    "UnknownSourceError",
    "partition_for_source",
    "IsolationViolation",
    "InvestigatorView",
    "PartitionVault",
    "CallRecord",
    "InvestigatorConfig",
    "InvestigatorReceipt",
    "InvestigatorRunError",
    "PartitionedInvestigator",
    "RECEIPT_SCHEMA",
    "run_case",
]
