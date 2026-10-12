"""Real LLM investigators operating inside the partition boundary (Part C).

Each investigator is a genuine LLM call loop driven by
:class:`repliclaw.investigators.LLMClient` (the repo's OpenAI-compatible
client with real usage accounting and a ``max_calls`` budget; default
endpoint/model come from ``LLMConfig`` — env ``REPLICLAW_LLM_API_KEY`` /
``CUSTOM_SIMULACHAT_KEY`` for the key). There are NO deterministic
heuristics, NO scripted policies, and NO silent fallback to a non-LLM
policy: if the endpoint is unreachable or a call fails,
:class:`InvestigatorRunError` is raised and the run is marked failed, never
faked.

Tool protocol
-------------
JSON-based, at the investigator level (deliberately NOT native
function-calling). The proxy's native tool support is unverified, a JSON
protocol works against any OpenAI-compatible chat endpoint, and every tool
call is a plain JSON object in the transcript, so the receipts are fully
auditable.

Bounds
------
``max_turns`` (LLM calls), ``token_budget`` (sum of ``usage.total_tokens``
across calls), ``wall_deadline_s`` (per-investigator wall clock), plus the
shared client's ``max_calls`` guard. Hitting a bound stops the loop cleanly
and is recorded in the receipt.

Usage integrity
---------------
Follows the repo's "never zero-fill" rule (P08 contract / judge item 7, see
``repliclaw.eess_live.budget_calls`` and ``eess_live/orchestrator.py``):
per-call usage is measured with the snapshot/delta pattern, and a call that
reports no usage fields is recorded with ``usage_present=False`` and
INVALIDATES the run (status ``invalid_usage``) — it is never zero-filled and
never silently estimated.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError

from repliclaw.canonical import canonical_json
from repliclaw.eess_live.budget_calls import usage_delta, usage_present, usage_snapshot
from repliclaw.escrow import EstimatedCost, PredictionPacket, commitment_hash
from repliclaw.investigators import BudgetExceeded, LLMClient

from .evidence import EvidencePartition
from .isolation import InvestigatorView, IsolationViolation

RECEIPT_SCHEMA = "repliclaw.indepinfo.receipt/v1"

CORRECTION_MSG = (
    "Your last response was not a valid action JSON object. Respond with "
    "exactly one JSON object: either {\"action\": \"tool_call\", \"tool\": "
    "<name>, \"args\": {...}} or the commit object described in your "
    "instructions. No prose outside the JSON."
)

_PREVIEW_CHARS = 160


class InvestigatorRunError(RuntimeError):
    """Raised when an LLM call (or the run) fails; the run is failed, not faked.

    ``receipt`` carries the partial receipt (transcript so far, usage so
    far) when one could be built.
    """

    def __init__(self, message: str, receipt: Optional["InvestigatorReceipt"] = None) -> None:
        super().__init__(message)
        self.receipt = receipt


class InvestigatorConfig(BaseModel):
    """Per-investigator bounds and call parameters."""

    max_turns: int = Field(default=6, ge=1)
    token_budget: int = Field(default=20000, ge=1)
    wall_deadline_s: float = Field(default=180.0, gt=0)
    max_tokens_per_call: int = Field(default=1024, ge=1)

    model_config = {"frozen": True}


class CallRecord(BaseModel):
    """Per-LLM-call telemetry for the receipt."""

    turn: int
    model_requested: str
    model_reported: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    wall_s: float = 0.0
    action: Optional[str] = None  # "tool_call" | "commit" | None (unparseable)
    tool: Optional[str] = None
    error: Optional[str] = None
    usage_present: bool = True  # False => the run is invalidated (never zero-filled)

    model_config = {"frozen": True}


class InvestigatorReceipt(BaseModel):
    """Structured receipt: the primary evidence that the investigator was a
    real LLM agent (full transcript, model id, per-call + total usage,
    wall clock, tool-call count, bounds hit)."""

    schema_: str = Field(default=RECEIPT_SCHEMA, alias="schema")
    agent_id: str
    case_id: str
    source_id: str
    model_requested: str
    model_reported: Optional[str] = None
    status: str = Field(pattern=r"^(committed|bound|failed|invalid_usage)$")
    transcript: List[Dict[str, str]]
    transcript_sha256: str = ""
    calls: List[CallRecord] = Field(default_factory=list)
    num_llm_calls: int = 0
    num_tool_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    wall_s: float = 0.0
    bounds_hit: List[str] = Field(default_factory=list)
    packet: Optional[Dict[str, Any]] = None
    commitment_sha256: Optional[str] = None
    reveal_status: Optional[str] = None  # set by run_case after the reveal
    error: Optional[str] = None

    model_config = {"populate_by_name": True, "frozen": True}

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)


# ---------------------------------------------------------------------------
# prompt + protocol helpers
# ---------------------------------------------------------------------------


def _system_prompt(partition: EvidencePartition, case_brief: str) -> str:
    records_json = json.dumps(
        [r.model_dump() for r in partition.records], indent=2, ensure_ascii=False
    )
    return f"""You are an independent diagnostic investigator in a controlled experiment on fragmented evidence.

