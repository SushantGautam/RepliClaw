"""Falsification comparison: independent evidence escrow vs pooled analysis.

A matched 4-arm comparison on the adversarial scientific-audit dataset
(RX-441) that MEASURES whether INDEPENDENT EVIDENCE ESCROW (each investigator
sees only its own source, seals a prediction before disclosure, then reveals
and aggregates) helps under fragmented, contradictory, and deceptive evidence
— versus pooled analysis. A null/negative result is a valid outcome; nothing
here is rigged to make any arm win.

Arms (all driven by real LLM calls, matched on total spend + allowed
experiments, over the same evidence union):
  * ``escrowed_independent`` (treatment) — N=4 partitioned investigators,
    one per source, sealed per-claim verdicts, reveal + majority aggregate.
  * ``open_sharing`` — N=4 investigators over all evidence, share then finalize.
  * ``central_adaptive`` — ONE strong central manager over all evidence.
  * ``single_investigator`` — ONE investigator over all evidence, single pass.

Public surface:
  * :class:`MatchedCaps` / :data:`DEFAULT_CAPS` — the matched per-claim envelope.
  * :data:`ARM_NAMES` / :data:`ARM_RUNNERS` / :class:`ArmResult` — the arms.
  * :func:`run_comparison` / :func:`make_client_factory` — the orchestrator.
  * :func:`score_arm` / :func:`score_all` / :func:`trap_claim_ids` — the
    EVALUATOR-ONLY scorer (the sole ground-truth reader).
  * :class:`MockLLMClient` — the offline double for ``--dry-run``.

Run it:
    uv run python -m repliclaw.benchmarks.falsification \
        --claims C1,C2,C3 --arms escrowed_independent,open_sharing,central_adaptive,single_investigator \
        --out <dir> [--dry-run]
"""
from .arms import (
    ARM_NAMES,
    ARM_RUNNERS,
    ArmResult,
    majority,
    parse_verdict_from_statement,
    run_central,
    run_escrowed,
    run_open_sharing,
    run_single,
)
from .config import DEFAULT_CAPS, MatchedCaps
from .evidence import (
    all_artifacts,
    artifact_index,
    build_evidence,
    claim_by_id,
    claim_ids,
    dataset_sha256,
    pooled_evidence_block,
)
from .mock import MockLLMClient
from .pooled import PooledInvestigator, PooledReceipt, PooledRunError
from .runner import RESULTS_SCHEMA, make_client_factory, run_comparison
from .scoring import score_all, score_arm, trap_claim_ids

__all__ = [
    "ARM_NAMES",
    "ARM_RUNNERS",
    "ArmResult",
    "majority",
    "parse_verdict_from_statement",
    "run_escrowed",
    "run_open_sharing",
    "run_central",
    "run_single",
    "MatchedCaps",
    "DEFAULT_CAPS",
    "all_artifacts",
    "artifact_index",
    "build_evidence",
    "claim_by_id",
    "claim_ids",
    "dataset_sha256",
    "pooled_evidence_block",
    "MockLLMClient",
    "PooledInvestigator",
    "PooledReceipt",
    "PooledRunError",
    "RESULTS_SCHEMA",
    "make_client_factory",
    "run_comparison",
    "score_arm",
    "score_all",
    "trap_claim_ids",
]
