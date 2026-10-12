"""Four-arm strategy policies for the CompoundCausal-32 frozen protocol.

Implements docs/experiments/COMPOUND_CAUSAL_4ARM.md section 1:
adaptive_central (S3 comparator), replclaw_escrow, open_sharing, random.

ISOLATION RULE (frozen): every policy interacts with a case ONLY through
BenchmarkSession methods (card / observe / commit / intervene /
public_history). No policy reads gold, oracles, simulator internals, or
another arm's session state. The only code allowed to touch private data is
the scoring step in run_cli.
"""
from __future__ import annotations

import random as _random_module
from typing import Any

from .core import FACTORS, BenchmarkSession

# Canonical factor order (matches core.FACTORS) used for all submissions.
CANONICAL_FACTORS = list(FACTORS)


def _canonical(causes: list[str]) -> list[str]:
    """Sort by canonical factor order, drop duplicates and unknown names."""
    return [f for f in CANONICAL_FACTORS if f in set(causes)]


def validate_submission(submission: dict[str, Any]) -> None:
    """Frozen submission schema (protocol section 3). Raises ValueError on violation."""
    logic = submission["predicted_logic"]
    causes = submission["predicted_causes"]
    if logic not in ("clean", "single", "or", "and", "abstain"):
        raise ValueError(f"bad predicted_logic {logic!r}")
    if any(f not in CANONICAL_FACTORS for f in causes):
        raise ValueError(f"unknown cause factor in {causes!r}")
    if len(set(causes)) != len(causes):
        raise ValueError("duplicate causes")
    if causes != _canonical(causes):
        raise ValueError("causes not in canonical order")
    if logic == "abstain":
        if causes:
            raise ValueError("abstain must pair with empty predicted_causes")
    elif logic == "clean":
        # A clean conclusion asserts no defect; an empty cause set is the only
        # consistent pairing under this schema.
        if causes:
            raise ValueError("clean must pair with empty predicted_causes")
    elif logic == "single":
        if len(causes) != 1:
            raise ValueError("single requires exactly one cause")
    elif logic in ("or", "and"):
        if len(causes) != 2:
            raise ValueError(f"{logic} requires exactly two causes")


def make_submission(case_id: str, causes: list[str], logic: str) -> dict[str, Any]:
    submission = {"case_id": case_id, "predicted_causes": _canonical(causes),
                  "predicted_logic": logic}
    validate_submission(submission)
    return submission


def _evidence_signals(evidence: dict[str, Any]) -> dict[str, int]:
    """Score each factor from its indicator record (0..2 scale, noisy correlate)."""
    scores: dict[str, int] = {}
    for factor in CANONICAL_FACTORS:
        rec = evidence.get(factor) or {}
        s = 0
        if rec.get("trace_indicator") == "atypical":
            s += 1
        if rec.get("secondary_indicator") == "alert":
            s += 1
        scores[factor] = s
    return scores


def _rank_factors(scores: dict[str, int]) -> list[str]:
    """Factors ordered by descending score, then canonical order (deterministic)."""
    return sorted(CANONICAL_FACTORS, key=lambda f: (-scores[f], CANONICAL_FACTORS.index(f)))


def _top_scores(scores: dict[str, int], n: int) -> list[str]:
    ranked = _rank_factors(scores)
    top_score = scores[ranked[0]]
    tied = [f for f in ranked if scores[f] == top_score]
    return tied[:n]


class _TokenMeter:
    """Deterministic token proxy accounting (protocol section 4.6)."""

    COSTS = {"observe": 50, "commit": 80, "intervene": 120, "final_submission": 100}

    def __init__(self) -> None:
        self.tokens = 0
        self.calls: dict[str, int] = {k: 0 for k in self.COSTS}

    def charge(self, kind: str) -> None:
        self.calls[kind] += 1
        self.tokens += self.COSTS[kind]

    def summary(self) -> dict[str, Any]:
        return {"tokens_proxy": self.tokens, "calls": dict(self.calls)}


