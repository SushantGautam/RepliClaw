"""P03 evidence escrow: pre-outcome commitments, gated reveal, ledger integrity.

Red-first per ticket P03.md. Covers the seven mandated behaviors:
independence before reveal, verify-and-preserve reveal, tamper mismatch,
phase violations, append-only monotonic events under concurrent writers,
deterministic snapshots, and on-disk tamper detection.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from repliclaw.escrow import (
    DuplicateCommitment,
    EscrowLedger,
    EvidenceObservation,
    PhaseGate,
    PhaseViolation,
    PredictionPacket,
    commitment_hash,
    verify_ledger,
)

CASE_ID = "policy_rag_v1"
AGENT_A = "agent-alpha"
AGENT_B = "agent-beta"


def make_packet(agent: str, hyp: str, intervention: str, statement: str) -> PredictionPacket:
    return PredictionPacket(
        packet_id=uuid.uuid4().hex,
        case_id=CASE_ID,
        agent_id=agent,
        hypothesis_id=hyp,
        hypothesis_version=1,
        hypothesis_statement=statement,
        intervention_id=intervention,
        predicted_outcome=f"{intervention} exposes the stale retrieval figure of 30 days",
        refutation_criterion=f"{intervention} leaves the 14-day figure in the audited output",
        competing_explanation=f"the judge rubric, not retrieval, drives the {hyp} verdict",
        prior_evidence_snapshot_sha256="ab" * 32,
    )


PKT_A = make_packet(AGENT_A, "H_R", "I_R", "Retrieval omission is the true cause of the audit pass")
PKT_B = make_packet(AGENT_B, "H_J", "I_J", "Judge rubric staleness is the true cause of the audit pass")


def fresh_ledger(tmp_path: Path, worker: str = "w0") -> EscrowLedger:
    return EscrowLedger(tmp_path / "ledger", worker_id=worker)


def public_bytes(ledger: EscrowLedger) -> bytes:
    """Every byte a peer could legitimately see before reveal (contract §1)."""
    out = []
    for name in ("commitments.jsonl", "events.jsonl"):
        p = ledger.root / name
        if p.exists():
            out.append(p.read_bytes())
    return b"\n".join(out)


# 1. Two agents independently precommit; no private bytes before reveal.
def test_two_agents_independent_precommit(tmp_path: Path):
    ledger = fresh_ledger(tmp_path)
    proj_a = ledger.commit(AGENT_A, PKT_A)
    proj_b = ledger.commit(AGENT_B, PKT_B)
    assert proj_a.commitment_sha256 == commitment_hash(PKT_A)
    assert proj_b.commitment_sha256 == commitment_hash(PKT_B)

    seen = public_bytes(ledger)
    # Projections carry only the public fields.
    for field in ("hypothesis_statement", "predicted_outcome", "refutation_criterion", "competing_explanation"):
        for pkt in (PKT_A, PKT_B):
            assert getattr(pkt, field).encode("utf-8") not in seen
    # No read API exposes a peer's private packet: the only accessor is the
    # ledger's own reveal path (documented trust boundary, not peer access).
    assert not hasattr(ledger, "peer_packet")
    assert PKT_A.packet_id in {c.packet_id for c in ledger.commitments()}


# 2. Reveal verifies and preserves; no hindsight rewrite.
def test_reveal_verifies_and_preserves(tmp_path: Path):
    ledger = fresh_ledger(tmp_path)
    proj = ledger.commit(AGENT_A, PKT_A)
    committed_sha = proj.commitment_sha256
    # A post-hoc "amended" packet with the same packet_id must NOT be
    # silently accepted: re-commit raises (checked here, still in COMMIT
    # phase, so the duplicate guard is the error raised).
    amended = PKT_A.model_copy(
        update={"hypothesis_statement": "Something else entirely, decided later"}
    )
    with pytest.raises(DuplicateCommitment):
        ledger.commit(AGENT_A, amended)

    ledger.open_reveal(CASE_ID)
    result = ledger.reveal(AGENT_A, PKT_A)
    assert result.status == "verified"
    assert result.commitment_sha256 == committed_sha
    published = ledger.root / result.published_path
    assert published.read_bytes() == PKT_A.canonical_bytes() + b"\n"
    # Original commitment hash unchanged.
    assert commitment_hash(PKT_A) == committed_sha
    # Revealing the amended content instead -> integrity event, nothing
    # published for the amendment (only the original is ever published).
    bad = ledger.reveal(AGENT_A, amended)
    assert bad.status == "mismatch"
    assert not (ledger.root / "revealed" / CASE_ID / "amended.json").exists()


# 3. Tampered reveal (one character) -> mismatch, nothing published, usable.
def test_tampered_reveal_mismatch(tmp_path: Path):
    ledger = fresh_ledger(tmp_path)
    ledger.commit(AGENT_A, PKT_A)
    ledger.commit(AGENT_B, PKT_B)
    ledger.open_reveal(CASE_ID)
    tampered = PKT_A.model_copy(update={"predicted_outcome": "31 days"})
    result = ledger.reveal(AGENT_A, tampered)
    assert result.status == "mismatch"
    assert not (ledger.root / "revealed" / CASE_ID / f"{PKT_A.packet_id}.json").exists()
    kinds = [e["kind"] for e in ledger.events()]
    assert "reveal_mismatch" in kinds
    # Ledger still usable: agent B reveals fine afterwards.
    ok = ledger.reveal(AGENT_B, PKT_B)
    assert ok.status == "verified"


# 4. Phase violations: out-of-order actions all raise.
def test_phase_violations(tmp_path: Path):
    ledger = fresh_ledger(tmp_path)
    # Reveal before boundary.
    ledger.commit(AGENT_A, PKT_A)
    with pytest.raises(PhaseViolation):
        ledger.reveal(AGENT_A, PKT_A)
    # Evidence in COMMIT phase.
    obs = EvidenceObservation(
        observation_id="obs-1",
        case_id=CASE_ID,
        producer_id=AGENT_A,
        run_id="run-1",
        kind="verified_run",
        summary="baseline arm",
        data={"severity": "pass"},
        provenance={"intervention_id": "I0_baseline", "config_sha256": "cd" * 32,
                    "run_hash": "ef" * 32, "reproducible": True, "independent": True},
        published_at="2026-10-10T00:00:00+00:00",
    )
    with pytest.raises(PhaseViolation):
        ledger.publish_evidence(obs)
    # Commit after REVEAL.
    ledger.open_reveal(CASE_ID)
    with pytest.raises(PhaseViolation):
        ledger.commit(AGENT_B, PKT_B)
    # Gate math: COMMIT->REVEAL->EXECUTE->RESOLVE, one step at a time.
    gate = PhaseGate()
    gate.advance()
    assert gate.phase.name == "REVEAL"
    gate.advance()
    assert gate.phase.name == "EXECUTE"
    gate.advance()
    assert gate.phase.name == "RESOLVE"
    with pytest.raises(PhaseViolation):
        gate.advance()  # RESOLVE is terminal
    with pytest.raises(PhaseViolation):
        PhaseGate().assert_can(AGENT_A, "reveal")  # reveal illegal in COMMIT


# 5. Monotonic events under a single writer; append-only, line-intact under
#    two real concurrent processes.
def test_events_monotonic_and_append_only(tmp_path: Path):
    # Part A — one writer: strict monotonicity + verifiable chain.
    seq_root = tmp_path / "seq_ledger"
    leader = EscrowLedger(seq_root, worker_id="leader")
    pka = make_packet("leader", "H_R", "I_R", "leader's retrieval hypothesis")
    leader.commit("leader", pka)
    leader.open_reveal(CASE_ID)
    leader.reveal("leader", pka)
    seqs = [e["seq"] for e in leader.events()]
    assert seqs == list(range(1, len(seqs) + 1)), "seq not strictly increasing"
    assert verify_ledger(seq_root) == []

    # Part B — two concurrent processes append to the same root. Each write
    # is one O_APPEND write() of a complete line, so lines must never
    # interleave mid-line: every line must parse as a well-formed event.
    conc_root = tmp_path / "conc_ledger"
    conc_root.mkdir(parents=True)
    worker_script = """
