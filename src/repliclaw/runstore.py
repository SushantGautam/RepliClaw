"""Run-local, append-only persistence for commitments, evidence, needs, and
events.

Design goals (DECISIONS.md D02/D03):
- Everything for one verification run lives under a single run directory
  (run-local isolation; no shared ~/.scienceclaw).
- Append-only JSONL + content-addressed commitment store → tamper-evident.
- The event log records, per phase, exactly which materials each agent could
  see — the auditable proof of pre-reveal independence.

Layout:
    {root}/
      run.json                  # RunMetadata
      claims.json
      commitments/{commitment_id}.json   # sealed commitment records
      evidence.jsonl
      needs.jsonl
      events.jsonl              # append-only audit trail
      artifacts/                # RunLocalArtifactStore base (see adapter)
      verdict.json
      report.md
      metrics.json
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    Commitment,
    CommitmentPhase,
    Claim,
    Evidence,
    EvidenceRelation,
    FollowUpNeed,
    Verdict,
)
from . import canonical

_LOCK = threading.Lock()

# Volatile fields excluded from the commitment seal: they change at reveal
# time, so the seal is computed over everything else.
_SEAL_EXCLUDE = ("revealed_content", "reveal_timestamp", "reveal_verified", "seal_hash")


def _seal_hash(record: Dict[str, Any]) -> str:
    return canonical.commit_hash({k: v for k, v in record.items() if k not in _SEAL_EXCLUDE})


def _verify_seal(d: Dict[str, Any]) -> None:
    seal_expected = d.get("seal_hash")
    if seal_expected is None:
        return
    if _seal_hash(d) != seal_expected:
        raise RevealMismatchError("commitment record tampered (seal mismatch)")


class RevealMismatchError(Exception):
    """Raised when revealed content does not match its commitment hash."""


class CommitmentStoreError(Exception):
    pass


class RunStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.commitments_dir = self.root / "commitments"
        self.artifacts_dir = self.root / "artifacts"
        for p in (self.root, self.commitments_dir, self.artifacts_dir):
            p.mkdir(parents=True, exist_ok=True)

    # ---- events ---------------------------------------------------------
    def event(self, kind: str, agent_id: str = "orchestrator", **data: Any) -> None:
        entry = {
            "kind": kind,
            "agent_id": agent_id,
            "ts": _ts(),
            **data,
        }
        with _LOCK:
            with open(self.root / "events.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def events(self) -> List[Dict[str, Any]]:
        p = self.root / "events.jsonl"
        if not p.exists():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    # ---- claim / run -----------------------------------------------------
    def save_claim(self, claim: Claim) -> None:
        (self.root / "claims.json").write_text(
            json.dumps(claim.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self.event("claim_ingested", claim_id=claim.claim_id, statement=claim.statement[:200])

    def save_run(self, run_meta: Dict[str, Any]) -> None:
        (self.root / "run.json").write_text(
            json.dumps(run_meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def load_claim(self) -> Optional[Claim]:
        p = self.root / "claims.json"
        if not p.exists():
            return None
        return Claim.model_validate(json.loads(p.read_text(encoding="utf-8")))

    # ---- commitments ------------------------------------------------------
    def commit(self, commitment: Commitment) -> str:
        """Persist a commitment in BLIND→COMMITTED state. Returns commitment_id.

        The sealed record contains only the hash + metadata; the content is
        included so that reveal can be re-verified offline, but phase gates
        (isolation.py) prevent reading it before reveal.
        """
        if commitment.phase not in (CommitmentPhase.BLIND, CommitmentPhase.COMMITTED):
            raise CommitmentStoreError("commit() expects a BLIND/COMMITTED commitment")
        commitment.phase = CommitmentPhase.COMMITTED
        path = self.commitments_dir / f"{commitment.commitment_id}.json"
        payload = commitment.to_dict()
        # Integrity: seal the hash over everything except volatile fields.
        payload["seal_hash"] = _seal_hash(payload)
        with _LOCK:
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self.event(
            "committed",
            agent_id=commitment.agent_id,
            commitment_id=commitment.commitment_id,
            content_hash=commitment.content_hash,
            seal_hash=payload["seal_hash"],
            phase="committed",
        )
        return commitment.commitment_id

    def get_commitment(self, commitment_id: str, reveal: bool = False) -> Optional[Commitment]:
        path = self.commitments_dir / f"{commitment_id}.json"
        if not path.exists():
            return None
        d = json.loads(path.read_text(encoding="utf-8"))
        _verify_seal(d)
        phase = CommitmentPhase(d["phase"])
        if not reveal and phase == CommitmentPhase.REVEALED:
            # Hide revealed content unless the caller is in the reveal phase.
            d["revealed_content"] = None
        c = Commitment(
            commitment_id=d["commitment_id"],
            claim_id=d["claim_id"],
            agent_id=d["agent_id"],
            role=d["role"],
            content=d.get("content", {}),
            content_hash=d["content_hash"],
            phase=phase,
            timestamp=d.get("timestamp", ""),
            model=d.get("model", "default"),
            evidence_refs=d.get("evidence_refs", []),
            revealed_content=d.get("revealed_content"),
            reveal_timestamp=d.get("reveal_timestamp"),
            reveal_verified=d.get("reveal_verified"),
        )
        return c

    def list_commitments(self) -> List[Dict[str, Any]]:
        out = []
        for p in sorted(self.commitments_dir.glob("*.json")):
            out.append(json.loads(p.read_text(encoding="utf-8")))
        return out

    def verify_reveal(self, commitment_id: str, revealed_content: Dict[str, Any]) -> Dict[str, Any]:
        """Verify revealed content against the persisted commitment and persist
        the revealed state. Raises RevealMismatchError on any mismatch."""
        d_path = self.commitments_dir / f"{commitment_id}.json"
        d = json.loads(d_path.read_text(encoding="utf-8"))
        _verify_seal(d)
        phase = CommitmentPhase(d["phase"])
        if phase == CommitmentPhase.REVEALED:
            if d.get("reveal_verified") is False:
                raise RevealMismatchError(f"commitment {commitment_id} was already rejected")
            return {"verified": d.get("reveal_verified") is True, "already_revealed": True}
        if phase == CommitmentPhase.REJECTED:
            # One-shot reveal: a commitment whose reveal mismatched is terminal.
            # Allowing a later "correct" reveal would let an agent game the
            # protocol (commit truth, reveal a doctored lie, then fix it).
            raise RevealMismatchError(f"commitment {commitment_id} is REJECTED (one-shot reveal; no re-reveal allowed)")
        if d["content_hash"] != canonical.commit_hash(revealed_content):
            self.event(
                "reveal_mismatch",
                commitment_id=commitment_id,
                expected=d["content_hash"][:16],
                got=canonical.commit_hash(revealed_content)[:16],
            )
            d["phase"] = CommitmentPhase.REJECTED.value
            d["revealed_content"] = revealed_content
            d["reveal_timestamp"] = d.get("reveal_timestamp") or _ts()
            d["reveal_verified"] = False
            d["seal_hash"] = _seal_hash(d)
            d_path.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
            raise RevealMismatchError(
                f"reveal content does not match commitment {commitment_id} "
                f"(expected {d['content_hash'][:16]}, got "
                f"{canonical.commit_hash(revealed_content)[:16]})"
            )
        # Match → mark revealed + verified.
        d["phase"] = CommitmentPhase.REVEALED.value
        d["revealed_content"] = revealed_content
        d["reveal_verified"] = True
        d["reveal_timestamp"] = _ts()
        d["seal_hash"] = _seal_hash(d)
        d_path.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        self.event(
            "revealed",
            agent_id=d["agent_id"],
            commitment_id=commitment_id,
            content_hash=d["content_hash"],
            verified=True,
        )
        return {"verified": True, "already_revealed": False}

    # ---- evidence / needs --------------------------------------------------
    def append_evidence(self, ev: Evidence) -> None:
        with _LOCK:
            with open(self.root / "evidence.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")
        self.event("evidence_recorded", agent_id=ev.agent_id, evidence_id=ev.evidence_id, relation=ev.relation.value)

    def evidence(self) -> List[Evidence]:
        p = self.root / "evidence.jsonl"
        if not p.exists():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out.append(
                Evidence(
                    evidence_id=d["evidence_id"],
                    claim_id=d["claim_id"],
                    agent_id=d["agent_id"],
                    relation=EvidenceRelation(d["relation"]),
                    finding=d["finding"],
                    commitment_id=d.get("commitment_id"),
                    artifact_ids=d.get("artifact_ids", []),
                    executable=d.get("executable", False),
                    quality=d.get("quality", "ok"),
                    confidence=d.get("confidence", 0.5),
                    timestamp=d.get("timestamp", ""),
                    independent_of=d.get("independent_of", []),
                    notes=d.get("notes", ""),
                )
            )
        return out

    def append_need(self, need: FollowUpNeed) -> None:
        with _LOCK:
            with open(self.root / "needs.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps(_need_dict(need), ensure_ascii=False) + "\n")
        self.event("need_emitted", need_id=need.need_id, kind_value=need.kind.value, query=need.query[:160])

    def update_need(self, need_id: str, **updates: Any) -> None:
        p = self.root / "needs.jsonl"
        if not p.exists():
            return
        lines = p.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines:
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("need_id") == need_id:
                d.update(updates)
            out.append(json.dumps(d, ensure_ascii=False))
        with _LOCK:
            p.write_text("\n".join(out) + "\n", encoding="utf-8")
        if "status" in updates:
            self.event("need_updated", need_id=need_id, status=updates["status"],
                       fulfilled_by_artifact_id=updates.get("fulfilled_by_artifact_id"))

    def needs(self) -> List[Dict[str, Any]]:
        p = self.root / "needs.jsonl"
        if not p.exists():
            return []
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]

    # ---- verdict ----------------------------------------------------------
    def save_verdict(self, verdict: Verdict) -> None:
        (self.root / "verdict.json").write_text(
            json.dumps(verdict.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self.event("verdict", label=verdict.label.value, confidence=verdict.confidence)

    def save_report(self, markdown: str) -> None:
        (self.root / "report.md").write_text(markdown, encoding="utf-8")

    def save_metrics(self, metrics: Dict[str, Any]) -> None:
        (self.root / "metrics.json").write_text(
            json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _need_dict(n: FollowUpNeed) -> Dict[str, Any]:
    d = asdict(n)
    d["kind"] = n.kind.value
    return d
