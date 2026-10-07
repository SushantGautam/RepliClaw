"""Observability: emit standard OpenTelemetry spans for a RepliClaw run.

Design (D06): RepliClaw does **not** import SimpleAuditStudio. It emits
conventional OTel/OpenInference spans that any consumer (SimpleAuditStudio's
OTLP ingestion, any OTel backend) can pick up later. This is the *actual*
integration seam the spec names as the preferred interoperability layer
(TASK_SPEC.md:48, non-goal :183: no proprietary trace schemas).

Hermetic-safety rules (D07/AC15):
* Only the OpenTelemetry **API** is imported at the call site — never the SDK.
  When no TracerProvider is configured (the default in tests) the spans are
  no-ops, so the 62-test hermetic suite and benchmark are unaffected.
* If the ``opentelemetry`` API is not installed at all (a clean env without
  the ``[otel]`` extra) every helper degrades to a plain no-op context
  manager. Core behavior, verdicts, and metrics are identical either way.
* OpenInference semantic-convention constants are used when available and fall
  back to the documented literal attribute names otherwise.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

# --- OpenTelemetry API (optional, no-op when absent) -----------------------
try:  # pragma: no cover - exercised implicitly by env
    from opentelemetry import trace as _otel_trace

    _OTEL = True
except Exception:  # pragma: no cover - clean env without [otel] extra
    _OTEL = False
    _otel_trace = None  # type: ignore[assignment]

_TRACER_NAME = "repliclaw"
_TRACER_VERSION = "0.1.0"

# Optional injection point (used by tests; never mutated in production). When set,
# spans route through this tracer regardless of the ambient TracerProvider, so
# callers/tests can capture spans without a global provider (and without the SDK).
_injected_tracer = None  # type: ignore[assignment]


def set_test_tracer(tracer) -> None:
    """Route span emission through *tracer* (e.g. an in-memory test provider).

    Pass ``None`` to fall back to the ambient OpenTelemetry TracerProvider.
    This is the seam that keeps the emission hermetic and testable without the SDK.
    """
    global _injected_tracer
    _injected_tracer = tracer


def _get_tracer():
    """Resolve the tracer to emit through.

    Prefers an injected tracer; otherwise resolves lazily against the *current*
    TracerProvider (the normal deployment order: import → configure → run). The
    returned tracer is a no-op when no provider is set, the hermetic default.
    """
    if _injected_tracer is not None:
        return _injected_tracer
    return _otel_trace.get_tracer(_TRACER_NAME, _TRACER_VERSION)

# --- OpenInference semantic conventions (optional, literal fallback) -------
try:  # pragma: no cover
    from openinference.semconv.trace import (
        OpenInferenceSpanKindValues as _OI_KIND,
    )
    from openinference.semconv.trace import (
        SpanAttributes as _OI_SPAN,
    )

    SPAN_KIND_ATTR = _OI_SPAN.OPENINFERENCE_SPAN_KIND
    SPAN_KIND_AGENT = _OI_KIND.AGENT.value
    SPAN_KIND_TOOL = _OI_KIND.TOOL.value
    AGENT_NAME_ATTR = _OI_SPAN.AGENT_NAME
    INPUT_VALUE_ATTR = _OI_SPAN.INPUT_VALUE
    OUTPUT_VALUE_ATTR = _OI_SPAN.OUTPUT_VALUE
    LLM_TOKEN_PROMPT_ATTR = _OI_SPAN.LLM_TOKEN_COUNT_PROMPT
    LLM_TOKEN_COMPLETION_ATTR = _OI_SPAN.LLM_TOKEN_COUNT_COMPLETION
    LLM_TOKEN_TOTAL_ATTR = _OI_SPAN.LLM_TOKEN_COUNT_TOTAL
except Exception:  # pragma: no cover - OpenInference not installed
    SPAN_KIND_ATTR = "openinference.span.kind"
    SPAN_KIND_AGENT = "AGENT"
    SPAN_KIND_TOOL = "TOOL"
    AGENT_NAME_ATTR = "agent.name"
    INPUT_VALUE_ATTR = "input.value"
    OUTPUT_VALUE_ATTR = "output.value"
    LLM_TOKEN_PROMPT_ATTR = "llm.token_count.prompt"
    LLM_TOKEN_COMPLETION_ATTR = "llm.token_count.completion"
    LLM_TOKEN_TOTAL_ATTR = "llm.token_count.total"

# RepliClaw namespaced attributes (no OpenInference equivalent for these).
RUN_ID_ATTR = "repliclaw.run_id"
STRATEGY_ATTR = "repliclaw.strategy"
CLAIM_ID_ATTR = "repliclaw.claim_id"
N_INVESTIGATORS_ATTR = "repliclaw.n_investigators"
PHASE_ATTR = "repliclaw.phase"
AGENT_ID_ATTR = "repliclaw.agent_id"
ROLE_ATTR = "repliclaw.role"
VERDICT_LABEL_ATTR = "repliclaw.verdict.label"
VERDICT_CONFIDENCE_ATTR = "repliclaw.verdict.confidence"


# --- Status helper (API-only) ----------------------------------------------
class _Status:
    OK = "OK"
    ERROR = "ERROR"
    UNSET = "UNSET"


def _set_status(span: Any, code: str, description: str = "") -> None:
    """Set a span status without importing the SDK. Uses the API SpanStatusCode."""
    if span is None or not _OTEL:
        return
    try:
        from opentelemetry.trace import StatusCode

        if code == _Status.ERROR:
            span.set_status(StatusCode.ERROR, description)
        elif code == _Status.OK:
            span.set_status(StatusCode.OK)
    except Exception:  # pragma: no cover - defensive
        pass


def start_span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """Open a NON-current span (explicitly ended by the caller).

    Used for phase duration markers: it is parented to the ambient context (the
    run span) but does NOT become the current span, so investigator spans opened
    inside the phase still nest directly under the run span rather than under the
    phase. Returns ``None`` when the OTel API is unavailable.
    """
    if not _OTEL:
        return None
    try:
        return _get_tracer().start_span(name, attributes=attributes)
    except Exception:  # pragma: no cover - defensive
        return None


def end_span(span: Optional[Any]) -> None:
    """Explicitly end a non-current span (no-op when absent/None)."""
    if span is None:
        return
    try:
        span.end()
    except Exception:  # pragma: no cover - defensive
        pass


@contextmanager
def _span(name: str, attributes: Optional[Dict[str, Any]] = None) -> Iterator[Optional[Any]]:
    """Open an OTel span as the current one; record any exception and re-raise.

    Yields the live span when the OTel API is available, else ``None``. When no
    TracerProvider is set the returned span is a no-op recording span, so this
    is safe in the hermetic test/benchmark path.
    """
    if not _OTEL:
        yield None
        return
    tracer = _get_tracer()
    with tracer.start_as_current_span(name, attributes=attributes) as span:
        try:
            yield span
        except Exception as exc:  # noqa: BLE001 - record then propagate
            if span is not None:
                try:
                    span.record_exception(exc)
                    _set_status(span, _Status.ERROR, str(exc))
                except Exception:  # pragma: no cover - defensive
                    pass
            raise


# --- Public span helpers ----------------------------------------------------
@contextmanager
def run_span(
    *,
    run_id: str,
    strategy: str,
    claim_id: str,
    n_investigators: int,
    task_instructions: str = "",
) -> Iterator[Optional[Any]]:
    """Root span for one protocol run (OpenInference AGENT)."""
    attrs: Dict[str, Any] = {
        SPAN_KIND_ATTR: SPAN_KIND_AGENT,
        RUN_ID_ATTR: run_id,
        STRATEGY_ATTR: strategy,
        CLAIM_ID_ATTR: claim_id,
        N_INVESTIGATORS_ATTR: n_investigators,
    }
    if task_instructions:
        attrs[INPUT_VALUE_ATTR] = task_instructions[:4000]
    with _span("repliclaw.run", attrs) as span:
        yield span


def finish_run_span(span: Optional[Any], *, label: str, confidence: float,
                    usage: Optional[Any], errors: List[str]) -> None:
    """Attach verdict + token-count outputs and a terminal status to the run span."""
    if span is None:
        return
    try:
        span.set_attribute(VERDICT_LABEL_ATTR, label)
        span.set_attribute(VERDICT_CONFIDENCE_ATTR, float(confidence))
        if usage is not None:
            span.set_attribute(LLM_TOKEN_PROMPT_ATTR, int(getattr(usage, "prompt_tokens", 0) or 0))
            span.set_attribute(LLM_TOKEN_COMPLETION_ATTR, int(getattr(usage, "completion_tokens", 0) or 0))
            span.set_attribute(LLM_TOKEN_TOTAL_ATTR, int(getattr(usage, "total_tokens", 0) or 0))
        if errors:
            _set_status(span, _Status.ERROR, f"{len(errors)} error(s)")
        else:
            _set_status(span, _Status.OK)
    except Exception:  # pragma: no cover - defensive
        pass


@contextmanager
def phase_span(phase: str) -> Iterator[Optional[Any]]:
    """Open a non-current phase span (blind/committed/revealing/evidence/...) that
    ends explicitly at the phase boundary.

    It is deliberately opened via the non-current span API (parented to the run
    span) rather than ``start_as_current_span`` so that investigator spans opened
    *inside* a phase still nest directly under the run span — the phase span is a
    duration/latency marker for the phase, not the parent of an investigator's
    isolated run.
    """
    span = start_span(f"repliclaw.phase.{phase}", {PHASE_ATTR: phase})
    try:
        yield span
    finally:
        end_span(span)


@contextmanager
def investigator_span(agent_id: str, role: str) -> Iterator[Optional[Any]]:
    """Span for one investigator's isolated run (OpenInference AGENT)."""
    attrs = {
        SPAN_KIND_ATTR: SPAN_KIND_AGENT,
        AGENT_ID_ATTR: agent_id,
        AGENT_NAME_ATTR: agent_id,
        ROLE_ATTR: role,
    }
    with _span("repliclaw.investigator", attrs) as span:
        yield span