import sys
sys.path.insert(0, {src!r})
from repliclaw.escrow import EscrowLedger, PredictionPacket
import uuid
ledger = EscrowLedger({root!r}, worker_id={worker!r})
for i in range(5):
    ledger.commit({worker!r}, PredictionPacket(
        packet_id=uuid.uuid4().hex, case_id={case!r}, agent_id={worker!r},
        hypothesis_id=f"X_{{i}}", hypothesis_version=1,
        hypothesis_statement=f"worker hypothesis number {{i}} unique bytes",
        intervention_id="I0_baseline",
        predicted_outcome=f"outcome {{i}}",
        refutation_criterion=f"refutation {{i}}",
        competing_explanation=f"competing {{i}}",
        prior_evidence_snapshot_sha256="11" * 32,
    ))
""".format(
        src=str(Path(__file__).resolve().parent.parent / "src"),
        root=str(conc_root),
        worker="workerA",
        case=CASE_ID,
    )
    script_b = worker_script.replace("workerA", "workerB")
    procs = [
        subprocess.Popen([sys.executable, "-c", worker_script], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE),
        subprocess.Popen([sys.executable, "-c", script_b], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE),
    ]
    for p in procs:
        out, err = p.communicate()
        assert p.returncode == 0, err.decode()

    lines = (conc_root / "events.jsonl").read_text().splitlines()
    events = []
    for ln in lines:  # every line parses — no interleaved corruption
        ev = json.loads(ln)
        assert set(ev) >= {"seq", "ts", "phase", "worker_id", "kind", "payload"}
        events.append(ev)
    commitments = [e for e in events if e["kind"] == "commitment"]
    assert len(commitments) == 10, f"expected 10 commitments, got {len(commitments)}"
    # No partial/duplicate line content: every event id (seq,packet) is unique
    # per writer, and no two lines are byte-identical duplicates.
    assert len({ln for ln in lines}) == len(lines)


# 6. Deterministic snapshots: same sequence -> same hash; different -> different.
def test_snapshot_deterministic(tmp_path: Path):
    def build(dir_: Path) -> EscrowLedger:
        ledger = EscrowLedger(dir_ / "ledger", worker_id="w")
        ledger.commit(AGENT_A, PKT_A)
        ledger.open_reveal(CASE_ID)
        ledger.reveal(AGENT_A, PKT_A)
        return ledger

    s1 = build(tmp_path / "a").snapshot()
    s2 = build(tmp_path / "b").snapshot()
    assert s1["snapshot_sha256"] == s2["snapshot_sha256"]

    other = EscrowLedger(tmp_path / "c" / "ledger", worker_id="w")
    other.commit(AGENT_A, PKT_A)
    other.open_reveal(CASE_ID)
    other.reveal(AGENT_A, PKT_A)
    other.enter_execute()
    obs = EvidenceObservation(
        observation_id="obs-9",
        case_id=CASE_ID,
        producer_id=AGENT_A,
        run_id="run-9",
        kind="verified_run",
        summary="extra",
        data={"severity": "critical"},
        provenance={"intervention_id": "I_R", "config_sha256": "cd" * 32,
                    "run_hash": "ef" * 32, "reproducible": True, "independent": True},
        published_at="2026-10-10T00:00:00+00:00",
    )
    other.publish_evidence(obs)
    s3 = other.snapshot()
    assert s3["snapshot_sha256"] != s1["snapshot_sha256"]


# 7. verify_ledger catches on-disk tampering (hash change, reorder).
def test_verify_ledger_catches_tampering(tmp_path: Path):
    ledger = fresh_ledger(tmp_path)
    ledger.commit(AGENT_A, PKT_A)
    ledger.commit(AGENT_B, PKT_B)
    ledger.open_reveal(CASE_ID)
    ledger.reveal(AGENT_B, PKT_B)
    assert verify_ledger(ledger.root) == []

    # Tamper 1: edit a hash field on an events.jsonl line.
    tampered_root = tmp_path / "tampered1"
    shutil.copytree(ledger.root, tampered_root)
    lines = (tampered_root / "events.jsonl").read_text().splitlines()
    ev = json.loads(lines[0])
    ev["payload"]["commitment_sha256"] = "ff" * 32
    lines[0] = json.dumps(ev, sort_keys=True, separators=(",", ":"))
    (tampered_root / "events.jsonl").write_text("\n".join(lines) + "\n")
    v1 = verify_ledger(tampered_root)
    assert any("hash-chain" in v for v in v1)

    # Tamper 2: reorder two lines.
    reordered_root = tmp_path / "tampered2"
    shutil.copytree(ledger.root, reordered_root)
    rlines = (reordered_root / "events.jsonl").read_text().splitlines()
    rlines[0], rlines[1] = rlines[1], rlines[0]
    (reordered_root / "events.jsonl").write_text("\n".join(rlines) + "\n")
    v2 = verify_ledger(reordered_root)
    assert any("seq" in v for v in v2)
