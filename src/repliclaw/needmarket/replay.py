"""Content-addressed evidence snapshots + event replay (ticket P04).

``snapshot(evidence)`` is the sha256 of the canonical evidence dump — the
"observation changed" signal that drives ``choice_changed`` events. The
replay helper rebuilds broker-visible state from the event log so P07 can
do counterfactual replay: run the same worker cycle against two different
evidence snapshots and compare the observed rankings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from repliclaw.canonical import canonical_json, sha256_hex


def snapshot(evidence: Any) -> str:
    """Content-addressed sha256 of a canonical evidence dump.

    Deterministic: same evidence content → same sha, regardless of key
    order or whitespace. Accepts any JSON-serializable structure.
    """
    return sha256_hex(canonical_json(evidence))


def replay_events(events_path: Path) -> List[Dict[str, Any]]:
    """Re-read the broker event log (append-only; crashed writers cannot
    have rewritten history, so replay is a plain sequential parse)."""
    if not Path(events_path).exists():
        return []
    out: List[Dict[str, Any]] = []
    for ln in Path(events_path).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            out.append(json.loads(ln))
    return out


def ranking_from_events(
    events: List[Dict[str, Any]], agent_id: str
) -> List[Dict[str, Any]]:
    """Extract an agent's choice_ranked / choice_changed trail, in order."""
    out: List[Dict[str, Any]] = []
    for ev in events:
        p = ev.get("payload", {})
        if p.get("agent_id") != agent_id:
            continue
        if ev["kind"] in ("choice_ranked", "choice_changed"):
            out.append(p)
    return out


__all__ = ["snapshot", "replay_events", "ranking_from_events"]