CASE: {partition.case_id}
CASE BRIEF: {case_brief or "(none)"}

You have access to EXACTLY ONE evidence source:
  name: {partition.source_name}
  source_id: {partition.source_id}
  description: {partition.source_description or "(none)"}

Your source's records (JSON array; index = position in the array):
{records_json}

You may not assume knowledge from any other source, service, or investigator.

Respond with EXACTLY ONE JSON object per turn — no prose outside the JSON.

To call a tool:
  {{"action": "tool_call", "tool": "<tool_name>", "args": {{...}}}}
Available tools (they operate ONLY on your own source):
  - "list_records": args {{}} — list your records (index, record_id, preview)
  - "get_record": args {{"index": <int>}} — fetch one full record by index
  - "search_records": args {{"query": "<substring>"}} — case-insensitive search over your records
  - "source_info": args {{}} — metadata about your source

When you have enough evidence, commit your prediction:
  {{"action": "commit",
    "hypothesis_statement": "<one falsifiable sentence naming the most likely root cause>",
    "predicted_outcome": "<what you predict will be observed if your hypothesis is true>",
    "refutation_criterion": "<the specific observation that would falsify it>",
    "competing_explanation": "<the strongest alternative explanation>",
    "intervention_id": "<short label for the single next diagnostic step you would take, or 'observational_only'>",
    "estimated_cost": {{"tokens": <int>, "wall_s": <float>}}}}

Rules:
- Commit as soon as you are reasonably confident; you have a limited number of turns.
- Base every claim strictly on your own source's records.
"""


def _parse_action(content: str) -> Tuple[Optional[str], Optional[str], Dict[str, Any], Optional[str]]:
    """Parse the model's JSON action. Returns (action, tool, args, error)."""
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return None, None, {}, f"not valid JSON: {e}"
    if not isinstance(obj, dict):
        return None, None, {}, "JSON must be an object"
    action = obj.get("action")
    if action == "tool_call":
        tool = obj.get("tool")
        args = obj.get("args") or {}
        if not isinstance(tool, str) or not isinstance(args, dict):
            return None, None, {}, "tool_call requires string 'tool' and object 'args'"
        return "tool_call", tool, args, None
    if action == "commit":
        return "commit", None, obj, None
    return None, None, {}, f"unknown action {action!r}"


def _preview(record: Any) -> str:
    text = canonical_json(record.data)
    return text if len(text) <= _PREVIEW_CHARS else text[:_PREVIEW_CHARS] + "…"


