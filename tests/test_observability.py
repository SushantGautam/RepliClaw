"""Observability / OTel + OpenInference span emission (D06, AC13/AC18).

RepliClaw emits conventional OpenTelemetry spans (OpenInference semantic
conventions + repliclaw.* attributes) that an OTLP consumer — e.g.
SimpleAuditStudio — can ingest later. It never imports SimpleAuditStudio, and
the emission is a no-op when no TracerProvider is configured, so the hermetic
suite is unaffected. These tests prove the emission is real (not a claim) by
installing a lightweight, SDK-free TracerProvider and driving actual runs.
"""
from pathlib import Path

from opentelemetry import trace

from repliclaw import observability as obs
from repliclaw.investigators import DeterministicInvestigator
from repliclaw.models import Claim
from repliclaw.protocol import STRATEGY_REPLICLAW, RepliClawProtocol

FIX = Path(__file__).resolve().parent / "fixtures"


# --- SDK-free span capture --------------------------------------------------
class _Span:
    def __init__(self, name, parent, attrs):
        self.name = name
        self.parent = parent
        self.attrs = dict(attrs)
        self.ended = False

    def set_attribute(self, k, v):
        self.attrs[k] = v

    def set_status(self, *a, **k):
        pass

    def record_exception(self, *a, **k):
        pass

    def end(self):
        self.ended = True

    def is_recording(self):
        return True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Tracer:
    def __init__(self, sink):
        self.sink = sink
        self._stack = []

    def _current(self):
        return self._stack[-1].name if self._stack else None

    def start_span(self, name, *a, **k):
        # Non-current span: parented to the current top, but does NOT become current.
        sp = _Span(name, self._current(), k.get("attributes") or {})
        self.sink.append(sp)
        return sp

    def start_as_current_span(self, name, *a, **k):
        attrs = k.get("attributes") or {}
        sp = _Span(name, self._current(), attrs)
        self.sink.append(sp)
        self._stack.append(sp)
        return _Ctx(self, sp)


class _Ctx:
    def __init__(self, tracer, span):
        self.tracer = tracer
        self.span = span

    def __enter__(self):
        return self.span

    def __exit__(self, *a):
        if self.tracer._stack and self.tracer._stack[-1] is self.span:
            self.tracer._stack.pop()
        return False


class _Provider:
    def __init__(self, sink=None):
        self.sink = sink if sink is not None else []
        self._tracer = _Tracer(self.sink)

    def get_tracer(self, *a, **k):
        return self._tracer


class _TracerGuard:
    """Capture spans via the module's test seam (no global provider mutation).

    We inject a tracer directly rather than overriding the ambient TracerProvider
    because this environment's OTel refuses to re-override a non-default provider,
    which would silently keep spans on the no-op provider. The seam keeps capture
    hermetic and reliable without ever touching global provider state. The guard
    and the provider share one sink list so ``guard.sink`` is what the tracer fills.
    """

    def __init__(self):
        self.sink = []
        self._provider = _Provider(sink=self.sink)

    def __enter__(self):
        obs.set_test_tracer(self._provider.get_tracer())
        return self

    def __exit__(self, *a):
        obs.set_test_tracer(None)
        return False


def _run(tmp, fixture):
    import json

    fx = json.loads((FIX / f"{fixture}.json").read_text())
    c = fx["claim"]
    claim = Claim(
        claim_id=f"claim-{fixture}",
        statement=c["statement"],
        domain=c.get("domain", "general"),
        data=c.get("data"),
        reference_truth=c.get("reference_truth"),
        seeded_fault=c.get("seeded_fault"),
    )
    proto = RepliClawProtocol(
        run_root=Path(tmp),
        investigator_factory=lambda cfg: DeterministicInvestigator(cfg),
        strategy=STRATEGY_REPLICLAW,
        min_independent=3,
    )
    return proto.run(claim), claim.claim_id


