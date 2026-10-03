"""Offline tests for scripts/measure_live_token_floor.py (P08, judge item 2 / F).

Ported from the p08/token-floor suite (commit 4af1d0d) to the CURRENT
151-line script, which is structurally different from the old one it was
written against:

* ``main()`` takes NO arguments — it parses ``sys.argv`` (``--work-dir``,
  ``--seed``) — and has no ``check_api_key`` / ``build_floor_doc`` /
  ``run_floor`` / ``EXIT_*`` helpers (those existed only in the old script).
* It pins the frozen §3.1 / D-10 values as module constants (``LAMBDA_`` /
  ``MU_`` / ``MAX_CYCLES_`` / ``LEASE_TTL_S_``) and patches
  ``orchestrator.LEASE_TTL_S`` + ``EESSLiveS5Arm._build_policy`` INSIDE
  ``main()`` for the duration of one run, restoring both in ``finally``.
  These tests assert the constants against the prereg values AND that the
  patches do NOT persist after a (failed) run.
* The only seam it exposes is the ``EESSLiveS5Arm`` arm adapter, which the
  tests stub with an offline stand-in that writes the SAME contract
  artifacts a real arm writes (``run-01/final_verdict.json`` +
  ``run-01/budget_ledger.json``) — no network, no key.

Hard rules honored (no live LLM API keys, no network):

1. Key gate — with no ``REPLICLAW_LLM_API_KEY`` / ``CUSTOM_SIMULACHAT_KEY``
   set, ``main()`` REFUSES cleanly with the documented "No LLM API key"
   ``RuntimeError`` and never constructs a network client: the module's
   ``LLMClient`` is replaced by a spy that records construction and raises
   the same clean refusal instead of opening any endpoint, and
   ``openai.OpenAI`` is patched to explode if it is ever constructed. No
   artifacts are written and the frozen-value patches are rolled back.
   (Note: the current script's ``LLMClient`` is lazily constructed once per
   run by its internal client factory — so the portable guarantee is "no
   *network* client is constructed / no request is sent", not "zero
   ``LLMClient()`` calls".)
2. Frozen-params constants match prereg §3.1 / D-10 (λ=0.5, μ=0.5,
   max_cycles=6, offer TTL=120 s).
3. floor.json / floor_summary.json schema validation against the committed
   fixtures (read-only), including internal-consistency arithmetic
   (per-agent totals == sum of calls, headroom margin == 60000 / floor).
   The committed run ledger has a per-call ``calls[]`` array (no
   ``agents[]`` key), so the per-agent arithmetic is validated at the ledger
   level and cross-checked against ``floor.json``'s ``measured_floor_tokens``.
4. Failure paths — per the CURRENT script's exit contract
   (``ok = tokens > 0 and status in {completed, aborted_budget}``): a run
   that produced ZERO tokens (even budget-aborted) must exit non-zero,
   while a budget-aborted run WITH positive tokens is a usable measured
   floor (exit 0, honestly labeled). Status values outside the tolerated
   set, missing usage, and corrupted ledgers must be rejected by the
   documented output contract (temp copies only — the committed fixtures
   are never mutated; a sha256/git invariant test guards this).

Nothing in this file calls the live endpoint.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
import types
from collections import Counter
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "measure_live_token_floor.py"

FLOOR_JSON = REPO_ROOT / "artifacts" / "p08" / "live_token_floor" / "floor.json"
FLOOR_SUMMARY = REPO_ROOT / "artifacts" / "p08" / "live_token_floor" / "floor_summary.json"
LEAD_LEDGER = (
    REPO_ROOT / "artifacts" / "p08" / "live_token_floor" / "work" / "run-01" / "budget_ledger.json"
)

sys.path.insert(0, str(REPO_ROOT / "src"))

from repliclaw.comparators.arms import ArmSpec  # noqa: E402
from repliclaw.comparators.budget import BudgetLedger, BudgetEnvelope  # noqa: E402
from repliclaw.eess_live import CASE_ID, EESSLiveS5Arm  # noqa: E402
import repliclaw.eess_live.orchestrator as orch  # noqa: E402
from repliclaw.models import Claim  # noqa: E402
import openai  # noqa: E402  (module-level attribute of the script's client dep)


# ---------------------------------------------------------------------------
# Load the measurement script as a module (it has no package of its own).
# exec_module only runs module-level code (constants + defs) — main() never
# runs at import time, so this is safe offline.
# ---------------------------------------------------------------------------
def _load_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("measure_live_token_floor", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M = _load_module()

FLOOR_SCHEMA = "p08.live_token_floor/1"
FLOOR_REQUIRED_KEYS = frozenset(
    {
        "schema",
        "harness_seed",
        "case_id",
        "arm",
        "live_llm",
        "date",
        "frozen_params",
        "envelope",
        "status",
        "verdict",
        "measured_floor_tokens",
        "measured_wall_s",
        "per_agent",
        "headroom",
        "work_dir",
    }
)
ENVELOPE_KEYS = frozenset({"max_tokens", "max_wall_s", "max_agents"})
FROZEN_PARAM_KEYS = frozenset({"lambda", "mu", "max_cycles", "offer_ttl_s"})
HEADROOM_KEYS = frozenset({"committed_ceiling_tokens", "measured_usage_fraction", "margin_x"})


# ---------------------------------------------------------------------------
# Offline contract-artifact writer (the stub arm's payload)
# ---------------------------------------------------------------------------
def _stub_artifacts(run_dir: Path, status: str, tokens: int, wall_s: float = 1.0) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "final_verdict.json").write_text(
        json.dumps(
            {
                "schema": "p08.final_verdict/1",
                "status": status,
                "verdict": "uncertain" if status == "completed" else None,
                "total_tokens": tokens,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    # Per-agent rollup in the same shape the real BudgetLedger snapshot has
    # in ``agents[]`` (the script builds floor.json's per_agent from this key).
    agent_tokens: dict[str, int] = {}
    agent_calls: dict[str, int] = {}
    order: list[str] = []
    for aid in ["alpha", "beta", "gamma", "alpha", "beta", "gamma"]:
        if aid not in agent_tokens:
            agent_tokens[aid] = 0
            agent_calls[aid] = 0
            order.append(aid)
        agent_tokens[aid] += 52
        agent_calls[aid] += 1
    (run_dir / "budget_ledger.json").write_text(
        json.dumps(
            {
                "schema": "p08.budget_ledger/1",
                "envelope": {"max_tokens": 60_000, "max_wall_s": 900.0, "max_agents": 3},
                "agents": [
                    {
                        "agent_id": aid,
                        "llm_calls": agent_calls[aid],
                        "total_tokens": agent_tokens[aid],
                    }
                    for aid in order
                ],
                "calls": [
                    {
                        "seq": i + 1,
                        "agent_id": aid,
                        "prompt_tokens": 40,
                        "completion_tokens": 12,
                        "total_tokens": 52,
                        "wall_s": 0.2,
                        "usage_present": True,
                    }
                    for i, aid in enumerate(["alpha", "beta", "gamma", "alpha", "beta", "gamma"])
                ],
                "totals": {
                    "llm_calls": 6,
                    "prompt_tokens": 240,
                    "completion_tokens": 72,
                    "total_tokens": tokens,
                    "wall_s": wall_s,
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


class _StubResult:
    def __init__(self, tokens: int) -> None:
        self.total_tokens = tokens


class _FakeArm:
    """Offline stand-in for EESSLiveS5Arm with the identical artifact
    contract: ``run()`` writes the same ``run-01/`` files a real arm writes.
    No network, no key, no real LLMClient."""

    @staticmethod
    def _build_policy(self: Any) -> Any:
        # Present because main() reads/restores the REAL class's
        # ``_build_policy`` on the arm class; never called by the stub.
        raise AssertionError("stub arm policy must not be built")

    def __init__(self, client_factory: Any, *, max_cycles: int = 6, harness_seed: int = 20261010):
        self._client_factory = client_factory
        self.max_cycles = max_cycles
        self.harness_seed = harness_seed

    def run(self, claim: Claim, ledger: BudgetLedger, spec: ArmSpec, work_dir: Path):
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)
        _stub_artifacts(work / "run-01", "completed", 6 * 52, wall_s=1.5)
        return _StubResult(6 * 52)


class _FakeAbortedArm(_FakeArm):
    """A budget-aborted run that still MEASURED a positive token floor —
    per the script's contract this is an OK (usable) measurement."""

    def run(self, claim: Claim, ledger: BudgetLedger, spec: ArmSpec, work_dir: Path):
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)
        _stub_artifacts(work / "run-01", "aborted_budget", 200)
        return _StubResult(200)


