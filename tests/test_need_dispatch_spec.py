"""SPEC for F06 — decentralized need-dispatch adversarial scenarios.

Every test in this module is marked `@pytest.mark.skip(reason="F06 spec")`:
they pin the acceptance surface of `docs/design/NEED_DISPATCH.md` §7 and are
RED BY DESIGN today because the decentralized claim/dispatch layer
(`repliclaw.need_dispatch`: NeedBroker / NeedWorker / FulfilmentProvenance)
does not exist yet. F06 implements the module, then removes the skips and
makes each scenario pass.

The scenarios are the decentralization oracle: a central (today-style)
implementation — orchestrator picks a role and invokes the follow-up in
process (protocol.py::_fulfill_need) — would fail SPEC-1 (no claim events),
SPEC-2 (no lease state), SPEC-3 (role preassigned), SPEC-4 (single-process
seal only), and SPEC-5 (no dedup contract).

Suite stays green while skipped (fleet rule: no failing tests).
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# SPEC-1: two eligible workers → exactly one fulfils (no double-fulfil)
# ---------------------------------------------------------------------------
@pytest.mark.skip(reason="F06 spec")
def test_two_eligible_workers_only_one_fulfils():
    """SPEC-1 (NEED_DISPATCH.md §7): two workers sharing one NeedBroker race
    the same need_key; exactly one claim wins, exactly one fulfilment
    artifact exists, the need leaves the open set, need status → fulfilled.

    Parametrize claim order (A-first, B-first) to cover both race
    interleavings. A central dispatcher would produce ZERO `claimed` events
    in the broker log — the log assertion is what makes this test the
    decentralization oracle.
    """
    # F06: build run-local index + broker + two NeedWorkers (distinct
    # capability.agent_id, both producible_types ⊇ {"analysis_result"});
    # race claims; assert:
    #   * exactly one claim() returns a Lease, the other None
    #   * broker log: exactly one live `claimed` event at race time
    #   * one fulfilment artifact; broker.fulfilled_artifact() == its id
    #   * need_key absent from open_needs() for both workers
    #   * FollowUpNeed.status == "fulfilled"


@pytest.mark.skip(reason="F06 spec")
def test_two_eligible_workers_only_one_fulfils_reverse_order():
    """SPEC-1 reverse interleaving (B claims before A). Same assertions as
    the forward case — the winner is determined by the atomic claim, never
    by scheduler order."""
    # F06: parametrization of the above with claim order reversed.


# ---------------------------------------------------------------------------
# SPEC-2: crash after claim → lease expiry → re-fulfil by another worker
# ---------------------------------------------------------------------------
@pytest.mark.skip(reason="F06 spec")
def test_crash_after_claim_lease_expiry_refulfil():
    """SPEC-2 (NEED_DISPATCH.md §7): worker A claims, dies mid-execution
    (no publish). While the lease is live, worker B must NOT be able to
    steal (claim → None). After the fake clock passes lease_deadline, B
    claims with a new claim_token, fulfils, and exactly one fulfilment is
    accepted. Broker claim_history shows the claimed(A) → claimed(B) chain.

    Parametrize 4 crash interleavings (claim→die, claim→renew→die,
    crash-before-execute, crash-after-execute) — all must end in exactly one
    accepted fulfilment, never zero, never two effects.
    """
    # F06: NeedBroker with a monkeypatched clock; A claims then is discarded
    # without mark_fulfilled; assert B.claim() is None pre-expiry and a valid
    # Lease post-expiry with claim_token != A's; assert one accepted
    # fulfilment; assert claim_history length >= 2.


@pytest.mark.skip(reason="F06 spec")
def test_restarted_worker_is_stateless_and_cannot_lease_steal():
    """SPEC-2b: a worker 'process' rebuilt from run_dir (fresh NeedWorker on
    the same broker files) sees no private in-memory state; it can only act
    on what the broker log says. A live lease owned by another worker blocks
    it even if the dead worker's own scratch dir still exists."""
    # F06: rebuild worker A2 from disk while A's lease is live; assert
    # A2.claim(same need_key) is None and no foreign scratch is read
    # (context_built events show includes_peer_materials=False).


