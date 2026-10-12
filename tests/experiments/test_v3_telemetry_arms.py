"""Tests for the V3 telemetry arms (addendum §2/§4): D-E-TELEM and C-EQ-TELEM.

Covers the JSON action protocol (lenient parse, single retry, hard failure),
D-E escrow commit-before-reveal ordering, deterministic committee ranking
math, ground-truth isolation, token-envelope aborts, C-EQ sealed-forecast
ordering, the planner loop, the findings-once rule, the prompt-volume canary
band, cross-run determinism, and the sandbox-payload parity canary.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import pytest

from repliclaw.experiments.v3.telemetry import FROZEN_PILOT_IDS as FROZEN
from repliclaw.experiments.v3.telemetry import PilotCaseRegistry
from repliclaw.experiments.v3.telemetry_arms import (
    MAX_TOKENS_PER_RUN,
    PROMPT_VOLUME_CEIL,
    PROMPT_VOLUME_FLOOR,
    AgentProtocolError,
    ArmEscrow,
    CEQTelemArm,
    ChatCompletionsLike,
    DetelemArm,
    FakeLLMClient,
    LLMToolSession,
    assert_volume_band,
    parse_action,
    prompt_volume_ratio,
)

REPO = Path(__file__).resolve().parents[2]
FAKE_UPSTREAM_ID = sorted(FROZEN)[0]
RANK5 = ["svc04", "svc00", "svc01", "svc02", "svc03"]  # all present in the fake case


# ---------------------------------------------------------------------------
# fake case + script helpers
# ---------------------------------------------------------------------------


def _build_fake_case(root: Path) -> Path:
    """Synthetic pilot-shaped case dir: 13 services svc00..svc12, svc04 spikes."""
    case = root / FAKE_UPSTREAM_ID
    case.mkdir(parents=True, exist_ok=True)
    onset = 1_000_000
    n = 800
    t = np.arange(onset - 600, onset + 200)
    rng = np.random.default_rng(7)
    data: dict[str, np.ndarray] = {"time": t}
    for i in range(13):
        base = 10.0 + rng.normal(0.0, 0.5, size=n)
        col = f"svc{i:02d}_s1"
        if i == 4:
            base = base.copy()
            base[600:] += 50.0
        data[col] = base
    data["svc00_const"] = np.full(n, 3.14)
    pd.DataFrame(data).to_parquet(case / "metrics.parquet")
    (case / "inject_time.txt").write_text(f"{onset}\n")
    pd.DataFrame(
        {
            "timestamp": np.array([onset - 100, onset, onset + 99]),
            "container_name": ["svc04", "svc00", "svc04"],
            "message": ["svc04 slow", "svc00 ok", "svc04 slower"],
        }
    ).to_parquet(case / "logs.parquet")
    pd.DataFrame(
        {
            "time": ["00:00"],
            "traceID": ["abc"],
            "spanID": ["def"],
            "serviceName": ["svc04"],
            "methodName": [None],
            "operationName": ["svc04/op"],
            "parentSpanID": [None],
            "startTimeMillis": [onset * 1000],
            "startTime": [onset * 1_000_000],
            "duration": [50_000],
            "statusCode": [0],
        }
    ).to_parquet(case / "traces.parquet")
    return case


@pytest.fixture()
def fake_registry(tmp_path: Path) -> PilotCaseRegistry:
    _build_fake_case(tmp_path)
    return PilotCaseRegistry(data_root=tmp_path)


def _tool(tool: str, **args: Any) -> str:
    return json.dumps({"action": "tool_call", "tool": tool, "args": args})


def _commit(ranking: list[str], confidence: float = 0.9) -> str:
    return json.dumps({"action": "commit", "ranking": ranking, "confidence": confidence})


DE_P1 = {
    "inv-a": (["svc04", "svc00", "svc01", "svc02", "svc03"], 0.9),
    "inv-b": (["svc04", "svc01", "svc00", "svc02", "svc05"], 0.8),
    "inv-c": (["svc00", "svc04", "svc01", "svc02", "svc03"], 0.7),
}


def _de_script() -> Any:
    """Deterministic D-E fake script (mechanism v2).

    Phase 1 (each independent investigator, own sandbox): system_context,
    then the pre-outcome escrow commit (p1). No consultation round —
    investigators never see each other's inferences.
    Committee (fresh session): top_anomalies, then commit (arm submits the
    deterministic committee-score ranking over the REVEALED p1 packets
    regardless of the committee's reply ranking).
    """
    state: dict[str, set] = {"p1_done": set()}

    def script(prompt: str, call_index: int) -> str:
        if "Adjudication table" in prompt:
            return _tool("top_anomalies", k=10)
        if "Observation for committee" in prompt:
            return _commit(RANK5, 0.99)
        if "BEST-EVIDENCE COMMIT" in prompt:
            return _commit(RANK5, 0.5)  # best-evidence fallback commit
        if "Begin your private" in prompt:
            return _tool("system_context")
        if "Observation for" in prompt:
            inv = _inv_of(prompt)
            assert inv not in state["p1_done"]
            state["p1_done"].add(inv)
            return _commit(*DE_P1[inv])
        raise AssertionError(f"UNROUTED D-E prompt: {prompt[:120]!r}")

    return script


def _inv_of(prompt: str) -> str:
    for inv in ("inv-a", "inv-b", "inv-c"):
        if f"Observation for {inv}" in prompt or f"agent {inv}" in prompt or f"investigator {inv}" in prompt:
            return inv
    # Forced-commit prompts carry the investigator in the context.
    raise AssertionError(f"cannot route prompt to an investigator: {prompt[:120]!r}")


def _ceq_script() -> Any:
    """Deterministic C-EQ fake script (content-routed, per-branch counters)."""
    mgr = [
        _commit(RANK5, 0.8),                 # 0: sealed pre-loop forecast
        _tool("system_context"),             # 1: planner round 1 tool 1
        _tool("top_anomalies", k=20),        # 2: planner round 1 tool 2
        _commit(RANK5, 0.85),                # 3: in-loop commit -> loop stops
        _commit(RANK5, 0.9),                 # 4: final commit after findings
    ]
    state = {"mi": 0}

    def script(prompt: str, call_index: int) -> str:
        if "Now commit your findings" in prompt:
            return _commit(RANK5, 0.6)
        if "One-shot consultation" in prompt:
            return _tool("service_logs", svc="svc04", k=50)
        out = mgr[state["mi"]]
        state["mi"] += 1
        return out

    return script


def _counter_clock() -> tuple[list[float], Callable[[], float]]:
    """(state, clock): monotonically advancing fake clock for deterministic ledgers."""
    state = [1_000_000.0]

    def clock() -> float:
        state[0] += 1.0
        return state[0]

    return state, clock


# ---------------------------------------------------------------------------
# protocol parsing
# ---------------------------------------------------------------------------


def test_parse_action_plain_json() -> None:
    action = parse_action(_tool("service_logs", svc="svc04", k=10))
    assert action == {"action": "tool_call", "tool": "service_logs", "args": {"svc": "svc04", "k": 10}}


def test_parse_action_fenced_json() -> None:
    fenced = "Here you go:\n```json\n" + _commit(RANK5, 0.7) + "\n```\nThanks."
    action = parse_action(fenced)
    assert action["action"] == "commit"
    assert action["ranking"] == RANK5
    assert action["confidence"] == 0.7


def test_parse_action_rejects_bad_actions() -> None:
    with pytest.raises(Exception):
        parse_action("no json object here at all")
    with pytest.raises(Exception):
        parse_action(json.dumps({"action": "teleport"}))
    with pytest.raises(Exception):  # wrong ranking length
        parse_action(json.dumps({"action": "commit", "ranking": ["svc04"], "confidence": 0.9}))
    with pytest.raises(Exception):  # confidence out of range
        parse_action(json.dumps({"action": "commit", "ranking": RANK5, "confidence": 1.5}))


def test_session_malformed_retry_then_success() -> None:
    def script(prompt: str, call_index: int) -> str:
        if "not a single valid JSON action object" in prompt:
            return _tool("system_context")  # the single retry
        return "I will do a thing but emit no json"  # first output malformed

    client = FakeLLMClient(script)
    session = LLMToolSession(client, system_prompt="sys", agent_id="x")
    action = session.ask("go")
    assert action["action"] == "tool_call"
    assert client.responses[0] == "I will do a thing but emit no json"
    assert json.loads(client.responses[1])["action"] == "tool_call"


def test_session_agent_protocol_error_after_persistent_malformed() -> None:
    # The session retries once on malformed output, then performs ONE bounded
    # recovery re-ask; only if the model is still malformed does it fail loudly.
    client = FakeLLMClient(
        ["first bad output", "second bad output", "third bad output"]
    )
    session = LLMToolSession(client, system_prompt="sys", agent_id="x")
    with pytest.raises(AgentProtocolError):
        session.ask("go")
    assert session.llm_call_count == 3


def test_session_recovers_on_third_attempt() -> None:
    # Two malformed outputs followed by a valid one: the bounded recovery retry
    # should return the valid action instead of crashing the arm.
    def script(prompt: str, call_index: int) -> str:
        if "not a single valid JSON action object" in prompt:
            return _tool("system_context")  # both correction prompts recover
        return "still no json here"

    client = FakeLLMClient(script)
    session = LLMToolSession(client, system_prompt="sys", agent_id="x")
    action = session.ask("go")
    assert action["action"] == "tool_call"


class _NoUsageClient:
    """Minimal chat client with no usage field -> length-estimate path."""

    class _Completions:
        def create(self, *, model: str, messages: list[dict[str, str]],
                   temperature: float = 0.0, **_kwargs: Any) -> Any:
            message = type("M", (), {"content": _commit(RANK5)})()
            choice = type("C", (), {"message": message})()
            return type("R", (), {"choices": [choice], "usage": None})()

    def __init__(self) -> None:
        self.chat: ChatCompletionsLike = self._Completions()


def test_session_token_accounting_usage_and_length_estimate() -> None:
    client = FakeLLMClient([_commit(RANK5)])
    session = LLMToolSession(client, system_prompt="sys", agent_id="x")
    session.ask("go")
    assert session.tokens_total > 0
    assert session._tokens[0].method == "usage"  # FakeLLMClient reports usage

    session2 = LLMToolSession(_NoUsageClient(), system_prompt="sys", agent_id="y")
    session2.ask("go")
    assert session2._tokens[0].method == "length_estimate"


class _CapturingNoUsageClient:
    """No-usage client that records the exact prompt chars sent on each call,
    so a test can compare the session's estimate against the real wire traffic."""

    class _Completions:
        def __init__(self, client: "_CapturingNoUsageClient") -> None:
            self._client = client

        def create(self, *, model: str, messages: list[dict[str, str]],
                   temperature: float = 0.0, **_kwargs: Any) -> Any:
            self._client.prompt_chars_seen.append(sum(len(m["content"]) for m in messages))
            message = type("M", (), {"content": _commit(RANK5)})()
            choice = type("C", (), {"message": message})()
            return type("R", (), {"choices": [choice], "usage": None})()

    def __init__(self) -> None:
        self.prompt_chars_seen: list[int] = []
        self.chat: ChatCompletionsLike = self._Completions(self)


def test_session_length_estimate_counts_only_marginal_prompt() -> None:
    """No-usage fallback must count the MARGINAL prompt per turn, not the
    full re-sent history: over 5 turns the estimate must stay at ~1x the
    per-turn prompt size (1.2x tolerance), and must equal the sum of the
    per-call prompt chars actually sent, divided by 4."""
    client = _CapturingNoUsageClient()
    session = LLMToolSession(client, system_prompt="sys", agent_id="x")
    for i in range(5):
        session.ask(f"turn {i}")

    assert all(t.method == "length_estimate" for t in session._tokens)
    # Never under-count: reported total equals the sum of each call's SENT
    # prompt chars (marginal per call, not the re-sent history) divided by 4.
    per_call_sent = client.prompt_chars_seen
    for i, rec in enumerate(session._tokens):
        sent = per_call_sent[i] - (per_call_sent[i - 1] if i else 0)
        assert rec.prompt_tokens == sent // 4
    assert session.prompt_tokens_total == sum(t.prompt_tokens for t in session._tokens)
    # No inflation: ≤ 5 x (per-turn prompt)//4 with 1.2x tolerance. (The old
    # full-history recount would be ~3.7x over this bound.)
    avg_single_turn = client.prompt_chars_seen[-1] // 4
    assert avg_single_turn > 0
    assert session.prompt_tokens_total <= 1.2 * 5 * avg_single_turn
    # Historical growth sanity: the 5th call's recorded estimate is the
    # marginal 1-turn delta, not the 5-turn history.
    assert session._tokens[-1].prompt_tokens == (
        client.prompt_chars_seen[-1] - client.prompt_chars_seen[-2]
    ) // 4


def test_session_prompt_tokens_equal_usage_sum_over_multi_turn() -> None:
    """When the client reports usage, the session's prompt-token total must
    equal the sum of usage.prompt_tokens across all 5 calls."""
    client = FakeLLMClient([_commit(RANK5)] * 5)
    session = LLMToolSession(client, system_prompt="sys", agent_id="x")
    for i in range(5):
        session.ask(f"turn {i}")

    assert session.llm_call_count == 5
    assert all(t.method == "usage" for t in session._tokens)
    assert session.prompt_tokens_total == sum(
        t.prompt_tokens for t in session._tokens
    )


class _CapturingCommitClient:
    """No-usage client that records the exact prompt chars sent on each call,
    always answering with a well-formed commit (protocol never breaks)."""

    class _Completions:
        def __init__(self, client: "_CapturingCommitClient") -> None:
            self._client = client

        def create(self, *, model: str, messages: list[dict[str, str]],
                   temperature: float = 0.0, **_kwargs: Any) -> Any:
            self._client.sent_chars.append(sum(len(m["content"]) for m in messages))
            message = type("M", (), {"content": _commit(RANK5)})()
            choice = type("C", (), {"message": message})()
            return type("R", (), {"choices": [choice], "usage": None})()

    def __init__(self) -> None:
        self.sent_chars: list[int] = []
        self.chat: ChatCompletionsLike = self._Completions(self)


def test_session_compaction_bounds_send_view_keeps_full_audit() -> None:
    """W3g: with large tool-observation prompts, the provider send-view must
    stay bounded (older observations stubbed) while the audit transcript and
    the volume-canary prompt list retain the FULL text, and the first
    instruction is never stubbed. Without compaction the send-view would grow
    linearly with every turn (full-history re-prompting blew the 60K envelope
    on the RCA-P-01 pilot relaunch)."""
    big_obs = "Observation: " + "x" * 700  # ~real service_metrics payload size
    client = _CapturingCommitClient()
    session = LLMToolSession(client, system_prompt="sys", agent_id="x")
    n = 15
    session.ask("phase instruction: investigate and commit")
    for i in range(1, n):
        session.ask(f"{i} " + big_obs)

    view = session._compacted_view()
    # First instruction (first user message) is verbatim, never stubbed.
    assert view[1]["content"] == "phase instruction: investigate and commit"
    assert "[older tool observation compacted" not in view[1]["content"]
    # Some old observations ARE stubbed.
    assert any("[older tool observation compacted" in m["content"]
               for m in view if m["role"] == "user")
    # Compaction active: the provider receives stubs where the un-compacted
    # view would carry 8 full 700-char observations.
    assert sum(1 for m in view if "[older tool observation compacted" in m["content"]) >= 5
    sent_chars = sum(len(m["content"]) for m in view)
    uncompacted_chars = sum(len(m["content"]) for m in session.messages)
    assert sent_chars < uncompacted_chars  # strictly smaller than full history
    # Growth stays bounded: 10 more turns must grow the send-view by far less
    # than one full 700-char observation per turn (each turn: +1 new obs,
    # +1 commit response, -1 obs converted to a stub as it slides out of the
    # recent-keep window).
    before = sent_chars
    for i in range(n, n + 10):
        session.ask(f"{i} " + big_obs)
    after = sum(len(m["content"]) for m in session._compacted_view())
    # 2071 measured for this shape; the un-compacted growth would be
    # 10 x (703 + commit) ~ 8000.
    assert after - before < 10 * 300
    # Deep in the session the send-view is a bounded fraction of the
    # un-compacted full history (~recent-keep window + stubs).
    uncompacted_deep = sum(len(m["content"]) for m in session.messages)
    assert after < uncompacted_deep * 0.6

    # Audit transcript retains every full observation (provenance intact).
    prompt_entries = [e for e in session.transcript if e["role"] == "prompt"]
    assert all(big_obs in e["content"] for e in prompt_entries[1:])
    # Volume-canary prompt list retains full text (canary math unchanged).
    assert all(big_obs in p for p in session.prompts[1:])
    # Length-estimate accounting: marginal over the SENT compacted view —
    # each call's estimate is exactly (sent_chars - prev_sent_chars) // 4,
    # so the total equals the final cumulative sent chars // 4 (bounded),
    # NOT the O(n^2) full-history re-send.
    assert all(t.method == "length_estimate" for t in session._tokens)
    # No-usage fallback never over-charges: each call's estimate is bounded
    # by what was actually SENT on that call (compacted view), and the
    # session total is bounded by the sum of sent sizes / 4 — NOT by the
    # O(n^2) full-history re-send (which would be ~25x larger here).
    assert session.prompt_tokens_total <= sum(
        c // 4 for c in client.sent_chars
    )
    assert session.prompt_tokens_total > 0
    # And that bound is far below the un-compacted full-history worst case
    # (every prompt re-sent on every later turn, ignoring assistant turns).
    full_history_tokens = (
        sum(len(p) for p in session.prompts) * (len(session.prompts) + 1) // 2 // 4
    )
    assert session.prompt_tokens_total < full_history_tokens // 3


# ---------------------------------------------------------------------------
# D-E-TELEM
# ---------------------------------------------------------------------------


def test_de_escrow_commit_before_reveal_ordering(fake_registry: PilotCaseRegistry, tmp_path: Path) -> None:
    times, clock = _counter_clock()
    times[0] += 100.0  # run start strictly precedes all commits
    arm = DetelemArm(
        client=FakeLLMClient(_de_script()),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=3,
        clock=clock,
    )
    result = arm.run()
    assert result.status == "completed", result

    assert result.escrow_ledger_path is not None
    ledger = json.loads(Path(result.escrow_ledger_path).read_text())
    assert ledger["arm"] == "D-E-TELEM"
    entries = ledger["entries"]
    # Mechanism v2: exactly ONE pre-outcome packet per investigator.
    assert len(entries) == 3
    assert {e["agent_id"] for e in entries} == {"inv-a", "inv-b", "inv-c"}
    assert all(e["phase"] == "phase1" for e in entries)
    # Every commit precedes its own reveal (commit-reveal ordering).
    for e in entries:
        assert e["committed_at"] < e["revealed_at"]
    # Commit sha256 recomputes from the canonical payload.
    for e in entries:
        payload = json.dumps(
            {"agent_id": e["agent_id"], "phase": e["phase"],
             "ranking": e["ranking"], "confidence": e["confidence"]},
            sort_keys=True, separators=(",", ":"),
        )
        assert e["commit_sha256"] == hashlib.sha256(payload.encode()).hexdigest()
    # PhaseGate transitions persisted: COMMIT init -> REVEAL after all commits.
    transitions = ledger["phase_transitions"]
    assert transitions[0]["phase"] == "COMMIT"
    assert any(t.get("to") == "REVEAL" for t in transitions)


def test_de_investigators_independent_no_shared_inference(
    fake_registry: PilotCaseRegistry, tmp_path: Path
) -> None:
    """Mechanism v2: no shared reasoning channel — no investigator prompt may
    mention another investigator's id, and no consultation prompt exists."""
    arm = DetelemArm(
        client=FakeLLMClient(_de_script()),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=3,
    )
    result = arm.run()
    assert result.status == "completed"
    for s in arm.sessions:
        if s.agent_id not in ("inv-a", "inv-b", "inv-c"):
            continue  # the committee adjudicates, it is not an investigator
        for p in s.prompts:
            assert "Commit-reveal consultation round" not in p
            for other in ("inv-a", "inv-b", "inv-c"):
                if other != s.agent_id:
                    assert other not in p, f"shared-inference leak of {other}"
    # 3 independent sandboxes (one per investigator) + 1 fresh committee.
    assert len(arm.sandboxes) == 4


def test_de_committee_ranking_math_hand_computed(fake_registry: PilotCaseRegistry, tmp_path: Path) -> None:
    arm = DetelemArm(
        client=FakeLLMClient(_de_script()),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=3,
    )
    result = arm.run()
    assert result.status == "completed"

    # Committee score = sum over investigators of (5 - rank + 1) * confidence
    # over each REVEALED phase-1 escrowed packet (rank 1-based); ties broken
    # alphabetically (mechanism v2: no consultation round, synthesis reads
    # the pre-outcome packets directly).
    scores: dict[str, float] = {}
    for rank_list, conf in DE_P1.values():
        for idx, svc in enumerate(rank_list, start=1):
            scores[svc] = scores.get(svc, 0.0) + (5 - idx + 1) * conf
    # Hand-check two entries (coef = 5-rank+1 = 6-rank: rank1->5, rank2->4, rank3->3):
    #   svc04 (rank1, rank1, rank2) = 5*0.9 + 5*0.8 + 4*0.7 = 11.3
    #   svc00 (rank2, rank3, rank1) = 4*0.9 + 3*0.8 + 5*0.7 = 9.5
    assert scores["svc04"] == pytest.approx(11.3)
    assert scores["svc00"] == pytest.approx(9.5)
    expected = sorted(scores, key=lambda s: (-scores[s], s))[:5]
    assert result.submitted_ranking == expected
    assert result.submitted_ranking[0] == "svc04"
    assert result.success_eligible is True
    # 4 sandboxes: 3 investigators + 1 fresh committee (equal-access parity).
    assert len(arm.sandboxes) == 4
    committee_sb = arm.sandboxes[3]
    assert any(c["tool"] == "submit_diagnosis" for c in committee_sb.call_log)
    # 1 committee tool call + 1 submit, each within the 24-call sandbox budget.
    assert len(committee_sb.call_log) == 2


def test_de_no_ground_truth_import(fake_registry: PilotCaseRegistry, tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("heldout_ground_truth must never be touched by the arms")

    monkeypatch.setattr("repliclaw.benchmarks.rcaeval.manifest.heldout_ground_truth", boom)
    src = (REPO / "src/repliclaw/experiments/v3/telemetry_arms.py").read_text()
    assert "rcaeval" not in src
    assert "heldout_ground_truth" not in src

    de = DetelemArm(
        client=FakeLLMClient(_de_script()),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=3,
    )
    de_res = de.run()
    assert de_res.status == "completed"
    assert de_res.submitted_ranking is not None

    ceq = CEQTelemArm(
        client=FakeLLMClient(_ceq_script()),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=5,
    )
    ceq_res = ceq.run()
    assert ceq_res.status == "completed"
    assert ceq_res.submitted_ranking is not None


def test_de_aborts_on_token_budget(fake_registry: PilotCaseRegistry, tmp_path: Path) -> None:
    def script(prompt: str, call_index: int) -> str | tuple[str, dict]:
        # One valid tool call whose reported usage blows the V3.1 90,000-token
        # envelope; the next per-round gate must abort before further work.
        return _tool("system_context"), {"prompt_tokens": MAX_TOKENS_PER_RUN + 1, "completion_tokens": 1}

    arm = DetelemArm(
        client=FakeLLMClient(script),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=3,
    )
    result = arm.run()
    assert result.status == "aborted_budget"
    assert result.submitted_ranking is None
    assert result.tokens_total > MAX_TOKENS_PER_RUN
    # Mechanism v2: the best-evidence commit path fires after the budget
    # abort; the script never commits, so the failure is a recorded
    # NON-COMMIT (transparent abort_reason, not a silent stall).
    assert result.abort_reason is not None
    assert result.abort_reason.startswith("non_commit:")


def test_de_tool_cap_forced_best_evidence_commit(
    fake_registry: PilotCaseRegistry, tmp_path: Path
) -> None:
    """Bounded experiment selection: the investigator gets exactly
    DE_PHASE1_TOOL_CAP tool calls; on exhaustion the arm forces a
    best-evidence commit (no silent stall, no 7th tool call)."""
    from repliclaw.experiments.v3.telemetry_arms import DE_PHASE1_TOOL_CAP

    def script(prompt: str, call_index: int) -> str:
        if "Adjudication table" in prompt:
            return _tool("top_anomalies", k=10)
        if "Observation for committee" in prompt:
            return _commit(RANK5, 0.99)
        if "BEST-EVIDENCE COMMIT" in prompt:
            return _commit(RANK5, 0.4)
        if "Begin your private" in prompt or "Observation for" in prompt:
            return _tool("system_context")  # keeps asking for tools forever
        raise AssertionError(f"UNROUTED D-E prompt: {prompt[:120]!r}")

    arm = DetelemArm(
        client=FakeLLMClient(script),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=3,
    )
    result = arm.run()
    assert result.status == "completed", result
    assert result.submitted_ranking is not None
    assert result.abort_reason is None  # cap path is NOT a budget failure
    for sb in arm.sandboxes[:3]:  # the three investigator sandboxes
        assert len(sb.call_log) == DE_PHASE1_TOOL_CAP
    ledger = json.loads(Path(result.escrow_ledger_path).read_text())
    assert len(ledger["entries"]) == 3  # every investigator committed anyway
    # The forced best-evidence prompt is in the audit transcript.
    assert any(
        "BEST-EVIDENCE COMMIT" in e["content"]
        for s in arm.sessions[:3] for e in s.transcript
    )


def test_de_non_commit_recorded_as_failure(
    fake_registry: PilotCaseRegistry, tmp_path: Path
) -> None:
    """An agent that never commits (even after the bounded forced-commit
    asks) is a FAILURE: recorded with abort_reason, never masked."""

    def script(prompt: str, call_index: int) -> str:
        return _tool("system_context")  # tool call forever, never a commit

    arm = DetelemArm(
        client=FakeLLMClient(script),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=3,
    )
    result = arm.run()
    assert result.status != "completed"
    assert result.submitted_ranking is None
    assert result.success_eligible is False
    assert result.abort_reason is not None
    assert result.abort_reason.startswith("non_commit:")
    # The escrow ledger was still persisted (audit trail intact).
    assert result.escrow_ledger_path is not None
    ledger = json.loads(Path(result.escrow_ledger_path).read_text())
    assert ledger["entries"] == []  # nothing was ever committed


def test_de_best_evidence_commit_after_budget_abort(
    fake_registry: PilotCaseRegistry, tmp_path: Path
) -> None:
    """Budget (token envelope) exhausted mid-investigation: every
    investigator still commits a best-evidence packet and the arm still
    submits — transparently flagged with abort_reason + warning."""

    def script(prompt: str, call_index: int) -> str | tuple[str, dict]:
        if "Adjudication table" in prompt:
            return _tool("top_anomalies", k=10)
        if "Observation for committee" in prompt:
            return _commit(RANK5, 0.99)
        if "BEST-EVIDENCE COMMIT" in prompt:
            return _commit(RANK5, 0.4)
        if "Begin your private" in prompt:
            return (
                _tool("system_context"),
                {"prompt_tokens": MAX_TOKENS_PER_RUN + 1, "completion_tokens": 1},
            )
        raise AssertionError(f"UNROUTED D-E prompt: {prompt[:120]!r}")

    arm = DetelemArm(
        client=FakeLLMClient(script),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=3,
    )
    result = arm.run()
    assert result.status == "completed", result
    assert result.submitted_ranking is not None
    assert result.abort_reason is not None
    assert result.abort_reason.startswith("budget_exhausted:")
    assert any("best-evidence commit path" in w for w in result.warnings)
    ledger = json.loads(Path(result.escrow_ledger_path).read_text())
    assert len(ledger["entries"]) == 3  # all three committed pre-reveal
    assert any(t.get("to") == "REVEAL" for t in ledger["phase_transitions"])


BAD_RANK5 = ["bad01", "bad02", "svc00", "svc01", "svc02"]


def test_de_invalid_commit_corrected_once(
    fake_registry: PilotCaseRegistry, tmp_path: Path
) -> None:
    """A commit naming a service not in the case inventory is rejected with
    ONE bounded correction ask; the escrowed packet is the corrected
    (valid) ranking — identical rule for both arms, no oracle content."""

    def script(prompt: str, call_index: int) -> str:
        if "Adjudication table" in prompt:
            return _tool("top_anomalies", k=10)
        if "Observation for committee" in prompt:
            return _commit(RANK5, 0.99)
        if "was REJECTED" in prompt:
            return _commit(RANK5, 0.85)
        if "Begin your private" in prompt:
            return _tool("system_context")
        if "Observation for" in prompt:
            return _commit(BAD_RANK5, 0.6)
        raise AssertionError(f"UNROUTED D-E prompt: {prompt[:120]!r}")

    arm = DetelemArm(
        client=FakeLLMClient(script),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=3,
    )
    result = arm.run()
    assert result.status == "completed", result
    assert result.submitted_ranking is not None
    ledger = json.loads(Path(result.escrow_ledger_path).read_text())
    # Every escrowed packet is the CORRECTED (valid) ranking.
    assert len(ledger["entries"]) == 3
    assert all(e["ranking"] == RANK5 for e in ledger["entries"])
    # Exactly one correction ask per investigator.
    for s in arm.sessions:
        if s.agent_id in ("inv-a", "inv-b", "inv-c"):
            rejects = [p for p in s.prompts if "was REJECTED" in p]
            assert len(rejects) == 1


def test_de_invalid_commit_repeated_is_non_commit_failure(
    fake_registry: PilotCaseRegistry, tmp_path: Path
) -> None:
    """Two invalid commits in a row is a recorded non-commit FAILURE (not
    masked, not a silent infinite loop)."""

    def script(prompt: str, call_index: int) -> str:
        if "Adjudication table" in prompt:
            return _commit(RANK5, 0.99)
        if "Observation for committee" in prompt:
            return _commit(RANK5, 0.99)
        if "Begin your private" in prompt:
            return _tool("system_context")
        if "Observation for" in prompt or "was REJECTED" in prompt:
            return _commit(BAD_RANK5, 0.6)
        raise AssertionError(f"UNROUTED D-E prompt: {prompt[:120]!r}")

    arm = DetelemArm(
        client=FakeLLMClient(script),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=3,
    )
    result = arm.run()
    assert result.status != "completed"
    assert result.submitted_ranking is None
    assert result.abort_reason is not None
    assert result.abort_reason.startswith("non_commit:")
    assert "invalid" in result.abort_reason or "re-commit" in result.abort_reason


def test_ceq_invalid_final_commit_corrected_once(
    fake_registry: PilotCaseRegistry, tmp_path: Path
) -> None:
    """C-EQ: the manager's final commit is validated against the inventory
    with one bounded correction ask (same rule as D-E)."""

    def script(prompt: str, call_index: int) -> str:
        if "One-shot consultation" in prompt:
            return _commit(RANK5, 0.6)
        if "Pre-outcome forecast" in prompt:
            return _commit(RANK5, 0.8)
        if "was REJECTED" in prompt:
            return _commit(RANK5, 0.9)
        if "Planner round" in prompt:
            return _commit(RANK5, 0.85)
        if "Final commit" in prompt:
            return _commit(BAD_RANK5, 0.7)
        raise AssertionError(f"UNROUTED C-EQ prompt: {prompt[:120]!r}")

    arm = CEQTelemArm(
        client=FakeLLMClient(script),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=5,
    )
    result = arm.run()
    assert result.status == "completed", result
    assert result.submitted_ranking == RANK5
    manager = next(s for s in arm.sessions if s.agent_id == "manager")
    assert sum(1 for p in manager.prompts if "was REJECTED" in p) == 1


def test_parse_action_batch() -> None:
    batch = json.dumps({
        "action": "tool_calls",
        "tools": [{"tool": "system_context", "args": {}},
                  {"tool": "service_metrics", "args": {"svc": "svc01", "k": 10}}],
    })
    action = parse_action(batch)
    assert action["action"] == "tool_calls"
    assert len(action["tools"]) == 2
    assert action["tools"][1]["args"] == {"svc": "svc01", "k": 10}
    # Empty / oversized / malformed batches are rejected.
    with pytest.raises(_malformed_type()):
        parse_action(json.dumps({"action": "tool_calls", "tools": []}))
    with pytest.raises(_malformed_type()):
        parse_action(json.dumps({"action": "tool_calls", "tools":
                                 [{"tool": f"t{i}"} for i in range(4)]}))
    with pytest.raises(_malformed_type()):
        parse_action(json.dumps({"action": "tool_calls", "tools": [
            {"tool": "top_anomalies", "args": "not-a-dict"}]}))


def _malformed_type() -> type:
    from repliclaw.experiments.v3.telemetry_arms import _MalformedActionError

    return _MalformedActionError


# ---------------------------------------------------------------------------
# V3.1 (AMEND_V3_1, approved D-V3-016): A1 amended envelope, A2-repealed
# canary invariance, A4 backend provenance
# ---------------------------------------------------------------------------


def test_v32_amended_envelope_constants() -> None:
    # V3.2 (AMEND_V3_2, approved D-V3-017): B1 90,000 -> 150,000 shared
    # per-run envelope; B3 band ceil 1.25 -> 1.40; B2 tool cap 24 -> 48.
    # (V3.1 A1 value was 90,000 — see v31_prereg_freeze.md for rounds 1-3.)
    assert MAX_TOKENS_PER_RUN == 150_000
    assert (PROMPT_VOLUME_FLOOR, PROMPT_VOLUME_CEIL) == (0.6, 1.40)
    from repliclaw.experiments.v3 import telemetry as tel

    assert tel.MAX_TOOL_CALLS == 48


def test_v31_envelope_parity_guard() -> None:
    # A1 applies IDENTICALLY to both arms via the shared constant; an
    # explicit envelope above the shared value must be rejected.
    from repliclaw.experiments.v3.telemetry_arms import _Envelope

    env = _Envelope()
    assert env.max_tokens_per_run == MAX_TOKENS_PER_RUN
    with pytest.raises(ValueError, match="A1 parity guard"):
        _Envelope(max_tokens_per_run=MAX_TOKENS_PER_RUN + 1)


def test_v31_backend_model_provenance_recorded(fake_registry: PilotCaseRegistry, tmp_path: Path) -> None:
    # A4: the gateway-echoed model id is captured per agent and surfaced on
    # ArmRunResult. We wrap a FakeLLMClient so each response echoes a model.
    base = FakeLLMClient(_ceq_script())

    class _EchoCompletions:
        def __init__(self, inner: Any, echoed: str) -> None:
            self._inner = inner
            self._echoed = echoed

        def create(self, *args: Any, **kwargs: Any) -> Any:
            resp = self._inner.create(*args, **kwargs)
            resp.model = self._echoed  # SimpleNamespace: attr settable
            return resp

    base.chat = _EchoCompletions(base.chat, "echoed-backend-xyz")
    arm = CEQTelemArm(
        client=base, registry=fake_registry, opaque_id="RCA-P-01", out_dir=tmp_path, seed=5,
    )
    result = arm.run()
    assert result.status == "completed"
    assert all(m == "echoed-backend-xyz" for m in result.backend_models)
    assert result.backend_models  # every session made LLM calls -> non-empty


def test_v32_band_recalibration_and_crash_invariance(fake_registry: PilotCaseRegistry, tmp_path: Path) -> None:
    # V3.2 B3: band ceil recalibrated 1.25 -> 1.40 from the MEASURED
    # distribution (completed 1.2245-1.2352; P-03 1.2843-1.2895; P-02
    # 1.3476); crash-on-violation BEHAVIOR unchanged (out-of-band still
    # crashes, in-band completes). The old V3.1 violations (1.2845-1.3476)
    # are now IN-band by design — this is the N1 recalibration.
    assert (PROMPT_VOLUME_FLOOR, PROMPT_VOLUME_CEIL) == (0.6, 1.40)
    # Observed historical violations now pass (recalibration intent).
    assert_volume_band(1.2895)  # R1/R2 P-03
    assert_volume_band(1.3476)  # R3 P-02
    # Guard still live above the observed deterministic exceedances.
    with pytest.raises(ValueError):
        assert_volume_band(1.41)
    with pytest.raises(ValueError):
        assert_volume_band(0.5)
    assert_volume_band(1.40)  # upper boundary passes

    arm = CEQTelemArm(
        client=FakeLLMClient(_ceq_script()),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=5,
    )
    result = arm.run()
    assert result.status == "completed"
    assert 0.6 <= (result.prompt_volume_ratio or 0.0) <= PROMPT_VOLUME_CEIL


# ---------------------------------------------------------------------------
# C-EQ-TELEM
# ---------------------------------------------------------------------------


def test_ceq_forecast_before_first_tool_and_loop_stops_on_commit(
    fake_registry: PilotCaseRegistry, tmp_path: Path
) -> None:
    times, clock = _counter_clock()
    times[0] += 100.0  # run start strictly precedes all commits
    arm = CEQTelemArm(
        client=FakeLLMClient(_ceq_script()),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=5,
        clock=clock,
    )
    result = arm.run()
    assert result.status == "completed", result
    assert result.submitted_ranking == RANK5

    manager = next(s for s in arm.sessions if s.agent_id == "manager")
    # The first manager LLM prompt is the sealed-forecast prompt; its commit
    # was escrowed before ANY sandbox tool call.
    assert "Pre-outcome forecast" in manager.prompts[0]
    assert manager.prompts[0].count("Pre-outcome forecast") == 1
    assert result.escrow_ledger_path is not None
    ledger = json.loads(Path(result.escrow_ledger_path).read_text())
    entries = ledger["entries"]
    forecast = [e for e in entries if e["phase"] == "forecast"]
    assert len(forecast) == 1
    assert forecast[0]["agent_id"] == "manager"
    assert forecast[0]["ranking"] == RANK5
    # Forecast commit strictly after run start (i.e. inside the run, at the
    # first manager LLM call which precedes any sandbox tool call).
    assert forecast[0]["committed_at"] > 1_000_100.0
    manager_sandbox = arm.sandboxes[0]
    # Planner loop stopped on the in-loop commit: only 2 tool calls, then the
    # one-shot submit_diagnosis (no further rounds consumed).
    tools = [c["tool"] for c in manager_sandbox.call_log]
    assert tools == ["system_context", "top_anomalies", "submit_diagnosis"]
    # 5 manager LLM calls: forecast + 2 tools + in-loop commit + final commit.
    assert manager.llm_call_count == 5
    # Sealed forecast line is carried into every planner prompt.
    planner_prompts = [p for p in manager.prompts if "Planner round" in p]
    assert len(planner_prompts) == 1  # loop exited on round 1's commit
    assert "sealed pre-outcome commit" in planner_prompts[0]


def test_ceq_findings_collected_once(fake_registry: PilotCaseRegistry, tmp_path: Path) -> None:
    arm = CEQTelemArm(
        client=FakeLLMClient(_ceq_script()),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=5,
    )
    result = arm.run()
    assert result.status == "completed"
    inv_sessions = [s for s in arm.sessions if s.agent_id != "manager"]
    assert sorted(s.agent_id for s in inv_sessions) == ["inv-a", "inv-b", "inv-c"]
    for s in inv_sessions:
        assert len(s.prompts) == 2  # single consultation + one post-tool commit prompt
        assert "One-shot consultation" in s.prompts[0]
    inv_sandboxes = arm.sandboxes[1:]
    assert len(inv_sandboxes) == 3
    for sb in inv_sandboxes:
        tools = [c["tool"] for c in sb.call_log]
        assert tools == ["service_logs"]  # exactly 1 of the 3-call cap, no submit
    # Final commit prompt reports all three findings, collected post-loop.
    manager = next(s for s in arm.sessions if s.agent_id == "manager")
    final = manager.prompts[-1]
    assert "Investigator findings (collected once, post-loop)" in final
    for inv in ("inv-a", "inv-b", "inv-c"):
        assert inv in final


def test_ceq_manager_batch_equivalent_parallelism(
    fake_registry: PilotCaseRegistry, tmp_path: Path
) -> None:
    """Mechanism v2: the C-EQ manager may issue a BATCH of tool calls in one
    turn (equivalent parallelism); both calls execute in one agent turn."""
    batch = json.dumps({"action": "tool_calls", "tools": [
        {"tool": "system_context", "args": {}},
        {"tool": "top_anomalies", "args": {"k": 20}},
    ]})

    def script(prompt: str, call_index: int) -> str:
        if "One-shot consultation" in prompt:
            return _commit(RANK5, 0.6)
        if "Pre-outcome forecast" in prompt:
            return _commit(RANK5, 0.8)
        if "Planner round" in prompt:
            return batch
        if "Observations from the last batch" in prompt:
            return _commit(RANK5, 0.85)
        if "Final commit" in prompt:
            return _commit(RANK5, 0.9)
        raise AssertionError(f"UNROUTED C-EQ prompt: {prompt[:120]!r}")

    arm = CEQTelemArm(
        client=FakeLLMClient(script),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=5,
    )
    result = arm.run()
    assert result.status == "completed", result
    assert result.submitted_ranking == RANK5
    manager = next(s for s in arm.sessions if s.agent_id == "manager")
    # Batch executed in ONE turn: forecast + batch ask + post-batch commit
    # + final commit = 4 manager calls (vs 5 for two single tool turns).
    assert manager.llm_call_count == 4
    tools = [c["tool"] for c in arm.sandboxes[0].call_log]
    assert tools == ["system_context", "top_anomalies", "submit_diagnosis"]
    # The batch extension is disclosed to the manager (system prompt), never
    # to C-EQ's consult-only investigators.
    assert "tool_calls" in manager.messages[0]["content"]
    for s in arm.sessions:
        if s.agent_id != "manager":
            assert "tool_calls" not in s.messages[0]["content"]


def test_ceq_best_evidence_commit_after_budget_abort(
    fake_registry: PilotCaseRegistry, tmp_path: Path
) -> None:
    """Mechanism v2 (parity with D-E): token budget exhausted mid-investigation
    -> the manager still commits its best-evidence ranking (flagged)."""

    def script(prompt: str, call_index: int) -> str | tuple[str, dict]:
        if "Pre-outcome forecast" in prompt:
            return _commit(RANK5, 0.8)
        if "BEST-EVIDENCE COMMIT" in prompt:
            return _commit(RANK5, 0.5)
        return (
            _tool("system_context"),
            {"prompt_tokens": MAX_TOKENS_PER_RUN + 1, "completion_tokens": 1},
        )

    arm = CEQTelemArm(
        client=FakeLLMClient(script),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=5,
    )
    result = arm.run()
    assert result.status == "completed", result
    assert result.submitted_ranking is not None
    assert result.abort_reason is not None
    assert result.abort_reason.startswith("budget_exhausted:")
    assert any("best-evidence commit path" in w for w in result.warnings)
    ledger = json.loads(Path(result.escrow_ledger_path).read_text())
    phases = [e["phase"] for e in ledger["entries"]]
    assert "forecast" in phases and "final" in phases


def test_volume_band_function() -> None:
    assert_volume_band(1.0)   # interior: passes
    assert_volume_band(0.6)   # lower boundary: passes
    assert_volume_band(1.40)  # upper boundary (V3.2) passes
    with pytest.raises(ValueError):
        assert_volume_band(0.5)
    with pytest.raises(ValueError):
        assert_volume_band(1.41)


def test_prompt_volume_ratio_definition() -> None:
    # ceq.py:329 — manager total tokens / (n × mean investigator tokens), len//4.
    manager = ["a" * 100, "b" * 200]  # 25 + 50 = 75 tokens
    inv = ["c" * 100, "d" * 100]      # 25 + 25 = 50 tokens (n=2, mean 25)
    assert prompt_volume_ratio(manager, inv) == pytest.approx(75 / 50)
    with pytest.raises(ValueError):
        prompt_volume_ratio(manager, [])


def test_ceq_volume_band_in_band_on_happy_path(fake_registry: PilotCaseRegistry, tmp_path: Path) -> None:
    arm = CEQTelemArm(
        client=FakeLLMClient(_ceq_script()),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=5,
    )
    result = arm.run()
    assert result.status == "completed"
    assert result.prompt_volume_ratio is not None
    assert 0.6 <= result.prompt_volume_ratio <= PROMPT_VOLUME_CEIL


def test_ceq_volume_breach_records_warning_not_crash(
    fake_registry: PilotCaseRegistry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A prompt-volume canary breach must NOT discard an already-submitted C-EQ
    ranking (that masked valid results on large-payload cases); it records a
    warning and still completes."""
    import repliclaw.experiments.v3.telemetry_arms as ta

    real = ta.prompt_volume_ratio

    def _breach(prompts_manager: Any, prompts_investigator_pool: Any) -> float:
        # Force the manager/investigator volume ratio above the ceiling so the
        # canary trips, regardless of the deterministic fake script's real value.
        return real(prompts_manager, prompts_investigator_pool) + 2.0

    monkeypatch.setattr(ta, "prompt_volume_ratio", _breach)
    arm = CEQTelemArm(
        client=FakeLLMClient(_ceq_script()),
        registry=fake_registry,
        opaque_id="RCA-P-01",
        out_dir=tmp_path,
        seed=5,
    )
    result = arm.run()
    assert result.status == "completed"
    assert result.submitted_ranking == RANK5  # ranking preserved, not discarded
    assert result.success_eligible is True
    assert any("prompt-volume" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# determinism + parity canaries
# ---------------------------------------------------------------------------


def test_de_determinism_same_script_same_seed(fake_registry: PilotCaseRegistry, tmp_path: Path) -> None:
    def _run(out: Path) -> Any:
        times, clock = _counter_clock()
        times[0] += 100.0  # run start strictly precedes all commits
        arm = DetelemArm(
            client=FakeLLMClient(_de_script()),
            registry=fake_registry,
            opaque_id="RCA-P-01",
            out_dir=out,
            seed=3,
            clock=clock,
        )
        result = arm.run()
        assert result.status == "completed"
        assert result.escrow_ledger_path is not None
        prompt_shas = [
            hashlib.sha256("\n".join(s.prompts).encode()).hexdigest() for s in arm.sessions
        ]
        return result.submitted_ranking, Path(result.escrow_ledger_path).read_text(), prompt_shas

    r1 = _run(tmp_path / "a")
    r2 = _run(tmp_path / "b")
    assert r1[0] == r2[0]            # identical submitted ranking
    assert r1[2] == r2[2]            # identical per-session prompt sequences
    assert r1[1] == r2[1]            # identical escrow ledger (counter clock)


def test_ceq_determinism_same_script_same_seed(fake_registry: PilotCaseRegistry, tmp_path: Path) -> None:
    def _run(out: Path) -> Any:
        arm = CEQTelemArm(
            client=FakeLLMClient(_ceq_script()),
            registry=fake_registry,
            opaque_id="RCA-P-01",
            out_dir=out,
            seed=5,
        )
        result = arm.run()
        assert result.status == "completed"
        prompt_shas = [
            hashlib.sha256("\n".join(s.prompts).encode()).hexdigest() for s in arm.sessions
        ]
        return result.submitted_ranking, prompt_shas, result.prompt_volume_ratio

    r1 = _run(tmp_path / "a")
    r2 = _run(tmp_path / "b")
    assert r1[0] == r2[0]            # identical submitted ranking
    assert r1[1] == r2[1]            # identical per-session prompt sequences
    assert r1[2] == r2[2]            # identical volume ratio


def test_sandbox_payload_parity_canary(fake_registry: PilotCaseRegistry) -> None:
    """Identical (tool, args) -> byte-identical payloads across fresh sandboxes:
    both arms observe a byte-for-byte identical surface (sandbox purity).
    """
    from repliclaw.experiments.v3.telemetry import TelemetrySandbox

    sb1 = TelemetrySandbox(fake_registry, "RCA-P-01")
    sb2 = TelemetrySandbox(fake_registry, "RCA-P-01")
    pairs = [
        (sb1.system_context(), sb2.system_context()),
        (sb1.top_anomalies(k=20), sb2.top_anomalies(k=20)),
        (sb1.service_metrics("svc04", k=30), sb2.service_metrics("svc04", k=30)),
        (sb1.service_metrics("svc04", k=10), sb2.service_metrics("svc04", k=10)),
        (sb1.service_logs("svc04", k=50), sb2.service_logs("svc04", k=50)),
        (sb1.service_traces("svc04", k=30), sb2.service_traces("svc04", k=30)),
    ]
    for p1, p2 in pairs:
        assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    # Same (tool, args) normalized identically in both arms' execution layer.
    de = DetelemArm.__new__(DetelemArm)
    ceq = CEQTelemArm.__new__(CEQTelemArm)
    for action in (
        {"action": "tool_call", "tool": "service_logs", "args": {"svc": "svc04", "k": 12}},
        {"action": "tool_call", "tool": "service_metrics", "args": {"svc": "svc01"}},
        {"action": "tool_call", "tool": "top_anomalies", "args": {}},
    ):
        assert de._execute_tool(sb1, action) == ceq._execute_tool(sb2, action)


def test_execute_tool_budget_exhausted_is_observation_not_crash(
    fake_registry: PilotCaseRegistry
) -> None:
    """Hitting the per-tool log/trace cap must return a ``budget_exhausted``
    observation (so the agent can still commit) rather than crash the arm, and
    it must behave identically in both arms (parity)."""
    from repliclaw.experiments.v3.telemetry import TelemetrySandbox

    sb = TelemetrySandbox(fake_registry, "RCA-P-01")
    de = DetelemArm.__new__(DetelemArm)
    ceq = CEQTelemArm.__new__(CEQTelemArm)
    action = {"action": "tool_call", "tool": "service_logs", "args": {"svc": "svc04", "k": 50}}
    # Exhaust the shared service_logs budget (MAX_LOGS_CALLS = 4).
    for _ in range(4):
        sb.service_logs("svc04", k=50)
    out_de = de._execute_tool(sb, action)
    assert out_de["payload"]["error"] == "budget_exhausted"
    assert "service_logs budget exhausted" in out_de["payload"]["detail"]
    # Identical treatment in the other arm on the same (exhausted) sandbox.
    out_ceq = ceq._execute_tool(sb, action)
    assert out_ceq == out_de


def test_both_arms_share_identical_tool_docs() -> None:
    import repliclaw.experiments.v3.telemetry_arms as arms

    for tool in ("system_context", "top_anomalies", "service_metrics",
                 "service_logs", "service_traces"):
        assert tool in arms.TOOL_DOCS
    # Same telemetry sandbox class backs both arms (parity by construction).
    assert DetelemArm._new_sandbox.__qualname__.startswith("_ArmBase")
    assert CEQTelemArm._new_sandbox is DetelemArm._new_sandbox


def test_arm_escrow_commit_reveal_semantics() -> None:
    escrow = ArmEscrow("D-E-TELEM", "RCA-P-01")
    assert escrow.entries == []
    escrow.commit("inv-a", "phase1", RANK5, 0.9)
    assert escrow.entries[0]["revealed"] is False
    assert escrow.entries[0]["revealed_at"] is None
    assert escrow.entries[0]["commit_sha256"]
    escrow.reveal_all()
    assert escrow.entries[0]["revealed"] is True
    assert escrow.entries[0]["revealed_at"] is not None
    json.dumps({"arm": escrow.arm_label, "opaque_case_id": escrow.opaque_case_id,
                "entries": escrow.entries})  # ledger is JSON-serializable


def test_model_substitution_label_default_and_override() -> None:
    client = FakeLLMClient([_commit(RANK5)])
    session = LLMToolSession(client, system_prompt="sys", agent_id="x")
    assert "MODEL-SUBSTITUTION" in session.model_label
    assert "Qwen3.8-27B" in session.model_label
    session2 = LLMToolSession(client, system_prompt="sys", agent_id="x", model_label="custom-label")
    assert session2.model_label == "custom-label"