class _FakeZeroTokensArm(_FakeArm):
    """A run that produced NO tokens at all (e.g. aborted before the first
    LLM call) — the script's contract: not a floor, exit non-zero."""

    def run(self, claim: Claim, ledger: BudgetLedger, spec: ArmSpec, work_dir: Path):
        work = Path(work_dir)
        work.mkdir(parents=True, exist_ok=True)
        _stub_artifacts(work / "run-01", "aborted_budget", 0)
        return _StubResult(0)


# ---------------------------------------------------------------------------
# Output-contract validator (mirrors the script's documented exit contract)
# ---------------------------------------------------------------------------
def validate_floor_against_ledger(doc: dict, ledger: dict) -> None:
    """Re-derive the script's final OK-check (return 0 only if ``ok``):

    ``ok = tokens > 0 and fv.get('status') in {'completed', 'aborted_budget'}``

    PLUS judge item 7 — a completed floor is void if ANY call in the run's
    own ledger reported no usage (never zero-filled).
    """
    status = doc.get("status")
    if status not in {"completed", "aborted_budget"}:
        raise ValueError(f"status {status!r} is not a usable floor")
    tokens = int(doc.get("measured_floor_tokens") or 0)
    if not tokens > 0:
        raise ValueError("measured floor must be a positive token count")
    margin = doc.get("headroom", {}).get("margin_x")
    recomputed = round(60_000 / tokens, 2) if tokens else None
    if margin is not None and margin != recomputed:
        raise ValueError(f"headroom margin {margin!r} != 60000/{tokens} = {recomputed}")
    calls = ledger.get("calls", [])
    if status == "completed" and calls and not all(c.get("usage_present") for c in calls):
        raise ValueError("completed floor run with a call that reported no usage")