# ---------------------------------------------------------------------------
# SPEC-3: eligibility-driven dispatch, NOT role-preassigned (negates G1)
# ---------------------------------------------------------------------------
@pytest.mark.skip(reason="F06 spec")
def test_falsification_need_not_preassigned_to_falsifier_role():
    """SPEC-3 (NEED_DISPATCH.md §7): a FALSIFICATION-kind need (today's
    central code force-maps it to InvestigatorRole.FALSIFIER,
    protocol.py:401-404) is published WITHOUT any role/agent field. Workers:
    falsifier-capable, statistician-capable (method_family='bootstrap', also
    produces analysis_result), and an ineligible analyst (different
    artifact_type).

    Assertions:
      * the published NeedItem has no role/agent_id field;
      * in at least one parametrized run the statistician — not the
        falsifier — wins the claim and fulfils;
      * FulfilmentProvenance.method_family ∈ {'falsifier-raw','bootstrap'};
      * the ineligible worker never appears in claim_history.
    A central dispatcher cannot satisfy this: it would attach the role
    before any worker sees the need.
    """
    # F06: parametrize claim outcomes (falsifier-wins / statistician-wins via
    # deterministic seed or injected claim ordering); assert provenance
    # method_family matches the winner, and NeedWorker.eligible depends only
    # on capability, not on need.kind.


# ---------------------------------------------------------------------------
# SPEC-4: pre-reveal, no worker sees another worker's conclusion
# ---------------------------------------------------------------------------
@pytest.mark.skip(reason="F06 spec")
def test_pre_reveal_no_peer_conclusion_visibility():
    """SPEC-4 (NEED_DISPATCH.md §7): two workers each hold a committed but
    UNREVEALED blind finding with a distinguishable conclusion string
    ('support…' vs 'refut…'). Through the legitimate API only, each worker
    attempts to see the other:
      * enforcer.peer_materials(...) → {} while gate is blind/committed;
      * enforcer.read_sealed_commitment(…, revealed=True) → IsolationViolation;
      * own InvestigationContext.to_prompt_block(revealed=False) contains
        NEITHER peer's conclusion substring;
      * the worker's context build log records includes_peer_materials=False
        (the worker code path never references a foreign store).
    Honest limit (NEED_DISPATCH.md §5.3.1): a deliberate raw read of
    artifacts/<peer>/store.jsonl is OS-possible on one host; the test pins
    that the SYSTEM path provides no such read, not that a malicious process
    is stopped.
    """
    # F06: two NeedWorkers + one shared ContextEnforcer (gate at committed);
    # commit both findings without reveal; run the four probes; assert each.


# ---------------------------------------------------------------------------
# SPEC-5: crash before publish (orphaned fulfilment) → no double effect
# ---------------------------------------------------------------------------
@pytest.mark.skip(reason="F06 spec")
def test_orphaned_fulfilment_no_double_effect():
    """SPEC-5 (NEED_DISPATCH.md §7): worker A saves a fulfilment Artifact,
    dies before broker.mark_fulfilled; lease expires; worker B re-claims and
    re-fulfils with a different payload. Assertions:
      * two fulfilment artifacts exist in the store (no silent deletion);
      * broker.fulfilled_artifact() returns exactly one id; the other is
        recorded as duplicate_suppressed in claim_history/events;
      * consume_fulfilments yields exactly ONE Evidence row (the
        at-least-once-work / exactly-once-effects contract, §4.3);
      * re-running the consumer is idempotent (same single Evidence, no
        append); verdict input contains the single row.
    """
    # F06: simulate A's publish-then-die; B re-claims; call consume_fulfilments
    # twice; assert counts and ids; assert event log has duplicate_suppressed.


# ---------------------------------------------------------------------------
# SPEC-6 (bonus): deterministic priority — every worker ranks identically
# ---------------------------------------------------------------------------
@pytest.mark.skip(reason="F06 spec")
def test_all_workers_rank_needs_identically():
    """SPEC-6 (NEED_DISPATCH.md §7): the same index snapshot yields the same
    (need_key, score) ordering from NeedWorker.scan_and_rank() in two
    distinct workers — score_need is a pure function of index contents
    (pressure.py:145-193), so no worker is favored or starved by the
    scheduler; the only nondeterminism is the claim race itself (SPEC-1).
    """
    # F06: fix the index + clock; run scan_and_rank in two workers; assert
    # identical ordering and scores (exact float equality is fine: same
    # inputs, same pure function).
