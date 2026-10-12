"""indepinfo Part A: evidence partitioning boundary + pre-reveal isolation.

Covers: per-source partitioning (no cross-source bytes), no global score
vector (per-partition snapshot hash), cross-partition read blocking,
cross-agent (and self) pre-reveal packet read blocking, commit-time
snapshot-hash enforcement, and the full commit -> reveal -> verify
lifecycle on the existing escrow ledger.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from repliclaw.benchmarks.indepinfo import (
    Evidence,
    EvidenceRecord,
    EvidenceSource,
    IsolationViolation,
    PartitionVault,
    UnknownSourceError,
    partition_for_source,
)
from repliclaw.canonical import canonical_json, sha256_hex
from repliclaw.escrow import EscrowLedger, PredictionPacket, commitment_hash, verify_ledger

CASE = "case-partition-1"


def make_evidence() -> Evidence:
    return Evidence(
        case_id=CASE,
        case_brief="three-source fragmented case",
        sources=[
            EvidenceSource(
                source_id="src-a",
                name="source A",
                description="A",
                records=[
                    EvidenceRecord(record_id="a1", data={"k": "alpha-only-value"}),
                    EvidenceRecord(record_id="a2", data={"k": "alpha-second"}),
                ],
            ),
            EvidenceSource(
                source_id="src-b",
                name="source B",
                description="B",
                records=[EvidenceRecord(record_id="b1", data={"k": "beta-only-value"})],
            ),
            EvidenceSource(
                source_id="src-c",
                name="source C",
                description="C",
                records=[EvidenceRecord(record_id="c1", data={"k": "gamma-only-value"})],
            ),
        ],
    )


def make_packet(agent: str, case: str = CASE, snapshot: str = "ab" * 32) -> PredictionPacket:
    return PredictionPacket(
        packet_id=uuid.uuid4().hex,
        case_id=case,
        agent_id=agent,
        hypothesis_id=f"H_{agent}",
        hypothesis_version=1,
        hypothesis_statement=f"{agent} hypothesis statement for {case}",
        intervention_id="observational_only",
        predicted_outcome=f"{agent} predicted outcome",
        refutation_criterion=f"{agent} refutation criterion",
        competing_explanation=f"{agent} competing explanation",
        prior_evidence_snapshot_sha256=snapshot,
    )


def fresh_vault(tmp_path: Path) -> tuple[Evidence, EscrowLedger, PartitionVault]:
    ev = make_evidence()
    ledger = EscrowLedger(tmp_path / "ledger", worker_id="w0")
    return ev, ledger, PartitionVault(ev, ledger, ev.case_id)


# 1. Partitioning: each investigator sees only its own source.
def test_partition_contains_only_own_source():
    ev = make_evidence()
    for src_id, own, foreign in (
        ("src-a", "alpha-only-value", ("beta-only-value", "gamma-only-value")),
        ("src-b", "beta-only-value", ("alpha-only-value", "gamma-only-value")),
        ("src-c", "gamma-only-value", ("alpha-only-value", "beta-only-value")),
    ):
        part = partition_for_source(ev, src_id)
        blob = canonical_json(part.model_dump())
        assert own in blob
        for f in foreign:
            assert f not in blob
        assert part.source_id == src_id
        assert part.case_id == CASE


def test_partition_records_match_source_exactly():
    ev = make_evidence()
    src_a = ev.sources[0]
    part = partition_for_source(ev, "src-a")
    assert [r.model_dump() for r in part.records] == [r.model_dump() for r in src_a.records]


def test_unknown_source_raises():
    ev = make_evidence()
    with pytest.raises(UnknownSourceError):
        partition_for_source(ev, "src-zzz")


# 2. No shared global score vector: the snapshot hash is per-partition.
def test_evidence_model_has_no_aggregate_fields():
    # Structural guard: the Evidence model carries only the sources — no
    # global score vector, no cross-source rollup.
    assert set(Evidence.model_fields) == {"case_id", "case_brief", "sources"}


def test_partition_hash_is_per_source_not_aggregate():
    ev = make_evidence()
    part_a = partition_for_source(ev, "src-a")
    src_a = ev.sources[0]
    expected = sha256_hex(
        canonical_json(
            {
                "case_id": CASE,
                "source_id": "src-a",
                "records": [r.model_dump() for r in src_a.records],
            }
        )
    )
    assert part_a.snapshot_sha256 == expected
    # ...and it is NOT the hash of any aggregate over all sources.
    aggregate = sha256_hex(
        canonical_json({"case_id": CASE, "sources": [s.model_dump() for s in ev.sources]})
    )
    assert part_a.snapshot_sha256 != aggregate
    # Distinct sources yield distinct partition hashes.
    hashes = {partition_for_source(ev, s.source_id).snapshot_sha256 for s in ev.sources}
    assert len(hashes) == 3


# 3. Isolation: cross-partition reads are blocked.
def test_cross_partition_read_blocked(tmp_path: Path):
    _, _, vault = fresh_vault(tmp_path)
    view_a = vault.view_for("inv-a", "src-a")
    with pytest.raises(IsolationViolation):
        view_a.read_partition("src-b")
    with pytest.raises(IsolationViolation):
        view_a.read_partition("src-c")
    # Own partition is readable.
    assert view_a.read_partition("src-a").source_id == "src-a"


# 4. Isolation: cross-agent (and self) pre-reveal packet reads are blocked.
def test_pre_reveal_packet_reads_blocked(tmp_path: Path):
    ev, ledger, vault = fresh_vault(tmp_path)
    view_a = vault.view_for("inv-a", "src-a")
    view_b = vault.view_for("inv-b", "src-b")
    pkt_a = make_packet("inv-a", snapshot=view_a.my_partition().snapshot_sha256)
    pkt_b = make_packet("inv-b", snapshot=view_b.my_partition().snapshot_sha256)
    view_a.commit(pkt_a)
    view_b.commit(pkt_b)

    # Pre-reveal: cross-agent read blocked...
    with pytest.raises(IsolationViolation):
        view_a.read_packet("inv-b", pkt_b.packet_id)
    # ...and even the owner cannot read its own sealed packet pre-reveal.
    with pytest.raises(IsolationViolation):
        view_a.read_packet("inv-a", pkt_a.packet_id)


# 5. Commit path enforces ownership + own-partition snapshot hash.
def test_commit_rejects_foreign_agent_and_wrong_snapshot(tmp_path: Path):
    _, _, vault = fresh_vault(tmp_path)
    view_a = vault.view_for("inv-a", "src-a")
    view_b = vault.view_for("inv-b", "src-b")

    # A packet for another agent cannot be committed through this view.
    foreign = make_packet("inv-b", snapshot=view_b.my_partition().snapshot_sha256)
    with pytest.raises(IsolationViolation):
        view_a.commit(foreign)

    # A packet whose snapshot hash is NOT its own partition hash (e.g. an
    # aggregate/global vector) is rejected.
    aggregate = sha256_hex(
        canonical_json({"case_id": CASE, "sources": [s.model_dump() for s in vault.evidence.sources]})
    )
    bad = make_packet("inv-a", snapshot=aggregate)
    with pytest.raises(IsolationViolation):
        view_a.commit(bad)

    # The correct own-partition hash is accepted.
    good = make_packet("inv-a", snapshot=view_a.my_partition().snapshot_sha256)
    proj = view_a.commit(good)
    assert proj.commitment_sha256 == commitment_hash(good)


# 6. Full lifecycle on the existing escrow: commit -> reveal -> verify.
def test_full_lifecycle_commit_reveal_verify(tmp_path: Path):
    ev, ledger, vault = fresh_vault(tmp_path)
    views = {
        "inv-a": vault.view_for("inv-a", "src-a"),
        "inv-b": vault.view_for("inv-b", "src-b"),
        "inv-c": vault.view_for("inv-c", "src-c"),
    }
    packets = {}
    for agent, view in views.items():
        pkt = make_packet(agent, snapshot=view.my_partition().snapshot_sha256)
        view.commit(pkt)
        packets[agent] = pkt

    vault.open_reveal()
    for agent, pkt in packets.items():
        result = ledger.reveal(agent, pkt)
        assert result.status == "verified"
        assert result.commitment_sha256 == commitment_hash(pkt)

    assert verify_ledger(ledger.root) == []


# 7. Post-reveal: revealed packets are readable; un-revealed ones are not.
def test_post_reveal_revealed_packets_readable(tmp_path: Path):
    ev, ledger, vault = fresh_vault(tmp_path)
    view_a = vault.view_for("inv-a", "src-a")
    view_b = vault.view_for("inv-b", "src-b")
    pkt_a = make_packet("inv-a", snapshot=view_a.my_partition().snapshot_sha256)
    pkt_b = make_packet("inv-b", snapshot=view_b.my_partition().snapshot_sha256)
    view_a.commit(pkt_a)
    view_b.commit(pkt_b)
    vault.open_reveal()
    assert ledger.reveal("inv-a", pkt_a).status == "verified"
    # inv-b's packet is committed but NOT revealed yet.

    # Post-reveal-phase, a committed-but-unrevealed packet is still unreadable.
    with pytest.raises(IsolationViolation):
        view_a.read_packet("inv-b", pkt_b.packet_id)

    # Once revealed, it is readable cross-agent (reveal = disclosure).
    assert ledger.reveal("inv-b", pkt_b).status == "verified"
    got = view_a.read_packet("inv-b", pkt_b.packet_id)
    assert got is not None
    assert got.packet_id == pkt_b.packet_id
    assert got.hypothesis_statement == pkt_b.hypothesis_statement

    # Unknown packet ids stay unreadable.
    with pytest.raises(IsolationViolation):
        view_a.read_packet("inv-c", "f" * 32)