# ---------------------------------------------------------------------------
# floor.json schema validator (schema + frozen params + arithmetic)
# ---------------------------------------------------------------------------
def validate_floor_doc(doc: dict) -> None:
    """Validate a floor.json document against the script's documented
    output contract (schema, frozen §3.1/D-10 params, envelope, headroom
    arithmetic vs the committed 60k ceiling)."""
    if not isinstance(doc, dict):
        raise ValueError("floor doc must be a JSON object")
    missing = FLOOR_REQUIRED_KEYS - doc.keys()
    if missing:
        raise ValueError(f"floor.json missing required keys: {sorted(missing)}")

    if doc["schema"] != FLOOR_SCHEMA:
        raise ValueError(f"schema {doc['schema']!r} != {FLOOR_SCHEMA!r}")
    if doc["arm"] != "S5":
        raise ValueError(f"arm must be 'S5', got {doc['arm']!r}")
    if doc["case_id"] != CASE_ID:
        raise ValueError(f"case_id {doc['case_id']!r} != orchestrator CASE_ID {CASE_ID!r}")
    if doc["live_llm"] is not True:
        raise ValueError("live_llm must be true (this is a live-LLM floor)")
    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", doc["date"]):
        raise ValueError(f"date {doc['date']!r} is not a UTC timestamp (…Z)")
    if not isinstance(doc["harness_seed"], int):
        raise ValueError("harness_seed must be an int")
    if not isinstance(doc["work_dir"], str) or not doc["work_dir"]:
        raise ValueError("work_dir must be a non-empty string")

    fp = doc["frozen_params"]
    if set(fp) != FROZEN_PARAM_KEYS:
        raise ValueError(f"frozen_params keys {sorted(fp)} != {sorted(FROZEN_PARAM_KEYS)}")
    if fp["lambda"] != 0.5:
        raise ValueError(f"frozen lambda {fp['lambda']!r} != 0.5 (prereg §3.1/D-10)")
    if fp["mu"] != 0.5:
        raise ValueError(f"frozen mu {fp['mu']!r} != 0.5 (prereg §3.1/D-10)")
    if fp["max_cycles"] != 6:
        raise ValueError(f"frozen max_cycles {fp['max_cycles']!r} != 6 (D-10)")
    if fp["offer_ttl_s"] != 120.0:
        raise ValueError(f"frozen offer_ttl_s {fp['offer_ttl_s']!r} != 120 (D-10)")

    env = doc["envelope"]
    if set(env) != ENVELOPE_KEYS:
        raise ValueError(f"envelope keys {sorted(env)} != {sorted(ENVELOPE_KEYS)}")
    if env["max_tokens"] != 60_000:
        raise ValueError(f"envelope.max_tokens {env['max_tokens']} != committed 60000 ceiling")
    if env["max_wall_s"] != 900.0:
        raise ValueError(f"envelope.max_wall_s {env['max_wall_s']} != 900.0")
    if env["max_agents"] != 3:
        raise ValueError(f"envelope.max_agents {env['max_agents']} != 3")

    floor = int(doc["measured_floor_tokens"])
    if not floor > 0:
        raise ValueError(f"measured_floor_tokens {floor} must be > 0")
    head = doc["headroom"]
    if set(head) != HEADROOM_KEYS:
        raise ValueError(f"headroom keys {sorted(head)} != {sorted(HEADROOM_KEYS)}")
    if head["committed_ceiling_tokens"] != 60_000:
        raise ValueError("headroom.committed_ceiling_tokens != 60000")
    if head["measured_usage_fraction"] != round(floor / 60_000, 4):
        raise ValueError(
            f"measured_usage_fraction {head['measured_usage_fraction']} != "
            f"round({floor}/60000, 4) = {round(floor / 60000, 4)}"
        )
    if head["margin_x"] != round(60_000 / floor, 2):
        raise ValueError(
            f"headroom margin {head['margin_x']} != 60000/{floor} = {round(60_000 / floor, 2)}"
        )
    if not isinstance(doc["per_agent"], list):
        raise ValueError("per_agent must be a list")


