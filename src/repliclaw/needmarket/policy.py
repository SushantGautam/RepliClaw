"""Per-agent action policies: the ONLY place scientific ranking happens
(EESS contract §4 — the broker never ranks).

Design (F04 §5, ticket P04): each agent ranks the open needs with a local,
transparent utility function over (needs, evidence snapshot, its own
capability config). The policies are pure functions of their inputs: same
(needs, snapshot sha, agent config, rng_seed) → same ranking, so ranking is
reproducible from a recorded snapshot (F04 carry-over 5: freeze the clock,
pin the seed).

``LocalEigPolicy`` utility:

    U = est_info_gain(need) / est_cost(need)
        + lam * diversity_bonus(need)
        - mu  * crowding_penalty(need)

- ``est_info_gain`` comes from a caller-supplied ``discriminability``
  mapping ``need_id -> {hypothesis_id: float}``. The policy never sees the
  oracle; P07 feeds real numbers derived from public evidence, tests use
  fixtures.
- ``est_cost`` is the need's token (or wall-second) cost estimate.
- ``diversity_bonus`` = fraction of hypotheses this need discriminates
  (needs that can tell more hypotheses apart are worth more).
- ``crowding_penalty`` = share of other open needs sharing this need's
  required capability (a crowded capability market has lower marginal
  value).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Protocol

from repliclaw.needmarket.needs import Need

Discriminability = Mapping[str, Mapping[str, float]]  # need_id -> {hyp: float}


class ActionPolicy(Protocol):
    """Local ranking: the interface every worker policy implements."""

    def rank(
        self,
        agent_id: str,
        needs: List[Need],
        evidence_snapshot_sha: str,
        rng_seed: int,
    ) -> List["RankedAction"]: ...

    def set_discriminability(self, mapping: "Discriminability") -> None: ...


@dataclass(frozen=True)
class RankedAction:
    """One ranked action (T4 trace: ``components`` + ``reason`` are the
    machine-checkable justification)."""

    need_id: str
    utility: float
    components: Dict[str, float] = field(default_factory=dict)
    reason: str = ""


def _est_cost(need: Need) -> float:
    if need.cost_estimate.tokens is not None:
        return max(float(need.cost_estimate.tokens), 1.0)
    return max(need.cost_estimate.wall_s, 1.0) * 100.0


def _info_gain(need: Need, discriminability: Discriminability) -> float:
    per_hyp = discriminability.get(need.need_id, {})
    if not per_hyp:
        return 0.0
    return sum(float(v) for v in per_hyp.values())


def _stable_order(actions: List[RankedAction]) -> List[RankedAction]:
    return sorted(actions, key=lambda a: (-a.utility, a.need_id))


class LocalEigPolicy:
    """Transparent local expected-information-gain policy (per agent).

    ``lam`` weights diversity, ``mu`` weights crowding; both are per-agent
    config so different agents can have different local utility.
    """

    def __init__(
        self,
        discriminability: Discriminability,
        lam: float = 0.5,
        mu: float = 0.25,
    ) -> None:
        self.discriminability: Dict[str, Dict[str, float]] = {
            k: dict(v) for k, v in discriminability.items()
        }
        self.lam = lam
        self.mu = mu

    def set_discriminability(self, mapping: Discriminability) -> None:
        """Update the evidence-derived discriminability (new observation)."""
        self.discriminability = {k: dict(v) for k, v in mapping.items()}

    def rank(
        self,
        agent_id: str,
        needs: List[Need],
        evidence_snapshot_sha: str,
        rng_seed: int,
    ) -> List[RankedAction]:
        actions: List[RankedAction] = []
        cap_counts: Dict[str, int] = {}
        for n in needs:
            cap_counts[n.required_capability] = cap_counts.get(n.required_capability, 0) + 1
        for n in needs:
            gain = _info_gain(n, self.discriminability)
            cost = _est_cost(n)
            per_hyp = self.discriminability.get(n.need_id, {})
            diversity = 1.0 if per_hyp else 0.0
            crowding = (cap_counts.get(n.required_capability, 1) - 1) / max(
                len(needs) - 1, 1
            )
            utility = gain / cost + self.lam * diversity - self.mu * crowding
            actions.append(
                RankedAction(
                    need_id=n.need_id,
                    utility=utility,
                    components={
                        "info_gain": gain,
                        "cost": cost,
                        "diversity_bonus": diversity,
                        "crowding_penalty": crowding,
                        "lam": self.lam,
                        "mu": self.mu,
                    },
                    reason=(
                        f"snapshot={evidence_snapshot_sha[:12]} "
                        f"discriminability({n.need_id})="
                        f"{ {k: round(v, 4) for k, v in per_hyp.items()} or 'none'}; "
                        f"capability {n.required_capability!r} shared by "
                        f"{cap_counts.get(n.required_capability, 1)} open need(s); "
                        f"agent={agent_id}"
                    ),
                )
            )
        return _stable_order(actions)


class RandomPolicy:
    """Seeded random comparator (mandatory cheap baseline).

    Fully deterministic under pinned (rng_seed, agent_id, snapshot sha,
    need set) — no wall clock, no unseeded randomness.
    """

    def rank(
        self,
        agent_id: str,
        needs: List[Need],
        evidence_snapshot_sha: str,
        rng_seed: int,
    ) -> List[RankedAction]:
        rng = random.Random(f"{rng_seed}|{agent_id}|{evidence_snapshot_sha}")
        actions = []
        for n in needs:
            # PREREG-2026-10-v1.2-AMENDMENT A6; CODE-JUDGE-HARNESS-20261008:
            # stream-preserving single-label fix. The OLD code consumed TWO
            # draws per need (utility=draw#1, components=draw#2), so the
            # trace component mislabeled a number that did NOT determine the
            # action. Collapsing to one draw is NOT selection-neutral: it
            # shifts the RNG stream for every need after the first, changing
            # the frozen A3-seed selection. Correct fix: keep consuming two
            # draws (byte-identical stream), but use ONLY draw#1 for the
            # utility AND for components["rng_draw"] so the trace labels the
            # number that actually selected. `_stream_pad` is the (unused)
            # draw#2, consumed solely to preserve stream compatibility.
            draw = float(rng.random())
            _stream_pad = float(rng.random())  # draw#2: consumed for stream compatibility only, never read
            actions.append(
                RankedAction(
                    need_id=n.need_id,
                    utility=draw,
                    components={"rng_draw": draw},
                    reason=(
                        f"random comparator draw; seed={rng_seed} agent={agent_id} "
                        f"snapshot={evidence_snapshot_sha[:12]}"
                    ),
                )
            )
        return _stable_order(actions)


class GreedySharedPolicy:
    """Anti-pattern comparator: agent-agnostic global score.

    Given the same snapshot, EVERY agent gets the identical ranking (that
    identical-for-all-agents property is exactly what the test asserts).
    """

    def __init__(self, discriminability: Discriminability) -> None:
        self.discriminability: Dict[str, Dict[str, float]] = {
            k: dict(v) for k, v in discriminability.items()
        }

    def rank(
        self,
        agent_id: str,
        needs: List[Need],
        evidence_snapshot_sha: str,
        rng_seed: int,
    ) -> List[RankedAction]:
        actions: List[RankedAction] = []
        for n in needs:
            gain = _info_gain(n, self.discriminability)
            cost = _est_cost(n)
            utility = gain / cost
            actions.append(
                RankedAction(
                    need_id=n.need_id,
                    utility=utility,
                    components={"info_gain": gain, "cost": cost},
                    reason=(
                        f"global greedy score (agent-agnostic); "
                        f"snapshot={evidence_snapshot_sha[:12]}"
                    ),
                )
            )
        return _stable_order(actions)


__all__ = [
    "ActionPolicy",
    "RankedAction",
    "LocalEigPolicy",
    "RandomPolicy",
    "GreedySharedPolicy",
    "Discriminability",
]
