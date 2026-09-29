"""Evidence graph, conflict detection, and error-correlation proxies.

The graph is built with NetworkX (ADOPT_LIBRARY, DECISIONS.md). Nodes are
claims/evidence; edges carry relation semantics. Independence is a graph
property, not an assertion: two pieces of evidence are independent if they
were produced by different agents whose pre-reveal contexts were disjoint
(enforced in isolation.py and logged in events.jsonl).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import networkx as nx

from .models import Evidence, EvidenceRelation


def build_evidence_graph(evidence: List[Evidence], claim_id: str = "") -> nx.DiGraph:
    G: nx.DiGraph = nx.DiGraph()
    if claim_id:
        G.add_node(claim_id, kind="claim")
    for ev in evidence:
        G.add_node(
            ev.evidence_id,
            kind="evidence",
            agent=ev.agent_id,
            relation=ev.relation.value,
            executable=ev.executable,
            confidence=ev.confidence,
            commitment=ev.commitment_id,
            artifacts=ev.artifact_ids,
            independent_of=ev.independent_of,
        )
        if ev.claim_id:
            G.add_edge(ev.claim_id, ev.evidence_id, relation=ev.relation.value)
        for other in ev.independent_of:
            G.add_edge(ev.evidence_id, other, relation="depends_on")
    return G


def to_dict(G: nx.DiGraph) -> Dict[str, Any]:
    return {
        "nodes": [
            {"id": n, **data} for n, data in G.nodes(data=True)
        ],
        "edges": [
            {"src": u, "dst": v, **data} for u, v, data in G.edges(data=True)
        ],
    }


def graph_report(G: nx.DiGraph) -> Dict[str, Any]:
    """Compact, deterministic summary of the evidence graph."""
    nodes = list(G.nodes(data=True))
    return {
        "n_nodes": G.number_of_nodes(),
        "n_edges": G.number_of_edges(),
        "n_evidence": sum(1 for _, d in nodes if d.get("kind") == "evidence"),
        "n_agents": len({d.get("agent") for _, d in nodes if d.get("agent")}),
        "by_relation": _count_by(nodes, "relation"),
        "independent_pairs": count_independent_pairs(nodes),
        "json": to_dict(G),
    }


def _count_by(nodes, key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for _, d in nodes:
        k = d.get(key)
        if k:
            out[k] = out.get(k, 0) + 1
    return out


def count_independent_pairs(nodes) -> int:
    """Number of unordered evidence pairs from distinct agents (diversity)."""
    agents = [d.get("agent") for _, d in nodes if d.get("kind") == "evidence"]
    pairs = 0
    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            if agents[i] != agents[j]:
                pairs += 1
    return pairs


# ---------------------------------------------------------------------------
# Conflict detection (deterministic boundary)
# ---------------------------------------------------------------------------
def detect_conflicts(evidence: List[Evidence]) -> List[Dict[str, Any]]:
    """Return a list of conflict records.

    Deterministic rule: a conflict exists when at least one piece of
    (independent, non-suspicious) evidence SUPPORTS the claim and at least
    one CONTRADICTS it. The record lists the agents and the quantitative
    anchors so the report can show exactly what disagreed.
    """
    support = [e for e in evidence if e.relation == EvidenceRelation.SUPPORTS and e.quality != "suspicious"]
    contradict = [
        e for e in evidence
        if e.relation in (EvidenceRelation.CONTRADICTS, EvidenceRelation.FAILS_TO_REPLICATE)
        and e.quality != "suspicious"
    ]
    if not (support and contradict):
        return []
    # Only count as a real conflict if the two sides are independent
    # (different agents) — same-agent support+contradict is just noise.
    s_agents = {e.agent_id for e in support}
    c_agents = {e.agent_id for e in contradict}
    if not (s_agents & c_agents):
        return [
            {
                "type": "supports_vs_contradicts",
                "agents": sorted(s_agents | c_agents),
                "support_evidence": [e.evidence_id for e in support],
                "contradict_evidence": [e.evidence_id for e in contradict],
                "independent": True,
            }
        ]
    return []


def insufficient_evidence(evidence: List[Evidence]) -> bool:
    """Sufficient ⇔ at least one DIRECTIONAL, EXECUTABLE piece of evidence.

    A directional relation (supports / contradicts / replicates /
    fails-to-replicate) that came from actual computation is enough to have a
    position. Pure abstentions/neutral (or non-executable opinion) do not
    constitute a basis for a verdict.
    """
    if not evidence:
        return True
    directional = [
        e for e in evidence
        if e.relation
        in (
            EvidenceRelation.SUPPORTS,
            EvidenceRelation.CONTRADICTS,
            EvidenceRelation.REPLICATES,
            EvidenceRelation.FAILS_TO_REPLICATE,
        )
    ]
    if not directional:
        return True
    return not any(e.executable for e in directional)


# ---------------------------------------------------------------------------
# Error-correlation proxies (AC11)
# ---------------------------------------------------------------------------
def strategy_error_correlation(
    error_matrix: Dict[str, List[float]],
) -> Optional[float]:
    """Average pairwise Pearson correlation of per-strategy error indicators
    across a shared set of tasks (AC11 error-correlation metric).

    `error_matrix`: strategy name -> list of error indicators over the SAME
    ordered set of tasks. Error indicator: 1.0 wrong, 0.5 INCONCLUSIVE, 0.0
    correct. A HIGH value means strategies fail on the same tasks (correlated
    error — the failure RepliClaw aims to reduce). A LOW/negative value means
    failure modes differ (independence). Requires >=2 strategies and >=3 tasks
    for a stable estimate.
    """
    import itertools

    strategies = [s for s, v in error_matrix.items() if len(v) > 0]
    n_tasks = min(len(v) for v in error_matrix.values()) if strategies else 0
    if len(strategies) < 2 or n_tasks < 3:
        return None
    aligned = {s: error_matrix[s][:n_tasks] for s in strategies}
    pairs = []
    for s1, s2 in itertools.combinations(strategies, 2):
        r = _pearson(aligned[s1], aligned[s2])
        pairs.append(r)
    if not pairs:
        return None
    return sum(pairs) / len(pairs)


def error_indicator(label: str, truth: str) -> float:
    """Map a verdict label + ground truth to an error indicator (0/0.5/1)."""
    if label == truth.upper():
        return 0.0
    if label == "INCONCLUSIVE":
        return 0.5
    return 1.0


def _pearson(x: List[float], y: List[float]) -> float:
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    if den == 0:
        return 0.0
    return num / den


def _rank(vals: List[float]) -> List[float]:
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    for r, i in enumerate(order):
        ranks[i] = float(r)
    return ranks


def conclusion_error_correlation(finding_lists: List[List[str]]) -> Optional[float]:
    """Pairwise error-correlation proxy across investigators WITHIN one run.

    For each pair of investigators, 1 if they reached the SAME conclusion,
    else 0. A near-uniform 1.0 means everyone agrees (could be correlated
    error); variation means independent error modes. Used as the
    intra-run diversity/complement of cross-run correlation.
    """
    if len(finding_lists) < 2:
        return None
    # Flatten into pairs.
    import itertools

    n_pairs = 0
    n_same = 0
    for a, b in itertools.combinations(finding_lists, 2):
        ca = (a or ["uncertain"])[0]
        cb = (b or ["uncertain"])[0]
        n_pairs += 1
        if ca == cb:
            n_same += 1
    if n_pairs == 0:
        return None
    return n_same / n_pairs
