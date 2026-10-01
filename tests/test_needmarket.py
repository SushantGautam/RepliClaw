"""P04 need market: atomic leases, local ranking, evidence-induced choice change.

Red-first per ticket P04.md. Covers the 8 mandated behaviors including
real-OS-subprocess atomicity (F04 carry-over 3), frozen-clock determinism
(carry-over 5), and open_needs closure (carry-over 1).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from repliclaw.needmarket import (
    BudgetExhausted,
    GreedySharedPolicy,
    LocalEigPolicy,
    Need,
    NeedBroker,
    NeedWorker,
    RandomPolicy,
    WorkerCapability,
    snapshot,
)

CASE = "policy_rag_v1"
SRC = str(Path(__file__).resolve().parent.parent / "src")


class FrozenClock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def make_need(need_id: str, cap: str = "simpleaudit_counterfactual", tokens: int = 100) -> Need:
    return Need(
        need_id=need_id,
        case_id=CASE,
        title=f"need {need_id}",
        description=f"run the {need_id} intervention arm",
        proposer_id="proposer",
        proposed_at="2026-10-10T00:00:00+00:00",
        required_capability=cap,
        cost_estimate={"tokens": tokens},
    )


def make_cap(agent_id: str, budget: Optional[int] = None, types: Optional[List[str]] = None) -> WorkerCapability:
    return WorkerCapability(
        agent_id=agent_id,
        producible_types=types or ["simpleaudit_counterfactual"],
        method_family="deterministic_rag",
        model=f"model-{agent_id}",
        budget_tokens=budget,
    )


EVID_A = {"I0_baseline": {"severity": "pass", "figure_days": 14}}
EVID_B = {
    "I0_baseline": {"severity": "pass", "figure_days": 14},
    "I_J_judge_fix": {"severity": "critical", "figure_days": 14, "note": "verdict flipped, output byte-identical"},
}


# 1. Atomic claim across TWO REAL OS PROCESSES (carry-over 3).
def test_atomic_claim_two_processes(tmp_path: Path):
    root = tmp_path / "broker"
    root.mkdir()
    NeedBroker(root, lease_ttl_s=30.0).publish(make_need("n1"))

    barrier = tmp_path / "go"
    winner = tmp_path / "winner.txt"
    script = f"""
import sys, time, os
sys.path.insert(0, {SRC!r})
from pathlib import Path
from repliclaw.needmarket import NeedBroker
b = NeedBroker(Path({str(root)!r}), lease_ttl_s=30.0)
while not Path({str(barrier)!r}).exists():
    time.sleep(0.005)
lease = b.claim("n1", os.environ["WORKER"])
if lease is not None:
    Path({str(winner)!r}).write_text("won")
"""
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", script],
            env=dict(os.environ, WORKER=name),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for name in ("wA", "wB")
    ]
    barrier.write_text("go")  # release the race
    results = [p.communicate(timeout=30) for p in procs]
    for p, (_, err) in zip(procs, results):
        assert p.returncode == 0, err.decode()

    broker = NeedBroker(root, lease_ttl_s=30.0)
    claimed = [e for e in broker.events() if e["kind"] == "need_claimed"]
    assert len(claimed) == 1, f"expected exactly one claim winner, got {len(claimed)}"
    assert winner.exists()
    # The lock names the single holder that won.
    lease = broker._read_lock("n1")
    assert lease is not None
    assert lease.holder_id == claimed[0]["payload"]["holder_id"]
    # No partial/corrupt lock files anywhere.
    for f in (root / "locks").iterdir():
        json.loads(f.read_text())


# 2. Lease expiry → re-claim with generation+1; no double-fulfil.
def test_lease_expiry_reclaim(tmp_path: Path):
    clock = FrozenClock()
    broker = NeedBroker(tmp_path / "b", lease_ttl_s=0.5, clock=clock)
    broker.publish(make_need("n2"))
    l1 = broker.claim("n2", "wA")
    assert l1 is not None and l1.generation == 1
    # Live lease blocks re-claim.
    assert broker.claim("n2", "wB") is None
    clock.advance(0.6)  # expire
    l2 = broker.claim("n2", "wB")
    assert l2 is not None
    assert l2.generation == 2
    assert [e for e in broker.events() if e["kind"] == "need_expired"]
    # Exactly-once effects: the first verified fulfilment (here the
    # superseded holder's late result, F04 §4.5) marks the need done;
    # the second verified fulfilment is suppressed.
    assert broker.fulfill("n2", "art-old", l1, verified=True) is True
    assert broker.fulfill("n2", "art-new", l2, verified=True) is False
    fulfilled = [e for e in broker.events() if e["kind"] == "need_fulfilled"]
    assert len(fulfilled) == 1
    assert fulfilled[0]["payload"]["artifact_id"] == "art-old"
    assert fulfilled[0]["payload"]["flag"] == "late_fulfilment"
    hist = broker.claim_history("n2")
    kinds = [e["kind"] for e in hist]
    assert kinds.count("need_claimed") == 2
    assert kinds.count("need_fulfilled") == 1


# 3. Crash recovery: SIGKILL the claimer; lease expires; another fulfils.
def test_crash_recovery(tmp_path: Path):
    root = tmp_path / "b"
    root.mkdir()
    # Real monotonic clock on BOTH processes (the killed claimer uses the
    # default clock, so the parent must too — a frozen clock only exists
    # inside one process).
    broker = NeedBroker(root, lease_ttl_s=0.5)
    broker.publish(make_need("n3"))

    script = f"""