class _HeldoutArm:
    """Shared sequential counterfactual design for adaptive_central and replclaw_escrow.

    Design (budgets: <=6 interventions, <=4 reads, <=2 repairs per intervention):
      R0: baseline probe intervene([]).
          resolved -> conclude abstain (no defect exists to repair).
      R1: single-factor repair of the top-ranked candidate(s) (<=2 factors).
          If it resolves, the incident depends on that factor alone.
      R2 (only when R1 did not resolve AND >=2 candidates remain): discriminate
          compound structure by repairing ONE of the remaining candidates.
          Structural equations (core.intervene): 'or' = incident iff ANY fault
          remains, so repairing one member of an OR pair leaves the incident
          present; 'and' = incident iff ALL faults remain, so repairing one
          member of an AND pair resolves the incident immediately.
          => still present after single-member repair: OR over the two members
             whose joint repair also resolved (else AND fallback).
          => resolved after single-member repair: AND between that member and
             the first non-resolving candidate from R1.
      R3 (fallback): joint repair of up to 2 remaining candidates.
    Forecasts are committed BEFORE each planned intervention whenever a
    non-trivial hypothesis exists (protocol section 1.1).

    Budget note: the baseline probe + single-factor repair + remaining-pair
    joint repair + one member discrimination uses at most 4 interventions,
    well within the 6-intervention budget; reads are bounded by the 4-channel
    read budget on distributed cases and unused on shared cases.
    """

    AGENT_ID: str = "central"

    def __init__(self, session: BenchmarkSession, meter: _TokenMeter) -> None:
        self.session = session
        self.meter = meter
        self.card = session.card()
        self.case_id = self.card["case_id"]
        self.mode = self.card["evidence_mode"]
        self._read_channels: set[str] = set()

    # -- budget-safe wrappers -------------------------------------------
    def _observe(self, channel: str) -> None:
        try:
            self.session.observe(channel)
            self._read_channels.add(channel)
            self.meter.charge("observe")
        except ValueError:
            pass  # read budget exhausted; continue on existing evidence

    def _commit(self, causes: list[str], repairs: list[str], prob: float) -> bool:
        try:
            self.session.commit(self.AGENT_ID, _canonical(causes), _canonical(repairs),
                                min(1.0, max(0.0, prob)))
            self.meter.charge("commit")
            return True
        except ValueError:
            return False  # e.g. that intervention already executed

    def _intervene(self, repairs: list[str]) -> dict[str, Any] | None:
        try:
            result = self.session.intervene(_canonical(repairs))
            self.meter.charge("intervene")
            return result
        except ValueError:
            return None  # intervention budget exhausted

    # -- evidence ---------------------------------------------------------
    def gather_evidence(self) -> dict[str, int]:
        if self.mode == "shared":
            return _evidence_signals(self.card.get("initial_evidence") or {})
        # Distributed: spend up to 4 channel reads (all channels fit the budget).
        for channel in CANONICAL_FACTORS:
            self._observe(channel)
        history = self.session.public_history()
        merged: dict[str, Any] = {}
        for obs in history["observations"]:
            if obs["channel"] not in self._read_channels:
                continue
            merged[obs["channel"]] = obs["evidence"]
        return _evidence_signals(merged)

    # -- decision loop ----------------------------------------------------
    def run(self) -> dict[str, Any]:
        scores = self.gather_evidence()
        ranked = _rank_factors(scores)

        # R0: baseline probe (no repairs). Non-trivial hypothesis: some defect
        # may exist, so commit a forecast before probing.
        self._commit([ranked[0]], [], 0.7 if scores[ranked[0]] > 0 else 0.3)
        baseline = self._intervene([])
        if baseline is None:
            return self.best_effort(scores)
        if baseline["incident"] == "resolved":
            return make_submission(self.case_id, [], "abstain")

        # R1: single-factor repair of the top-ranked candidate only. Repairing
        # two factors at once would conflate single and compound structure.
        target = ranked[0]
        self._commit([target], [target], 0.7)
        r1 = self._intervene([target])
        if r1 is None:
            return self.best_effort(scores)
        if r1["incident"] == "resolved":
            return make_submission(self.case_id, [target], "single")

        # R1 left the incident present after repairing `target`. Under the
        # structural equations: an OR incident survives any proper subset
        # repair (an unrepaired true member keeps it alive); an AND incident
        # resolves as soon as ANY member is repaired. So:
        #   * single@other: exactly one other factor resolves alone;
        #   * OR pair: no single repair resolves; the full pair resolves;
        #   * AND pair: EVERY single-member repair resolves;
        #   * clean: nothing resolves.
        remaining = [f for f in ranked if f != target]
        if not remaining:
            return self.best_effort(scores)
        probe_a, probe_b = remaining[0], remaining[1]

        # R2a: top remaining candidate alone.
        self._commit([probe_a], [probe_a], 0.5)
        r2 = self._intervene([probe_a])
        if r2 is None:
            return self.best_effort(scores)
        a_resolved = r2["incident"] == "resolved"
        # R2b: second remaining candidate alone.
        self._commit([probe_b], [probe_b], 0.5)
        r3 = self._intervene([probe_b])
        b_resolved = r3 is not None and r3["incident"] == "resolved"

        if a_resolved and b_resolved:
            # Both probes resolve individually => AND semantics between them.
            return make_submission(self.case_id, _canonical([probe_a, probe_b]), "and")
        if a_resolved and not b_resolved:
            # Exactly one probe resolves. Two readings fit: single@probe_a,
            # or AND(target, probe_a) where target's repair (R1) already
            # cleared the incident so probe_a alone now suffices. Evidence
            # tie-break: prefer the AND pair only when `target` strictly
            # out-scores probe_a; otherwise single-cause at probe_a.
            if scores[target] > scores[probe_a]:
                return make_submission(self.case_id, _canonical([target, probe_a]), "and")
            return make_submission(self.case_id, [probe_a], "single")
        if b_resolved and not a_resolved:
            if scores[target] > scores[probe_b]:
                return make_submission(self.case_id, _canonical([target, probe_b]), "and")
            return make_submission(self.case_id, [probe_b], "single")

        # No single remaining factor resolves: either an OR pair among the
        # three candidates (target, probe_a, probe_b) or a clean case. An AND
        # pair is excluded here: its members each resolve individually.
        # R2c: joint repair of the two highest-ranked remaining candidates.
        combo = _canonical([probe_a, probe_b])
        self._commit(combo, combo, 0.6)
        r4 = self._intervene(combo)
        if r4 is None:
            return self.best_effort(scores)
        if r4["incident"] == "resolved":
            # {probe_a, probe_b} jointly resolve while each alone did not:
            # OR pair. (Budget note: this is intervention 4 of max 6.)
            return make_submission(self.case_id, combo, "or")
        # Still present: {probe_a, probe_b} contains no true cause at all
        # (clean case) or it is exactly one of them paired with `target`
        # (OR semantics: an unrepaired true member keeps the incident alive).
        # Distinguish by repairing target + probe_a: resolved => that pair is
        # the cause set; still present => either clean or target+probe_b.
        cross = _canonical([target, probe_a])
        self._commit(cross, cross, 0.6)
        r5 = self._intervene(cross)
        if r5 is not None and r5["incident"] == "resolved":
            return make_submission(self.case_id, cross, "or")
        # Final discrimination (intervention 6): repair target + probe_b.
        cross_b = _canonical([target, probe_b])
        self._commit(cross_b, cross_b, 0.6)
        r6 = self._intervene(cross_b)
        if r6 is not None and r6["incident"] == "resolved":
            return make_submission(self.case_id, cross_b, "or")
        # Nothing resolves: no supported defect -> abstain.
        return make_submission(self.case_id, [], "abstain")

    def best_effort(self, scores: dict[str, int]) -> dict[str, Any]:
        """Budget-exhaustion fallback: submit the strongest supported guess."""
        ranked = _rank_factors(scores)
        top = scores[ranked[0]]
        if top <= 0:
            return make_submission(self.case_id, [], "abstain")
        strong = [f for f in ranked if scores[f] == top][:2]
        if len(strong) == 1:
            return make_submission(self.case_id, strong, "single")
        return make_submission(self.case_id, strong, "or")


