"""V3 telemetry-observational arms: D-E-TELEM and C-EQ-TELEM.

Implements ``docs/next_stage/design/v3_telemetry_arm_addendum.md`` §2/§4
(matched-ACCESS observational diagnostic agents) on top of the W3a
sandbox (``repliclaw.experiments/v3/telemetry.py``). Both arms are
LLM-driven via one shared JSON action protocol and one shared
:class:`TelemetrySandbox` interface, so parity holds by construction:

* identical tool set, identical per-query payloads (pure function of
  case + args — the sandbox guarantees byte-identity), identical
  per-sandbox tool budget (24), identical token envelope (90,000 per
  run, V3.1 AMEND_V3_1 A1 — shared constant for both arms), identical
  wall cap (900 s), identical opaque case id, identical
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

Mechanism v2 (lane-mechanism mechanism smoke, 2026-10-12 — EVOLVING
INSTRUMENT; NOT comparable to prior V3.2 rounds):

* D-E-TELEM investigators operate INDEPENDENTLY: the original phase-2
  cross-consultation (which shared the other investigators' inferences)
  is REMOVED. Investigators may share raw observational tool access only,
  never inferences. Each investigator gets a bounded number of tool/query
  turns (``DE_PHASE1_TOOL_CAP``, CLI-overridable) and MUST escrow a
  ranked candidate-cause packet (phase "phase1") BEFORE any reveal or
  synthesis. Synthesis is the deterministic committee ranking over the
  revealed escrowed packets, submitted through the arm's own fresh
  sandbox.
* BEST-EVIDENCE COMMIT rule (BOTH arms): when a budget is exhausted (tool
  cap, token envelope, or wall cap) the arm still commits a best-evidence
  ranking. A non-commit is a recorded FAILURE carrying
  ``ArmRunResult.abort_reason`` (``"non_commit:..."``) — it is never
  masked and never silently retry-stalled.
* C-EQ-TELEM stays STRONG (not crippled): identical tool set, identical
  per-run token envelope, and equivalent parallelism — the manager may
  issue a BATCH of up to ``CEQ_MANAGER_BATCH_MAX`` tool calls per turn
  (``{"action": "tool_calls", "tools": [...]}``).
* Commit VALIDATION (both arms, identical rule): a committed ranking that
  names a service not in the case's metric inventory (hallucinated name) is
  rejected with up to ``MAX_COMMIT_CORRECTIONS`` bounded correction asks
  (at most one tool call served per episode if the model asks for
  observable data such as the inventory); a non-commit / exhausted budget is
  a recorded non-commit failure (``abort_reason="non_commit:..."``).
  Service names are observable data (system_context) — no oracle content.
* Escrow packets are hashed with ``repliclaw.canonical`` (the escrow
  module's canonical form) and the COMMIT -> REVEAL boundary is gated by
  ``repliclaw.escrow.phase.PhaseGate`` (transitions persisted in the
  ledger JSON).

This remains ACCESS-MATCHED OBSERVATIONAL diagnosis: the sandbox exposes
observational queries only (no executable interventions). Label every
result with :data:`MECHANISM_LABEL`; never claim a causal-intervention
advantage from these runs.

Prompt-volume parity hook: :func:`prompt_volume_ratio` mirrors the exact
ratio definition at ``experiments/v3/ceq.py:329`` (manager total prompt
tokens / (number of investigator prompts x mean investigator prompt
tokens)) with the [0.6, 1.25] canary band from ``ceq.py``.

Scientific rules honored here:

* NO ground truth anywhere in prompts or tools. This module never
  imports the scorer-only heldout ground-truth function; scoring is the
  scorer's job (``service_level_success`` on ``telemetry.py``, applied by
  the scorer with its own resolve path).
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
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Protocol, Sequence, runtime_checkable

from repliclaw.canonical import canonical_json, sha256_hex
from repliclaw.escrow.phase import Phase, PhaseGate
from repliclaw.experiments.v3.telemetry import (
    PilotCaseRegistry,
    TelemetrySandbox,
    ToolBudgetExhausted,
    UnknownServiceError,
)

# ---------------------------------------------------------------------------
# Frozen arm constants (addendum §2 / §6.2, ceq_arm_design §5)
# ---------------------------------------------------------------------------

#: Mandatory scientific label for any run through these arms (J-SCI rule).
MODEL_SUBSTITUTION_LABEL = "MODEL-SUBSTITUTION (SimulaChat default, Qwen3.8-27B)"

#: Mandatory mechanism label for mechanism-v2 runs (observational diagnosis
#: only — the sandbox has no executable interventions).
MECHANISM_LABEL = (
    "ACCESS-MATCHED OBSERVATIONAL diagnosis (telemetry sandbox exposes "
    "observational queries only — NO executable interventions)"
)

#: Per-run token envelope (V3.2: AMEND_V3_2 item B1, approved D-V3-017 —
#: 90,000 -> 150,000, applied IDENTICALLY to BOTH arms via this shared
#: constant; evidence: R3 D-E budget aborts at 90,710–92,847 with 33 tool
#: calls — the token cap truncated mid-investigation, so 150K ≈ 61% headroom
#: over observed demand. V3.1 A1 (60K->90K) and A2 repeal history recorded
#: in D-V3-016 / v31_prereg_freeze.md.)
MAX_TOKENS_PER_RUN = 150_000
#: Per-run wall cap in seconds (addendum §6.2).
WALL_CAP_S = 900.0
#: Prompt-volume band (V3.2: AMEND_V3_2 item B3, approved D-V3-017 —
#: ceil 1.25 -> 1.40 with the MEASURED evidence distribution: completed runs
#: 1.2245–1.2352; RCA-P-03 1.2843–1.2895 (both 60K/90K, both models);
#: RCA-P-02 1.3476 (90K, both seeds, deterministic). Floor 0.6 and
#: crash-on-violation UNCHANGED; the guard stays live above the observed
#: deterministic exceedances. N1 calibration disclosure per science-judge.)
PROMPT_VOLUME_FLOOR = 0.6
PROMPT_VOLUME_CEIL = 1.40

#: Fixed D-E investigator ids.
INVESTIGATOR_IDS: tuple[str, str, str] = ("inv-a", "inv-b", "inv-c")
#: C-EQ planner loop cap (ceq_arm_design: at most 4 planner rounds).
PLANNER_ROUNDS_MAX = 4
#: C-EQ post-loop investigator tool cap (addendum: no tools beyond 3 calls).
CEQ_INVESTIGATOR_TOOL_CAP = 3
#: D-E phase-2 additional tool-call cap per investigator (one consultation round).
#: RETAINED for API backward compatibility; the mechanism-v2 D-E arm has no
#: consultation round (investigators are independent) — use DE_PHASE1_TOOL_CAP.
DE_PHASE2_TOOL_CAP = 4
#: D-E mechanism v2: bounded tool/query turns per investigator (phase 1).
#: Small by design; CLI-overridable (mechanism smoke runner ``--de-tool-cap``).
DE_PHASE1_TOOL_CAP = 6
#: C-EQ mechanism v2: max tool calls per manager turn (equivalent parallelism;
#: the batch is executed as one agent turn on the manager's sandbox).
CEQ_MANAGER_BATCH_MAX = 3
#: Commit-validation corrections: max bounded correction asks per invalid
#: commit (and at most one tool call served per episode, if the model asks for
#: observable data such as the service inventory). Identical for both arms.
MAX_COMMIT_CORRECTIONS = 2

#: Context-compaction constants (W3g harness-side fix — addendum §6.3).
#: The provider send-view keeps the system prompt + first user instruction and the
#: most recent ``_COMPACTION_RECENT_KEEP`` messages verbatim; older *user* messages
#: (tool observations, which are idempotent and re-fetchable) are replaced by a
#: short stub. Model responses are NEVER compacted. This does not change information
#: access (any compacted observation can be re-requested as a tool call) and does not
#: touch the audit transcript, the prompt-volume canary, or the 90,000 envelope.
_COMPACTION_RECENT_KEEP = 6
_COMPACTION_STUB_CHARS = 120
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

#: C-EQ-only batch extension (disclosed in the C-EQ manager prompt; D-E
#: investigators never see it, so their action space stays single-call).
BATCH_ACTION_PROTOCOL = """C-EQ batch extension — you may instead issue up to
  {batch_max} tool calls as ONE batch in a single turn:
  {{"action": "tool_calls", "tools": [{{"tool": "<tool name>", "args": {{...}}}}, ...]}}