def validate_floor_against_ledger_doc(doc: dict, ledger: dict) -> None:
    """Cross-check floor.json's numbers against the run's own ledger
    (every number in floor.json must come from the run's artifacts)."""
    totals = ledger.get("totals", {})
    if totals.get("total_tokens") != int(doc["measured_floor_tokens"]):
        raise ValueError(
            f"measured_floor_tokens {doc['measured_floor_tokens']} != "
            f"ledger totals.total_tokens {totals.get('total_totals') or totals.get('total_tokens')}"
        )
    calls = ledger.get("calls", [])
    if calls:
        if sum(int(c.get("total_tokens") or 0) for c in calls) != int(doc["measured_floor_tokens"]):
            raise ValueError("sum of ledger call tokens != measured_floor_tokens")
        if all(not c.get("usage_present") for c in calls):
            raise ValueError("all ledger calls report missing usage")
    # The script's per_agent is built from ledger["agents"] (absent in the
    # committed run), so it is empty here; if present it must match the
    # per-call ledger exactly.
    for entry in doc.get("per_agent", []):
        aid = entry.get("agent_id")
        agent_calls = [c for c in calls if c.get("agent_id") == aid]
        if not agent_calls:
            raise ValueError(f"per_agent entry for {aid!r} has no ledger calls")
        if int(entry.get("total_tokens") or 0) != sum(int(c.get("total_tokens") or 0) for c in agent_calls):
            raise ValueError(f"per_agent[{aid}].total_tokens != sum of its calls")
        if int(entry.get("llm_calls") or 0) != len(agent_calls):
            raise ValueError(f"per_agent[{aid}].llm_calls != number of its calls")
    # The envelope in floor.json must match the run ledger's envelope.
    env = ledger.get("envelope", {})
    for k in ("max_tokens", "max_wall_s", "max_agents"):
        if k in env and doc["envelope"][k] != env[k]:
            raise ValueError(f"envelope.{k} mismatch between floor.json and run ledger")


@pytest.fixture(scope="module")
def floor_fixture() -> tuple[dict, dict]:
    """(floor.json, lead-run budget_ledger.json) — committed fixtures, read-only."""
    doc = json.loads(FLOOR_JSON.read_text(encoding="utf-8"))
    ledger = json.loads(LEAD_LEDGER.read_text(encoding="utf-8"))
    assert doc.get("measured_floor_tokens") is not None
    return doc, ledger


