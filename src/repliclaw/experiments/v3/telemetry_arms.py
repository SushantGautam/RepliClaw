"""V3 telemetry-observational arms: D-E-TELEM and C-EQ-TELEM.

Implements ``docs/next_stage/design/v3_telemetry_arm_addendum.md`` §2/§4
(matched-ACCESS observational diagnostic agents) on top of the W3a
sandbox (``repliclaw.experiments/v3/telemetry.py``). Both arms are
LLM-driven via one shared JSON action protocol and one shared
:class:`TelemetrySandbox` interface, so parity holds by construction:

* identical tool set, identical per-query payloads (pure function of
  case + args — the sandbox guarantees byte-identity), identical
  per-sandbox tool budget (24), identical token envelope (60,000 per
  run), identical wall cap (900 s), identical opaque case id, identical
  model label (MODEL-SUBSTITUTION, SimulaChat default, Qwen3.8-27B).
* The ONE designed difference (disclosed per protocol S5): the
  coordination regime, plus the C-EQ volume-bounded union evidence view.

D-E-TELEM — decentralized committee of 3 investigators (fixed ids
``inv-a`` / ``inv-b`` / ``inv-c``, distinct stance prompts, seed-
stamped), each on its OWN sandbox with an independent budget:

* Phase 1: every investigator commits (escrows: sha256 + payload kept
  private) a ranked-5 diagnosis BEFORE any cross-sharing.
* Phase 2 (commit-reveal): one shared consultation round — each
  investigator sees the OTHER two's revealed rankings + confidences and
  may issue up to 4 more tool calls, then a final submission.
* Phase 3: deterministic committee ranking — per-service score is the
  sum of ``(6 - rank) * confidence`` over the investigators' final
  submissions (rank 1..5), ties broken alphabetically — submitted
  through the arm's own 4th (fresh, equal-access) sandbox.

C-EQ-TELEM — single adaptive central manager: a pre-loop sealed
forecast (``PredictionPacket``-style ``{predicted_root_service,
confidence}`` committed to escrow BEFORE any tool call), a planner loop
of up to 4 rounds over its own sandbox's union evidence view, a single
post-loop consultation of 3 fresh investigators (single prompt, no
tools beyond 3 calls each), and a final ranked-5 commit through its own
sandbox.

Prompt-volume parity hook: :func:`prompt_volume_ratio` mirrors the exact
ratio definition at ``experiments/v3/ceq.py:329`` (manager total prompt
tokens / (number of investigator prompts x mean investigator prompt
tokens)) with the [0.6, 1.25] canary band from ``ceq.py``.

Scientific rules honored here:

* NO ground truth anywhere in prompts or tools. This module never
  imports the scorer-only heldout ground-truth function; scoring is the
  scorer's job (``service_level_success`` on ``telemetry.py`` under
  ``ScorerContext``).
* No fixed script: which tools to call next is always an LLM action.
* No oracle: agents only ever see sandbox payloads.

LLM client: any OpenAI-compatible ``chat.completions``-style client
(:class:`ChatClientLike`). :func:`make_simula_client` builds the
env-only SimulaChat client (``SIMULACHAT_BASE_URL`` /
``SIMULACHAT_API_KEY`` / ``SIMULACHAT_MODEL``) from
``repliclaw.benchmarks.agentrx.simula`` (D-V3-010). :class:`FakeLLMClient`
is the offline scripted client for tests.
"""
from __future__ import annotations

import hashlib
import json
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Protocol, Sequence, runtime_checkable

from repliclaw.experiments.v3.telemetry import PilotCaseRegistry, TelemetrySandbox

# ---------------------------------------------------------------------------
# Frozen arm constants (addendum §2 / §6.2, ceq_arm_design §5)
# ---------------------------------------------------------------------------

#: Mandatory scientific label for any run through these arms (J-SCI rule).
MODEL_SUBSTITUTION_LABEL = "MODEL-SUBSTITUTION (SimulaChat default, Qwen3.8-27B)"

#: Per-run token envelope (addendum §6.2: unchanged from frozen spec §4).
MAX_TOKENS_PER_RUN = 60_000
#: Per-run wall cap in seconds (addendum §6.2).
WALL_CAP_S = 900.0
#: Prompt-volume band (copied from experiments/v3/ceq.py: PROMPT_VOLUME_FLOOR/CEIL).
PROMPT_VOLUME_FLOOR = 0.6
PROMPT_VOLUME_CEIL = 1.25

#: Fixed D-E investigator ids.
INVESTIGATOR_IDS: tuple[str, str, str] = ("inv-a", "inv-b", "inv-c")
#: C-EQ planner loop cap (ceq_arm_design: at most 4 planner rounds).
PLANNER_ROUNDS_MAX = 4
#: C-EQ post-loop investigator tool cap (addendum: no tools beyond 3 calls).
CEQ_INVESTIGATOR_TOOL_CAP = 3
#: D-E phase-2 additional tool-call cap per investigator (one consultation round).
DE_PHASE2_TOOL_CAP = 4
#: D-E committee (fresh sandbox) tool-call cap before unconditional submit.
DE_COMMITTEE_TOOL_CAP = 4
#: Diagnosis length: both arms commit a ranked-5 service list.
RANKING_LENGTH = 5

