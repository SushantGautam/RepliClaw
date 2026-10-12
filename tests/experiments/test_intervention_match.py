"""FF-04: D-E-TELEM vs C-EQ-TELEM intervention-match proof.

Proves, with executable tests, that the two arms run against EXACTLY the
same real interface. Six tests, one per ticket item:

1. ``test_action_menu_byte_identical``   — the tool menu presented to the LLM
   (captured from the messages actually sent on the real serving path) is
   byte-identical across every session of both arms and equals the shared
   ``TOOL_DOCS + ACTION_PROTOCOL`` canonical block (mechanism v2: the ONLY
   disclosed menu difference is the C-EQ manager's batch extension).
2. ``test_budget_caps_identical``        — both arms enforce the identical
   shared sandbox total (``MAX_TOOL_CALLS``) and per-tool (``MAX_LOGS_CALLS``)
   caps with identical exhaustion behavior, driven by a scripted client
   hammering one tool, plus the identical shared token/wall envelope.
   (Mechanism v2: D-E additionally bounds each investigator at
   ``DE_PHASE1_TOOL_CAP`` turns — a designed mechanism difference — and still
   completes via the forced best-evidence commit.)
3. ``test_environment_snapshot_identical`` — the same opaque case id resolves
   to the same case dir and byte-identical ``system_context`` /
   ``top_anomalies`` payloads in both arms.
4. ``test_ceq_no_fixed_script``          — identical seed + identical scripted
   client, DIFFERENT tool feedback (two cases) -> the C-EQ planner commits
   different decisions (rank-1 = the service the feedback scores top);
   same feedback -> same decision. Decisions are a function of observed
   feedback, not a fixed script.
5. ``test_ceq_no_oracle_in_prompt``      — the real C-EQ planner prompt and
   every agent-visible prompt/payload of both arms contain no
   defect-class literal, no root-cause service (the service embedded in the
   upstream id), no upstream case id, and no sealed label-column literal.
6. ``test_no_central_starvation``        — under a token-exhausting scripted
   workload both arms abort at the SAME shared token ceiling; the shared
   sandbox ceiling (48) is reachable on both arms' own sandboxes; and a
   full C-EQ tool-hammer run finishes with no budget cutoff.

Offline only: no network, no LLM calls (``FakeLLMClient`` scripted clients).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import pytest

from repliclaw.experiments.v3.telemetry import (
    FORBIDDEN_LABEL_LITERALS,
    FROZEN_PILOT_IDS,
    MAX_LOGS_CALLS,
    MAX_TOOL_CALLS,
    PilotCaseRegistry,
    TelemetrySandbox,
)
from repliclaw.experiments.v3.telemetry_arms import (
    ACTION_PROTOCOL,
    BATCH_ACTION_PROTOCOL,
    CEQ_MANAGER_BATCH_MAX,
    DE_PHASE1_TOOL_CAP,
    MAX_TOKENS_PER_RUN,
    TOOL_DOCS,
    WALL_CAP_S,
    CEQTelemArm,
    DetelemArm,
    FakeLLMClient,
    parse_action,
)

SORTED_FROZEN = sorted(FROZEN_PILOT_IDS)
UP1 = SORTED_FROZEN[0]  # upstream id behind RCA-P-01 (contains root-cause service + defect class)
UP2 = SORTED_FROZEN[1]  # upstream id behind RCA-P-02 (different defect class)
OP1 = "RCA-P-01"
OP2 = "RCA-P-02"
SPIKE1 = "svc04"  # service the synthetic RCA-P-01 telemetry scores top
SPIKE2 = "svc07"  # service the synthetic RCA-P-02 telemetry scores top
SERVICES = [f"svc{i:02d}" for i in range(13)]
# First line of TOOL_DOCS — unique, so extraction cannot latch onto prose
# mentions like "inspect telemetry with the OBS tools before the arm submits".
MENU_MARKER = "OBS tools (telemetry sandbox for this incident):"
# The OBS tool menu exactly as frozen in the sandbox interface.
EXPECTED_MENU_TOOLS = ["system_context", "top_anomalies", "service_metrics", "service_logs", "service_traces"]

Script = Callable[[str, int], str]


# ---------------------------------------------------------------------------
# synthetic case builder + fixtures (13 services; one service spikes in the
# faulty window so top_anomalies ranks it first — the only "evidence")
# ---------------------------------------------------------------------------


def _build_case(root: Path, upstream: str, spike_idx: int) -> Path:
    case = root / upstream
    case.mkdir(parents=True, exist_ok=True)
    onset = 1_000_000
    n = 800
    t = np.arange(onset - 600, onset + 200)
    rng = np.random.default_rng(7)
    data: dict[str, np.ndarray] = {"time": t}
    for i in range(13):
        base = 10.0 + rng.normal(0.0, 0.5, size=n)
        if i == spike_idx:
            base = base.copy()
            base[600:] += 50.0
        data[f"svc{i:02d}_s1"] = base
    data["svc00_const"] = np.full(n, 3.14)
    pd.DataFrame(data).to_parquet(case / "metrics.parquet")
    (case / "inject_time.txt").write_text(f"{onset}\n")
    return case


@pytest.fixture()
def registry(tmp_path: Path) -> PilotCaseRegistry:
    _build_case(tmp_path, UP1, 4)  # RCA-P-01 -> SPIKE1
    _build_case(tmp_path, UP2, 7)  # RCA-P-02 -> SPIKE2
    return PilotCaseRegistry(data_root=tmp_path)


def _tool(tool: str, **args: Any) -> str:
    return json.dumps({"action": "tool_call", "tool": tool, "args": args})


def _commit(ranking: list[str], confidence: float = 0.9) -> str:
    return json.dumps({"action": "commit", "ranking": ranking, "confidence": confidence})


def _ranking(top: str) -> list[str]:
    return [top] + [s for s in SERVICES if s != top][:4]


def _first_service(prompt: str) -> str | None:
    """First ``"service": "<name>"`` in a rendered top_anomalies evidence view."""
    m = re.search(r'"service":\s*"([A-Za-z0-9_-]+)"', prompt)
    return m.group(1) if m else None


def _sha(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# completing scripts (both arms reach a normal completed run)
# ---------------------------------------------------------------------------


def _de_complete_script() -> Script:
    """Mechanism v2: one pre-outcome escrow commit per independent
    investigator (no consultation round), then the committee commit."""

    def script(prompt: str, call_index: int) -> str:
        if "Adjudication table" in prompt:
            return _commit(_ranking("svc04"), 0.99)
        if "BEST-EVIDENCE COMMIT" in prompt:
            return _commit(_ranking("svc04"), 0.4)
        if "Begin your private" in prompt:
            return _tool("system_context")
        if "Observation for" in prompt:
            return _commit(_ranking("svc04"), 0.8)
        raise AssertionError(f"UNROUTED D-E prompt: {prompt[:120]!r}")

    return script


def _ceq_complete_script() -> Script:
    mgr = [
        _commit(_ranking("svc04"), 0.8),          # sealed forecast
        _tool("system_context"),                  # planner round 1 tool 1
        _tool("top_anomalies", k=20),             # planner round 1 tool 2
        _commit(_ranking("svc04"), 0.85),         # in-loop commit -> loop stops
        _commit(_ranking("svc04"), 0.9),          # final commit
    ]
    state = {"mi": 0}

    def script(prompt: str, call_index: int) -> str:
        if "Now commit your findings" in prompt:
            return _commit(_ranking("svc00"), 0.6)
        if "One-shot consultation" in prompt:
            return _tool("system_context")
        out = mgr[state["mi"]]
        state["mi"] += 1
        return out

    return script


def _agent_visible_texts(arm: DetelemArm | CEQTelemArm) -> list[str]:
    """System prompt + every user prompt the harness actually built per session."""
    texts: list[str] = []
    for s in arm.sessions:
        texts.append(s.messages[0]["content"])
        texts.extend(s.prompts)
    return texts


class _CapturingClient:
    """Wraps a scripted client and records every message list actually sent."""

    def __init__(self, inner: FakeLLMClient) -> None:
        self._inner = inner
        self.sent: list[list[dict[str, str]]] = []
        self.chat = self._CapChat(self)

    class _CapChat:
        def __init__(self, outer: "_CapturingClient") -> None:
            self._outer = outer

        def create(self, *, model: str, messages: list[dict[str, str]], temperature: float = 0.0,
                   **_kw: Any) -> Any:
            self._outer.sent.append([dict(m) for m in messages])
            return self._outer._inner.chat.create(model=model, messages=messages, temperature=temperature)


def _menu_block(system_prompt: str) -> str:
    """The tool-menu block exactly as embedded in the agent system prompt."""
    return system_prompt[system_prompt.index(MENU_MARKER):]


# ---------------------------------------------------------------------------
# 1. action menu byte-identical (real serving path: captured sent messages)
# ---------------------------------------------------------------------------


def test_action_menu_byte_identical(registry: PilotCaseRegistry, tmp_path: Path) -> None:
    cap_de = _CapturingClient(FakeLLMClient(_de_complete_script()))
    cap_ceq = _CapturingClient(FakeLLMClient(_ceq_complete_script()))
    de = DetelemArm(client=cap_de, registry=registry, opaque_id=OP1, out_dir=tmp_path / "de", seed=1)
    ceq = CEQTelemArm(client=cap_ceq, registry=registry, opaque_id=OP1, out_dir=tmp_path / "ceq", seed=1)
    r_de, r_ceq = de.run(), ceq.run()
    assert r_de.status == "completed" and r_ceq.status == "completed"
    assert cap_de.sent and cap_ceq.sent, "no LLM calls captured — not the real serving path"

    blocks: list[str] = []
    for call in [*cap_de.sent, *cap_ceq.sent]:
        assert call[0]["role"] == "system"
        blocks.append(_menu_block(call[0]["content"]))
    # Mechanism v2: the ONE designed, disclosed difference in the menu is the
    # C-EQ manager's batch extension (equivalent parallelism). Every session
    # must present exactly the shared frozen menu, optionally followed by the
    # manager-only batch extension and nothing else.
    base_menu = TOOL_DOCS + "\n\n" + ACTION_PROTOCOL
    batch_suffix = "\n\n" + BATCH_ACTION_PROTOCOL.format(batch_max=CEQ_MANAGER_BATCH_MAX)
    cores: list[str] = []
    for b in blocks:
        if b == base_menu:
            cores.append(b)
        elif b == base_menu + batch_suffix:
            cores.append(base_menu)
        else:
            raise AssertionError(f"unexpected action-menu block (menu drift): {b[-200:]!r}")
    # (a) byte-identical core menu across EVERY session of BOTH arms
    canonical = {
        json.dumps({"tools": re.findall(r"^- (\w+)\(", b, re.M),
                    "menu_sha256": hashlib.sha256(b.encode("utf-8")).hexdigest()}, sort_keys=True)
        for b in cores
    }
    assert len(canonical) == 1, f"action menu differs across arms/sessions: {len(blocks)} blocks"
    # (b) equals the shared frozen menu block (no arm-local drift)
    assert all(b == base_menu for b in cores)
    # (c) advertises exactly the frozen OBS tool set, in order
    assert re.findall(r"^- (\w+)\(", blocks[0], re.M) == EXPECTED_MENU_TOOLS
    # (d) the batch extension appears ONLY on C-EQ manager sessions
    for b in blocks:
        if "tool_calls" in b:
            assert b == base_menu + batch_suffix


# ---------------------------------------------------------------------------
# 2. identical total + per-tool budget caps, same exhaustion behavior
# ---------------------------------------------------------------------------


def _hammer(
    arm_cls: type[DetelemArm] | type[CEQTelemArm],
    registry: PilotCaseRegistry,
    out: Path,
    tool: str,
    args: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    """Drive the arm's real execution seam with a scripted client that hammers
    one tool until the sandbox budget is exhausted. A per-tool or total budget
    cap is a NORMAL end-of-evidence condition: the arm returns a
    ``budget_exhausted`` observation (parity-preserving) rather than crashing.
    Returns (calls actually recorded by the sandbox, the first exhausted
    observation payload)."""
    client = FakeLLMClient(lambda _p, _i: _tool(tool, **args))
    arm = arm_cls(client=client, registry=registry, opaque_id=OP1, out_dir=out, seed=1)
    sandbox = arm._new_sandbox()
    for i in range(MAX_TOOL_CALLS + MAX_LOGS_CALLS + 4):
        resp = client.chat.create(model="default", messages=[{"role": "user", "content": f"hammer {i}"}])
        action = parse_action(resp.choices[0].message.content)
        obs = arm._execute_tool(sandbox, action)
        if obs["payload"].get("error") == "budget_exhausted":
            return sandbox._total_calls, obs["payload"]
    raise AssertionError(f"{tool}: budget never exhausted within {MAX_TOOL_CALLS + MAX_LOGS_CALLS + 4} calls")


def test_budget_caps_identical(registry: PilotCaseRegistry, tmp_path: Path) -> None:
    # Total cap: hammer an uncapped tool until exhaustion — identical on both arms.
    total_de = _hammer(DetelemArm, registry, tmp_path / "de-total", "top_anomalies", {"k": 20})
    total_ceq = _hammer(CEQTelemArm, registry, tmp_path / "ceq-total", "top_anomalies", {"k": 20})
    assert total_de == total_ceq, f"total-cap exhaustion differs: D-E {total_de} vs C-EQ {total_ceq}"
    assert total_de[0] == MAX_TOOL_CALLS
    assert total_de[1]["error"] == "budget_exhausted"
    assert f"({MAX_TOOL_CALLS} calls)" in total_de[1]["detail"]

    # Per-tool cap: hammer service_logs — identical on both arms.
    logs_de = _hammer(DetelemArm, registry, tmp_path / "de-logs", "service_logs", {"svc": "svc00", "k": 10})
    logs_ceq = _hammer(CEQTelemArm, registry, tmp_path / "ceq-logs", "service_logs", {"svc": "svc00", "k": 10})
    assert logs_de == logs_ceq, f"per-tool cap exhaustion differs: D-E {logs_de} vs C-EQ {logs_ceq}"
    assert logs_ceq[0] == MAX_LOGS_CALLS
    assert logs_ceq[1]["error"] == "budget_exhausted"
    assert f"({MAX_LOGS_CALLS} calls)" in logs_ceq[1]["detail"]

    # Per-run envelope (token + wall ceiling): one shared constant, both arms.
    de = DetelemArm(client=FakeLLMClient([]), registry=registry, opaque_id=OP1, out_dir=tmp_path / "de-env")
    ceq = CEQTelemArm(client=FakeLLMClient([]), registry=registry, opaque_id=OP1, out_dir=tmp_path / "ceq-env")
    assert de.envelope == ceq.envelope
    assert de.envelope.max_tokens_per_run == MAX_TOKENS_PER_RUN
    assert de.envelope.wall_cap_s == WALL_CAP_S

    # End-to-end (mechanism v2): a full D-E run hammered with one tool is
    # bounded by the DESIGNED per-investigator tool cap (bounded experiment
    # selection — a disclosed mechanism difference, not a parity item); each
    # investigator still finishes via the forced best-evidence commit, so the
    # run completes with exactly 3 x DE_PHASE1_TOOL_CAP tool calls.
    def _de_hammer(prompt: str, _i: int) -> str:
        if "BEST-EVIDENCE COMMIT" in prompt:
            return _commit(_ranking("svc04"), 0.3)
        if "Adjudication table" in prompt:
            return _commit(_ranking("svc04"), 0.99)
        return _tool("top_anomalies", k=20)

    r = DetelemArm(
        client=FakeLLMClient(_de_hammer),
        registry=registry,
        opaque_id=OP1,
        out_dir=tmp_path / "de-ham",
        seed=1,
    ).run()
    assert r.status == "completed", r
    # 3 investigators x bounded cap + 1 committee submit_diagnosis.
    assert r.tool_calls == 3 * DE_PHASE1_TOOL_CAP + 1
    assert r.submitted_ranking is not None
    assert not r.crash_error


# ---------------------------------------------------------------------------
# 3. identical environment snapshot for the same opaque case id
# ---------------------------------------------------------------------------


def test_environment_snapshot_identical(registry: PilotCaseRegistry, tmp_path: Path) -> None:
    # Two independently-constructed registries: the same opaque id must resolve
    # to the same case dir with byte-identical case data.
    reg_a = PilotCaseRegistry(data_root=registry.data_root)
    reg_b = PilotCaseRegistry(data_root=registry.data_root)
    dir_a, dir_b = reg_a.case_dir(OP1), reg_b.case_dir(OP1)
    assert dir_a == dir_b
    for name in ("metrics.parquet", "inject_time.txt"):
        assert dir_a / name == dir_b / name and (dir_a / name).is_file()
        assert hashlib.sha256((dir_a / name).read_bytes()).hexdigest() == \
            hashlib.sha256((dir_b / name).read_bytes()).hexdigest()

    # One sandbox per arm (each arm's own construction path) -> byte-identical
    # payloads for the same opaque case id.
    de = DetelemArm(client=FakeLLMClient([]), registry=reg_a, opaque_id=OP1, out_dir=tmp_path / "de")
    ceq = CEQTelemArm(client=FakeLLMClient([]), registry=reg_b, opaque_id=OP1, out_dir=tmp_path / "ceq")
    sb_de, sb_ceq = de._new_sandbox(), ceq._new_sandbox()
    pairs = [
        (sb_de.system_context(), sb_ceq.system_context()),
        (sb_de.top_anomalies(k=20), sb_ceq.top_anomalies(k=20)),
    ]
    for a, b in pairs:
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
        assert _sha(a) == _sha(b)


# ---------------------------------------------------------------------------
# 4. C-EQ planner: decisions are a function of observed feedback, not a script
# ---------------------------------------------------------------------------


def _ceq_feedback_script() -> Script:
    """Content-routed: commits are DERIVED from the top_anomalies evidence in
    the planner prompt (rank-1 = the service the feedback scores top). The
    script knows no case id, no service, no seed — only what it observes."""

    def script(prompt: str, call_index: int) -> str:
        if "Now commit your findings" in prompt:
            return _commit(_ranking("svc00"), 0.6)
        if "One-shot consultation" in prompt:
            return _tool("system_context")
        if "Pre-outcome forecast (SEALED)" in prompt:
            return _commit(_ranking("svc00"), 0.5)
        if "Planner round" in prompt:
            return _tool("system_context")
        # Mechanism v2: the post-batch continuation renders
        # "Observations from the last batch: - <tool>(...) -> ...".
        if "Observations from the last batch" in prompt and "- top_anomalies(" in prompt:
            return _commit(_ranking(_first_service(prompt) or "svc00"), 0.85)
        if "Observations from the last batch" in prompt:
            return _tool("top_anomalies", k=20)
        if "Final commit" in prompt:
            return _commit(_ranking(_first_service(prompt) or "svc00"), 0.9)
        raise AssertionError(f"UNROUTED C-EQ prompt: {prompt[:120]!r}")

    return script


def _run_ceq(registry: PilotCaseRegistry, out: Path, opaque: str, seed: int = 11):
    arm = CEQTelemArm(
        client=FakeLLMClient(_ceq_feedback_script()),
        registry=registry,
        opaque_id=opaque,
        out_dir=out,
        seed=seed,
    )
    return arm, arm.run()


def _manager_decisions(arm: CEQTelemArm) -> list[dict[str, Any]]:
    assert arm.sessions[0].agent_id == "manager"
    return [parse_action(e["content"]) for e in arm.sessions[0].transcript if e["role"] == "response"]


def test_ceq_no_fixed_script(registry: PilotCaseRegistry, tmp_path: Path) -> None:
    seed = 11
    arm_a, res_a = _run_ceq(registry, tmp_path / "a", OP1, seed)      # feedback scores SPIKE1 top
    arm_b, res_b = _run_ceq(registry, tmp_path / "b", OP2, seed)      # feedback scores SPIKE2 top
    arm_a2, res_a2 = _run_ceq(registry, tmp_path / "a2", OP1, seed)   # identical feedback again
    for res in (res_a, res_b, res_a2):
        assert res.status == "completed"

    # Different tool feedback -> different planner decisions (rank-1 tracks the
    # service the feedback scores top):
    assert res_a.submitted_ranking[0] == SPIKE1
    assert res_b.submitted_ranking[0] == SPIKE2
    assert res_a.submitted_ranking != res_b.submitted_ranking
    # The planner's own commit decisions (not just the final submission) differ:
    commits_a = [d["ranking"] for d in _manager_decisions(arm_a) if d["action"] == "commit"]
    commits_b = [d["ranking"] for d in _manager_decisions(arm_b) if d["action"] == "commit"]
    assert any(r[0] == SPIKE1 for r in commits_a) and any(r[0] == SPIKE2 for r in commits_b)
    assert commits_a != commits_b
    # Identical seed + identical feedback -> identical decisions (determinism,
    # ruling out randomness):
    assert res_a2.submitted_ranking == res_a.submitted_ranking


# ---------------------------------------------------------------------------
# 5. no oracle in any agent-visible prompt/payload (both arms, real prompts)
# ---------------------------------------------------------------------------


def test_ceq_no_oracle_in_prompt(registry: PilotCaseRegistry, tmp_path: Path) -> None:
    de = DetelemArm(client=FakeLLMClient(_de_complete_script()), registry=registry,
                    opaque_id=OP1, out_dir=tmp_path / "de", seed=1)
    ceq = CEQTelemArm(client=FakeLLMClient(_ceq_complete_script()), registry=registry,
                      opaque_id=OP1, out_dir=tmp_path / "ceq", seed=1)
    r_de, r_ceq = de.run(), ceq.run()
    assert r_de.status == "completed" and r_ceq.status == "completed"

    # The oracle for this case is its UPSTREAM identity: the upstream id
    # re1ob_adservice_cpu_1 embeds the root-cause service (parts[1]) and the
    # defect class (parts[2]); the sealed label-column names are also forbidden.
    parts = UP1.split("_")
    assert len(parts) == 4, f"unexpected upstream id shape: {UP1!r}"
    forbidden = (
        UP1,               # upstream case id
        parts[1],          # root-cause service embedded in the upstream id
        parts[2],          # defect-class literal embedded in the upstream id
        *FORBIDDEN_LABEL_LITERALS,  # sealed label-column names
    )

    # Agent-visible surface: every real prompt of both arms (system + user,
    # including the C-EQ planner prompts and rendered observations) PLUS the
    # full, untruncated tool payloads of both arms' shared sandbox.
    texts = _agent_visible_texts(de) + _agent_visible_texts(ceq)
    for arm in (de, ceq):
        sb = TelemetrySandbox(arm._registry, OP1)
        texts += [
            json.dumps(sb.system_context()),
            json.dumps(sb.top_anomalies(k=20)),
            json.dumps(sb.service_metrics("svc00", k=30)),
            json.dumps(sb.service_logs("svc00", k=50)),
            json.dumps(sb.service_traces("svc00", k=30)),
        ]
    assert len(texts) > 20, "scan surface suspiciously small — harness path not exercised"

    hits: dict[str, int] = {}
    for text in texts:
        low = text.lower()
        for lit in forbidden:
            if lit in low:
                hits[lit] = hits.get(lit, 0) + 1
    assert not hits, f"oracle literal leaked into agent-visible text: {hits}"

    # Positive controls: the scan actually saw the serving surface, and the
    # ONLY case identifier agents see is the opaque id.
    joined = "\n".join(texts)
    assert OP1 in joined, "opaque case id never reached the agent — scan saw nothing real"
    assert "Planner round" in joined, "C-EQ planner prompt missing from the scan surface"


# ---------------------------------------------------------------------------
# 6. no central starvation: C-EQ reaches the same effective budget ceiling
# ---------------------------------------------------------------------------


def test_no_central_starvation(registry: PilotCaseRegistry, tmp_path: Path) -> None:
    big_usage = {"prompt_tokens": 60_000, "completion_tokens": 0}

    # (a) A scripted workload that exhausts the shared token budget: BOTH arms
    # abort at the SAME shared token ceiling — no arm-specific earlier cutoff.
    r_de = DetelemArm(
        client=FakeLLMClient(lambda _p, _i: (_tool("top_anomalies", k=20), big_usage)),
        registry=registry,
        opaque_id=OP1,
        out_dir=tmp_path / "de-starve",
        seed=1,
    ).run()

    def _ceq_starve(prompt: str, call_index: int) -> tuple[str, dict[str, int]]:
        if "Pre-outcome forecast" in prompt:
            return _commit(_ranking("svc00"), 0.5), big_usage
        return _tool("top_anomalies", k=20), big_usage

    r_ceq = CEQTelemArm(client=FakeLLMClient(_ceq_starve), registry=registry,
                        opaque_id=OP1, out_dir=tmp_path / "ceq-starve", seed=1).run()

    assert r_de.status == "aborted_budget" and r_ceq.status == "aborted_budget"
    assert r_de.tokens_total == r_ceq.tokens_total
    assert r_de.tokens_total > MAX_TOKENS_PER_RUN
    # The binding constraint was the shared TOKEN ceiling, not a per-arm tool cap:
    assert r_de.tool_calls < MAX_TOOL_CALLS and r_ceq.tool_calls < MAX_TOOL_CALLS

    # (b) The shared per-sandbox ceiling is reachable on BOTH arms' own sandboxes
    # (no hidden per-arm cap below it) — identical exhaustion, same as test 2.
    total_de = _hammer(DetelemArm, registry, tmp_path / "de-sb", "top_anomalies", {"k": 20})
    total_ceq = _hammer(CEQTelemArm, registry, tmp_path / "ceq-sb", "top_anomalies", {"k": 20})
    assert total_de == total_ceq and total_de[0] == MAX_TOOL_CALLS

    # (c) The enforced ceilings are the same shared constants on both arms.
    de = DetelemArm(client=FakeLLMClient([]), registry=registry, opaque_id=OP1, out_dir=tmp_path / "de-env")
    ceq = CEQTelemArm(client=FakeLLMClient([]), registry=registry, opaque_id=OP1, out_dir=tmp_path / "ceq-env")
    assert de.envelope == ceq.envelope
    assert de.envelope.max_tokens_per_run == MAX_TOKENS_PER_RUN
    assert de.envelope.wall_cap_s == WALL_CAP_S

    # (d) Full C-EQ run under a tool-hammering workload (never commits in the
    # planner loop): it is NOT cut off early by any budget — the manager's own
    # sandbox uses 12 of the shared 48 and the run finishes with no budget
    # failure (the only failure this synthetic workload may trigger is the F5
    # prompt-volume parity canary, which is calibrated for evidence-producing
    # workloads and is NOT a budget ceiling).
    def _ceq_hammer(prompt: str, call_index: int) -> str:
        if "Now commit your findings" in prompt:
            return _commit(_ranking("svc00"), 0.6)
        if "One-shot consultation" in prompt:
            return _tool("top_anomalies", k=20)
        if "Pre-outcome forecast (SEALED)" in prompt:
            return _commit(_ranking("svc00"), 0.5)
        if "Final commit" in prompt:
            return _commit(_ranking("svc00"), 0.9)
        return _tool("top_anomalies", k=20)

    arm = CEQTelemArm(client=FakeLLMClient(_ceq_hammer), registry=registry,
                      opaque_id=OP1, out_dir=tmp_path / "ceq-ham", seed=1)
    r = arm.run()
    assert r.status != "aborted_budget", f"C-EQ cut off by a budget: {r.crash_error!r}"
    # Manager sandbox: 12 OBS tool calls (4 rounds x 3) + 1 submit_diagnosis
    # (the commit is budget-counted like any call) = 13 << shared ceiling 48.
    mgr_log = arm.sandboxes[0].call_log
    assert len([c for c in mgr_log if c["tool"] != "submit_diagnosis"]) == 12
    assert [c for c in mgr_log if c["tool"] == "submit_diagnosis"]  # exactly the final commit
    assert len(mgr_log) == 13
    assert r.tool_calls == 16  # 12 manager OBS + 1 manager submit + 3 findings (1 each)
    assert all(len(sb.call_log) <= MAX_TOOL_CALLS for sb in arm.sandboxes)
    if r.status == "crashed":
        assert (r.crash_error or "").startswith("ValueError: prompt-volume"), \
            f"unexpected non-budget crash: {r.crash_error!r}"