def _transcript_sha256(agent_id: str, transcript: List[Dict[str, str]]) -> str:
    """Content hash of the audit transcript (mirrors LLMToolSession.transcript_sha256)."""
    canonical = json.dumps(
        [{"agent": agent_id, "content": e["content"], "role": e["role"]} for e in transcript],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# investigator
# ---------------------------------------------------------------------------


class PartitionedInvestigator:
    """A real LLM investigator bound to one :class:`InvestigatorView`.

    (i) receives only its own source partition (via the view),
    (ii) computes ``prior_evidence_snapshot_sha256`` from its OWN partition,
    (iii) seals via ``EscrowLedger.commit`` (through ``view.commit``),
    (iv) is driven by :class:`LLMClient`.

    ``client`` is an :class:`LLMClient` (or a test double subclassing it,
    e.g. a :class:`repliclaw.eess_live.fake.FakeLLMClient`-style scripted
    double).
    """

    def __init__(self, view: InvestigatorView, client: LLMClient, config: InvestigatorConfig) -> None:
        self.view = view
        self.client = client
        self.config = config
        self._packet: Optional[PredictionPacket] = None
        self._receipt: Optional[InvestigatorReceipt] = None

    @property
    def packet(self) -> Optional[PredictionPacket]:
        """The committed packet (None until the investigator commits)."""
        return self._packet

    @property
    def receipt(self) -> Optional[InvestigatorReceipt]:
        """The receipt from the last :meth:`run` (None before the first run)."""
        return self._receipt

    # -- main loop ---------------------------------------------------------
    def run(self) -> InvestigatorReceipt:
        """Run the bounded investigation; commit via escrow; return receipt.

        Raises :class:`InvestigatorRunError` (with the partial receipt
        attached) on any LLM failure or unexpected error — the run is
        marked failed, never faked.
        """
        partition = self.view.my_partition()
        model = self.client.cfg.model
        start = time.monotonic()
        transcript: List[Dict[str, str]] = [
            {"role": "system", "content": _system_prompt(partition, self.view.case_brief)},
            {"role": "user", "content": "Begin your investigation. Respond with exactly one JSON object."},
        ]
        calls: List[CallRecord] = []
        total_prompt = total_completion = total_tokens = 0
        num_tool_calls = 0
        bounds_hit: List[str] = []
        status = "bound"
        error: Optional[str] = None
        model_reported: Optional[str] = None

        try:
            for turn in range(1, self.config.max_turns + 1):
                if time.monotonic() - start >= self.config.wall_deadline_s:
                    bounds_hit.append("wall_deadline")
                    break
                before = usage_snapshot(self.client)
                t0 = time.perf_counter()
                try:
                    content = self.client.chat_messages(
                        transcript, max_tokens=self.config.max_tokens_per_call
                    )
                except BudgetExceeded:
                    # Shared client's max_calls guard: a cost bound, not a
                    # failure — stop cleanly and record it.
                    bounds_hit.append("client_max_calls")
                    status = "bound"
                    break
                except Exception as e:  # endpoint down, HTTP error, timeout...
                    status = "failed"
                    error = f"LLM call failed on turn {turn}: {type(e).__name__}: {e}"
                    break
                wall = time.perf_counter() - t0
                delta = usage_delta(before, usage_snapshot(self.client))
                present = usage_present(delta)
                call_prompt = delta.prompt_tokens
                call_completion = delta.completion_tokens
                call_total = delta.total_tokens
                total_prompt += call_prompt
                total_completion += call_completion
                total_tokens += call_total
                reported = getattr(self.client, "last_model", None)
                if isinstance(reported, str) and reported:
                    model_reported = reported
                content = (content or "").strip()
                transcript.append({"role": "assistant", "content": content})

                action, tool, args, parse_error = _parse_action(content)
                calls.append(
                    CallRecord(
                        turn=turn,
                        model_requested=model,
                        model_reported=model_reported,
                        prompt_tokens=call_prompt,
                        completion_tokens=call_completion,
                        total_tokens=call_total,
                        wall_s=round(wall, 4),
                        action=action,
                        tool=tool,
                        error=parse_error,
                        usage_present=present,
                    )
                )

                if not present:
                    # Usage-integrity rule (P08 contract / judge item 7): a
                    # call that reports no usage is never zero-filled — the
                    # record above shows WHERE usage went missing, and the
                    # run is invalidated below.
                    status = "invalid_usage"
                    error = (
                        f"LLM call on turn {turn} reported no usage fields — "
                        "run invalidated (never zero-filled)"
                    )
                    break

                if action is None:
                    transcript.append({"role": "user", "content": CORRECTION_MSG})
                elif action == "tool_call" and tool is not None:
                    num_tool_calls += 1
                    result = self._execute_tool(tool, args, partition)
                    transcript.append(
                        {"role": "user", "content": json.dumps({"tool_result": result}, ensure_ascii=False)}
                    )
                elif action == "tool_call":
                    # Defensive: _parse_action guarantees a string tool here.
                    transcript.append({"role": "user", "content": CORRECTION_MSG})
                else:  # commit
                    try:
                        packet = self._build_packet(
                            args, partition, total_tokens, time.monotonic() - start
                        )
                        self.view.commit(packet)
                    except (ValidationError, IsolationViolation, ValueError) as e:
                        # Invalid commit from the model: give it one more
                        # chance within its remaining budget (no fallback).
                        transcript.append(
                            {
                                "role": "user",
                                "content": (
                                    f"Your commit was rejected ({e}). "
                                    "Respond with a corrected commit JSON object."
                                ),
                            }
                        )
                        continue
                    self._packet = packet
                    status = "committed"
                    break

                if total_tokens > self.config.token_budget:
                    bounds_hit.append("token_budget")
                    status = "bound"
                    break
            else:
                bounds_hit.append("max_turns")
                status = "bound"
        except Exception as e:  # phase violation, ledger error, ...
            status = "failed"
            error = f"unexpected error: {type(e).__name__}: {e}"

        receipt = InvestigatorReceipt(
            agent_id=self.view.agent_id,
            case_id=self.view.case_id,
            source_id=self.view.source_id,
            model_requested=model,
            model_reported=model_reported,
            status=status,
            transcript=transcript,
            transcript_sha256=_transcript_sha256(self.view.agent_id, transcript),
            calls=calls,
            num_llm_calls=len(calls),
            num_tool_calls=num_tool_calls,
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_tokens,
            wall_s=round(time.monotonic() - start, 4),
            bounds_hit=bounds_hit,
            packet=self._packet.to_dict() if self._packet is not None else None,
            commitment_sha256=commitment_hash(self._packet) if self._packet is not None else None,
            error=error,
        )
        self._receipt = receipt
        if status == "failed":
            raise InvestigatorRunError(
                f"investigator {self.view.agent_id!r} failed: {error}", receipt=receipt
            )
        if status == "invalid_usage":
            raise InvestigatorRunError(
                f"investigator {self.view.agent_id!r} invalidated: {error}", receipt=receipt
            )
        return receipt

    # -- tools (operate ONLY on this investigator's own partition) ---------
    def _execute_tool(self, tool: str, args: Dict[str, Any], partition: EvidencePartition) -> Dict[str, Any]:
        if tool == "list_records":
            return {
                "records": [
                    {"index": i, "record_id": r.record_id, "preview": _preview(r)}
                    for i, r in enumerate(partition.records)
                ]
            }
        if tool == "get_record":
            raw = args.get("index")
            if not isinstance(raw, int) or isinstance(raw, bool):
                return {"error": "get_record requires integer 'index'"}
            idx = raw
            if not 0 <= idx < len(partition.records):
                return {"error": f"index {idx} out of range (0..{len(partition.records) - 1})"}
            return partition.records[idx].model_dump()
        if tool == "search_records":
            q = str(args.get("query", "")).lower()
            if not q:
                return {"error": "search_records requires non-empty 'query'"}
            hits = []
            for i, r in enumerate(partition.records):
                hay = (r.record_id + " " + canonical_json(r.data)).lower()
                if q in hay:
                    hits.append({"index": i, **r.model_dump()})
            return {"query": q, "count": len(hits), "records": hits[:20]}
        if tool == "source_info":
            return {
                "source_id": partition.source_id,
                "name": partition.source_name,
                "description": partition.source_description,
                "record_count": len(partition.records),
            }
        return {
            "error": f"unknown tool {tool!r}; available: list_records, get_record, search_records, source_info"
        }

    # -- packet construction -------------------------------------------------
    def _build_packet(
        self, args: Dict[str, Any], partition: EvidencePartition, tokens_so_far: int, wall_so_far: float
    ) -> PredictionPacket:
        def _req(key: str) -> str:
            v = args.get(key)
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"commit field {key!r} must be a non-empty string")
            return v.strip()

        est = args.get("estimated_cost") or {}
        if not isinstance(est, dict):
            raise ValueError("estimated_cost must be an object")
        intervention = str(args.get("intervention_id") or "").strip() or "observational_only"
        return PredictionPacket(
            packet_id=uuid.uuid4().hex,
            case_id=partition.case_id,
            agent_id=self.view.agent_id,
            hypothesis_id=f"H_{self.view.agent_id}",
            hypothesis_version=1,
            hypothesis_statement=_req("hypothesis_statement"),
            intervention_id=intervention,
            predicted_outcome=_req("predicted_outcome"),
            refutation_criterion=_req("refutation_criterion"),
            competing_explanation=_req("competing_explanation"),
            estimated_cost=EstimatedCost(
                tokens=int(est.get("tokens", tokens_so_far)),
                wall_s=float(est.get("wall_s", wall_so_far)),
            ),
            prior_evidence_snapshot_sha256=partition.snapshot_sha256,
        )


__all__ = [
    "CORRECTION_MSG",
    "RECEIPT_SCHEMA",
    "CallRecord",
    "InvestigatorConfig",
    "InvestigatorReceipt",
    "InvestigatorRunError",
    "PartitionedInvestigator",
]