#: Shared OBS tool descriptions — embedded verbatim in every agent prompt so
#: both arms see byte-identical tool documentation.
TOOL_DOCS = """OBS tools (telemetry sandbox for this incident):
- system_context(): static per-case context — service inventory, per-service
  metric counts, time window, reported anomaly onset, logs/traces availability.
- top_anomalies(k=20): ranked (service, metric, score) anomaly list
  (shared reference math; the faulty window is [onset, onset+600s)).
- service_metrics(svc, k=30): per-metric fault-vs-normal window statistics
  for one service (svc: service name, k: int).
- service_logs(svc, k=50): up to k log lines around the reported anomaly
  onset for one service (may be unavailable).
- service_traces(svc, k=30): up to k span rows around onset for one service
  (may be unavailable).
Every tool call counts against a fixed per-agent budget; there is no other
data source. You never have access to ground truth."""

ACTION_PROTOCOL = """Action protocol — reply with EXACTLY ONE JSON object, nothing else:
  {"action": "tool_call", "tool": "<tool name>", "args": {...}}
to invoke one of the OBS tools, or, only when you are ready to commit:
  {"action": "commit", "ranking": ["svc1", "svc2", "svc3", "svc4", "svc5"],
   "confidence": <float between 0 and 1>}
The commit ranking is your ranked-5 root-cause diagnosis (rank 1 = most
likely root cause). Do not emit any text outside the single JSON object."""


class AgentProtocolError(RuntimeError):
    """The LLM produced malformed action output twice in a row."""


class _MalformedActionError(AgentProtocolError):
    """Internal: one malformed output (recoverable via the single retry)."""


class _BudgetAbort(Exception):
    """Internal: the per-run token envelope or wall cap was breached."""


# ---------------------------------------------------------------------------
# LLM client protocol + fake client
# ---------------------------------------------------------------------------


@runtime_checkable
class ChatCompletionsLike(Protocol):
    """Narrow OpenAI-compatible ``chat.completions`` surface."""

    def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        **kwargs: Any,
    ) -> Any: ...


@runtime_checkable
class ChatClientLike(Protocol):
    """Narrow OpenAI-compatible client surface (``client.chat``)."""

    chat: ChatCompletionsLike


def make_simula_client(model: str | None = None, timeout: float = 120.0) -> Any:
    """Build the env-only SimulaChat client (D-V3-010; no credentials in code).

    Lazily imports ``repliclaw.benchmarks.agentrx.simula`` so the arms import
    cleanly offline. Raises :class:`~...SimulaChatMissingEnvError` when the
    ``SIMULACHAT_*`` environment is incomplete.
    """
    from repliclaw.benchmarks.agentrx.simula import SimulaChatClient, load_config

    config = load_config(model=model)
    return SimulaChatClient(config=config, timeout=timeout)


