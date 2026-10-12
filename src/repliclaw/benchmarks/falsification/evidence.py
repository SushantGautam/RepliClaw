"""Adapt the adversarial-audit dataset to the two evidence shapes the arms need.

* The ESCROWED arm consumes an :class:`repliclaw.benchmarks.indepinfo.Evidence`
  (named sources, each a partition of content-hashed records). We build one
  :class:`Evidence` per claim: the sources/records are identical across claims,
  but ``case_id`` is the claim id and ``case_brief`` carries the claim
  statement + the verdict-commit instruction (the case brief is a shared task
  description, not evidence, so it is safe for every investigator).

* The POOLED arms consume the flat list of ALL artifacts (the union). No arm
  gets secret extra evidence: the escrowed arm's partitions exactly cover the
  same union the pooled arms see.

This module reads ONLY the public loader
(:mod:`repliclaw.benchmarks.adversarial_audit.data`). It never touches ground
truth or trap annotations — those are evaluator-only and live in the scorer.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from repliclaw.benchmarks.adversarial_audit import data as aa_data
from repliclaw.benchmarks.indepinfo import Evidence, EvidenceRecord, EvidenceSource

#: Instruction appended to every escrowed investigator's case brief so the
#: sealed packet's ``hypothesis_statement`` carries a machine-parseable verdict.
VERDICT_INSTRUCTION = (
    "When you commit, your hypothesis_statement MUST begin with exactly one of "
    '"VERDICT: TRUE", "VERDICT: FALSE", or "VERDICT: ABSTAIN" (use ABSTAIN if '
    "your single source is insufficient to decide the claim as worded), "
    "followed by a one-sentence justification grounded in your source's records."
)


def all_artifacts() -> List[Dict[str, Any]]:
    """The full public evidence union (all 18 artifacts), in stable order."""
    return aa_data.load_evidence()


def artifact_index() -> Dict[str, Dict[str, Any]]:
    """``{artifact_id: artifact}`` over the full union."""
    return {a["artifact_id"]: a for a in all_artifacts()}


def dataset_sha256() -> str:
    """Content hash of the public dataset (claims + evidence), for provenance."""
    payload = {
        "claims": aa_data.load_claims(),
        "evidence": aa_data.load_evidence(),
        "sources": aa_data.list_sources(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def claim_by_id(claim_id: str) -> Dict[str, Any]:
    for c in aa_data.load_claims():
        if c["claim_id"] == claim_id:
            return c
    raise KeyError(f"unknown claim {claim_id!r}")


def claim_ids() -> List[str]:
    return [c["claim_id"] for c in aa_data.load_claims()]


def _source_records(source_id: str) -> List[EvidenceRecord]:
    """One :class:`EvidenceRecord` per artifact in the source's partition."""
    records = []
    for art in aa_data.evidence_for_source(source_id):
        records.append(
            EvidenceRecord(
                record_id=art["artifact_id"],
                data={
                    "artifact_id": art["artifact_id"],
                    "title": art["title"],
                    "type": art["type"],
                    "content": art["content"],
                    "claims_addressed": art.get("claims_addressed", []),
                },
            )
        )
    return records


def build_evidence(claim_id: str) -> Evidence:
    """Build the per-claim :class:`Evidence` for the escrowed arm.

    ``case_id`` is the claim id; ``case_brief`` names the claim and instructs
    the verdict-commit format. The four source partitions are the dataset's
    named sources, each holding exactly its own artifacts.
    """
    claim = claim_by_id(claim_id)
    case_brief = (
        f"CLAIM {claim['claim_id']}: {claim['statement']}\n"
        "Task: decide whether this claim is TRUE or FALSE exactly as worded, "
        "using ONLY your own source's records. Weigh each artifact's "
        "methodology (validation status, sample size, confidence intervals, "
        "confounders, allocation) before trusting its headline number. A claim "
        "is TRUE only if the evidence supports it exactly as stated; a "
        "materially different magnitude, or a confounded association presented "
        "as causal, makes it FALSE.\n" + VERDICT_INSTRUCTION
    )
    sources = [
        EvidenceSource(
            source_id=s["source_id"],
            name=s["name"],
            description=s["description"],
            records=_source_records(s["source_id"]),
        )
        for s in aa_data.list_sources()
    ]
    return Evidence(case_id=claim_id, case_brief=case_brief, sources=sources)


def pooled_evidence_block(claim_id: str) -> str:
    """Render the FULL evidence union (all artifacts) as a prompt block.

    This is what the pooled arms (open_sharing, central_adaptive,
    single_investigator) see: every artifact, with its source, so they can
    cross-reference. The escrowed arm never receives this block.
    """
    claim = claim_by_id(claim_id)
    lines = [f"CLAIM {claim['claim_id']}: {claim['statement']}", "", "EVIDENCE ARTIFACTS (all sources):"]
    for i, art in enumerate(all_artifacts()):
        lines.append(
            f"[{i}] {art['artifact_id']} (source: {art['source']}, type: {art['type']}) "
            f"— {art['title']}"
        )
        lines.append(f"    {art['content']}")
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "VERDICT_INSTRUCTION",
    "all_artifacts",
    "artifact_index",
    "dataset_sha256",
    "claim_by_id",
    "claim_ids",
    "build_evidence",
    "pooled_evidence_block",
]