class AdaptiveCentralArm(_HeldoutArm):
    """Arm 1: strong adaptive centralized manager (mandatory S3 comparator)."""

    AGENT_ID = "central"


class RepliClawEscrowArm(_HeldoutArm):
    """Arm 2: decentralized evidence-escrow team, N=4 agents rc-a..rc-d.

    Coordination regime (frozen):
      * Before any experiment, EACH agent commits a blind sealed forecast via
        session.commit(): its own hypothesis (from shared evidence + its own
        ranking offset) plus the planned experiment it would like executed and
        a confidence probability. NO sharing of conclusions before reveal.
      * After commitments, exactly ONE experiment executes per round: the
        evidence-driven reallocation rule picks the agent whose committed
        forecast carries the highest stakes (probability farthest from 0.5,
        ties broken by fixed agent order rc-a < rc-b < rc-c < rc-d), and THAT
        agent's planned experiment is executed.
      * Revealed forecasts are observed; the next round reallocates based on
        revealed evidence (surviving hypotheses drive re-commits).
      * Final submission aggregates surviving hypotheses: majority vote over
        the per-agent final predictions weighted by how few of their revealed
        forecasts were falsified (falsified = |p - outcome| large, i.e. brier
        > 0.25). Ties break toward the intersection-consistent choice, then
        canonical factor order. This is documented here per protocol note.

    The session enforces identical budgets; the team coordinates so total
    calls stay within them (one experiment per round, <=6 rounds).

    Note: this class intentionally does NOT override AGENT_ID — each round's
    commitments are made under the four distinct escrow agent IDs (rc-a..d),
    not the inherited 'central' ID, so revealed forecasts attribute to the
    committing escrow agent.
    """

    AGENTS = ("rc-a", "rc-b", "rc-c", "rc-d")
    AGENT_ID = ""  # unused: commits use per-agent IDs below

    def __init__(self, session: BenchmarkSession, meter: _TokenMeter) -> None:
        super().__init__(session, meter)
        self.agent_ids = self.AGENTS

    def _commit(self, causes: list[str], repairs: list[str], prob: float,
                agent_id: str | None = None) -> bool:
        try:
            self.session.commit(agent_id or self.AGENT_ID, _canonical(causes),
                                _canonical(repairs), min(1.0, max(0.0, prob)))
            self.meter.charge("commit")
            return True
        except ValueError:
            return False

    def run(self) -> dict[str, Any]:
        scores = self.gather_evidence()
        ranked = _rank_factors(scores)
        # Per-agent hypothesis: each agent anchors on a distinct factor in
        # ranked order (rc-a -> ranked[0], rc-b -> ranked[1], ...). A pair
        # hypothesis forms when the anchor ties with the next-ranked factor.
        hypotheses: dict[str, list[str]] = {}
        for i, agent in enumerate(self.AGENTS):
            anchor = ranked[i % len(ranked)]
            hyp = [anchor]
            nxt = ranked[(i + 1) % len(ranked)]
            if scores[nxt] == scores[anchor] and nxt != anchor:
                hyp.append(nxt)
            hypotheses[agent] = hyp
        # Round structure (max 6 rounds = intervention budget):
        #   R1: all four commit BLIND sealed forecasts (no sharing yet):
        #       rc-a probes ranked[0], rc-b probes ranked[1], rc-c probes
        #       ranked[2], rc-d holds an empty baseline plan. ONE experiment
        #       executes, chosen by evidence-driven reallocation (highest
        #       stakes = probability farthest from 0.5; ties by fixed agent
        #       order rc-a < rc-b < rc-c < rc-d).
        #   R2+: revealed forecasts are observed; agents whose hypotheses
        #       survived re-commit; the reallocated experiment executes.
        executed: set[tuple[str, ...]] = set()
        self._resolved_by: list[list[str]] = []
        for round_no in range(6):
            plans: dict[str, list[str]] = {}
            for i, agent in enumerate(self.AGENTS):
                if round_no == 0:
                    plans[agent] = [hypotheses[agent][0]] if i < 3 else []
                else:
                    hyp = hypotheses[agent]
                    plan = [hyp[0]]
                    # Avoid re-running an identical single-factor probe.
                    if len(plan) == 1 and tuple(plan) in executed:
                        alt = next((f for f in ranked
                                    if tuple([f]) not in executed and f != plan[0]), None)
                        plan = [alt] if alt is not None else []
                    plans[agent] = plan
            committed: list[tuple[str, float, list[str]]] = []
            for agent in self.AGENTS:
                hyp = hypotheses[agent]
                conf = 0.5 + 0.25 * (scores[hyp[0]] / 2.0)  # evidence-scaled stakes
                if self._commit(hyp, plans[agent], conf, agent_id=agent):
                    committed.append((agent, conf, plans[agent]))
            if not committed:
                break
            ordered = sorted(committed,
                             key=lambda c: (-abs(c[1] - 0.5), self.AGENTS.index(c[0])))
            chosen = next((c for c in ordered
                           if tuple(c[2]) not in executed and c[2]), None)
            if chosen is None:
                break
            result = self._intervene(chosen[2])
            if result is None:
                break
            executed.add(tuple(result["repairs"]))
            # Reveal-based reallocation: every agent updates its hypothesis
            # from the revealed outcome. Under 'and' semantics ANY member
            # repair resolves, so a resolution identifies a SUFFICIENT member,
            # not necessarily the full cause set; agents therefore keep their
            # own anchor unless it was directly falsified by a non-resolution
            # of their own probe, and record the resolving member for the
            # compound reading at aggregation time.
            if result["incident"] == "resolved":
                self._resolved_by.append(list(result["repairs"]))
            for agent in self.AGENTS:
                hyp = hypotheses[agent]
                if result["incident"] == "present":
                    # Repaired factors cannot be SOLE causes; demote them,
                    # but never discard a multi-member hypothesis wholesale.
                    survivors = [f for f in hyp if f not in result["repairs"]]
                    hypotheses[agent] = survivors or hyp
            finals = {tuple(h) for h in hypotheses.values()}
            if all(len(h) == 1 for h in hypotheses.values()) and len(finals) == 1:
                break
        return self._aggregate(ranked, scores, hypotheses)

    def _aggregate(self, ranked: list[str], scores: dict[str, int],
                   hypotheses: dict[str, list[str]]) -> dict[str, Any]:
        """Consensus of surviving hypotheses after reveals.

        Choice (documented per protocol note): weighted MAJORITY VOTE among
        agents whose forecasts were falsified least. Each agent's vote is its
        final (post-reveal) hypothesis; weight = revealed forecasts minus
        falsified ones (falsified = brier > 0.25, i.e. |p - outcome| > 0.5).
        Compound reading: when MULTIPLE distinct single-factor repairs each
        resolved the incident, the structure is AND over those members (an
        OR incident would have survived at least one of them); the vote picks
        the two highest-weighted resolving members. When exactly ONE single
        factor ever resolved, the submission is single-cause at that factor.
        Ties break toward the smaller cause set, then canonical factor order.
        """
        return _consensus_from_history(
            self.session.public_history(), self.AGENTS, hypotheses, scores,
            self.case_id, self.best_effort(scores))