class FakeLLMClient:
    """Scriptable offline client for tests (no network, deterministic).

    ``script`` is either a list of canned response strings (consumed in
    call order) or a callable ``(prompt, call_index) -> str`` (or a tuple
    ``(content, usage_override_dict)`` to override token usage, e.g. to
    trigger the per-run token-envelope abort).

    Records every prompt (the latest user turn) and response. Usage is
    reported as ``prompt_tokens = len(all message contents)//4`` and
    ``completion_tokens = len(content)//4`` unless overridden.
    """

    def __init__(self, script: Sequence[str] | Callable[..., Any]) -> None:
        self._script = script
        self.prompts: list[str] = []
        self.responses: list[str] = []
        # Annotated against the protocol so mypy checks conformance directly.
        self.chat: ChatCompletionsLike = self._Completions(self)

    def _next(self, prompt: str, call_index: int) -> tuple[str, dict[str, int] | None]:
        out = self._script(prompt, call_index) if callable(self._script) else self._script[call_index]
        if isinstance(out, tuple):
            return out[0], out[1]
        return out, None

    class _Completions:
        def __init__(self, client: "FakeLLMClient") -> None:
            self._client = client

        def create(self, *, model: str, messages: list[dict[str, str]], temperature: float = 0.0,
                   **_kwargs: Any) -> SimpleNamespace:
            client = self._client
            prompt = messages[-1]["content"]
            call_index = len(client.prompts)
            content, usage_override = client._next(prompt, call_index)
            client.prompts.append(prompt)
            client.responses.append(content)
            prompt_tokens = sum(len(m["content"]) for m in messages) // 4
            completion_tokens = len(content) // 4
            if usage_override is not None:
                prompt_tokens = int(usage_override.get("prompt_tokens", prompt_tokens))
                completion_tokens = int(usage_override.get("completion_tokens", completion_tokens))
            return SimpleNamespace(
                id=f"fake-{call_index}",
                model=model,
                choices=[SimpleNamespace(
                    message=SimpleNamespace(content=content, role="assistant"),
                    index=0,
                    finish_reason="stop",
                )],
                usage=SimpleNamespace(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
            )

# ---------------------------------------------------------------------------
# JSON action parsing + LLM tool session
# ---------------------------------------------------------------------------

_CORRECTION_PROMPT = (
    "Your last reply was not a single valid JSON action object. Reply again "
    "with EXACTLY ONE JSON object matching the action protocol — no prose, "
    "no markdown fences."
)


def _extract_json_object(text: str) -> dict[str, Any]:
    """Find the first JSON object in ``text`` (lenient: code fences, prose)."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    decoder = json.JSONDecoder()
    for i, ch in enumerate(stripped):
        if ch != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(stripped[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    raise _MalformedActionError(f"no JSON object found in response: {text[:200]!r}")


def parse_action(content: str) -> dict[str, Any]:
    """Parse + validate one model output into an action dict.

    Returns ``{"action": "tool_call", "tool": str, "args": dict}`` or
    ``{"action": "commit", "ranking": list[str] (len 5), "confidence": float
    in [0,1]}``. Raises :class:`AgentProtocolError` (via
    :class:`_MalformedActionError`) on anything else.
    """
    obj = _extract_json_object(content)
    action = obj.get("action")
    if action == "tool_call":
        tool = obj.get("tool")
        args = obj.get("args")
        if not isinstance(tool, str) or not isinstance(args, dict):
            raise _MalformedActionError(f"bad tool_call action: {obj!r}")
        return {"action": "tool_call", "tool": tool, "args": dict(args)}
    if action == "commit":
        ranking = obj.get("ranking")
        confidence = obj.get("confidence")
        if not isinstance(ranking, list) or len(ranking) != RANKING_LENGTH or not all(
            isinstance(s, str) for s in ranking
        ):
            raise _MalformedActionError(f"bad commit ranking: {obj!r}")
        if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            raise _MalformedActionError(f"bad commit confidence: {obj!r}")
        return {"action": "commit", "ranking": list(ranking), "confidence": float(confidence)}
    raise _MalformedActionError(f"unknown action: {obj!r}")


@dataclass
class _TokenRecord:
    prompt_tokens: int
    completion_tokens: int
    method: str  # "usage" | "length_estimate"

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMToolSession:
    """One agent conversation on the JSON action protocol.

    Every prompt and response is recorded in :attr:`transcript` (audit);
    token accounting uses the client's ``usage`` when present, otherwise a
    ``len//4`` length estimate — the method actually used is recorded per
    call. All records carry the model-substitution label (default
    :data:`MODEL_SUBSTITUTION_LABEL`).

    A malformed model output triggers exactly ONE retry with a correction
    prompt; a second malformed output raises :class:`AgentProtocolError`.
    """

    def __init__(
        self,
        client: ChatClientLike,
        system_prompt: str,
        agent_id: str,
        *,
        model_label: str | None = None,
        model: str = "default",
        temperature: float = 0.2,
    ) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self.agent_id = agent_id
        self.model_label = model_label if model_label is not None else MODEL_SUBSTITUTION_LABEL
        self.messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        self.transcript: list[dict[str, Any]] = []
        self.prompts: list[str] = []  # every user prompt sent (for the volume canary)
        self._tokens: list[_TokenRecord] = []

    # -- accounting ----------------------------------------------------------
    @property
    def prompt_tokens_total(self) -> int:
        return sum(t.prompt_tokens for t in self._tokens)

    @property
    def completion_tokens_total(self) -> int:
        return sum(t.completion_tokens for t in self._tokens)

    @property
    def tokens_total(self) -> int:
        return self.prompt_tokens_total + self.completion_tokens_total

    @property
    def llm_call_count(self) -> int:
        return len(self._tokens)

    def transcript_sha256(self) -> str:
        canonical = json.dumps(
            [{"agent": self.agent_id, "content": e["content"], "role": e["role"]}
             for e in self.transcript],
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # -- the one entry point ---------------------------------------------------
    def ask(self, user_prompt: str) -> dict[str, Any]:
        """Send one user prompt, retry once on malformed output, return the action."""
        prompt = user_prompt
        for attempt in (1, 2):
            self.messages.append({"role": "user", "content": prompt})
            self.prompts.append(prompt)
            self.transcript.append({"role": "prompt", "agent": self.agent_id, "content": prompt,
                                    "model_label": self.model_label, "ts": time.time()})
            response = self._client.chat.create(
                model=self._model, messages=list(self.messages), temperature=self._temperature
            )
            content: str = response.choices[0].message.content
            self.transcript.append({"role": "response", "agent": self.agent_id, "content": content,
                                    "model_label": self.model_label, "ts": time.time()})
            self._tokens.append(self._usage_tokens(response))
            try:
                return parse_action(content)
            except _MalformedActionError:
                if attempt == 2:
                    raise AgentProtocolError(
                        f"agent {self.agent_id!r}: two consecutive malformed action outputs"
                    ) from None
                prompt = _CORRECTION_PROMPT
        raise AssertionError("unreachable")

    def _usage_tokens(self, response: Any) -> _TokenRecord:
        usage = getattr(response, "usage", None)
        pt = getattr(usage, "prompt_tokens", None) if usage is not None else None
        ct = getattr(usage, "completion_tokens", None) if usage is not None else None
        if isinstance(pt, int) and isinstance(ct, int):
            return _TokenRecord(pt, ct, "usage")
        prompt_chars = sum(len(m["content"]) for m in self.messages)
        completion_chars = len(self.transcript[-1]["content"])
        return _TokenRecord(prompt_chars // 4, completion_chars // 4, "length_estimate")


# ---------------------------------------------------------------------------
# Prompt-volume parity hook (exact ratio definition: experiments/v3/ceq.py:329)
# ---------------------------------------------------------------------------


def _prompt_tokens(prompt: str) -> int:
    """Fake tokenization for the offline volume canary (len//4), R6-labeled."""
    return len(prompt) // 4


def prompt_volume_ratio(prompts_manager: Sequence[str],
                        prompts_investigator_pool: Sequence[str]) -> float:
    """F5 two-sided canary input: sum(fake prompt tokens) ratio C-EQ / D-E.

    Exact definition copied from ``experiments/v3/ceq.py:329``: manager
    total prompt tokens / (number of investigator prompts x mean
    investigator prompt tokens).
    """
    a = sum(_prompt_tokens(p) for p in prompts_manager)
    n = len(prompts_investigator_pool)
    if n == 0:
        raise ValueError("prompt_volume_ratio: empty investigator prompt pool")
    b = n * (sum(_prompt_tokens(p) for p in prompts_investigator_pool) / n)
    return a / b


def assert_volume_band(ratio: float) -> None:
    """Fail loud outside the [0.6, 1.25] prompt-volume canary band (ceq.py)."""
    if not (PROMPT_VOLUME_FLOOR <= ratio <= PROMPT_VOLUME_CEIL):
        raise ValueError(
            f"prompt-volume ratio {ratio:.4f} outside canary band "
            f"[{PROMPT_VOLUME_FLOOR}, {PROMPT_VOLUME_CEIL}]"
        )


# ---------------------------------------------------------------------------
# Escrow ledger (commit-reveal; mirrors eess_live/escrow.py semantics)
# ---------------------------------------------------------------------------


class ArmEscrow:
    """Minimal commit-reveal escrow for pre-outcome diagnosis commitments.

    A commit stores a sha256 over the canonical payload while keeping the
    payload private (``revealed=False``); :meth:`reveal_all` stamps the
    reveal timestamp only after every agent has committed. The ledger is
    persisted as JSON at :meth:`save`. ``clock`` is injectable for
    deterministic test ledgers.
    """

    def __init__(self, arm_label: str, opaque_case_id: str,
                 clock: Callable[[], float] | None = None) -> None:
        self.arm_label = arm_label
        self.opaque_case_id = opaque_case_id
        self._clock = clock if clock is not None else time.time
        self.entries: list[dict[str, Any]] = []

    @staticmethod
    def _canonical_payload(agent_id: str, phase: str, ranking: list[str], confidence: float) -> str:
        return json.dumps(
            {"agent_id": agent_id, "phase": phase, "ranking": ranking, "confidence": confidence},
            sort_keys=True,
            separators=(",", ":"),
        )

    def commit(self, agent_id: str, phase: str, ranking: list[str], confidence: float) -> dict[str, Any]:
        payload = self._canonical_payload(agent_id, phase, ranking, confidence)
        sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        entry = {
            "agent_id": agent_id,
            "phase": phase,
            "committed_at": self._clock(),
            "commit_sha256": sha,
            "ranking": list(ranking),
            "confidence": confidence,
            "revealed_at": None,
            "revealed": False,
        }
        self.entries.append(entry)
        return entry

    def reveal_all(self) -> None:
        """COMMIT -> REVEAL boundary: legal only after all agents committed."""
        now = self._clock()
        for entry in self.entries:
            entry["revealed_at"] = now
            entry["revealed"] = True

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            {"arm": self.arm_label, "opaque_case_id": self.opaque_case_id, "entries": self.entries},
            indent=2,
        ) + "\n", encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
# Run result + shared arm plumbing
# ---------------------------------------------------------------------------


@dataclass
class ArmRunResult:
    arm: str
    opaque_case_id: str
    submitted_ranking: list[str] | None
    success_eligible: bool
    tokens_total: int
    wall_s: float
    tool_calls: int
    llm_calls: int
    escrow_ledger_path: str | None
    prompt_volume_ratio: float | None
    protocol_errors: int
    status: str  # "completed" | "crashed" | "aborted_budget"


@dataclass
class _Envelope:
    max_tokens_per_run: int = MAX_TOKENS_PER_RUN
    wall_cap_s: float = WALL_CAP_S


_OBS_TOOLS = ("system_context", "top_anomalies", "service_metrics", "service_logs", "service_traces")


def _render_observations(observations: list[dict[str, Any]], limit_per_obs: int = 800) -> str:
    """Render an agent's union evidence view (its own sandbox calls only)."""
    if not observations:
        return "(no observations yet)"
    lines: list[str] = []
    for obs in observations:
        payload = json.dumps(obs["payload"], sort_keys=True)
        if len(payload) > limit_per_obs:
            payload = payload[:limit_per_obs] + " ...[truncated]"
        lines.append(f"- {obs['tool']}({json.dumps(obs['args'], sort_keys=True)}) -> {payload}")
    return "\n".join(lines)


class _ArmBase:
    """Shared plumbing: envelope enforcement, sandbox/tool execution, accounting."""

    arm_label: str = "ARM"

    def __init__(
        self,
        *,
        client: ChatClientLike,
        registry: PilotCaseRegistry,
        opaque_id: str,
        out_dir: str | Path,
        seed: int = 0,
        model_label: str | None = None,
        envelope: _Envelope | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._client = client
        self._registry = registry
        self._opaque_id = opaque_id
        self._out_dir = Path(out_dir)
        self._seed = int(seed)
        self._model_label = model_label if model_label is not None else MODEL_SUBSTITUTION_LABEL
        self.envelope = envelope if envelope is not None else _Envelope()
        self.sandboxes: list[TelemetrySandbox] = []
        self.sessions: list[LLMToolSession] = []
        self.protocol_errors = 0
        self._clock = clock if clock is not None else time.monotonic
        self._start = 0.0

    # -- lifecycle helpers -----------------------------------------------------
    def _new_sandbox(self) -> TelemetrySandbox:
        sandbox = TelemetrySandbox(self._registry, self._opaque_id)
        self.sandboxes.append(sandbox)
        return sandbox

    def _new_session(self, agent_id: str, system_prompt: str) -> LLMToolSession:
        session = LLMToolSession(
            self._client, system_prompt, agent_id, model_label=self._model_label
        )
        self.sessions.append(session)
        return session

    def _tokens_total(self) -> int:
        return sum(s.tokens_total for s in self.sessions)

    def _llm_calls(self) -> int:
        return sum(s.llm_call_count for s in self.sessions)

    def _tool_calls(self) -> int:
        return sum(len(sb.call_log) for sb in self.sandboxes)

    def _enforce_envelope(self) -> None:
        """Per-round envelope gate: wall cap + token budget (abort, no submit)."""
        if self._clock() - self._start > self.envelope.wall_cap_s:
            raise _BudgetAbort(f"wall cap {self.envelope.wall_cap_s}s exceeded")
        if self._tokens_total() > self.envelope.max_tokens_per_run:
            raise _BudgetAbort(
                f"token budget {self.envelope.max_tokens_per_run} exceeded "
                f"({self._tokens_total()} tokens)"
            )

    def _execute_tool(self, sandbox: TelemetrySandbox, action: dict[str, Any]) -> dict[str, Any]:
        """Execute one tool_call action on a sandbox; returns the observation."""
        tool = action["tool"]
        if tool not in _OBS_TOOLS:
            raise AgentProtocolError(f"unknown tool requested: {tool!r}")
        args = action["args"]
        if tool == "system_context":
            payload: Any = sandbox.system_context()
            log_args: dict[str, Any] = {}
        elif tool == "top_anomalies":
            payload = sandbox.top_anomalies(k=int(args.get("k", 20)))
            log_args = {"k": int(args.get("k", 20))}
        elif tool == "service_metrics":
            payload = sandbox.service_metrics(str(args.get("svc", "")), k=int(args.get("k", 30)))
            log_args = {"svc": str(args.get("svc", "")), "k": int(args.get("k", 30))}
        elif tool == "service_logs":
            payload = sandbox.service_logs(str(args.get("svc", "")), k=int(args.get("k", 50)))
            log_args = {"svc": str(args.get("svc", "")), "k": int(args.get("k", 50))}
        else:  # service_traces
            payload = sandbox.service_traces(str(args.get("svc", "")), k=int(args.get("k", 30)))
            log_args = {"svc": str(args.get("svc", "")), "k": int(args.get("k", 30))}
        return {"tool": tool, "args": log_args, "payload": payload}

    def _result(
        self,
        *,
        submitted_ranking: list[str] | None,
        status: str,
        escrow_ledger_path: str | None,
        prompt_volume_ratio: float | None,
    ) -> ArmRunResult:
        return ArmRunResult(
            arm=self.arm_label,
            opaque_case_id=self._opaque_id,
            submitted_ranking=submitted_ranking,
            success_eligible=submitted_ranking is not None,
            tokens_total=self._tokens_total(),
            wall_s=round(self._clock() - self._start, 3),
            tool_calls=self._tool_calls(),
            llm_calls=self._llm_calls(),
            escrow_ledger_path=escrow_ledger_path,
            prompt_volume_ratio=prompt_volume_ratio,
            protocol_errors=self.protocol_errors,
            status=status,
        )


# ---------------------------------------------------------------------------
# D-E-TELEM: decentralized committee with pre-outcome hypothesis escrow
# ---------------------------------------------------------------------------

_INVESTIGATOR_STANCES: dict[str, str] = {
    "inv-a": (
        "top-down: start from the aggregate anomaly scores and drill into the "
        "top-scoring services before considering anything else"
    ),
    "inv-b": (
        "log/trace forensics: prioritize log and trace evidence around the "
        "reported anomaly onset, and cross-check metric signals against it"
    ),
    "inv-c": (
        "differential exclusion: rule out services whose normal windows look "
        "clean, and rank the survivors by how strongly the evidence excludes "
        "the alternatives"
    ),
}


class DetelemArm(_ArmBase):
    """D-E-TELEM: 3 investigators, own sandboxes, escrow commit-reveal, committee."""

    arm_label = "D-E-TELEM"

    def _investigator_system_prompt(self, inv_id: str) -> str:
        stance = _INVESTIGATOR_STANCES[inv_id]
        return (
            f"You are investigator {inv_id} on a root-cause diagnosis task over one "
            f"incident's telemetry (opaque case {self._opaque_id}). You have NO access "
            f"to ground truth, and no other data source.\n"
            f"Assigned stance (deterministic, seed {self._seed}): {stance}.\n\n"
            f"{TOOL_DOCS}\n\n{ACTION_PROTOCOL}"
        )

    def run(self) -> ArmRunResult:
        self._start = self._clock()
        self._clock()  # advance so the first escrow commit is strictly after start
        escrow = ArmEscrow(self.arm_label, self._opaque_id, clock=self._clock)
        escrow_path = self._out_dir / f"{self.arm_label.lower()}-escrow.json"
        try:
            return self._run_inner(escrow)
        except _BudgetAbort:
            return self._result(submitted_ranking=None, status="aborted_budget",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None)
        except Exception as exc:  # noqa: BLE001 — crash is recorded, not raised
            if isinstance(exc, AgentProtocolError):
                self.protocol_errors += 1
            print(f"[{self.arm_label}] crashed: {exc}\n{traceback.format_exc()}", flush=True)
            return self._result(submitted_ranking=None, status="crashed",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None)

    def _run_inner(self, escrow: ArmEscrow) -> ArmRunResult:
        sandboxes = [self._new_sandbox() for _ in INVESTIGATOR_IDS]
        sessions = [self._new_session(inv, self._investigator_system_prompt(inv))
                    for inv in INVESTIGATOR_IDS]

        # ---- Phase 1: private investigation + escrow commit (no cross-sharing)
        phase1_prompt = (
            f"Begin your private investigation of opaque case {self._opaque_id}. "
            f"Issue tool calls to gather evidence. When (and only when) you are ready, "
            f"commit your ranked-5 diagnosis with a confidence. Your commit is ESCROWED: "
            f"it is hashed and sealed now, and revealed to the other investigators only "
            f"after everyone has committed. You will get one consultation round after "
            f"the reveal."
        )
        for inv, sandbox, session in zip(INVESTIGATOR_IDS, sandboxes, sessions):
            observations: list[dict[str, Any]] = []
            action = session.ask(phase1_prompt)
            while action["action"] == "tool_call":
                self._enforce_envelope()
                observations.append(self._execute_tool(sandbox, action))
                self._enforce_envelope()
                action = session.ask(self._continuation_prompt(observations, inv))
            escrow.commit(inv, "phase1", action["ranking"], action["confidence"])
        # COMMIT -> REVEAL boundary (only now that all three committed).
        escrow.reveal_all()

        # ---- Phase 2: one shared consultation round (see OTHER two only)
        for inv, sandbox, session in zip(INVESTIGATOR_IDS, sandboxes, sessions):
            others = [e for e in escrow.entries if e["agent_id"] != inv and e["phase"] == "phase1"]
            reveal_block = "\n".join(
                f"- {e['agent_id']}: ranking={e['ranking']} confidence={e['confidence']}"
                for e in others
            )
            prompt = (
                "Commit-reveal consultation round. The OTHER investigators have "
                "committed and revealed their escrowed phase-1 diagnoses (you never "
                "see your own reveal here):\n"
                f"{reveal_block}\n"
                "You may issue up to "
                f"{DE_PHASE2_TOOL_CAP} more tool calls on your own sandbox, then you "
                "MUST commit your FINAL ranked-5 diagnosis with a confidence. Your "
                "final submission is what the committee adjudication uses."
            )
            p2_observations: list[dict[str, Any]] = []
            tools_left = DE_PHASE2_TOOL_CAP
            action = session.ask(prompt)
            while action["action"] == "tool_call":
                if tools_left <= 0:
                    raise _BudgetAbort(f"{inv}: phase-2 tool cap ({DE_PHASE2_TOOL_CAP}) exceeded")
                tools_left -= 1
                self._enforce_envelope()
                p2_observations.append(self._execute_tool(sandbox, action))
                self._enforce_envelope()
                action = session.ask(self._continuation_prompt(p2_observations, inv))
            escrow.commit(inv, "phase2-final", action["ranking"], action["confidence"])

        # ---- Phase 3: deterministic committee ranking via a fresh 4th sandbox
        finals = {e["agent_id"]: e for e in escrow.entries if e["phase"] == "phase2-final"}
        scores: dict[str, float] = {}
        for agent_id in INVESTIGATOR_IDS:
            entry = finals[agent_id]
            for rank, svc in enumerate(entry["ranking"], start=1):
                # (5 - rank + 1) * confidence; rank is 1-based over the 5 slots.
                scores[svc] = scores.get(svc, 0.0) + (RANKING_LENGTH - rank + 1) * entry["confidence"]
        committee_ranking = sorted(scores, key=lambda s: (-scores[s], s))[:RANKING_LENGTH]

        committee_sandbox = self._new_sandbox()  # fresh: equal tool access (parity)
        committee_session = self._new_session(
            "committee",
            "You are the D-E adjudication committee over opaque case "
            f"{self._opaque_id}. The investigators' final escrowed submissions have "
            f"been adjudicated deterministically into a committee ranking (scores "
            f"below). You may inspect telemetry with the OBS tools before the arm "
            f"submits; you do NOT choose the ranking — reply with a commit action "
            f"when you are ready for submission.\n\n{TOOL_DOCS}\n\n"
            + ACTION_PROTOCOL,
        )
        score_block = "\n".join(f"- {s}: {v:.4f}" for s, v in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])))
        committee_observations: list[dict[str, Any]] = []
        action = committee_session.ask(
            "Adjudication table (sum of (6-rank)*confidence across investigators):\n"
            f"{score_block}\n\nCommittee ranking: {committee_ranking}. "
            "Inspect if useful, then commit."
        )
        tools_left = DE_COMMITTEE_TOOL_CAP
        while action["action"] == "tool_call":
            if tools_left <= 0:
                break  # unconditional submit below; sandbox budget also caps this
            tools_left -= 1
            self._enforce_envelope()
            committee_observations.append(self._execute_tool(committee_sandbox, action))
            self._enforce_envelope()
            action = committee_session.ask(self._continuation_prompt(committee_observations, "committee"))
        self._enforce_envelope()
        confirmed = committee_sandbox.submit_diagnosis(committee_ranking)

        escrow_path = self._out_dir / f"{self.arm_label.lower()}-escrow.json"
        result = self._result(
            submitted_ranking=confirmed["ranking"],
            status="completed",
            escrow_ledger_path=str(escrow.save(escrow_path)),
            prompt_volume_ratio=None,
        )
        return result

    def _continuation_prompt(self, observations: list[dict[str, Any]], inv: str) -> str:
        last = observations[-1]
        payload = json.dumps(last["payload"], sort_keys=True)
        if len(payload) > 800:
            payload = payload[:800] + " ...[truncated]"
        return (
            f"Observation for {inv} from {last['tool']}("
            f"{json.dumps(last['args'], sort_keys=True)}):\n{payload}\n"
            "Respond with your next action (one more tool call, or commit when ready)."
        )