@pytest.fixture(scope="module")
def summary_fixture() -> dict:
    return json.loads(FLOOR_SUMMARY.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# 1. Key gate: refuse cleanly, no network, no artifacts
# ---------------------------------------------------------------------------
def _no_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REPLICLAW_LLM_API_KEY", raising=False)
    monkeypatch.delenv("CUSTOM_SIMULACHAT_KEY", raising=False)


class _RefusingClient:
    """An LLMClient stand-in that raises the documented clean refusal the
    moment any endpoint call is attempted (never opens a connection)."""

    def __init__(self, cfg: Any = None):
        self.cfg = cfg

    def chat_json(self, *a: Any, **k: Any) -> Any:
        raise RuntimeError(
            "No LLM API key configured. Set REPLICLAW_LLM_API_KEY "
            "(or CUSTOM_SIMULACHAT_KEY) or use backend='deterministic'."
        )


def _no_network_client() -> type:
    return _RefusingClient


def test_key_gate_refuses_cleanly_without_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """With no key in the environment, main() must REFUSE cleanly with the
    documented 'No LLM API key' RuntimeError and must NOT construct any
    network client (openai.OpenAI patched to explode). The module's
    LLMClient is spied to record (lazy) construction."""
    _no_key_env(monkeypatch)
    work = tmp_path / "work"

    constructed = {"n": 0}
    orig_build = EESSLiveS5Arm._build_policy

    class _SpyClient(_RefusingClient):
        def __init__(self, cfg: Any = None):
            constructed["n"] += 1
            super().__init__(cfg)

    monkeypatch.setattr(M, "LLMClient", _SpyClient)

    openai_constructed = {"n": 0}

    def _boom_openai(*a: Any, **k: Any):
        openai_constructed["n"] += 1
        raise AssertionError("openai.OpenAI must never be constructed without a key")

    monkeypatch.setattr(openai, "OpenAI", _boom_openai)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["measure_live_token_floor", "--work-dir", str(work)])

    with pytest.raises(RuntimeError, match="No LLM API key"):
        M.main()

    # The real LLMClient class was never used (module seam replaced); the
    # run made exactly one (lazy) client construction and stopped there.
    assert constructed["n"] == 1
    assert openai_constructed["n"] == 0, "a network client was constructed without a key"
    # No artifacts written: no floor.json in the (temp) output dir.
    assert not (tmp_path / "artifacts" / "p08" / "live_token_floor" / "floor.json").exists()
    # The frozen-value patches are rolled back (do NOT persist).
    assert EESSLiveS5Arm._build_policy is orig_build  # type: ignore[attr-defined]
    assert getattr(orch, "LEASE_TTL_S") == 60.0  # module default restored
    # The work dir was created (the arm's run-01/ dir skeleton), but the
    # refused run produced ZERO artifact files in it.
    assert work.is_dir()
    files = [p for p in work.rglob("*") if p.is_file()]
    assert files == [], f"a refused run left artifact files behind: {files}"