Batched calls are executed as one equivalent-parallel batch against your
sandbox (each call still counts against the shared per-sandbox budgets)."""


class AgentProtocolError(RuntimeError):
    """The LLM produced malformed action output twice in a row."""


class _MalformedActionError(AgentProtocolError):
    """Internal: one malformed output (recoverable via the single retry)."""


class _BudgetAbort(Exception):
    """Internal: the per-run token envelope or wall cap was breached."""


class _NonCommitError(Exception):
    """Internal: an agent refused/failed to commit its best-evidence ranking
    after the bounded forced-commit asks. Recorded as a FAILURE with
    ``abort_reason="non_commit:..."`` (never masked, never retry-stalled)."""


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

    Returns ``{"action": "tool_call", "tool": str, "args": dict}``,
    ``{"action": "tool_calls", "tools": [ {tool, args}, ... ]}`` (C-EQ batch,
    1..``CEQ_MANAGER_BATCH_MAX`` entries), or
    ``{"action": "commit", "ranking": list[str] (len 5), "confidence": float
    in [0,1]}``. Raises :class:`AgentProtocolError` (via
    :class:`_MalformedActionError`) on anything else.
    """
    obj = _extract_json_object(content)
    action = obj.get("action")
    if action == "tool_calls":
        tools = obj.get("tools")
        if (
            not isinstance(tools, list)
            or not tools
            or len(tools) > CEQ_MANAGER_BATCH_MAX
            or not all(isinstance(t, dict) and isinstance(t.get("tool"), str) for t in tools)
            or any(
                t.get("args") is not None and not isinstance(t.get("args"), dict) for t in tools
            )
        ):
            raise _MalformedActionError(f"bad tool_calls batch: {obj!r}")
        return {
            "action": "tool_calls",
            "tools": [
                {"tool": t["tool"], "args": dict(t["args"]) if t.get("args") is not None else {}}
                for t in tools
            ],
        }
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
        self._prev_sent_prompt_chars = 0  # chars of the SENT (compacted) view at the previous call
        self.backend_model: str | None = None  # AMEND_V3_1 A4: first-call gateway echo

    def record_backend_model(self, response: Any) -> None:
        """AMEND_V3_1 A4: capture the gateway-echoed model id on the first LLM
        response (pure provenance — no behavioral effect)."""
        if self.backend_model is None:
            echoed = getattr(response, "model", None)
            if isinstance(echoed, str) and echoed:
                self.backend_model = echoed

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
        """Send one user prompt, retry once on malformed output, return the action.

        On a second consecutive malformed output the session performs ONE bounded
        recovery re-ask before failing loudly, so a transient double-malformed
        burst does not crash an otherwise-valid investigation.
        """
        prompt = user_prompt
        malformed_count = 0
        max_attempts = 3  # initial + one correction retry + one recovery retry
        while True:
            self.messages.append({"role": "user", "content": prompt})
            self.prompts.append(prompt)
            self.transcript.append({"role": "prompt", "agent": self.agent_id, "content": prompt,
                                    "model_label": self.model_label, "ts": time.time()})
            # Compaction (W3g): the provider sees a compacted send-view; the audit
            # transcript and the volume-canary prompt list above keep the FULL text.
            sent = self._compacted_view()
            response = self._client.chat.create(
                model=self._model, messages=sent, temperature=self._temperature
            )
            content: str = response.choices[0].message.content
            self.transcript.append({"role": "response", "agent": self.agent_id, "content": content,
                                    "model_label": self.model_label, "ts": time.time()})
            self.record_backend_model(response)
            self._tokens.append(self._usage_tokens(response))
            try:
                return parse_action(content)
            except _MalformedActionError:
                malformed_count += 1
                if malformed_count >= max_attempts:
                    raise AgentProtocolError(
                        f"agent {self.agent_id!r}: repeated malformed action outputs"
                    ) from None
                prompt = _CORRECTION_PROMPT

    def _compacted_view(self) -> list[dict[str, str]]:
        """Provider send-view: system prompt + first user instruction + the most
        recent ``_COMPACTION_RECENT_KEEP`` messages verbatim; older *user* messages
        (tool observations — idempotent, re-fetchable via a tool call) become a
        short stub. Model responses and the first instruction are never compacted.

        This is a cost-reduction measure on full-history re-prompting (W3g); it does
        not alter the information the agent can access, the audit transcript, the
        prompt-volume canary, or the frozen token envelope.
        """
        msgs = self.messages
        # The first user message is the phase instruction — never stubbed.
        first_user_idx = next(
            (i for i, m in enumerate(msgs) if m["role"] == "user"), None
        )
        compact_from = len(msgs) - _COMPACTION_RECENT_KEEP
        out: list[dict[str, str]] = []
        for i, m in enumerate(msgs):
            if m["role"] == "system":
                out.append(m)
                continue
            stubbable = (
                m["role"] == "user"
                and (first_user_idx is None or i > first_user_idx)
                and i < compact_from
                and len(m["content"]) > _COMPACTION_STUB_CHARS
            )
            if stubbable:
                stub = (m["content"][:_COMPACTION_STUB_CHARS]
                        + " … [older tool observation compacted; re-issue the tool "
                          "call to retrieve the full data]")
                out.append({"role": "user", "content": stub})
            else:
                out.append(m)
        return out

    def _usage_tokens(self, response: Any) -> _TokenRecord:
        usage = getattr(response, "usage", None)
        pt = getattr(usage, "prompt_tokens", None) if usage is not None else None
        ct = getattr(usage, "completion_tokens", None) if usage is not None else None
        if isinstance(pt, int) and isinstance(ct, int):
            return _TokenRecord(pt, ct, "usage")
        # Estimate: count only the MARGINAL prompt chars of the SENT (compacted)
        # view added since the previous call — consistent with what the provider
        # actually re-receives each turn (W3g).
        sent = self._compacted_view()
        sent_chars = sum(len(m["content"]) for m in sent)
        prompt_chars = max(0, sent_chars - self._prev_sent_prompt_chars)
        self._prev_sent_prompt_chars = sent_chars
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

    A commit stores a sha256 over the canonical payload (``repliclaw.canonical``
    — the escrow module's canonical form) while keeping the payload private
    (``revealed=False``); :meth:`reveal_all` stamps the reveal timestamp only
    after every agent has committed. The COMMIT -> REVEAL boundary is gated by
    a ``repliclaw.escrow.phase.PhaseGate`` and every transition is recorded in
    :attr:`phase_transitions`. The ledger is persisted as JSON at
    :meth:`save`. ``clock`` is injectable for deterministic test ledgers.
    """

    def __init__(self, arm_label: str, opaque_case_id: str,
                 clock: Callable[[], float] | None = None) -> None:
        self.arm_label = arm_label
        self.opaque_case_id = opaque_case_id
        self._clock = clock if clock is not None else time.time
        self.entries: list[dict[str, Any]] = []
        self.gate = PhaseGate()
        self.phase_transitions: list[dict[str, Any]] = [
            {"phase": Phase.COMMIT.name, "at": None, "note": "gate initialized"}
        ]

    @staticmethod
    def _canonical_payload(agent_id: str, phase: str, ranking: list[str], confidence: float) -> str:
        return canonical_json(
            {"agent_id": agent_id, "phase": phase, "ranking": ranking, "confidence": confidence}
        )

    def commit(self, agent_id: str, phase: str, ranking: list[str], confidence: float) -> dict[str, Any]:
        # Service-validity (ranking must cover the case's metric inventory) is
        # NOT checked here — escrow has no sandbox reference; validation
        # happens at the final TelemetrySandbox.submit_diagnosis.
        self.gate.assert_can(agent_id, "commit")
        payload = self._canonical_payload(agent_id, phase, ranking, confidence)
        sha = sha256_hex(payload)
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
        """COMMIT -> REVEAL boundary: legal only after all agents committed
        (PhaseGate: one forward transition, recorded in the ledger)."""
        if self.gate.phase is not Phase.COMMIT:
            raise RuntimeError("ArmEscrow.reveal_all: reveal boundary already passed")
        now = self._clock()
        self.gate.advance()  # COMMIT -> REVEAL
        self.gate.assert_can("gate", "reveal")
        self.phase_transitions.append(
            {"from": Phase.COMMIT.name, "to": Phase.REVEAL.name, "at": now}
        )
        for entry in self.entries:
            entry["revealed_at"] = now
            entry["revealed"] = True

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(
            {"arm": self.arm_label, "opaque_case_id": self.opaque_case_id,
             "entries": self.entries, "phase_transitions": self.phase_transitions},
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
    crash_error: str | None = None  # type + text of the crashing exception (cause attribution)
    #: Transparent failure attribution (mechanism v2): "budget_exhausted:..."
    #: when the best-evidence commit path fired, "non_commit:..." when an
    #: agent failed to commit after the bounded forced-commit asks.
    abort_reason: str | None = None
    backend_models: tuple[str | None, ...] = ()  # AMEND_V3_1 A4: per-agent gateway echoes
    warnings: tuple[str, ...] = ()  # non-fatal disclosures (e.g. prompt-volume band breach)


@dataclass
class _Envelope:
    max_tokens_per_run: int | None = None
    wall_cap_s: float = WALL_CAP_S

    def __post_init__(self) -> None:
        # Default lazily from the shared module constant (V3.1, AMEND_V3_1 A1):
        # the per-run envelope must apply IDENTICALLY to both arms, so the
        # default is read at construction time, and any explicit value above
        # the shared constant is rejected (asymmetry guard, D-V3-016).
        if self.max_tokens_per_run is None:
            self.max_tokens_per_run = MAX_TOKENS_PER_RUN
        if self.max_tokens_per_run > MAX_TOKENS_PER_RUN:
            raise ValueError(
                f"envelope max_tokens_per_run {self.max_tokens_per_run} exceeds "
                f"the shared envelope {MAX_TOKENS_PER_RUN} (A1 parity guard)"
            )


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
        verbose_crash: bool = True,
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
        self._crash_error: str | None = None
        self._clock = clock if clock is not None else time.monotonic
        self._start = 0.0
        self.verbose_crash = verbose_crash

    # -- lifecycle helpers -----------------------------------------------------
    def _record_crash(self, exc: Exception) -> None:
        """Log an arm crash to stderr; demote to a one-liner when the crash
        is expected (canary label-gate) via ``verbose_crash=False``."""
        self._crash_error = f"{type(exc).__name__}: {exc}"
        if self.verbose_crash:
            print(f"[{self.arm_label}] crashed: {exc}\n{traceback.format_exc()}",
                  file=sys.stderr, flush=True)
        else:
            print(f"[{self.arm_label}] expected crash (label gate): {exc}",
                  file=sys.stderr, flush=True)
        if isinstance(exc, AgentProtocolError):
            self.protocol_errors += 1
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
        assert self.envelope.max_tokens_per_run is not None  # normalized in __post_init__
        if self._tokens_total() > self.envelope.max_tokens_per_run:
            raise _BudgetAbort(
                f"token budget {self.envelope.max_tokens_per_run} exceeded "
                f"({self._tokens_total()} tokens)"
            )

    def _commit_or_correct(
        self, session: LLMToolSession, agent_id: str, sandbox: TelemetrySandbox,
        action: dict[str, Any], context: str,
    ) -> dict[str, Any]:
        """Validate a committed ranking against the case's service inventory.

        An unknown service (hallucinated name) is a NORMAL protocol failure,
        not an arm crash: up to ``MAX_COMMIT_CORRECTIONS`` bounded correction
        asks (the valid service names are observable data — no oracle
        content). If a correction ask is answered with a tool call, that ONE
        tool call is served (e.g. the model fetching the inventory via
        ``system_context``) and it is asked to commit again. A non-commit or
        an exhausted correction budget raises :class:`_NonCommitError` — a
        recorded failure (never masked, never a silent stall). Identical
        rule for both arms.
        """
        current = action
        attempts = 0
        tools_served = 0
        while True:
            try:
                sandbox.validate_ranking(current["ranking"])
                return current
            except UnknownServiceError as exc:
                if attempts >= MAX_COMMIT_CORRECTIONS:
                    raise _NonCommitError(
                        f"{agent_id}: re-commit still invalid after "
                        f"{MAX_COMMIT_CORRECTIONS} corrections ({exc})"
                    ) from None
                attempts += 1
                reply = session.ask(
                    f"{context}: your commit was REJECTED — {exc}. Commit again "
                    "with a ranked-5 list using ONLY service names that "
                    "actually appear in the case's telemetry (see "
                    "system_context and the other tool outputs); do not "
                    "invent service names. If you are unsure of the service "
                    "names, request the system_context tool."
                )
                if reply["action"] == "tool_call" and tools_served == 0:
                    obs = self._execute_tool(sandbox, reply)
                    tools_served += 1
                    payload = json.dumps(obs["payload"], sort_keys=True)
                    if len(payload) > 800:
                        payload = payload[:800] + " ...[truncated]"
                    follow = session.ask(
                        f"Observation from {obs['tool']}("
                        f"{json.dumps(obs['args'], sort_keys=True)}):\n{payload}\n"
                        "Now commit again (commit action ONLY): ranked-5 list "
                        "using only the actual service names."
                    )
                    if follow["action"] != "commit":
                        raise _NonCommitError(
                            f"{agent_id}: no re-commit after inventory correction"
                        ) from None
                    current = follow
                    continue
                if reply["action"] != "commit":
                    raise _NonCommitError(
                        f"{agent_id}: no re-commit after inventory correction"
                    ) from None
                current = reply

    def _execute_tools(
        self, sandbox: TelemetrySandbox, actions: Sequence[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Execute a batch of tool_call actions on one sandbox in ONE agent
        turn (C-EQ equivalent parallelism). Sandbox calls stay sequential
        and each still counts against the shared per-sandbox budgets."""
        return [self._execute_tool(sandbox, a) for a in actions]

    def _forced_commit(self, session: LLMToolSession, agent_id: str, context: str) -> dict[str, Any]:
        """BEST-EVIDENCE COMMIT: bounded final asks to commit (no further
        tool calls allowed). A non-commit raises :class:`_NonCommitError` —
        the caller records it as a failure with an abort_reason."""
        action = session.ask(
            f"BEST-EVIDENCE COMMIT ({context}): your investigation budget is "
            "exhausted and no further tool calls are allowed. You MUST commit "
            "now: reply with a commit action containing your current "
            "best-evidence ranked-5 diagnosis and a confidence (lower the "
            "confidence if your evidence is thin)."
        )
        if action["action"] != "commit":
            action = session.ask(
                "No further tool calls are possible. Reply NOW with a commit "
                "action ONLY: your best-evidence ranked-5 ranking + confidence."
            )
        if action["action"] != "commit":
            raise _NonCommitError(
                f"{agent_id}: no best-evidence commit after budget exhaustion"
            )
        return action

    def _execute_tool(self, sandbox: TelemetrySandbox, action: dict[str, Any]) -> dict[str, Any]:
        """Execute one tool_call action on a sandbox; returns the observation.

        A per-tool or total budget cap (``ToolBudgetExhausted``) is a NORMAL
        end-of-evidence condition for an agent, not an arm fault: it is returned
        as a ``budget_exhausted`` observation so the agent can still commit its
        diagnosis instead of the whole arm crashing (parity-preserving — the
        shared caps are unchanged, both arms get identical treatment).
        """
        tool = action["tool"]
        if tool not in _OBS_TOOLS:
            raise AgentProtocolError(f"unknown tool requested: {tool!r}")
        args = action["args"]
        try:
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
        except ToolBudgetExhausted as exc:
            return {"tool": tool, "args": args,
                    "payload": {"error": "budget_exhausted", "detail": str(exc)}}
        return {"tool": tool, "args": log_args, "payload": payload}

    def _result(
        self,
        *,
        submitted_ranking: list[str] | None,
        status: str,
        escrow_ledger_path: str | None,
        prompt_volume_ratio: float | None,
        warnings: Sequence[str] = (),
        abort_reason: str | None = None,
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
            crash_error=self._crash_error if status == "crashed" else None,
            backend_models=tuple(s.backend_model for s in self.sessions),
            warnings=tuple(warnings),
            abort_reason=abort_reason,
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
    """D-E-TELEM (mechanism v2): 3 INDEPENDENT investigators (own sandboxes,
    bounded tool/query turns, no shared reasoning channel), pre-outcome
    escrow commit BEFORE any reveal, then deterministic synthesis over the
    revealed packets via the arm's own fresh sandbox.

    BEST-EVIDENCE COMMIT: if a budget (tool cap / token envelope / wall cap)
    is exhausted, the arm still commits a best-evidence ranking; a non-commit
    is a recorded failure carrying ``abort_reason``.
    """

    arm_label = "D-E-TELEM"

    def __init__(self, *, phase1_tool_cap: int = DE_PHASE1_TOOL_CAP, **kwargs: Any) -> None:
        if phase1_tool_cap < 1:
            raise ValueError("phase1_tool_cap must be >= 1")
        super().__init__(**kwargs)
        self._phase1_tool_cap = int(phase1_tool_cap)

    def _investigator_system_prompt(self, inv_id: str) -> str:
        stance = _INVESTIGATOR_STANCES[inv_id]
        return (
            f"You are investigator {inv_id} on a root-cause diagnosis task over one "
            f"incident's telemetry (opaque case {self._opaque_id}). You work "
            f"INDEPENDENTLY: no other investigator shares inferences with you, and "
            f"you will share nothing but your escrowed packet. You have NO access "
            f"to ground truth, and no other data source. You have at most "
            f"{self._phase1_tool_cap} tool calls; when your tool budget is exhausted "
            f"you must commit your best-evidence ranking.\n"
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
        except _BudgetAbort as exc:
            # Normal path only: the budget broke before the best-evidence
            # commit path could produce a ranking (e.g. during synthesis).
            return self._result(submitted_ranking=None, status="aborted_budget",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None,
                                abort_reason=f"budget_exhausted:{exc}")
        except _NonCommitError as exc:
            self._record_crash(exc)
            return self._result(submitted_ranking=None, status="aborted_budget",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None,
                                abort_reason=f"non_commit:{exc}")
        except Exception as exc:  # noqa: BLE001 — crash is recorded, not raised
            self._record_crash(exc)
            return self._result(submitted_ranking=None, status="crashed",
                                escrow_ledger_path=str(escrow.save(escrow_path)),
                                prompt_volume_ratio=None)

    def _run_inner(self, escrow: ArmEscrow) -> ArmRunResult:
        sandboxes = [self._new_sandbox() for _ in INVESTIGATOR_IDS]
        sessions = [self._new_session(inv, self._investigator_system_prompt(inv))
                    for inv in INVESTIGATOR_IDS]

        # ---- Phase 1: independent investigation + escrow commit (NO cross-sharing)
        phase1_prompt = (
            f"Begin your private, independent investigation of opaque case "
            f"{self._opaque_id}. You have at most {self._phase1_tool_cap} tool "
            f"calls. Issue tool calls to gather evidence. When (and only when) you "
            f"are ready — or as soon as your tool budget runs out — commit your "
            f"best-evidence ranked-5 diagnosis with a confidence. Your commit is "
            f"ESCROWED: it is hashed and sealed now, and revealed for the "
            f"deterministic committee synthesis only AFTER every investigator has "
            f"committed. You see no other investigator's inferences."
        )
        committed: set[str] = set()
        abort_reason: str | None = None
        try:
            for inv, sandbox, session in zip(INVESTIGATOR_IDS, sandboxes, sessions):
                self._enforce_envelope()
                action = session.ask(phase1_prompt)
                observations: list[dict[str, Any]] = []
                tools_left = self._phase1_tool_cap
                while action["action"] == "tool_call":
                    if tools_left <= 0:
                        break  # tool budget exhausted -> forced best-evidence commit
                    tools_left -= 1
                    self._enforce_envelope()
                    observations.append(self._execute_tool(sandbox, action))
                    self._enforce_envelope()
                    action = session.ask(self._continuation_prompt(observations, inv))
                if action["action"] == "commit":
                    commit_action = action
                else:
                    commit_action = self._forced_commit(
                        session, inv,
                        f"tool budget cap ({self._phase1_tool_cap}) reached",
                    )
                commit_action = self._commit_or_correct(
                    session, inv, sandbox, commit_action,
                    f"investigator {inv} phase-1 escrow commit",
                )
                escrow.commit(inv, "phase1", commit_action["ranking"],
                              commit_action["confidence"])
                committed.add(inv)
        except _BudgetAbort as exc:
            # BEST-EVIDENCE COMMIT rule: the run budget (token envelope or
            # wall cap) broke mid-investigation — every investigator still
            # commits its best-evidence packet before the reveal boundary.
            abort_reason = f"budget_exhausted:{exc}"
            for inv, sandbox, session in zip(INVESTIGATOR_IDS, sandboxes, sessions):
                if inv in committed:
                    continue
                commit_action = self._forced_commit(session, inv, abort_reason)
                commit_action = self._commit_or_correct(
                    session, inv, sandbox, commit_action,
                    f"investigator {inv} best-evidence commit",
                )
                escrow.commit(inv, "phase1", commit_action["ranking"],
                              commit_action["confidence"])
                committed.add(inv)
        # COMMIT -> REVEAL boundary (only now that all three committed).
        escrow.reveal_all()
        return self._synthesize_and_submit(escrow, abort_reason=abort_reason)

    def _synthesize_and_submit(self, escrow: ArmEscrow,
                               *, abort_reason: str | None = None) -> ArmRunResult:
        """Deterministic synthesis over the REVEALED escrowed packets, submitted
        through the arm's own fresh 4th (equal-access) sandbox. In the
        best-evidence commit path (``abort_reason`` set) the per-round envelope
        gate is skipped so the arm can still finish; the extra spend is
        recorded transparently on the result."""
        phase1 = {e["agent_id"]: e for e in escrow.entries if e["phase"] == "phase1"}
        scores: dict[str, float] = {}
        for agent_id in INVESTIGATOR_IDS:
            entry = phase1[agent_id]
            for rank, svc in enumerate(entry["ranking"], start=1):
                # (5 - rank + 1) * confidence; rank is 1-based over the 5 slots.
                scores[svc] = scores.get(svc, 0.0) + (RANKING_LENGTH - rank + 1) * entry["confidence"]
        committee_ranking = sorted(scores, key=lambda s: (-scores[s], s))[:RANKING_LENGTH]

        def _gate() -> None:
            if abort_reason is None:
                self._enforce_envelope()

        committee_sandbox = self._new_sandbox()  # fresh: equal tool access (parity)
        committee_session = self._new_session(
            "committee",
            "You are the D-E adjudication committee over opaque case "
            f"{self._opaque_id}. The investigators' escrowed packets have been "
            f"revealed and adjudicated deterministically into a committee "
            f"ranking (scores below). You may inspect telemetry with the OBS "
            f"tools before the arm submits; you do NOT choose the ranking — "
            f"reply with a commit action when you are ready for submission.\n\n"
            f"{TOOL_DOCS}\n\n" + ACTION_PROTOCOL,
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
            _gate()
            committee_observations.append(self._execute_tool(committee_sandbox, action))
            _gate()
            action = committee_session.ask(self._continuation_prompt(committee_observations, "committee"))
        _gate()
        confirmed = committee_sandbox.submit_diagnosis(committee_ranking)

        escrow_path = self._out_dir / f"{self.arm_label.lower()}-escrow.json"
        warnings = (f"best-evidence commit path used: {abort_reason}",) if abort_reason else ()
        return self._result(
            submitted_ranking=confirmed["ranking"],
            status="completed",
            escrow_ledger_path=str(escrow.save(escrow_path)),
            prompt_volume_ratio=None,
            warnings=warnings,
            abort_reason=abort_reason,
        )

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
    """C-EQ-TELEM (mechanism v2): sealed pre-loop forecast, <=4 planner rounds
    with EQUIVALENT PARALLELISM (the manager may batch up to
    ``CEQ_MANAGER_BATCH_MAX`` tool calls per turn), findings once, final
    commit — with the same best-evidence commit rule as D-E."""

    arm_label = "C-EQ-TELEM"

    def __init__(self, *, batch_max: int = CEQ_MANAGER_BATCH_MAX, **kwargs: Any) -> None:
        if not (1 <= batch_max <= CEQ_MANAGER_BATCH_MAX):
            raise ValueError(f"batch_max must be 1..{CEQ_MANAGER_BATCH_MAX}")
        super().__init__(**kwargs)
        self._batch_max = int(batch_max)

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
        return (
            base
            + ACTION_PROTOCOL
            + "\n\n"
            + BATCH_ACTION_PROTOCOL.format(batch_max=self._batch_max)
        )

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
        except _BudgetAbort as exc:
            # BEST-EVIDENCE COMMIT rule (same as D-E): the run budget broke
            # mid-investigation — the manager still commits its best-evidence
            # ranking (one bounded final ask) and the arm submits it.
            abort_reason = f"budget_exhausted:{exc}"
            try:
                commit_action = self._forced_commit(
                    manager_session, "manager", abort_reason
                )
            except _NonCommitError as nce:
                self._record_crash(nce)
                return self._result(submitted_ranking=None, status="aborted_budget",
                                    escrow_ledger_path=str(escrow.save(escrow_path)),
                                    prompt_volume_ratio=None,
                                    abort_reason=f"non_commit:{nce}")
            escrow.commit("manager", "final", commit_action["ranking"],
                          commit_action["confidence"])
            commit_action = self._commit_or_correct(
                manager_session, "manager", manager_sandbox, commit_action,
                "manager best-evidence final commit",
            )
            confirmed = manager_sandbox.submit_diagnosis(commit_action["ranking"])
            return self._result(
                submitted_ranking=confirmed["ranking"],
                status="completed",
                escrow_ledger_path=str(escrow.save(escrow_path)),
                prompt_volume_ratio=None,
                warnings=(f"best-evidence commit path used: {abort_reason}",),
                abort_reason=abort_reason,
            )
        except Exception as exc:  # noqa: BLE001 — crash is recorded, not raised
            self._record_crash(exc)
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
                f"Issue 1-3 tool calls for this round — either as ONE batch "
                f"action (\"tool_calls\", up to {self._batch_max} tools per turn) "
                "or as separate tool_call actions — or commit your ranked-5 "
                "diagnosis if you already have enough evidence."
            )
            round_tools = 0
            action = manager_session.ask(prompt)
            while action["action"] in ("tool_call", "tool_calls"):
                batch = (
                    [action] if action["action"] == "tool_call"
                    else action["tools"][: self._batch_max]
                )
                remaining = 3 - round_tools
                batch = batch[:remaining]  # 1-3 tool calls per round
                if not batch:
                    break  # round full; continue next round
                round_tools += len(batch)
                self._enforce_envelope()
                new_obs = self._execute_tools(manager_sandbox, batch)
                observations.extend(new_obs)
                self._enforce_envelope()
                action = manager_session.ask(
                    f"Observations from the last batch:\n"
                    f"{_render_observations(new_obs)}\n"
                    f"Round {round_no}: issue another batch (up to {remaining - len(batch)} "
                    "more this round) or commit."
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
        final_action = self._commit_or_correct(
            manager_session, "manager", manager_sandbox, final_action,
            "manager final commit",
        )
        self._enforce_envelope()
        confirmed = manager_sandbox.submit_diagnosis(final_action["ranking"])
        escrow_path = self._out_dir / f"{self.arm_label.lower()}-escrow.json"
        ratio = prompt_volume_ratio(
            manager_session.prompts,
            [p for s in self.sessions if s.agent_id != "manager" for p in s.prompts],
        )
        # The prompt-volume band is an anti-starvation *canary*, not a fatal gate.
        # When it is breached we must NOT discard a ranking the manager already
        # computed and submitted (that masked valid C-EQ results on large-payload
        # cases); instead we keep the result and disclose the breach as a warning.
        try:
            assert_volume_band(ratio)
            vol_warnings: list[str] = []
        except ValueError as exc:
            vol_warnings = [f"prompt-volume canary breach: {exc}"]
            print(f"[{self.arm_label}] WARNING: {exc}", file=sys.stderr, flush=True)
        return self._result(
            submitted_ranking=confirmed["ranking"],
            status="completed",
            escrow_ledger_path=str(escrow.save(escrow_path)),
            prompt_volume_ratio=ratio,
            warnings=vol_warnings,
        )


__all__ = [
    "ACTION_PROTOCOL",
    "AgentProtocolError",
    "ArmEscrow",
    "ArmRunResult",
    "BATCH_ACTION_PROTOCOL",
    "CEQ_INVESTIGATOR_TOOL_CAP",
    "CEQ_MANAGER_BATCH_MAX",
    "CEQTelemArm",
    "ChatClientLike",
    "ChatCompletionsLike",
    "DE_COMMITTEE_TOOL_CAP",
    "DE_PHASE1_TOOL_CAP",
    "DE_PHASE2_TOOL_CAP",
    "DetelemArm",
    "MAX_COMMIT_CORRECTIONS",
    "MECHANISM_LABEL",
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