# ---------------------------------------------------------------------------
# C-EQ-TELEM: single adaptive central manager
# ---------------------------------------------------------------------------


class CEQTelemArm(_ArmBase):
    """C-EQ-TELEM: sealed pre-loop forecast, <=4 planner rounds, findings once."""

    arm_label = "C-EQ-TELEM"

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
        self._clock()  # advance so the first escrow commit is strictly after start
        escrow = ArmEscrow(self.arm_label, self._opaque_id, clock=self._clock)
        manager_sandbox = self._new_sandbox()
        manager_session = self._new_session("manager", self._manager_system_prompt())
        escrow_path = self._out_dir / f"{self.arm_label.lower()}-escrow.json"
        try:
            return self._run_inner(escrow, manager_sandbox, manager_session)
        except _BudgetAbort:
            return self._result(submitted_ranking=None, status="aborted_budget",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None)
        except Exception as exc:  # noqa: BLE001 — crash is recorded, not raised
            if isinstance(exc, AgentProtocolError):
                self.protocol_errors += 1
            print(f"[{self.arm_label}] crashed: {exc}\n{traceback.format_exc()}", flush=True)
            return self._result(submitted_ranking=None, status="crashed",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None)

    def _run_inner(
        self,
        escrow: ArmEscrow,
        manager_sandbox: TelemetrySandbox,
        manager_session: LLMToolSession,
    ) -> ArmRunResult:
        # ---- Sealed forecast: committed to escrow BEFORE any tool call ----
        forecast_action = manager_session.ask(
            "Pre-outcome forecast (SEALED): before you issue ANY tool call, commit "
            "your current best ranked-5 hypothesis for the root-cause service with a "
            "confidence. Use only what you know now (no tool evidence yet). Reply "
            "with a commit action."
        )
        assert forecast_action["action"] == "commit"
        escrow.commit(
            "manager", "forecast", forecast_action["ranking"], forecast_action["confidence"]
        )
        forecast_line = (
            f"predicted_root_service={forecast_action['ranking'][0]} "
            f"confidence={forecast_action['confidence']} (sealed pre-outcome commit)"
        )

        # ---- Planner loop: up to 4 rounds over the union evidence view ----
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
                    break  # 1-3 tool calls per round; continue next round
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

        # ---- Post-loop: consult 3 fresh investigators ONCE each (no scripts) ----
        findings: list[dict[str, Any]] = []
        for inv in INVESTIGATOR_IDS:
            self._enforce_envelope()
            inv_sandbox = self._new_sandbox()
            inv_session = self._new_session(inv, self._investigator_system_prompt(inv))
            tools_left = CEQ_INVESTIGATOR_TOOL_CAP
            findings_payload = _render_observations(observations, limit_per_obs=600)
            action = inv_session.ask(
                "One-shot consultation: the manager's union evidence view is below. "
                f"You have at most {CEQ_INVESTIGATOR_TOOL_CAP} tool calls. Investigate "
                "briefly, then reply with a commit action (your ranked-5 findings + "
                "confidence) as your single finding for the manager.\n"
                f"Evidence view:\n{findings_payload}"
            )
            inv_observations: list[dict[str, Any]] = []
            while action["action"] == "tool_call":
                if tools_left <= 0:
                    raise _BudgetAbort(f"{inv}: findings tool cap ({CEQ_INVESTIGATOR_TOOL_CAP}) exceeded")
                tools_left -= 1
                self._enforce_envelope()
                last_action = action
                inv_observations.append(self._execute_tool(inv_sandbox, last_action))
                self._enforce_envelope()
                action = inv_session.ask(
                    f"Observation from {last_action['tool']}("
                    f"{json.dumps(last_action['args'], sort_keys=True)}):\n"
                    f"{_render_observations(inv_observations[-1:], limit_per_obs=600)}\n"
                    "Now commit your findings (commit action)."
                )
            findings.append({
                "agent_id": inv,
                "ranking": action["ranking"],
                "confidence": action["confidence"],
                "tool_calls": len(inv_observations),
            })
        findings_block = "\n".join(
            f"- {f['agent_id']}: ranking={f['ranking']} confidence={f['confidence']} "
            f"({f['tool_calls']} tool calls)"
            for f in findings
        )

        # ---- Final commit ----
        self._enforce_envelope()
        final_action = manager_session.ask(
            "Final commit. The planner loop is over"
            + (" (you already committed a ranking in-loop; you may keep or revise it)."
               if loop_committed is not None else ".")
            + f"\nSealed forecast line: {forecast_line}\n"
            f"Investigator findings (collected once, post-loop):\n{findings_block}\n"
            f"Union evidence view:\n{_render_observations(observations)}\n"
            f"Budget so far: {self._tokens_total()} tokens. Commit your final "
            "ranked-5 diagnosis with a confidence."
        )
        assert final_action["action"] == "commit"
        self._enforce_envelope()
        confirmed = manager_sandbox.submit_diagnosis(final_action["ranking"])
        escrow_path = self._out_dir / f"{self.arm_label.lower()}-escrow.json"
        ratio = prompt_volume_ratio(
            manager_session.prompts,
            [p for s in self.sessions if s.agent_id != "manager" for p in s.prompts],
        )
        assert_volume_band(ratio)
        return self._result(
            submitted_ranking=confirmed["ranking"],
            status="completed",
            escrow_ledger_path=str(escrow.save(escrow_path)),
            prompt_volume_ratio=ratio,
        )


__all__ = [
    "ACTION_PROTOCOL",
    "AgentProtocolError",
    "ArmEscrow",
    "ArmRunResult",
    "CEQ_INVESTIGATOR_TOOL_CAP",
    "CEQTelemArm",
    "ChatClientLike",
    "ChatCompletionsLike",
    "DE_COMMITTEE_TOOL_CAP",
    "DE_PHASE2_TOOL_CAP",
    "DetelemArm",
    "FakeLLMClient",
    "INVESTIGATOR_IDS",
    "LLMToolSession",
    "MAX_TOKENS_PER_RUN",
    "MODEL_SUBSTITUTION_LABEL",
    "PROMPT_VOLUME_CEIL",
    "PROMPT_VOLUME_FLOOR",
    "PLANNER_ROUNDS_MAX",
    "RANKING_LENGTH",
    "TOOL_DOCS",
    "WALL_CAP_S",
    "assert_volume_band",
    "make_simula_client",
    "parse_action",
    "prompt_volume_ratio",
]
