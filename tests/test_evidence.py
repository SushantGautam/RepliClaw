"""Evidence graph + error-correlation proxy (AC09/AC11): conflict detection,
diversity, and the cross-strategy error-correlation metric."""
from repliclaw.evidence import (
    count_independent_pairs,
    detect_conflicts,
    error_indicator,
    graph_report,
    build_evidence_graph,
    strategy_error_correlation,
)
from repliclaw.models import Evidence, EvidenceRelation


def ev(agent, relation, agent_id=None):
    return Evidence(
        evidence_id=f"ev-{agent}-{relation.value}",
        claim_id="claim-e",
        agent_id=agent_id or agent,
        relation=relation,
        finding={"conclusion": relation.value},
        executable=True,
        confidence=0.8,
    )


def test_detect_conflict_supports_vs_contradicts_independent():
    f = EvidenceRelation
    evs = [ev("a", f.SUPPORTS), ev("b", f.CONTRADICTS)]
    conflicts = detect_conflicts(evs)
    assert len(conflicts) == 1
    assert conflicts[0]["independent"] is True
    assert set(conflicts[0]["agents"]) == {"a", "b"}


def test_no_conflict_when_same_agent_or_one_sided():
    f = EvidenceRelation
    # One-sided only.
    assert detect_conflicts([ev("a", f.SUPPORTS), ev("b", f.SUPPORTS)]) == []
    # Same agent on both sides is noise, not an independent conflict.
    assert detect_conflicts([ev("a", f.SUPPORTS), ev("a", f.CONTRADICTS)]) == []


def test_suspicious_evidence_does_not_create_conflict():
    f = EvidenceRelation
    good = ev("a", f.SUPPORTS)
    sus = ev("b", f.CONTRADICTS)
    sus.quality = "suspicious"
    assert detect_conflicts([good, sus]) == []


def test_graph_report_counts_and_diversity():
    f = EvidenceRelation
    evs = [ev("a", f.SUPPORTS), ev("b", f.SUPPORTS), ev("c", f.CONTRADICTS)]
    G = build_evidence_graph(evs, claim_id="claim-e")
    rep = graph_report(G)
    assert rep["n_evidence"] == 3
    assert rep["n_agents"] == 3
    assert rep["by_relation"]["supports"] == 2
    assert rep["by_relation"]["contradicts"] == 1
    # All pairs are from distinct agents -> C(3,2)=3.
    assert rep["independent_pairs"] == count_independent_pairs(
        list(G.nodes(data=True))
    ) == 3


def test_error_indicator_mapping():
    assert error_indicator("SUPPORTED", "supported") == 0.0
    assert error_indicator("REFUTED", "supported") == 1.0
    assert error_indicator("INCONCLUSIVE", "supported") == 0.5


def test_error_correlation_high_when_same_failures():
    # Two strategies failing on the SAME tasks -> high positive correlation.
    matrix = {
        "s1": [1.0, 1.0, 0.0, 1.0],
        "s2": [1.0, 1.0, 0.0, 1.0],
    }
    r = strategy_error_correlation(matrix)
    assert r is not None and r > 0.99


def test_error_correlation_low_when_anticorrelated():
    # Strategies failing on DIFFERENT tasks -> negative/low correlation.
    matrix = {
        "s1": [1.0, 0.0, 0.0, 0.0],
        "s2": [0.0, 1.0, 1.0, 1.0],
    }
    r = strategy_error_correlation(matrix)
    assert r is not None and r < 0.0


def test_error_correlation_needs_enough_data():
    # <2 strategies or <3 tasks -> None (not estimable).
    assert strategy_error_correlation({"s1": [1.0, 0.0]}) is None
    assert strategy_error_correlation({"s1": [1.0, 0.0, 1.0]}) is None