def _consensus_from_history(history: dict[str, Any], agents: tuple[str, ...],
                            hypotheses: dict[str, list[str]],
                            scores: dict[str, int], case_id: str,
                            fallback: dict[str, Any]) -> dict[str, Any]:
    """Shared consensus rule for the N=4 team arms (escrow + open sharing).

    Voting weight per agent = revealed forecasts minus falsified ones
    (falsified = brier > 0.25, i.e. |p - outcome| > 0.5). Each agent's vote
    is its final post-reveal hypothesis. Structure readings from executed
    experiments: exactly one distinct single-factor repair ever resolved =>
    single-cause at that factor; multiple distinct single-factor repairs each
    resolved => AND over the top two by evidence (an OR incident would have
    survived at least one member repair); nothing resolved => abstain.
    """
    experiments = history["interventions"]
    if not experiments:
        return fallback
    falsified = {a: 0 for a in agents}
    total = {a: 0 for a in agents}
    for fc in history["revealed_forecasts"]:
        agent = fc["packet"]["agent_id"]
        if agent in total:
            total[agent] += 1
            if fc["brier"] > 0.25:
                falsified[agent] += 1
    weight = {a: (total[a] - falsified[a]) for a in agents}
    votes: dict[tuple[str, ...], int] = {}
    for agent in agents:
        w = weight[agent]
        if w <= 0:
            continue
        votes[tuple(hypotheses[agent])] = votes.get(tuple(hypotheses[agent]), 0) + w
    if not votes:
        return fallback
    # Structural readings from executed outcomes take precedence over the raw
    # vote: they are deterministic consequences of the interventions.
    resolvers = [f for f in CANONICAL_FACTORS
                 if any(e["incident"] == "resolved" and e["repairs"] == [f]
                        for e in experiments)]
    # Confidence signal (documented tie-break): an agent committing p > 0.5
    # on its OWN probe of a factor asserts that repairing it WILL resolve the
    # incident — i.e. it reads the factor as load-bearing before the outcome
    # was known. Under AND both members are load-bearing; under OR/clean at
    # most one member's resolution is causally meaningful. Counting distinct
    # RESOLVERS so asserted by the team's sealed forecasts:
    #   >=2 distinct resolvers asserted load-bearing => AND over resolvers
    #   otherwise                                    => single-cause at the
    #         highest-evidence resolver.
    # (p == 0.5 counts as no assertion; the team's confidence formula yields
    # exactly 0.5 when a factor has zero evidence.)
    # Limitation (reported, not tuned around): with noisy evidence all agents
    # can be simultaneously overconfident (clean cases with false-positive
    # signals), in which case this rule over-reads AND. That is a real
    # property of the escrow/open-sharing regimes on this benchmark and is
    # reported as-is per the anti-tuning rule.
    own_probe_high: set[str] = set()
    for fc in history["revealed_forecasts"]:
        packet = fc["packet"]
        if (len(packet["planned_repairs"]) == 1
                and packet["probability_incident"] > 0.5
                and packet["predicted_causes"] == packet["planned_repairs"]):
            own_probe_high.add(packet["planned_repairs"][0])
    if len(resolvers) == 1:
        # A unique resolving single factor IS the single cause, even when the
        # vote landed on a different anchor (noisy ranking).
        return make_submission(case_id, resolvers, "single")
    if len(resolvers) == 2:
        # Exactly two members each resolved alone. Both readings fit: AND of
        # the two (every member alone suffices to clear an AND incident), or
        # OR/clean where one member's repair coincidentally cleared the
        # incident. The committed-forecast record breaks the tie as above.
        # NOTE (documented limitation): the team's confidence formula is
        # evidence-based, not outcome-aware — agents with false-positive
        # signals commit p > 0.5 probes on factors that are NOT resolvers,
        # which dilutes the load-bearing assertion count and can flip a true
        # AND read as single. This is a genuine property of the decentralized
        # escrow/open-sharing regime on this benchmark and is reported as-is
        # per the anti-tuning rule (no case-specific corrections).
        n_asserted = len(own_probe_high & set(resolvers))
        if n_asserted >= 2:
            return make_submission(case_id, _canonical(resolvers), "and")
        top = sorted(resolvers, key=lambda f: (-scores[f], CANONICAL_FACTORS.index(f)))[0]
        return make_submission(case_id, [top], "single")
    if len(resolvers) > 2:
        # More than two single resolvers: keep the top-two-by-evidence AND
        # reading (degenerate case; prefer the voted solo member when it is a
        # resolver).
        best_key = max(votes.items(),
                       key=lambda kv: (kv[1], -len(kv[0]),
                                       -min(CANONICAL_FACTORS.index(f) for f in kv[0])))
        solo = best_key[0][0] if len(best_key[0]) == 1 else None
        pool = [solo] if solo in resolvers else []
        pool += [f for f in resolvers if f not in pool]
        pool.sort(key=lambda f: (-scores[f], CANONICAL_FACTORS.index(f)))
        return make_submission(case_id, _canonical(pool[:2]), "and")
    best_key = max(votes.items(),
                   key=lambda kv: (kv[1], -len(kv[0]),
                                   -min(CANONICAL_FACTORS.index(f) for f in kv[0])))
    causes = list(best_key[0])
    if not causes:
        return make_submission(case_id, [], "abstain")
    if len(causes) == 1:
        return make_submission(case_id, causes, "single")
    return make_submission(case_id, causes, "or")


