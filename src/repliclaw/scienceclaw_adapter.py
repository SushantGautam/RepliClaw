"""Thin adapter over vendored ScienceClaw (DECISIONS.md D01/D04).

Reuses, unmodified:
- `artifacts.artifact.Artifact` — content-hashed, lineage-bearing artifact
- `artifacts.artifact.ArtifactStore` — JSONL persistence (via run-local subclass)
- `artifacts.needs.NeedItem` — unmet-need signal
- `artifacts.pressure.score_need` — deterministic need urgency

Adds:
- `RunLocalArtifactStore` — run-scoped base dir (upstream hardcodes ~/.scienceclaw)
- `needs_from_run` — bridges RepliClaw FollowUpNeed → ScienceClaw NeedItem
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_DEPS = Path(__file__).resolve().parent.parent.parent / "deps" / "scienceclaw"


def _ensure_sc_path() -> None:
    if str(_DEPS) not in sys.path:
        sys.path.insert(0, str(_DEPS))


_ensure_sc_path()

from artifacts.artifact import Artifact, ArtifactStore  # noqa: E402
from artifacts.needs import NeedItem  # noqa: E402
from artifacts.pressure import NeedRef, score_need  # noqa: E402


class RunLocalArtifactStore(ArtifactStore):
    """ArtifactStore rooted at a per-run directory instead of ~/.scienceclaw.

    Keeps upstream behavior (JSONL store + global index + content hash +
    lineage) but scopes everything to the run so runs are hermetic and the
    shared index cannot leak between claims (independence by construction).
    """

    def __init__(self, agent_name: str, base_dir: str | Path):
        # Bypass upstream __init__ (it hardcodes ~) and rebuild paths.
        self.agent_name = agent_name
        self._base = Path(base_dir)
        self.store_path = self._base / "artifacts" / agent_name / "store.jsonl"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._global_index_path = self._base / "global_index.jsonl"
        self._id_index: Optional[Dict[str, int]] = None

    # Upstream methods reference self._base / self.store_path — both set above.


def artifact_from_finding(
    agent_id: str,
    investigation_id: str,
    finding: Dict[str, Any],
    artifact_type: str = "analysis_result",
    parent_artifact_ids: Optional[List[str]] = None,
    result_quality: str = "ok",
    needs: Optional[List[Dict[str, Any]]] = None,
    summary: str = "",
) -> Artifact:
    """Create (not yet save) a ScienceClaw Artifact from a revealed finding."""
    return Artifact.create(
        artifact_type=artifact_type,
        producer_agent=agent_id,
        skill_used="repliclaw-investigation",
        payload=finding,
        investigation_id=investigation_id,
        parent_artifact_ids=parent_artifact_ids or [],
        result_quality=result_quality,
        needs=needs or [],
        summary=summary or finding.get("conclusion", "")[:200],
    )


def needs_to_need_items(needs: List[Dict[str, Any]]) -> List[NeedItem]:
    """Bridge RepliClaw needs dicts → ScienceClaw NeedItem (validates the
    native schema is usable for replication/falsification needs)."""
    items = []
    for n in needs:
        items.append(
            NeedItem(
                artifact_type=n.get("artifact_type", "analysis_result"),
                query=n["query"],
                rationale=n["rationale"],
                branch=n.get("branch", True),
            )
        )
    return items


def pressure_score(
    need: Dict[str, Any],
    parent_artifact_id: str,
    producer_agent: str,
    investigation_id: str,
    global_index_lines: Optional[List[Dict[str, Any]]] = None,
    depth: int = 0,
) -> float:
    """Deterministic urgency via upstream score_need (D04)."""
    ref = NeedRef(
        parent_artifact_id=parent_artifact_id,
        need_index=0,
        producer_agent=producer_agent,
        investigation_id=investigation_id,
        artifact_type=need.get("artifact_type", "analysis_result"),
        query=need["query"],
        rationale=need["rationale"],
        parent_timestamp=need.get("created_at", ""),
    )
    return score_need(need=ref, depth=depth, global_index_lines=global_index_lines or [])