def test_no_provider_is_safe_noop(tmp_path):
    """Hermetic default: no TracerProvider configured → spans are no-ops, no
    exception, and the run still produces its verdict. (AC15: the 62-test suite
    and benchmark never require the OTel SDK.)"""
    assert not trace.get_tracer_provider().get_tracer("x").start_span("s").is_recording()
    # The no-op helpers still yield cleanly.
    with obs.run_span(run_id="r", strategy="repl_claw", claim_id="c", n_investigators=3) as s:
        with obs.phase_span("blind"):
            with obs.investigator_span("a1", "analyst"):
                pass
        obs.finish_run_span(s, label="SUPPORTED", confidence=0.9,
                            usage=type("U", (), {"prompt_tokens": 1, "completion_tokens": 1,
                                                "total_tokens": 2})(), errors=[])
    # And a real run is unaffected.
    res, _ = _run(tmp_path, "clean_supported")
    assert res.verdict.label.value == "SUPPORTED"


def test_run_emits_root_investigator_and_phase_spans(tmp_path):
    """A real run emits a repliclaw.run root with investigator + phase children,
    OpenInference span-kind on the run/investigator spans, and the verdict on
    the root span (D06; AC13 cross-team observability)."""
    with _TracerGuard() as guard:
        res, claim_id = _run(tmp_path, "clean_supported")

    names = [sp.name for sp in guard.sink]
    assert "repliclaw.run" in names
    # One investigator span per independent investigator (>=3 for repl_claw).
    inv = [sp for sp in guard.sink if sp.name == "repliclaw.investigator"]
    assert len(inv) >= 3, names
    # Phase spans cover the protocol lifecycle.
    phases = {sp.name for sp in guard.sink if sp.name.startswith("repliclaw.phase.")}
    assert "repliclaw.phase.blind" in phases
    assert "repliclaw.phase.verdict" in phases

    # Parenting: every investigator span hangs off the root run span.
    run = next(sp for sp in guard.sink if sp.name == "repliclaw.run")
    assert all(sp.parent == "repliclaw.run" for sp in inv)

    # OpenInference semantic conventions are present with real values.
    assert run.attrs.get("openinference.span.kind") == "AGENT"
    assert run.attrs.get("repliclaw.strategy") == STRATEGY_REPLICLAW
    assert run.attrs.get("repliclaw.claim_id") == claim_id
    assert run.attrs.get("repliclaw.n_investigators") >= 3
    assert any(sp.attrs.get("repliclaw.role") for sp in inv)

    # Verdict outcome is attached to the root span.
    assert run.attrs.get("repliclaw.verdict.label") == res.verdict.label.value == "SUPPORTED"
    assert abs(run.attrs.get("repliclaw.verdict.confidence", 0.0) - res.verdict.confidence) < 1e-9


def test_conflict_run_emits_followup_investigator_span(tmp_path):
    """The misleading case triggers an emergent follow-up: the follow-up
    investigator must appear as a span under the root (AC07 observability)."""
    with _TracerGuard() as guard:
        res, _ = _run(tmp_path, "misleading_wrong_test")

    inv = [sp for sp in guard.sink if sp.name == "repliclaw.investigator"]
    followups = [sp for sp in inv if str(sp.attrs.get("repliclaw.agent_id", "")).startswith("inv-followup")]
    # A genuine conflict ⇒ an emergent falsification follow-up ran.
    assert followups, [sp.attrs.get("repliclaw.agent_id") for sp in inv]
    assert all(sp.parent == "repliclaw.run" for sp in followups)
    assert res.verdict.label.value == "REFUTED"


def test_constants_match_openinference_semconv():
    """The attribute names/values RepliClaw emits are the genuine OpenInference
    semantic conventions (no proprietary schema — TASK_SPEC.md non-goal :183)."""
    assert obs.SPAN_KIND_ATTR == "openinference.span.kind"
    assert obs.SPAN_KIND_AGENT == "AGENT"
    assert obs.AGENT_NAME_ATTR == "agent.name"
    assert obs.LLM_TOKEN_TOTAL_ATTR == "llm.token_count.total"