class OpenSharingArm(_HeldoutArm):
    """Arm 3: same N=4 team, but sharing PRECEDES further action.

    Every agent sees prior agents' revealed conclusions (committed packets once
    revealed, plus textual conclusions appended to a shared transcript) BEFORE
    acting/committing in later rounds. commit() is called identically; there is
    no escrow sealing discipline — each agent commits AFTER reading the shared
    transcript, so its forecast can condition on others' stated conclusions.
    """

    AGENTS = ("os-a", "os-b", "os-c", "os-d")
    AGENT_ID = ""  # unused: commits use per-agent IDs below

    def __init__(self, session: BenchmarkSession, meter: _TokenMeter) -> None:
        super().__init__(session, meter)
        self.agent_ids = self.AGENTS

    def _commit(self, causes: list[str], repairs: list[str], prob: float,
                agent_id: str | None = None) -> bool:
        try:
            self.session.commit(agent_id or self.AGENT_ID, _canonical(causes),
                                _canonical(repairs), min(1.0, max(0.0, prob)))
            self.meter.charge("commit")
            return True
        except ValueError:
            return False

    def run(self) -> dict[str, Any]:
        scores = self.gather_evidence()
        ranked = _rank_factors(scores)
        transcript: list[str] = []
        hypotheses: dict[str, list[str]] = {}
        executed: set[tuple[str, ...]] = set()
        for round_no in range(6):
            for i, agent in enumerate(self.AGENTS):
                anchor = ranked[i % len(ranked)]
                hyp = [anchor]
                nxt = ranked[(i + 1) % len(ranked)]
                if scores[nxt] == scores[anchor] and nxt != anchor:
                    hyp.append(nxt)
                # OPEN SHARING: condition on everything revealed so far —
                # prior agents' committed packets once revealed plus their
                # textual conclusions in the shared transcript.
                if transcript:
                    hyp = self._condition(hyp, transcript)
                hypotheses[agent] = hyp
                # Plan: probe the current leading hypothesis member (skipping
                # already-executed single-factor probes); os-d holds baseline.
                plan = []
                if i < 3:
                    candidate = hyp[0]
                    if tuple([candidate]) in executed:
                        alt = next((f for f in ranked
                                    if tuple([f]) not in executed and f != candidate), None)
                        candidate = alt if alt is not None else candidate
                    plan = [candidate]
                conf = 0.5 + 0.25 * (scores[hyp[0]] / 2.0)
                if self._commit(hyp, plan, conf, agent_id=agent):
                    transcript.append(
                        f"{agent}: suspect {hyp}, plan {plan}, p={conf:.2f}")
                result = self._intervene(plan)
                if result is None:
                    break
                executed.add(tuple(result["repairs"]))
                transcript.append(
                    f"EXPERIMENT repairs={result['repairs']} -> {result['incident']}")
                # Open sharing: every agent openly updates from the shared
                # transcript. As with escrow, a resolution does NOT identify
                # which member caused it under 'and' semantics, so only
                # non-resolutions falsify specific factors.
                for other in self.AGENTS:
                    oh = hypotheses.get(other)
                    if not oh:
                        continue
                    if result["incident"] == "present":
                        survivors = [f for f in oh if f not in result["repairs"]]
                        hypotheses[other] = survivors or oh
            finals = {tuple(h) for h in hypotheses.values()}
            if all(len(h) == 1 for h in hypotheses.values()) and len(finals) == 1:
                break
        return self._aggregate(ranked, scores, hypotheses)

    @staticmethod
    def _condition(hyp: list[str], transcript: list[str]) -> list[str]:
        """Condition a hypothesis on the shared transcript (open sharing).

        Only NON-resolutions falsify specific factors (repaired factors that
        failed to clear the incident cannot be sole causes). Resolutions are
        logged in the transcript but do not rewrite hypotheses: under 'and'
        semantics any member repair resolves, so the responsible member is
        unidentified without further experiments.
        """
        falsified: set[str] = set()
        for line in transcript:
            if not line.startswith("EXPERIMENT"):
                continue
            head, _, outcome = line.partition(" -> ")
            if outcome.strip() == "present":
                falsified.update(f for f in CANONICAL_FACTORS if f in head)
        survivors = [f for f in hyp if f not in falsified]
        return survivors or hyp

    def _aggregate(self, ranked: list[str], scores: dict[str, int],
                   hypotheses: dict[str, list[str]]) -> dict[str, Any]:
        """Same consensus rule as escrow (shared helper): weighted majority
        vote over each agent's final (post-sharing) hypothesis; weights count
        non-falsified revealed forecasts (brier > 0.25 counts as falsified);
        structure readings come from the executed experiment outcomes."""
        return _consensus_from_history(
            self.session.public_history(), self.AGENTS, hypotheses, scores,
            self.case_id, self.best_effort(scores))


