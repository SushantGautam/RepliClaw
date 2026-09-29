"""commit/reveal integrity: hash stability, tamper detection, one-shot reveal (AC04)."""
import pytest

from repliclaw import canonical
from repliclaw.models import Commitment, commit_payload
from repliclaw.runstore import RevealMismatchError, RunStore


def _finding(**over):
    base = {
        "conclusion": "supported",
        "statement": "the effect is real",
        "plan": "t-test",
        "evidence": {"p": 0.001, "t": 3.4},
        "confidence": 0.9,
        "executable": True,
    }
    base.update(over)
    return base


def test_commit_hash_is_canonical_and_stable():
    a = _finding()
    b = _finding()
    # Byte-stable: same object -> same hash.
    assert canonical.commit_hash(a) == canonical.commit_hash(b)
    # Key order / whitespace must not change the hash.
    reordered = {k: a[k] for k in sorted(a)}
    assert canonical.commit_hash(reordered) == canonical.commit_hash(a)


def test_commit_hash_changes_with_substance():
    a = _finding()
    b = _finding(conclusion="refuted")  # doctored conclusion
    assert canonical.commit_hash(a) != canonical.commit_hash(b)


def test_commit_then_reveal_verifies_and_roundtrips(tmp_path):
    store = RunStore(tmp_path)
    payload = commit_payload(_finding())
    c = Commitment(
        commitment_id="cmt-1",
        claim_id="claim-x",
        agent_id="inv-a",
        role="analyst",
        content=payload,
        content_hash=canonical.commit_hash(payload),
    )
    store.commit(c)
    res = store.verify_reveal("cmt-1", payload)
    assert res["verified"] is True and res["already_revealed"] is False


def test_doctored_reveal_is_rejected_and_commitment_becomes_rejected(tmp_path):
    store = RunStore(tmp_path)
    payload = commit_payload(_finding(conclusion="supported"))
    c = Commitment(
        commitment_id="cmt-2",
        claim_id="claim-x",
        agent_id="inv-a",
        role="analyst",
        content=payload,
        content_hash=canonical.commit_hash(payload),
    )
    store.commit(c)
    doctored = dict(payload)
    doctored["conclusion"] = "supported"  # same
    doctored["statement"] = "I actually saw it"  # tamper
    with pytest.raises(RevealMismatchError):
        store.verify_reveal("cmt-2", doctored)
    # After a mismatch the commitment is REJECTED.
    rec = store.get_commitment("cmt-2")
    assert rec.reveal_verified is False


def test_one_shot_reveal_blocks_re_reveal_after_rejection(tmp_path):
    """Fake-independence hole: commit truth, reveal a lie, then 'fix' it.

    The protocol must not allow a later correct reveal of a REJECTED commitment.
    """
    store = RunStore(tmp_path)
    truth = commit_payload(_finding(conclusion="supported"))
    c = Commitment(
        commitment_id="cmt-3",
        claim_id="claim-x",
        agent_id="inv-a",
        role="analyst",
        content=truth,
        content_hash=canonical.commit_hash(truth),
    )
    store.commit(c)
    lie = dict(truth)
    lie["conclusion"] = "refuted"
    with pytest.raises(RevealMismatchError):
        store.verify_reveal("cmt-3", lie)
    # Now try to reveal the ORIGINAL (correct) content — must still be blocked.
    with pytest.raises(RevealMismatchError):
        store.verify_reveal("cmt-3", truth)


def test_on_disk_tamper_breaks_seal(tmp_path):
    """Directly editing the persisted commitment JSON must be detected by the
    seal hash (tamper-evident, AC04)."""
    import json

    store = RunStore(tmp_path)
    payload = commit_payload(_finding())
    c = Commitment(
        commitment_id="cmt-4",
        claim_id="claim-x",
        agent_id="inv-a",
        role="analyst",
        content=payload,
        content_hash=canonical.commit_hash(payload),
    )
    store.commit(c)
    f = store.commitments_dir / "cmt-4.json"
    d = json.loads(f.read_text())
    # Tamper with a sealed field (e.g. swap the committed content).
    d["content"]["confidence"] = 0.1
    f.write_text(json.dumps(d))
    with pytest.raises(RevealMismatchError):
        store.verify_reveal("cmt-4", payload)


def test_event_log_records_commit_and_reveal(tmp_path):
    store = RunStore(tmp_path)
    payload = commit_payload(_finding())
    c = Commitment(
        commitment_id="cmt-5",
        claim_id="claim-x",
        agent_id="inv-a",
        role="analyst",
        content=payload,
        content_hash=canonical.commit_hash(payload),
    )
    store.commit(c)
    store.verify_reveal("cmt-5", payload)
    kinds = [e["kind"] for e in store.events()]
    assert "committed" in kinds and "revealed" in kinds
