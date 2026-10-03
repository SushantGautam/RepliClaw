"""P08/A6 — RandomPolicy single-draw regression (amendment A6, test 3).

Amendment docs/experiments/PREREG-2026-10-v1.2-AMENDMENT.md §A6 item 3:
``RandomPolicy.rank`` previously made TWO RNG draws per need
(``utility=float(rng.random())`` and
``components={"rng_draw": float(rng.random())}``), so the trace component
labeled a different number than the utility that selected the action.
The pre-run fix is STREAM-PRESERVING: it still consumes two draws per need
(the second, ``_stream_pad``, is never read) so the frozen A3-seed
selection is unchanged, while ``components["rng_draw"]`` now stores draw#1
— the number that actually selected.

Proof required here (selection-neutral + trace-correct):
  (a) for a pinned (rng_seed, agent_id, snapshot sha, need set),
      ``utility == components["rng_draw"]`` for EVERY ranked action;
  (b) SELECTION ORDER BYTE-IDENTICAL before/after: the ordered need_id list
      and the top-1 choice are identical when the OLD two-draw logic is run
      as an inline reference (old code is not kept in the tree — see
      ``rank_reference_two_draw``).

Why the order is provably identical: the fixed code is STREAM-PRESERVING
(CODE-JUDGE-HARNESS-20261008). It still consumes two ``rng.random()`` calls
per need — the first as ``utility``, the second as a never-read pad (
``_stream_pad``) — so the RNG consumption sequence is byte-identical to the
old code, and every need's utility is bit-for-bit unchanged. The only
change is that ``components["rng_draw"]`` now stores draw#1 (the number
that actually selected) instead of draw#2. ``_stable_order`` sorts by
``(-utility, need_id)`` and the reason string interpolates no draw value,
so utilities unchanged ⇒ ranked need_id order byte-identical. This test
asserts exactly that, with the old behavior inlined as the reference.

Fixture (documented, per A6):
  * rng_seed  = 20261010 — the pinned A3 primary harness seed
    (src/repliclaw/eess_live/arm.py ``harness_seed``; PREREG v1.1 §9.1).
  * agent_id  = "agent_0", snapshot = "sha256:" + "0"*64 — fixed stand-in
    for one A3 run's evidence snapshot sha (shape matches the real
    73-char hex-sha string; content irrelevant to order identity because
    both code paths share it inside the RNG stream seed).
  * needs     = four synthetic ``Need`` objects mirroring
    ``make_need`` in src/repliclaw/slice/orchestrate.py over the real
    offline-slice arms (``need_<arm>_<proposer>`` ids, capability
    "counterfactual-arm", cost 1000 tokens / 5 s): I0_baseline,
    I_R_retrieval_fix, I_J_judge_fix, I_P_policy_conflict (the three
    intervention arms of slice.derive.ARM_BY_HYP + baseline). Synthetic
    mirrors are used so the test is independent of the SimpleAudit import
    chain; the need_id set matches the offline slice.
"""
from __future__ import annotations

import random
from typing import List

from repliclaw.needmarket import Need, RandomPolicy
from repliclaw.needmarket.needs import CostEstimate
from repliclaw.needmarket.policy import RankedAction, _stable_order

# ---------------------------------------------------------------------------
# Pinned A6 fixture
# ---------------------------------------------------------------------------
A6_SEED = 20261010  # A3 primary harness seed
A6_AGENT = "agent_0"
A6_SNAPSHOT_SHA = "sha256:" + "0" * 64
A6_ARMS = ("I0_baseline", "I_R_retrieval_fix", "I_J_judge_fix", "I_P_policy_conflict")
A6_PROPOSER = "agent_0"


def _a6_needs() -> List[Need]:
    """The fixed need list (mirror of the orchestrate.py offline slice)."""
    return [
        Need(
            need_id=f"need_{arm}_{A6_PROPOSER}",
            case_id="policy_rag_v1",
            title=f"Run counterfactual arm {arm}",
            description=f"Execute the {arm} intervention arm.",
            proposer_id=A6_PROPOSER,
            proposed_at="2026-10-10T00:00:00+00:00",
            required_capability="counterfactual-arm",
            cost_estimate=CostEstimate(tokens=1000, wall_s=5.0),
        )
        for arm in A6_ARMS
    ]


def rank_reference_two_draw(
    agent_id: str,
    needs: List[Need],
    evidence_snapshot_sha: str,
    rng_seed: int,
) -> List[RankedAction]:
    """INLINE reference of the PRE-FIX RandomPolicy.rank (two draws per need).

    Not the old module code (which no longer exists in the tree) — a verbatim
    re-implementation of the old body, kept only to prove selection-order
    byte-identity per amendment A6 item 3.
    """
    rng = random.Random(f"{rng_seed}|{agent_id}|{evidence_snapshot_sha}")
    actions = [
        RankedAction(
            need_id=n.need_id,
            utility=float(rng.random()),
            components={"rng_draw": float(rng.random())},
            reason=(
                f"random comparator draw; seed={rng_seed} agent={agent_id} "
                f"snapshot={evidence_snapshot_sha[:12]}"
            ),
        )
        for n in needs
    ]
    return _stable_order(actions)


# (a) Trace correctness: utility and the trace component are the SAME draw.
def test_random_policy_utility_equals_trace_component():
    for needs in (_a6_needs(), _a6_needs()[1:], _a6_needs()[:2]):
        ranked = RandomPolicy().rank(A6_AGENT, needs, A6_SNAPSHOT_SHA, rng_seed=A6_SEED)
        assert [a.need_id for a in ranked]  # sanity: non-empty
        for a in ranked:
            assert a.components["rng_draw"] == a.utility, (
                f"{a.need_id}: trace component {a.components['rng_draw']!r} must label "
                f"the utility that selected the action ({a.utility!r})"
            )
            assert set(a.components) == {"rng_draw"}


# (b) Selection-order byte-identity, pinned A3 seed.
def test_random_policy_selection_order_identical_to_two_draw_reference():
    needs = _a6_needs()
    fixed = RandomPolicy().rank(A6_AGENT, needs, A6_SNAPSHOT_SHA, rng_seed=A6_SEED)
    old = rank_reference_two_draw(A6_AGENT, needs, A6_SNAPSHOT_SHA, rng_seed=A6_SEED)

    assert len(fixed) == len(old)
    # The ordered need_id list is byte-identical (the A6 requirement).
    assert [a.need_id for a in fixed] == [a.need_id for a in old], (
        f"selection order changed: {[a.need_id for a in fixed]} "
        f"vs old {[a.need_id for a in old]} — A6 requires re-pinning the A3 seed"
    )
    # Top-1 choice identical.
    assert fixed[0].need_id == old[0].need_id
    # Utilities (draw#1, unchanged by the stream-preserving fix) and reason
    # strings are identical; the only change is the trace component, which
    # now stores draw#1 instead of the old, never-read draw#2.
    assert [a.utility for a in fixed] == [a.utility for a in old]
    assert [a.reason for a in fixed] == [a.reason for a in old]
    assert [a.components["rng_draw"] for a in fixed] == [a.utility for a in fixed]
    assert [a.components["rng_draw"] for a in old] != [a.utility for a in old]
    # And per the fix: each fixed utility IS its trace draw.
    for a in fixed:
        assert a.utility == a.components["rng_draw"]