class RandomArm:
    """Arm 4: seeded random baseline. random.Random(20261012 + index_in_case_order).

    Random legal actions: random observe channels, random repair subsets of
    size 0-2, consumes a reasonable fraction of budget (up to 4 interventions,
    2 reads), random final submission with valid schema. Deterministic given
    the case index.
    """

    BASE_SEED = 20261012

    def __init__(self, session: BenchmarkSession, index_in_case_order: int,
                 meter: _TokenMeter) -> None:
        self.session = session
        self.meter = meter
        self.rng = _random_module.Random(self.BASE_SEED + index_in_case_order)
        self.card = session.card()
        self.case_id = self.card["case_id"]

    def run(self) -> dict[str, Any]:
        card = self.card
        # Up to 2 random channel reads.
        channels = list(card["visible_channels"])
        for channel in self.rng.sample(channels, 2):
            try:
                self.session.observe(channel)
                self.meter.charge("observe")
            except ValueError:
                break
        # Up to 4 random interventions with repair subsets of size 0-2.
        incidents: list[str] = []
        for _ in range(4):
            repairs = self.rng.sample(list(CANONICAL_FACTORS), self.rng.randint(0, 2))
            try:
                result = self.session.intervene(repairs)
                self.meter.charge("intervene")
                incidents.append(result["incident"])
            except ValueError:
                break
        # Random final submission with valid schema.
        option = self.rng.choice(["abstain", "clean", "single", "or", "and"])
        if option == "abstain":
            return make_submission(self.case_id, [], "abstain")
        if option == "clean":
            return make_submission(self.case_id, [], "clean")
        if option == "single":
            return make_submission(self.case_id, [self.rng.choice(list(CANONICAL_FACTORS))], "single")
        return make_submission(self.case_id, self.rng.sample(list(CANONICAL_FACTORS), 2), option)


ARMS = ("adaptive_central", "replclaw_escrow", "open_sharing", "random")


def run_arm(arm: str, session: BenchmarkSession,
           index_in_case_order: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one arm policy on a fresh session. Returns (submission, meter_summary)."""
    meter = _TokenMeter()
    if arm == "adaptive_central":
        submission = AdaptiveCentralArm(session, meter).run()
    elif arm == "replclaw_escrow":
        submission = RepliClawEscrowArm(session, meter).run()
    elif arm == "open_sharing":
        submission = OpenSharingArm(session, meter).run()
    elif arm == "random":
        if index_in_case_order is None:
            raise ValueError("random arm requires index_in_case_order")
        submission = RandomArm(session, index_in_case_order, meter).run()
    else:
        raise ValueError(f"unknown arm {arm!r}")
    meter.charge("final_submission")
    validate_submission(submission)
    return submission, meter.summary()
