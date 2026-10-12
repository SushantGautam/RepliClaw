"""V4 deadline-bound concurrent arms: D-E-DET and C-EQ-DET (access-matched, observational).

Implements the prospective V4 instrument proposed in
``docs/next_stage/design/v4_deadline_instrument.md``.  Both arms run on the SAME
shared :class:`~repliclaw.experiments.v3.telemetry.TelemetrySandbox` interface
(the OBS read-only telemetry tools) with byte-identical tool menus, budgets and
envelopes — they are **access-matched observational** diagnostic agents, NOT
intervention-matched: no live system is ever executed against, and no action
perturbs the environment.  That distinction is deliberate; the historical
"intervention-matched" label applied to TELEM arms was a terminology error
(see ``docs/next_stage/AUDIT_SCIENCE_MISMATCH_20261012.md`` §1).

The ONE designed difference between the arms is the coordination regime:

* **D-E-DET** — three investigators operate CONCURRENTLY (threads), each with
  its own sandbox + session, bounded per-investigator reasoning
  (:data:`DE_PHASE1_TOOL_CAP` tool calls), and a hard per-investigator deadline
  (:data:`DE_INVESTIGATOR_DEADLINE_S`).  Every investigator MUST commit a
  ranked-5 diagnosis before the deadline; if the LLM loop has not committed by
  then, the arm commits the investigator's best-so-far fallback ranking
  deterministically (top-5 of that investigator's observed anomaly scores) so
  the committee always has three escrowed entries.  Phase 2 (commit-reveal
  consultation) and phase 3 (deterministic committee adjudication + fresh
  committee sandbox) follow the V3.7 design unchanged.
* **C-EQ-DET** — one adaptive central manager with the identical shared
  envelope, the same planner-loop shape as C-EQ-TELEM (sealed pre-outcome
  forecast, up to :data:`PLANNER_ROUNDS_MAX` rounds, post-loop consultation of
  three fresh investigators at :data:`CEQ_INVESTIGATOR_TOOL_CAP` tools each).
  The post-loop consultations run CONCURRENTLY for wall-time parity with the
  concurrent D-E phase 1.

Shared fairness guarantees (parity by construction):

* identical :data:`MAX_TOKENS_PER_RUN` token envelope and
  :data:`WALL_CAP_S` wall cap, enforced from one shared counter (any agent
  breaching it aborts the whole arm — both arms get this);
* identical per-sandbox tool budget (:data:`MAX_TOOL_CALLS`) and per-tool caps
  inherited from :class:`TelemetrySandbox`;
* identical opaque case id, model label, temperature, action protocol;
* the deadline/fallback machinery exists ONLY in D-E-DET (it is the treatment:
  bounded local reasoning under a hard clock).  C-EQ-DET gets no deadline
  because a single manager with the same total envelope already faces the
  identical binding constraint (the shared token/wall envelope).

Mechanism ablation hooks (V4 preregistration §5): set
``consultation=False`` to disable phase-2 reveal (escrow-only ablation), or
``committee=False`` to submit the deterministic committee ranking without the
fresh committee sandbox round (adjudication-only ablation).  Both flags apply
to D-E-DET only; C-EQ-DET is the reference arm and is never ablated.

Offline-first: every test uses :class:`FakeLLMClient` scripted clients; no
network access is required.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from repliclaw.experiments.v3.telemetry import (
    PilotCaseRegistry,
    TelemetrySandbox,
)
from repliclaw.experiments.v3.telemetry_arms import (
    ACTION_PROTOCOL,
    ArmEscrow,
    ArmRunResult,
    CEQ_INVESTIGATOR_TOOL_CAP,
    ChatClientLike,
    INVESTIGATOR_IDS,
    LLMToolSession,
    MAX_TOKENS_PER_RUN,
    MODEL_SUBSTITUTION_LABEL,
    PLANNER_ROUNDS_MAX,
    RANKING_LENGTH,
    TOOL_DOCS,
    WALL_CAP_S,
    _ArmBase,
    _BudgetAbort,
    _Envelope,
    _INVESTIGATOR_STANCES,
    _render_observations,
)


# ---------------------------------------------------------------------------
# Frozen V4 constants (prospective — see v4_deadline_instrument.md §3)
# ---------------------------------------------------------------------------

#: Per-investigator phase-1 tool-call cap (bounded local reasoning).
DE_PHASE1_TOOL_CAP = 12
#: Hard per-investigator deadline in seconds (wall clock).
DE_INVESTIGATOR_DEADLINE_S = 120.0
#: Fallback confidence recorded when the deadline forces a fallback commit.
FALLBACK_CONFIDENCE = 0.3
#: Committee tool cap (same as V3.7).
DE_COMMITTEE_TOOL_CAP_V4 = 4
#: Phase-2 consult tool cap per investigator (same as V3.7 final value).
DE_PHASE2_TOOL_CAP_V4 = 8

__all__ = [
    "CEQDetArm",
    "DE_FALLBACK_CONFIDENCE",
    "DE_INVESTIGATOR_DEADLINE_S",
    "DE_PHASE1_TOOL_CAP",
    "DE_PHASE2_TOOL_CAP_V4",
    "DE_COMMITTEE_TOOL_CAP_V4",
    "DetelemDetArm",
    "DeadlineExceeded",
]

DE_FALLBACK_CONFIDENCE = FALLBACK_CONFIDENCE


class DeadlineExceeded(Exception):
    """An investigator hit its hard deadline without committing."""


def _fallback_ranking(sandbox: TelemetrySandbox) -> list[str]:
    """Deterministic best-so-far ranking from the sandbox's top_anomalies view.

    Called ONLY when an investigator fails to commit before the deadline.
    It reuses the shared reference math (no new scoring code) and returns the
    top :data:`RANKING_LENGTH` distinct services by anomaly score.  This is a
    mechanism floor, not a second diagnostician: it cannot exceed what the
    investigator already saw, because it reads the same payloads.
    """
    payload = sandbox.top_anomalies(k=50)
    seen: list[str] = []
    for row in payload.get("rows", []):
        svc = str(row.get("service", ""))
        if svc and svc not in seen:
            seen.append(svc)
        if len(seen) >= RANKING_LENGTH:
            break
    # Pad deterministically from the case's service inventory (the same
    # ordering system_context exposes) so the fallback always returns exactly
    # RANKING_LENGTH distinct valid services.
    if len(seen) < RANKING_LENGTH:
        inv = sandbox._inventory()  # deterministic per-case service ordering
        for svc in inv:
            if svc not in seen:
                seen.append(svc)
            if len(seen) >= RANKING_LENGTH:
                break
    return seen[:RANKING_LENGTH]


@dataclass
class _InvestigatorOutcome:
    agent_id: str
    ranking: list[str]
    confidence: float
    status: str  # "committed" | "deadline_fallback" | "crashed"
    tokens: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    wall_s: float = 0.0
    repeated_actions: int = 0  # count of exact (tool,args) repeats beyond the first


def _count_repeated_actions(call_log: Sequence[dict[str, Any]]) -> int:
    seen: set[str] = set()
    repeats = 0
    for c in call_log:
        key = json.dumps((c.get("tool"), c.get("args")), sort_keys=True)
        if key in seen:
            repeats += 1
        else:
            seen.add(key)
    return repeats


# ---------------------------------------------------------------------------
# D-E-DET: concurrent deadline-bound decentralized committee
# ---------------------------------------------------------------------------


class DetelemDetArm(_ArmBase):
    """D-E-DET: concurrent investigators, per-investigator deadlines, fallback."""

    arm_label = "D-E-TELEM-DET"

    def __init__(self, *args: Any,
                 consultation: bool = True,
                 committee: bool = True,
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.consultation = consultation
        self.committee = committee
        self._lock = threading.Lock()
        self._token_snapshots: list[int] = []
        self.phase_metrics: dict[str, Any] = {}

    # -- accounting (thread-safe) ---------------------------------------------
    def _tokens_total(self) -> int:
        with self._lock:
            return sum(s.tokens_total for s in self.sessions)

    def _llm_calls(self) -> int:
        with self._lock:
            return sum(s.llm_call_count for s in self.sessions)

    def _new_session(self, agent_id: str, system_prompt: str) -> LLMToolSession:
        session = LLMToolSession(
            self._client, system_prompt, agent_id, model_label=self._model_label
        )
        with self._lock:
            self.sessions.append(session)
        return session

    def _investigator_system_prompt(self, inv_id: str) -> str:
        stance = _INVESTIGATOR_STANCES[inv_id]
        return (
            f"You are investigator {inv_id} on a root-cause diagnosis task over one "
            f"incident's telemetry (opaque case {self._opaque_id}). You have NO access "
            f"to ground truth, and no other data source.\n"
            f"Assigned stance (deterministic, seed {self._seed}): {stance}.\n"
            f"HARD CONSTRAINTS: you may issue at most {DE_PHASE1_TOOL_CAP} tool calls "
            f"in total, and you MUST commit your ranked-5 diagnosis before your "
            f"personal deadline. Plan a short investigation; do not re-issue queries "
            f"you already made.\n\n"
            f"{TOOL_DOCS}\n\n{ACTION_PROTOCOL}"
        )

    # -- phase 1 worker ---------------------------------------------------------
    def _run_investigator(self, inv: str, sandbox: TelemetrySandbox,
                          session: LLMToolSession, escrow: ArmEscrow,
                          start: float) -> _InvestigatorOutcome:
        personal_deadline = start + DE_INVESTIGATOR_DEADLINE_S
        prompt = (
            f"Begin your private investigation of opaque case {self._opaque_id}. "
            f"Issue tool calls to gather evidence (at most {DE_PHASE1_TOOL_CAP} in "
            f"total). When ready, commit your ranked-5 diagnosis with a confidence. "
            f"Your commit is ESCROWED: hashed and sealed now, revealed to the other "
            f"investigators only after everyone has committed."
        )
        observations: list[dict[str, Any]] = []
        tools_left = DE_PHASE1_TOOL_CAP
        try:
            action = session.ask(prompt)
            while action["action"] == "tool_call":
                if time.monotonic() > personal_deadline:
                    raise DeadlineExceeded(inv)
                if tools_left <= 0:
                    # Budget exhausted mid-loop: force a commit attempt once more.
                    action = session.ask(
                        "Tool budget exhausted. Commit your ranked-5 diagnosis NOW."
                    )
                    break
                tools_left -= 1
                self._enforce_envelope()
                observations.append(self._execute_tool(sandbox, action))
                action = session.ask(self._continuation_prompt(observations, inv))
            if action["action"] != "commit":
                raise DeadlineExceeded(inv)
            ranking, confidence = action["ranking"], action["confidence"]
            status = "committed"
        except DeadlineExceeded:
            ranking = _fallback_ranking(sandbox)
            confidence = DE_FALLBACK_CONFIDENCE
            status = "deadline_fallback"
        except Exception:  # noqa: BLE001 — recorded, demoted to fallback
            ranking = _fallback_ranking(sandbox)
            confidence = DE_FALLBACK_CONFIDENCE
            status = "crashed"
        escrow.commit(inv, "phase1", ranking, confidence)
        return _InvestigatorOutcome(
            agent_id=inv,
            ranking=list(ranking),
            confidence=float(confidence),
            status=status,
            tokens=session.tokens_total,
            llm_calls=session.llm_call_count,
            tool_calls=len(sandbox.call_log),
            wall_s=round(time.monotonic() - start, 3),
            repeated_actions=_count_repeated_actions(sandbox.call_log),
        )

    @staticmethod
    def _continuation_prompt(observations: list[dict[str, Any]], inv: str) -> str:
        last = observations[-1]
        payload = json.dumps(last["payload"], sort_keys=True)
        if len(payload) > 800:
            payload = payload[:800] + " ...[truncated]"
        return (
            f"Observation for {inv} from {last['tool']}("
            f"{json.dumps(last['args'], sort_keys=True)}):\n{payload}\n"
            "Respond with your next action (one more tool call, or commit when ready)."
        )

    # -- main run ---------------------------------------------------------------
    def run(self) -> ArmRunResult:
        self._start = self._clock()
        self._clock()
        escrow = ArmEscrow(self.arm_label, self._opaque_id, clock=self._clock)
        escrow_path = self._out_dir / f"{self.arm_label.lower()}-escrow.json"
        warnings: list[str] = []
        try:
            result = self._run_inner(escrow, warnings, escrow_path)
            return result
        except _BudgetAbort:
            return self._result(submitted_ranking=None, status="aborted_budget",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None,
                                warnings=tuple(warnings))
        except Exception as exc:  # noqa: BLE001 — crash is recorded, not raised
            self._record_crash(exc)
            return self._result(submitted_ranking=None, status="crashed",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None,
                                warnings=tuple(warnings))

    def _run_inner(self, escrow: ArmEscrow, warnings: list[str],
                   escrow_path: "Path") -> ArmRunResult:
        t0 = time.monotonic()
        sandboxes = [self._new_sandbox() for _ in INVESTIGATOR_IDS]
        sessions = [self._new_session(inv, self._investigator_system_prompt(inv))
                    for inv in INVESTIGATOR_IDS]

        # ---- Phase 1: CONCURRENT private investigation + escrow commit --------
        outcomes: dict[str, _InvestigatorOutcome] = {}
        errors: list[Exception] = []
        err_lock = threading.Lock()

        def worker(inv: str, sb: TelemetrySandbox, ss: LLMToolSession) -> None:
            try:
                outcomes[inv] = self._run_investigator(inv, sb, ss, escrow, t0)
            except Exception as exc:  # noqa: BLE001 — surfaced below
                with err_lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(inv, sb, ss), daemon=True)
                   for inv, sb, ss in zip(INVESTIGATOR_IDS, sandboxes, sessions)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if errors:
            raise errors[0]
        p1_wall = time.monotonic() - t0

        fallbacks = sorted(o.agent_id for o in outcomes.values()
                           if o.status != "committed")
        if fallbacks:
            warnings.append(f"deadline_fallback_used_for={','.join(fallbacks)}")
        escrow.reveal_all()

        # ---- Phase 2: one shared consultation round (optional ablation) -------
        if self.consultation:
            for inv, sandbox, session in zip(INVESTIGATOR_IDS, sandboxes, sessions):
                others = [e for e in escrow.entries
                          if e["agent_id"] != inv and e["phase"] == "phase1"]
                reveal_block = "\n".join(
                    f"- {e['agent_id']}: ranking={e['ranking']} "
                    f"confidence={e['confidence']}" for e in others
                )
                prompt = (
                    "Commit-reveal consultation round. The OTHER investigators have "
                    "committed and revealed their escrowed phase-1 diagnoses:\n"
                    f"{reveal_block}\n"
                    f"You may issue up to {DE_PHASE2_TOOL_CAP_V4} more tool calls on "
                    "your own sandbox, then you MUST commit your FINAL ranked-5 "
                    "diagnosis with a confidence."
                )
                p2_obs: list[dict[str, Any]] = []
                tools_left = DE_PHASE2_TOOL_CAP_V4
                action = session.ask(prompt)
                while action["action"] == "tool_call":
                    if tools_left <= 0:
                        raise _BudgetAbort(
                            f"{inv}: phase-2 tool cap ({DE_PHASE2_TOOL_CAP_V4}) exceeded"
                        )
                    tools_left -= 1
                    self._enforce_envelope()
                    p2_obs.append(self._execute_tool(sandbox, action))
                    action = session.ask(self._continuation_prompt(p2_obs, inv))
                escrow.commit(inv, "phase2-final", action["ranking"], action["confidence"])
        else:
            # Escrow-only ablation: promote phase-1 entries as finals.
            for inv in INVESTIGATOR_IDS:
                entry = next(e for e in escrow.entries
                             if e["agent_id"] == inv and e["phase"] == "phase1")
                escrow.commit(inv, "phase2-final", entry["ranking"], entry["confidence"])

        # ---- Phase 3: deterministic committee ranking --------------------------
        finals = {e["agent_id"]: e for e in escrow.entries if e["phase"] == "phase2-final"}
        scores: dict[str, float] = {}
        for agent_id in INVESTIGATOR_IDS:
            entry = finals[agent_id]
            for rank, svc in enumerate(entry["ranking"], start=1):
                scores[svc] = scores.get(svc, 0.0) + (RANKING_LENGTH - rank + 1) * entry["confidence"]
        committee_ranking = sorted(scores, key=lambda s: (-scores[s], s))[:RANKING_LENGTH]

        if self.committee:
            committee_sandbox = self._new_sandbox()
            committee_session = self._new_session(
                "committee",
                "You are the D-E adjudication committee over opaque case "
                f"{self._opaque_id}. The investigators' final escrowed submissions "
                "have been adjudicated deterministically into a committee ranking "
                "(scores below). You may inspect telemetry with the OBS tools before "
                "the arm submits; you do NOT choose the ranking — reply with a "
                "commit action when you are ready for submission.\n\n"
                f"{TOOL_DOCS}\n\n" + ACTION_PROTOCOL,
            )
            score_block = "\n".join(
                f"- {s}: {v:.4f}" for s, v in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
            )
            committee_obs: list[dict[str, Any]] = []
            action = committee_session.ask(
                "Adjudication table (sum of (6-rank)*confidence across investigators):\n"
                f"{score_block}\n\nCommittee ranking: {committee_ranking}. "
                "Inspect if useful, then commit."
            )
            tools_left = DE_COMMITTEE_TOOL_CAP_V4
            while action["action"] == "tool_call":
                if tools_left <= 0:
                    break
                tools_left -= 1
                self._enforce_envelope()
                committee_obs.append(self._execute_tool(committee_sandbox, action))
                action = committee_session.ask(self._continuation_prompt(committee_obs, "committee"))
            self._enforce_envelope()
            confirmed = committee_sandbox.submit_diagnosis(committee_ranking)
        else:
            # Adjudication-only ablation: submit directly via a fresh sandbox.
            committee_sandbox = self._new_sandbox()
            confirmed = committee_sandbox.submit_diagnosis(committee_ranking)

        self.phase_metrics = {
            "phase1_wall_s": round(p1_wall, 3),
            "investigators": [o.__dict__ for o in
                              (outcomes[i] for i in INVESTIGATOR_IDS)],
            "fallback_agents": fallbacks,
            "time_to_first_commit_s": min(
                o.wall_s for o in outcomes.values()),
        }
        result = self._result(
            submitted_ranking=confirmed["ranking"],
            status="completed",
            escrow_ledger_path=str(escrow.save(escrow_path)),
            prompt_volume_ratio=None,
            warnings=tuple(warnings),
        )
        return result


# ---------------------------------------------------------------------------
# C-EQ-DET: adaptive central manager (reference arm)
# ---------------------------------------------------------------------------


class CEQDetArm(_ArmBase):
    """C-EQ-DET: sealed forecast, planner loop, concurrent post-loop consults."""

    arm_label = "C-EQ-TELEM-DET"

    def _manager_system_prompt(self) -> str:
        base = (
            f"You are the single central manager for the root-cause diagnosis of "
            f"opaque case {self._opaque_id} (seed {self._seed}). You have NO access "
            f"to ground truth. You plan and execute tool queries yourself, across "
            f"at most {PLANNER_ROUNDS_MAX} planner rounds; each round you may issue "
            f"1-3 tool calls. You see a union evidence view of everything observed "
            f"in your sandbox so far, plus your sealed pre-outcome forecast, which "
            f"you committed to escrow before any tool use and must treat as fixed. "
            f"When you have enough evidence, commit your ranked-5 diagnosis.\n\n"
            f"{TOOL_DOCS}\n\n"
        )
        return base + ACTION_PROTOCOL

    def _investigator_system_prompt(self, inv_id: str) -> str:
        stance = _INVESTIGATOR_STANCES[inv_id]
        return (
            f"You are a consult-only investigator ({inv_id}) for opaque case "
            f"{self._opaque_id}. You are consulted exactly ONCE by the manager, "
            f"with at most {CEQ_INVESTIGATOR_TOOL_CAP} tool calls available. "
            f"Assigned stance (deterministic, seed {self._seed}): {stance}.\n\n"
            f"{TOOL_DOCS}\n\n{ACTION_PROTOCOL}"
        )

    def run(self) -> ArmRunResult:
        self._start = self._clock()
        self._clock()
        escrow = ArmEscrow(self.arm_label, self._opaque_id, clock=self._clock)
        escrow_path = self._out_dir / f"{self.arm_label.lower()}-escrow.json"
        try:
            return self._run_inner(escrow, escrow_path)
        except _BudgetAbort:
            return self._result(submitted_ranking=None, status="aborted_budget",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None)
        except Exception as exc:  # noqa: BLE001
            self._record_crash(exc)
            return self._result(submitted_ranking=None, status="crashed",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None)

    def _run_inner(self, escrow: ArmEscrow, escrow_path: "Path") -> ArmRunResult:
        manager_sandbox = self._new_sandbox()
        manager_session = self._new_session("manager", self._manager_system_prompt())

        # ---- Sealed forecast BEFORE any tool call -----------------------------
        forecast_action = manager_session.ask(
            "Pre-outcome forecast (SEALED): before you issue ANY tool call, commit "
            "your current best ranked-5 hypothesis for the root-cause service with "
            "a confidence. Use only what you know now (no tool evidence yet). Reply "
            "with a commit action."
        )
        assert forecast_action["action"] == "commit"
        escrow.commit("manager", "forecast",
                      forecast_action["ranking"], forecast_action["confidence"])
        forecast_line = (
            f"predicted_root_service={forecast_action['ranking'][0]} "
            f"confidence={forecast_action['confidence']} (sealed pre-outcome commit)"
        )

        # ---- Planner loop -------------------------------------------------------
        observations: list[dict[str, Any]] = []
        loop_committed: dict[str, Any] | None = None
        for round_no in range(1, PLANNER_ROUNDS_MAX + 1):
            self._enforce_envelope()
            prompt = (
                f"Planner round {round_no}/{PLANNER_ROUNDS_MAX}. Budget so far: "
                f"{self._tokens_total()} tokens, {len(observations)} observations. "
                f"Sealed forecast line: {forecast_line}\n"
                f"Union evidence view (everything observed in your sandbox):\n"
                f"{_render_observations(observations)}\n"
                "Issue 1-3 tool calls for this round by responding with a single "
                "tool_call action (you will be asked again for the rest of the "
                "round), or commit your ranked-5 diagnosis if you already have "
                "enough evidence."
            )
            round_tools = 0
            action = manager_session.ask(prompt)
            while action["action"] == "tool_call":
                if round_tools >= 3:
                    break
                round_tools += 1
                self._enforce_envelope()
                last_action = action
                observations.append(self._execute_tool(manager_sandbox, last_action))
                self._enforce_envelope()
                action = manager_session.ask(
                    f"Observation from {last_action['tool']}("
                    f"{json.dumps(last_action['args'], sort_keys=True)}):\n"
                    f"{_render_observations(observations[-1:])}\n"
                    f"Round {round_no}: issue another tool call (up to 3 this "
                    "round) or commit."
                )
            if action["action"] == "commit":
                loop_committed = action
                break

        # ---- Post-loop: 3 fresh investigators, CONSULTED CONCURRENTLY ---------
        findings: list[dict[str, Any]] = []
        findings_payload = _render_observations(observations, limit_per_obs=600)
        results: dict[str, dict[str, Any]] = {}
        f_errs: list[Exception] = []
        f_lock = threading.Lock()

        def consult(inv: str) -> None:
            try:
                inv_sandbox = self._new_sandbox()
                inv_session = self._new_session(inv, self._investigator_system_prompt(inv))
                tools_left = CEQ_INVESTIGATOR_TOOL_CAP
                fa = inv_session.ask(
                    "One-shot consultation: the manager's union evidence view is "
                    "below. You have at most "
                    f"{CEQ_INVESTIGATOR_TOOL_CAP} tool calls. Investigate briefly, "
                    "then reply with a commit action (your ranked-5 findings + "
                    f"confidence) as your single finding for the manager.\n"
                    f"Evidence view:\n{findings_payload}"
                )
                obs: list[dict[str, Any]] = []
                while fa["action"] == "tool_call":
                    if tools_left <= 0:
                        break
                    tools_left -= 1
                    self._enforce_envelope()
                    obs.append(self._execute_tool(inv_sandbox, fa))
                    fa = inv_session.ask(
                        f"Observation from {fa['tool']}({json.dumps(fa['args'], sort_keys=True)}):\n"
                        f"{_render_observations(obs[-1:])}\n"
                        "Issue another tool call (within your cap) or commit."
                    )
                results[inv] = {"ranking": fa["ranking"], "confidence": fa["confidence"]}
            except Exception as exc:  # noqa: BLE001
                with f_lock:
                    f_errs.append(exc)

        threads = [threading.Thread(target=consult, args=(inv,), daemon=True)
                   for inv in INVESTIGATOR_IDS]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if f_errs:
            raise f_errs[0]
        findings = [results[inv] for inv in INVESTIGATOR_IDS]

        # ---- Final commit through the manager's own sandbox --------------------
        final_ranking = (loop_committed["ranking"] if loop_committed
                         else findings[0]["ranking"])
        confirmed = manager_sandbox.submit_diagnosis(final_ranking)
        return self._result(
            submitted_ranking=confirmed["ranking"],
            status="completed",
            escrow_ledger_path=str(escrow.save(escrow_path)),
            prompt_volume_ratio=None,
        )