def test_key_gate_refusal_does_not_write_floor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Same refusal, from the committed cwd, proving the hardcoded
    artifacts/p08/live_token_floor/floor.json is NOT created by a refused run.
    (Read-only: only asserts absence of a NEW file; the committed file is
    left untouched and re-verified by the sha256 invariant test below.)"""
    _no_key_env(monkeypatch)
    monkeypatch.setattr(M, "LLMClient", _no_network_client())
    monkeypatch.chdir(tmp_path)  # isolate the hardcoded relative output dir
    monkeypatch.setattr(sys, "argv", ["measure_live_token_floor", "--work-dir", str(tmp_path / "w")])

    with pytest.raises(RuntimeError, match="No LLM API key"):
        M.main()

    assert not (tmp_path / "artifacts" / "p08" / "live_token_floor" / "floor.json").exists()


# ---------------------------------------------------------------------------
# 2. Frozen-params constants (prereg §3.1 / D-10)
# ---------------------------------------------------------------------------
def test_frozen_param_constants_match_prereg():
    assert M.LAMBDA_ == 0.5
    assert M.MU_ == 0.5
    assert M.MAX_CYCLES_ == 6
    assert M.LEASE_TTL_S_ == 120.0


def test_frozen_param_types():
    assert isinstance(M.LAMBDA_, float)
    assert isinstance(M.MU_, float)
    assert isinstance(M.MAX_CYCLES_, int)
    assert isinstance(M.LEASE_TTL_S_, float)


def test_constants_match_committed_floor_json(floor_fixture):
    doc, _ = floor_fixture
    assert doc["frozen_params"]["lambda"] == M.LAMBDA_
    assert doc["frozen_params"]["mu"] == M.MU_
    assert doc["frozen_params"]["max_cycles"] == M.MAX_CYCLES_
    assert doc["frozen_params"]["offer_ttl_s"] == M.LEASE_TTL_S_


def test_frozen_params_in_floor_json_reject_drift(floor_fixture):
    doc, _ = floor_fixture
    bad = copy.deepcopy(doc)
    bad["frozen_params"]["lambda"] = 0.25  # drift from the frozen 0.5
    with pytest.raises(ValueError, match="lambda"):
        validate_floor_doc(bad)


# ---------------------------------------------------------------------------
# 3. floor.json / floor_summary.json schema + arithmetic (committed fixtures)
# ---------------------------------------------------------------------------
def test_floor_json_fixture_validates(floor_fixture):
    doc, _ = floor_fixture
    validate_floor_doc(doc)  # must not raise
    assert doc["headroom"]["committed_ceiling_tokens"] == 60_000


def test_floor_json_fixture_arithmetic_vs_ledger(floor_fixture):
    doc, ledger = floor_fixture
    validate_floor_against_ledger_doc(doc, ledger)  # cross-check vs run ledger
    # Per-agent totals == sum of calls (the committed ledger has no
    # agents[] key, so per_agent is [] — validate the arithmetic at the
    # ledger level instead, and cross-check the floor total).
    per_agent_tokens: dict[str, int] = defaultdict(int)
    per_agent_calls: Counter[str] = Counter()
    for c in ledger["calls"]:
        per_agent_tokens[c["agent_id"]] += int(c["total_tokens"])
        per_agent_calls[c["agent_id"]] += 1
    assert sum(per_agent_tokens.values()) == int(doc["measured_floor_tokens"])
    assert dict(per_agent_tokens) == {"alpha": 504, "beta": 400, "gamma": 454}
    assert dict(per_agent_calls) == {"alpha": 2, "beta": 2, "gamma": 2}
    # Headroom margin == 60000 / floor (the script's own formula).
    assert doc["headroom"]["margin_x"] == round(60_000 / int(doc["measured_floor_tokens"]), 2)
    assert doc["headroom"]["measured_usage_fraction"] == round(
        int(doc["measured_floor_tokens"]) / 60_000, 4
    )
    # usage_present flag on every call (judge item 7).
    assert all(c["usage_present"] for c in ledger["calls"])


def test_floor_summary_json_fixture_validates(floor_fixture, summary_fixture):
    doc, _ = floor_fixture
    s = summary_fixture
    assert s["schema"] == "p08.live_token_floor_summary/1"
    # Same frozen §3.1/D-10 params as floor.json.
    assert s["frozen_params"] == doc["frozen_params"]
    assert s["frozen_params"]["lambda"] == 0.5
    assert s["frozen_params"]["max_cycles"] == 6
    runs = s["runs"]
    assert len(runs) >= 1
    per_agent_calls = {"alpha": 2, "beta": 2, "gamma": 2}
    for r in runs:
        assert r["status"] == "completed"
        assert int(r["measured_floor_tokens"]) > 0
        assert int(r["llm_calls"]) == 6
        assert r["llm_calls_per_agent"] == per_agent_calls
        assert (REPO_ROOT / r["work_dir"]).exists(), "run work_dir must exist (read-only)"
    toks = [int(r["measured_floor_tokens"]) for r in runs]
    assert list(s["floor_range_tokens"]) == [min(toks), max(toks)]
    # Headroom re-derived from the WORST (max-token) run vs the 60k ceiling.
    worst = max(toks)
    assert s["headroom_vs_60k"]["max_usage_fraction"] == round(worst / 60_000, 4)
    assert s["headroom_vs_60k"]["min_margin_x"] == round(60_000 / worst, 2)
    # The lead run is the floor.json fixture itself.
    lead = next(r for r in runs if r["harness_seed"] == doc["harness_seed"])
    assert int(lead["measured_floor_tokens"]) == int(doc["measured_floor_tokens"])


# ---------------------------------------------------------------------------
# 4. Failure paths (status != completed / missing usage / zero tokens)
# ---------------------------------------------------------------------------
def test_failure_paths_reject_bad_docs(floor_fixture):
    doc, ledger = floor_fixture

    # (a) status != completed (and not the tolerated aborted_budget).
    bad = copy.deepcopy(doc)
    bad["status"] = "exploded"
    with pytest.raises(ValueError, match="status"):
        validate_floor_against_ledger(bad, ledger)

    # (b) missing usage on a call in a completed run -> void.
    bad2 = copy.deepcopy(doc)
    badled = copy.deepcopy(ledger)
    badled["calls"][0]["usage_present"] = False
    with pytest.raises(ValueError, match="usage"):
        validate_floor_against_ledger(bad2, badled)

    # (c) zero tokens -> not a floor.
    bad3 = copy.deepcopy(doc)
    bad3["measured_floor_tokens"] = 0
    bad3["headroom"]["margin_x"] = None
    bad3["headroom"]["measured_usage_fraction"] = 0.0
    with pytest.raises(ValueError, match="positive"):
        validate_floor_against_ledger(bad3, ledger)

    # (d) floor total not matching its own run ledger -> not a floor.
    bad4 = copy.deepcopy(doc)
    bad4["measured_floor_tokens"] = int(doc["measured_floor_tokens"]) + 1
    bad4["headroom"]["measured_usage_fraction"] = round(bad4["measured_floor_tokens"] / 60_000, 4)
    bad4["headroom"]["margin_x"] = round(60_000 / bad4["measured_floor_tokens"], 2)
    with pytest.raises(ValueError, match="measured_floor_tokens"):
        validate_floor_against_ledger_doc(bad4, ledger)


def test_corrupted_fixture_copy_rejected_not_mutated(tmp_path: Path, floor_fixture):
    """A CORRUPTED TEMP COPY of the committed fixture must be rejected; the
    committed file is never mutated (re-validated from disk, sha256-checked)."""
    doc, ledger = floor_fixture
    committed_sha_before = _sha256(FLOOR_JSON)

    # Corrupt a temp copy (never the committed file).
    corrupt_path = tmp_path / "floor_corrupt.json"
    corrupt = copy.deepcopy(doc)
    corrupt["frozen_params"]["max_cycles"] = 2  # wrong (not the frozen 6)
    corrupt_path.write_text(json.dumps(corrupt), encoding="utf-8")
    loaded = json.loads(corrupt_path.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="max_cycles"):
        validate_floor_doc(loaded)

    # The committed fixture is byte-identical and still valid.
    assert _sha256(FLOOR_JSON) == committed_sha_before
    fresh = json.loads(FLOOR_JSON.read_text(encoding="utf-8"))
    validate_floor_doc(fresh)
    validate_floor_against_ledger_doc(fresh, ledger)


# ---------------------------------------------------------------------------
# 5. End-to-end main() with a stubbed offline arm (no network, no key)
# ---------------------------------------------------------------------------
def test_main_end_to_end_offline_writes_floor_and_exits_0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Exercise main()'s full artifact path offline: a stubbed S5 arm writes
    the same contract files a real arm writes; main() reads them back,
    writes floor.json, and exits 0 (status completed, tokens > 0)."""
    monkeypatch.setitem(__import__("os").environ, "REPLICLAW_LLM_API_KEY", "unused-offline")
    monkeypatch.setattr(M, "EESSLiveS5Arm", _FakeArm)
    monkeypatch.setattr(M, "LLMClient", _no_network_client())  # never used by the stub

    def _boom_openai(*a: Any, **k: Any) -> Any:
        raise AssertionError("openai.OpenAI must never be constructed in an offline test")

    monkeypatch.setattr(openai, "OpenAI", _boom_openai)
    monkeypatch.chdir(tmp_path)  # isolate the hardcoded relative output dir
    seed = 20261010
    monkeypatch.setattr(
        sys, "argv", ["measure_live_token_floor", "--work-dir", str(tmp_path / "work"), "--seed", str(seed)]
    )

    rc = M.main()

    assert rc == 0, "a network client was constructed in a stub run"
    floor_path = tmp_path / "artifacts" / "p08" / "live_token_floor" / "floor.json"
    assert floor_path.exists(), "floor.json was not written"
    doc = json.loads(floor_path.read_text(encoding="utf-8"))
    validate_floor_doc(doc)
    assert doc["status"] == "completed"
    assert doc["arm"] == "S5"
    assert doc["case_id"] == CASE_ID
    assert doc["harness_seed"] == seed
    assert doc["measured_floor_tokens"] == 6 * 52
    assert doc["headroom"]["margin_x"] == round(60_000 / (6 * 52), 2)
    # per_agent is populated from the run's own ledger (this run HAS one).
    assert {e["agent_id"] for e in doc["per_agent"]} == {"alpha", "beta", "gamma"}
    for e in doc["per_agent"]:
        assert e["llm_calls"] == 2
        assert e["total_tokens"] == 2 * 52
    # The contract artifacts exist where the arm writes them.
    assert (tmp_path / "work" / "run-01" / "final_verdict.json").exists()
    assert (tmp_path / "work" / "run-01" / "budget_ledger.json").exists()
    # Frozen-value patches are rolled back after the run.
    assert getattr(orch, "LEASE_TTL_S") == 60.0