import sys, signal
sys.path.insert(0, {SRC!r})
from pathlib import Path
from repliclaw.needmarket import NeedBroker
b = NeedBroker(Path({str(root)!r}), lease_ttl_s=0.5)
lease = b.claim("n3", "crashed")
assert lease is not None
print("claimed", flush=True)
signal.pause()  # sleep until SIGKILL
"""
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait until the claim event is durable (lock + event written).
    deadline = time.time() + 15
    while time.time() < deadline:
        if any(
            e["kind"] == "need_claimed" for e in NeedBroker(root, lease_ttl_s=0.5).events()
        ):
            break
        time.sleep(0.05)
    proc.kill()  # SIGKILL
    out, _ = proc.communicate(timeout=10)
    assert b"claimed" in out

    time.sleep(0.6)  # real time: lease TTL (0.5s) has passed
    broker = NeedBroker(root, lease_ttl_s=0.5)
    l2 = broker.claim("n3", "wB")
    assert l2 is not None and l2.generation == 2
    assert broker.fulfill("n3", "art-saved", l2, verified=True) is True
    # Broker log consistent end-to-end.
    kinds = [e["kind"] for e in broker.events() if e["payload"].get("need_id") == "n3"]
    assert kinds.count("need_claimed") == 2
    assert kinds.count("need_expired") >= 1
    assert kinds.count("need_fulfilled") == 1


# 4. No central ranking: the broker API cannot rank or assign.
def test_no_central_ranking(tmp_path: Path):
    import inspect

    broker_methods = [
        name
        for name, _ in inspect.getmembers(NeedBroker, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]
    banned = {"rank", "rank_needs", "assign", "allocate", "choose", "select", "order_needs", "best_need"}
    assert not (set(broker_methods) & banned), f"broker exposes ranking API: {broker_methods}"
    # claim requires an agent (no anonymous assignment).
    sig = inspect.signature(NeedBroker.claim)
    assert "agent_id" in sig.parameters
    # open_needs returns unsorted-by-utility publication order (a filter, not a ranking):
    broker = NeedBroker(tmp_path / "b")
    broker.publish(make_need("a1", tokens=999))
    broker.publish(make_need("a2", tokens=1))
    opened = broker.open_needs(exclude_agent="nobody")
    assert [n.need_id for n in opened] == ["a1", "a2"]  # publication order preserved


# 5. Evidence changes choice (T4): observed ranking delta + choice_changed.
def test_evidence_changes_choice(tmp_path: Path):
    clock = FrozenClock()
    broker = NeedBroker(tmp_path / "b", lease_ttl_s=10.0, clock=clock)
    for nid, tok in (("I_R", 100), ("I_J", 100), ("I_P", 100)):
        broker.publish(make_need(nid, tokens=tok))

    # Snapshot A: only I_R discriminates → top choice I_R.
    disc_a: Dict[str, Dict[str, float]] = {"I_R": {"H_R": 0.9}}
    policy = LocalEigPolicy(disc_a)
    cap = make_cap("wA")

    def execute(need: Need) -> Dict[str, Any]:
        return {"artifact_id": f"art-{need.need_id}", "verified": True}

    w = NeedWorker(cap, broker, policy, execute, rng_seed=0)
    r1 = w.cycle(EVID_A)
    assert r1 is not None
    snap_a = snapshot(EVID_A)
    # I_J now fulfilled via I_R? No: worker claims the top-ranked eligible.
    # Top under snapshot A is I_R (info gain 0.9).
    assert r1.claimed_need_id == "I_R"

    # New evidence arrives (I_J_judge_fix run published): discriminability
    # now also favors I_J.
    policy.set_discriminability({"I_J": {"H_R": 0.95, "H_J": 0.4}})
    r2 = w.cycle(EVID_B)
    snap_b = snapshot(EVID_B)
    assert snap_a != snap_b
    # Observed: the agent's ranking (hence claimed action) changed.
    assert r2 is not None
    assert r2.claimed_need_id == "I_J"

    changed = [e for e in broker.events() if e["kind"] == "choice_changed"]
    assert changed, "choice_changed event must fire when evidence changes the ranking"
    payload = changed[0]["payload"]
    assert payload["agent_id"] == "wA"
    assert payload["snapshot_sha"] == snap_b
    assert payload["prev_ranking"] != payload["new_ranking"]
    assert payload["delta_reason"]


# 6. Policy determinism (frozen inputs) + GreedyShared agent-agnostic.
def test_policy_determinism(tmp_path: Path):
    needs = [make_need("d1", tokens=10), make_need("d2", tokens=50), make_need("d3", tokens=50)]
    disc = {"d1": {"H": 1.0}, "d3": {"H": 0.5}}
    for factory in (
        lambda: LocalEigPolicy(disc),
        lambda: RandomPolicy(),
        lambda: GreedySharedPolicy(disc),
    ):
        p1, p2 = factory(), factory()
        r1 = p1.rank("wA", needs, "snap-abc", rng_seed=42)
        r2 = p2.rank("wA", needs, "snap-abc", rng_seed=42)
        assert [a.need_id for a in r1] == [a.need_id for a in r2]
        assert [a.utility for a in r1] == [a.utility for a in r2]
    # Different seed → (for RandomPolicy) possibly different order, but
    # same seed twice always equal (already asserted above).
    g = GreedySharedPolicy(disc)
    rA = g.rank("wA", needs, "snap-abc", rng_seed=1)
    rB = g.rank("wB", needs, "snap-abc", rng_seed=1)
    assert [(a.need_id, a.utility) for a in rA] == [(a.need_id, a.utility) for a in rB]


# 7. open_needs excludes leased (live) + fulfilled (carry-over 1).
def test_open_needs_excludes_leased_fulfilled(tmp_path: Path):
    broker = NeedBroker(tmp_path / "b", lease_ttl_s=10.0, clock=FrozenClock())
    broker.publish(make_need("x1"))
    broker.publish(make_need("x2"))
    broker.publish(make_need("x3"))
    assert {n.need_id for n in broker.open_needs("nobody")} == {"x1", "x2", "x3"}

    l1 = broker.claim("x1", "wA")
    assert l1 is not None
    l2 = broker.claim("x2", "wB")
    assert l2 is not None
    assert broker.fulfill("x2", "art", l2, verified=True) is True

    opened = {n.need_id for n in broker.open_needs("nobody")}
    assert opened == {"x3"}, f"leased/fulfilled must be excluded, got {opened}"
    # Also excluded for the proposer.
    assert broker.open_needs("proposer") == []


# 8. Budget enforcement (no ranking involved).
def test_budget_enforced(tmp_path: Path):
    broker = NeedBroker(tmp_path / "b", lease_ttl_s=10.0, clock=FrozenClock())
    broker.publish(make_need("b1", tokens=100))
    broker.publish(make_need("b2", tokens=150))
    # Budget 100: can claim b1, cannot claim b2.
    with pytest.raises(BudgetExhausted):
        broker.claim("b2", "wA", agent_budget_tokens=100)
    l1 = broker.claim("b1", "wA", agent_budget_tokens=100)
    assert l1 is not None
    assert broker.fulfill("b1", "art-b1", l1, verified=True) is True
    # After fulfilling b1 (spent 100), remaining is 0: b2 now also refused.
    with pytest.raises(BudgetExhausted):
        broker.claim("b2", "wA", agent_budget_tokens=100)
    # A different agent with its own budget can still claim b2.
    l2 = broker.claim("b2", "wB", agent_budget_tokens=200)
    assert l2 is not None
