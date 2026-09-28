"""Pre-reveal isolation (AC03): an investigator cannot see a peer's sealed
conclusion before the reveal phase, and every read/denial is auditable."""
import json

import pytest

from repliclaw import canonical
from repliclaw.isolation import ContextEnforcer, IsolationViolation, PhaseGate
from repliclaw.models import Claim, Commitment, InvestigatorConfig, InvestigatorRole
from repliclaw.runstore import RunStore


def _inv(agent_id, role=InvestigatorRole.ANALYST):
    return InvestigatorConfig(agent_id=agent_id, role=role, allowed_sources=["bundled_data"])


def _claim():
    return Claim(claim_id="claim-x", statement="the effect is real",
                 data={"n": 400})


def _store(tmp_path):
    return RunStore(tmp_path)


def _committed(store, agent_id, conclusion):
    payload = {
        "conclusion": conclusion,
        "statement": f"{agent_id} says {conclusion}",
        "plan": "t-test",
        "evidence": {"p": 0.001},
        "confidence": 0.9,
        "executable": True,
    }
    c = Commitment(
        commitment_id=f"cmt-{agent_id}",
        claim_id="claim-x",
        agent_id=agent_id,
        role="analyst",
        content=payload,
        content_hash=canonical.commit_hash(payload),
    )
    store.commit(c)
    return c


def test_peer_materials_denied_pre_reveal(tmp_path):
    store = _store(tmp_path)
    gate = PhaseGate()  # starts in 'blind'
    enforcer = ContextEnforcer(store, gate)
    _committed(store, "inv-b", "supported")
    got = enforcer.peer_materials("claim-x", for_agent="inv-a")
    assert got == {}
    # Denial is audited.
    kinds = [e["kind"] for e in store.events()]
    assert "isolation_enforced" in kinds


def test_blind_read_returns_metadata_only(tmp_path):
    store = _store(tmp_path)
    gate = PhaseGate()
    enforcer = ContextEnforcer(store, gate)
    _committed(store, "inv-b", "supported")
    meta = enforcer.read_sealed_commitment("cmt-inv-b", for_agent="inv-a", revealed=False)
    # Hash/phase metadata present...
    assert meta["content_hash"] and meta["phase"] == "committed"
    # ...but content withheld.
    assert "content" not in meta or meta.get("content") is None
    assert meta.get("revealed_content") is None


def test_forced_content_read_pre_reveal_raises(tmp_path):
    store = _store(tmp_path)
    gate = PhaseGate()
    enforcer = ContextEnforcer(store, gate)
    _committed(store, "inv-b", "supported")
    with pytest.raises(IsolationViolation):
        enforcer.read_sealed_commitment("cmt-inv-b", for_agent="inv-a", revealed=True)


def test_peer_materials_visible_after_reveal(tmp_path):
    store = _store(tmp_path)
    gate = PhaseGate()
    enforcer = ContextEnforcer(store, gate)
    c = _committed(store, "inv-b", "supported")
    # Agent B reveals its committed content (verified).
    store.verify_reveal(c.commitment_id, c.content)
    gate.advance("committed")
    gate.advance("revealing")
    gate.advance("revealed")
    got = enforcer.peer_materials("claim-x", for_agent="inv-a")
    assert "inv-b" in got
    assert got["inv-b"]["conclusion"] == "supported"


def test_prompt_block_pre_reveal_excludes_peer_materials(tmp_path):
    store = _store(tmp_path)
    gate = PhaseGate()
    enforcer = ContextEnforcer(store, gate)
    claim = _claim()
    ctx = enforcer.build_context(
        claim=claim,
        investigator=_inv("inv-a"),
        task_instructions="assess the claim",
    )
    block = ctx.to_prompt_block(revealed=False)
    # Even if revealed_materials were (maliciously) pre-populated, the
    # blind-phase prompt must not include them.
    ctx.revealed_materials = {"inv-b": {"conclusion": "SUPPORTED-SECRET"}}
    block_blind = ctx.to_prompt_block(revealed=False)
    assert "SUPPORTED-SECRET" not in block_blind
    assert "# PEER MATERIALS" not in block_blind


def test_context_build_is_audited(tmp_path):
    store = _store(tmp_path)
    gate = PhaseGate()
    enforcer = ContextEnforcer(store, gate)
    enforcer.build_context(
        claim=_claim(), investigator=_inv("inv-a"), task_instructions="assess"
    )
    events = [e for e in store.events() if e["kind"] == "context_built"]
    assert events and events[0]["includes_peer_materials"] is False