def test_main_exit_code_zero_when_budget_aborted_with_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """CURRENT script contract: a budget-aborted run that still measured a
    positive token floor is a USABLE measurement (``ok`` includes
    ``aborted_budget``) -> exit 0, honestly labeled in floor.json."""
    monkeypatch.setitem(__import__("os").environ, "REPLICLAW_LLM_API_KEY", "unused-offline")
    monkeypatch.setattr(M, "EESSLiveS5Arm", _FakeAbortedArm)
    monkeypatch.setattr(M, "LLMClient", _no_network_client())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["measure_live_token_floor", "--work-dir", str(tmp_path / "w")])

    rc = M.main()

    assert rc == 0, "a budget-aborted run with a positive floor is a usable measurement"
    # floor.json is still written, honestly labeled (not hidden).
    floor_path = tmp_path / "artifacts" / "p08" / "live_token_floor" / "floor.json"
    doc = json.loads(floor_path.read_text(encoding="utf-8"))
    assert doc["status"] == "aborted_budget"
    assert doc["measured_floor_tokens"] == 200


def test_main_exit_code_nonzero_when_no_tokens_measured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A run that produced ZERO tokens (e.g. aborted before any LLM call)
    must make main() exit non-zero: ``ok`` requires ``tokens > 0``."""
    monkeypatch.setitem(__import__("os").environ, "REPLICLAW_LLM_API_KEY", "unused-offline")
    monkeypatch.setattr(M, "EESSLiveS5Arm", _FakeZeroTokensArm)
    monkeypatch.setattr(M, "LLMClient", _no_network_client())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["measure_live_token_floor", "--work-dir", str(tmp_path / "w")])

    rc = M.main()

    assert rc == 1, "a run with zero measured tokens must not report a usable floor"
    floor_path = tmp_path / "artifacts" / "p08" / "live_token_floor" / "floor.json"
    doc = json.loads(floor_path.read_text(encoding="utf-8"))
    assert doc["measured_floor_tokens"] == 0
    assert doc["headroom"]["margin_x"] is None  # 60000/0 guarded, not written as a number


# ---------------------------------------------------------------------------
# 6. argv / seed handling (--seed and --work-dir are respected)
# ---------------------------------------------------------------------------
def test_main_honors_seed_and_work_dir_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The current script's main() parses --seed and --work-dir from
    sys.argv; the stub records both and the written floor.json reflects the
    (non-default) seed."""
    monkeypatch.setitem(__import__("os").environ, "REPLICLAW_LLM_API_KEY", "unused-offline")
    seen: dict[str, Any] = {}

    class _RecordingArm(_FakeArm):
        def __init__(self, *a: Any, **k: Any):
            super().__init__(*a, **k)
            seen["harness_seed"] = self.harness_seed  # ctor kwarg from --seed

        def run(self, claim, ledger, spec, work_dir):
            seen["work_dir"] = str(Path(work_dir))  # arg from --work-dir
            return super().run(claim, ledger, spec, work_dir)

    monkeypatch.setattr(M, "EESSLiveS5Arm", _RecordingArm)
    monkeypatch.setattr(M, "LLMClient", _no_network_client())
    monkeypatch.chdir(tmp_path)
    custom_seed = 20261020
    custom_work = tmp_path / "custom_work"
    monkeypatch.setattr(
        sys, "argv", ["measure_live_token_floor", "--work-dir", str(custom_work), "--seed", str(custom_seed)]
    )

    rc = M.main()

    assert rc == 0
    assert seen["harness_seed"] == custom_seed
    assert seen["work_dir"] == str(custom_work)
    doc = json.loads(
        (tmp_path / "artifacts" / "p08" / "live_token_floor" / "floor.json").read_text(encoding="utf-8")
    )
    assert doc["harness_seed"] == custom_seed
    assert doc["work_dir"] == str(custom_work)


# ---------------------------------------------------------------------------
# 7. Invariant: the committed fixtures are never mutated by this suite
# ---------------------------------------------------------------------------
def test_committed_fixtures_untouched():
    """Guard: the read-only committed fixtures are byte-identical to HEAD.
    (If a test ever writes to artifacts/, this fails loudly.)"""
    import subprocess

    out = subprocess.run(
        ["git", "status", "--porcelain", str(FLOOR_JSON), str(FLOOR_SUMMARY)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == "", f"committed fixture artifacts were modified:\n{out.stdout}"
