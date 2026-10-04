"""Comparator harness + matched-budget parity proof for P05.

``ComparatorHarness`` runs every registered arm under ONE shared
``BudgetEnvelope`` and produces a per-arm result table plus a parity report.
``assert_budget_parity`` is the pure function that decides whether a set of
``ArmResult``s constitutes a valid matched-budget comparison:

- every arm must have been given the SAME envelope (identical content hash),
  AND
- no arm may have consumed more than the envelope declared.

If either fails, ``parity`` is ``False`` and the comparison is flagged
invalid — the harness never silently fakes parity.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..investigators import (
    BudgetExceeded,
    DeterministicInvestigator,
    LLMClient,
    LLMInvestigator,
)
from ..models import Claim, InvestigatorConfig
from . import case_loader
from .arms import ArmResult, ArmSpec
from .budget import BudgetEnvelope, BudgetLedger, BudgetOverflow
from .managers import AdaptiveCentralManager, EESSArm, OpenSharingSwarm, SingleAgentBaseline

# Evaluator/sealed-truth fields that must NEVER be carried by an arm-side
# ``Claim``. An arm constructing a REPORTED verdict (or an artifact) from any
# of these would leak the oracle into a scored output. See
# PREREG-2026-10 v1.2 A6 and CODE-JUDGE-HARNESS-20261008 item 3 (the
# harness-layer redaction of the two-layer no-oracle-leak fix).
_ARM_SIDE_TRUTH_FIELDS = ("reference_truth", "seeded_fault")


def redact_claim_for_arms(claim: Claim) -> Claim:
    """Return a copy of ``claim`` with all evaluator/sealed-truth fields
    nulled, for safe hand-off to an arm.

    This is the HARNESS-layer guard of the two-layer no-oracle-leak fix
    (CODE-JUDGE-HARNESS-20261008 item 3): the arm must be constructible
    without any ground-truth label, so no arm object can carry it. The
    fallback-layer guard (``EESSArm._verdict`` no longer consulting
    ``claim.reference_truth``) is defense in depth.

    Returns a NEW ``Claim`` (the caller's object is not mutated); the
    statement/data the arm actually reasons over are preserved.
    """
    return claim.model_copy(update={f: None for f in _ARM_SIDE_TRUTH_FIELDS})


def arm_registry() -> Dict[str, Callable[[Callable[[InvestigatorConfig], Any]], Any]]:
    """The named comparator arms, keyed by arm name.

    Values are constructors taking an investigator factory.
    """
    return {
        "single_agent": SingleAgentBaseline,
        "adaptive_central": AdaptiveCentralManager,
        "open_sharing_swarm": OpenSharingSwarm,
        "eess": EESSArm,
    }


def assert_budget_parity(
    results: List[ArmResult],
    envelope: BudgetEnvelope,
) -> Dict[str, Any]:
    """Decide whether a set of arm results is a valid matched-budget comparison.

    Returns a report dict with:
      * ``parity``            — True only if all arms share one envelope AND
                                none exceeded it;
      * ``n_arms``            — number of arms checked;
      * ``envelope_sha256``   — the envelope hash all arms should match;
      * ``envelope_hashes``   — the set of distinct envelope hashes observed;
      * ``over_budget_arms``  — arms whose reported usage exceeds the envelope.
    """
    expected = envelope.sha256()
    hashes = {r.envelope_sha256 for r in results}
    over = [
        r.arm_name
        for r in results
        if r.total_tokens > envelope.max_tokens
        or r.total_wall_s > envelope.max_wall_s + 1e-9
        or r.n_agents > envelope.max_agents
    ]
    parity = hashes == {expected} and not over
    return {
        "parity": parity,
        "n_arms": len(results),
        "envelope_sha256": expected,
        "envelope_hashes": sorted(hashes),
        "over_budget_arms": over,
    }


class ComparatorHarness:
    """Runs all registered arms under ONE shared envelope and reports parity.

    Each arm gets a FRESH ``BudgetLedger`` bound to the SAME envelope, so an
    arm that overruns the shared budget raises ``BudgetOverflow`` (parity is
    never silently faked). The returned report carries the per-arm results and
    the parity verdict.
    """

    def __init__(self, investigator_factory: Callable[[InvestigatorConfig], Any]):
        self._factory = investigator_factory

    def run(
        self,
        claim: Claim,
        envelope: BudgetEnvelope,
        work_root: Path,
    ) -> Dict[str, Any]:
        work_root = Path(work_root)
        # Harness-layer no-oracle-leak guard: redact evaluator/sealed truth
        # BEFORE any arm is constructed (CODE-JUDGE-HARNESS-20261008 item 3).
        # The shared claim passed to every arm must carry no ground-truth
        # label; ``claim.model_copy`` keeps the caller's object intact.
        claim = redact_claim_for_arms(claim)
        registry = arm_registry()
        results: List[ArmResult] = []
        for name, ctor in registry.items():
            arm = ctor(self._factory)
            ledger = BudgetLedger(envelope)
            spec = ArmSpec(arm_name=name, claim_id=claim.claim_id, envelope=envelope)
            results.append(arm.run(claim, ledger, spec, work_root / name))
        report = assert_budget_parity(results, envelope)
        return {
            "claim_id": claim.claim_id,
            "envelope": envelope.to_dict(),
            "envelope_sha256": envelope.sha256(),
            "arms": {r.arm_name: r.to_dict() for r in results},
            "parity": report,
        }


# ---------------------------------------------------------------------------
# P08 runner CLI (prereg v1.1 §10.1, checklist items 4 / 7 / 8)
# ---------------------------------------------------------------------------
# One arm, one case, one run. Every arm receives the SAME shared Claim built
# by ``case_loader`` (same-task, C1) and a fresh ``BudgetLedger`` bound to the
# SAME declared envelope, so the envelope sha256 is identical across arms.
# Runs with missing usage are INVALIDATED, never zero-filled (judge item 7).
# The D-10 frozen pin (λ=μ=0.5, max_cycles=6, broker TTL=120 s) is enforced by
# ``--assert-frozen`` on the live path.

# Arm CLI labels / registry keys (prereg §3.2, artifact contract §7).
ARM_ALIASES = {
    "S0": "single_agent",
    "S3": "adaptive_central",
    "S4": "open_sharing_swarm",
    "S5": "eess",
    "A1": "eess_no_escrow",
    "A3": "eess_random_select",
    "single_agent": "single_agent",
    "adaptive_central": "adaptive_central",
    "open_sharing_swarm": "open_sharing_swarm",
    "eess": "eess",
    "eess_offline": "eess_offline",  # deterministic 0-token parity arm (v1.1 §3.3)
    "eess_no_escrow": "eess_no_escrow",
    "eess_random_select": "eess_random_select",
}

# Live-LLM arms: CAN run live (primary case) — need a real client (or the fake).
# PREREG-2026-10 v1.2 A8 (RC-1, executor parity): the P1 pair (S5 vs S4) — and
# the RQ2 comparators S3/S0 — run the SAME live-LLM executor as S5 (same
# LLMConfig + harness seed), so all six arms are live ON THE PRIMARY CASE
# (policy_rag_v1). S0/S3/S4 route through the EXISTING comparators arms with an
# LLM investigator factory (see _run_live_strategy), NOT through
# eess_live.live_arm_registry.
#
# DEFECT C1 FIX (case-conditional live-vs-offline): "in LIVE_KEYS" only says an
# arm *can* be live — it is live ONLY on the primary case. On the secondary
# no-LLM case (tox21_ar_agonist) S0/S3/S4 MUST run offline (deterministic,
# exit 0) — that is the frozen v1.1 RQ4/P4 no-LLM sub-study, which pre-dates A8
# and is preserved verbatim (test_p08_runner_cli.tox21 offline arms). S5/A1/A3
# are live-ONLY: they refuse the secondary case (the `if spec.secondary and
# is_live` refusal branch below still fires for them, since is_live stays True
# for them). The decision is computed in run_one_arm as:
#   is_live = (arm_key in LIVE_KEYS) and (not spec.secondary
#             or arm_key in _LIVE_ONLY_KEYS)
LIVE_KEYS = {
    "eess",
    "eess_no_escrow",
    "eess_random_select",
    "single_agent",
    "adaptive_central",
    "open_sharing_swarm",
}
# The three strategy arms that are live on the primary but MUST run offline on
# the secondary no-LLM case (A8 + frozen RQ4/P4). They go through the
# comparators arms + LLMInvestigator when live; they are simply absent from
# LIVE_KEYS on the secondary case, so run_one_arm falls to the offline path.
_LIVE_STRATEGY_KEYS = {"single_agent", "adaptive_central", "open_sharing_swarm"}
# Arms that are live ONLY (refuse the secondary no-LLM case): the EESS-lifecycle
# arms. They never run offline on the secondary — the refusal branch is their
# correct, frozen behaviour (prereg v1.1 H).
_LIVE_ONLY_KEYS = {"eess", "eess_no_escrow", "eess_random_select"}

# D-10 frozen pin (prereg v1.1 §3.2): λ=μ=0.5, max_cycles=6, broker TTL=120 s.
FROZEN_LAM = 0.5
FROZEN_MU = 0.5
FROZEN_MAX_CYCLES = 6
FROZEN_LEASE_TTL_S = 120.0

# Exit codes.
EXIT_OK = 0
EXIT_REFUSAL = 2  # clean, expected refusal (secondary case / bad arm / live gate)
EXIT_RUN_ABORTED = 3  # the arm ran but did not complete (aborted/invalid)


def _det_factory(cfg: InvestigatorConfig) -> DeterministicInvestigator:
    return DeterministicInvestigator(cfg)


def _fake_client(_agent_id: str) -> Any:
    """The offline fake client (no network, deterministic)."""
    from ..eess_live import FakeLLMClient

    return FakeLLMClient()


def _live_client(_agent_id: str) -> Any:
    """A real LLM client (needs REPLICLAW_LLM_ALLOW_LIVE + key)."""
    return LLMClient()


def _tree_sha(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_envelope(
    case_name: str,
    tokens: Optional[int],
    wall: Optional[float],
    agents: Optional[int],
) -> BudgetEnvelope:
    """Build the run envelope; fall back to ``default_envelope`` per field."""
    d = case_loader.default_envelope(case_name)
    return BudgetEnvelope(
        max_tokens=d.max_tokens if tokens is None else int(tokens),
        max_wall_s=d.max_wall_s if wall is None else float(wall),
        max_agents=d.max_agents if agents is None else int(agents),
    )


def _effective_live_params(args: argparse.Namespace) -> Dict[str, Any]:
    """The effective D-10-relevant params for a live run (for --assert-frozen)."""
    return {
        "lam": FROZEN_LAM,
        "mu": FROZEN_MU,
        "max_cycles": args.max_cycles,
        "lease_ttl_s": FROZEN_LEASE_TTL_S,
    }


def _assert_frozen(effective: Dict[str, Any]) -> None:
    """Raise SystemExit(2) if any effective live param deviates from D-10."""
    frozen = {
        "lam": FROZEN_LAM,
        "mu": FROZEN_MU,
        "max_cycles": FROZEN_MAX_CYCLES,
        "lease_ttl_s": FROZEN_LEASE_TTL_S,
    }
    for k, v in frozen.items():
        if abs(float(effective[k]) - float(v)) > 1e-9:
            print(
                f"--assert-frozen: {k}={effective[k]} deviates from the D-10 "
                f"frozen pin {k}={v}",
                file=sys.stderr,
            )
            raise SystemExit(2)


def _write_offline_artifacts(
    run_dir: Path,
    arm_key: str,
    spec: "case_loader.CaseSpec",
    result: ArmResult,
    status: str,
    envelope: BudgetEnvelope,
    harness_seed: int,
    tree_sha: str,
) -> None:
    """Write the contract run layout for offline arms (artifact contract §1).

    Live arms write ``final_verdict.json`` / ``budget_ledger.json`` /
    ``traces.jsonl`` / ``counterfactuals/`` themselves; offline arms (S0/S3/S4
    and ``eess_offline``) account usage at the harness level, so the runner
    writes all four files (plus ``run_metadata.json``) with deterministic
    ``usage_present=true`` 0-token accounting.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    total_tokens = int(getattr(result, "total_tokens", 0) or 0)
    wall = float(getattr(result, "total_wall_s", 0.0) or 0.0)
    n_agents = int(getattr(result, "n_agents", 0) or 1)
    completed = status == "completed"

    # budget_ledger.json — single harness-level call, usage_present=true.
    (run_dir / "budget_ledger.json").write_text(
        json.dumps(
            {
                "schema": "p08.budget_ledger/1",
                "envelope": {**envelope.to_dict(), "sha256": envelope.sha256()},
                "calls": [
                    {
                        "seq": 1,
                        "agent_id": arm_key,
                        "prompt_tokens": total_tokens,
                        "completion_tokens": 0,
                        "total_tokens": total_tokens,
                        "wall_s": round(wall, 6),
                        "usage_present": True,  # offline deterministic accounting
                    }
                ],
                "totals": {
                    "prompt_tokens": total_tokens,
                    "completion_tokens": 0,
                    "total_tokens": total_tokens,
                    "llm_calls": 1,
                    "wall_s": round(wall, 6),
                },
                "overflow_events": [],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    # final_verdict.json
    (run_dir / "final_verdict.json").write_text(
        json.dumps(
            {
                "schema": "p08.final_verdict/1",
                "arm": arm_key,
                "case_id": spec.case_id,
                "run_id": f"{arm_key}/run-01",
                "harness_seed": harness_seed,
                "envelope_sha256": envelope.sha256(),
                "n_agents": n_agents,
                "total_tokens": total_tokens,
                "wall_s": round(wall, 6),
                "status": status,
                "verdict": (str(result.verdict_label).lower() if completed else None),
                "defect_class": None,
                "target_artifact": None,
                "confidence": (
                    float(result.detail.get("confidence") or 0.0) if completed else None
                ),
                "hypotheses": [],
                "counterfactual_slots_granted": 0,
                "counterfactual_slots_executed": 0,
                "integrity_rejections": 0,
                "agent_verdicts": [],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    # traces.jsonl
    lines = [
        {"seq": 1, "agent_id": None, "type": "trace",
         "payload": {"event": "run_start", "arm": arm_key}},
        {"seq": 2, "agent_id": None, "type": "verdict",
         "payload": {"status": status, "verdict": result.verdict_label if completed else None}},
    ]
    (run_dir / "traces.jsonl").write_text(
        "".join(json.dumps(line, sort_keys=True) + "\n" for line in lines),
        encoding="utf-8",
    )


def _run_offline(
    arm_key: str,
    claim: Claim,
    envelope: BudgetEnvelope,
    work_dir: Path,
) -> ArmResult:
    """Run an offline arm (S0/S3/S4/eess_offline) under a fresh shared ledger."""
    if arm_key == "eess_offline":
        arm: Any = EESSArm(_det_factory)
    else:
        ctor = {"single_agent": SingleAgentBaseline,
                "adaptive_central": AdaptiveCentralManager,
                "open_sharing_swarm": OpenSharingSwarm}[arm_key]
        arm = ctor(_det_factory)
    spec_arm = ArmSpec(arm_name=arm_key, claim_id=claim.claim_id, envelope=envelope)
    return arm.run(claim, BudgetLedger(envelope), spec_arm, work_dir)


def _run_live(
    arm_key: str,
    claim: Claim,
    envelope: BudgetEnvelope,
    work_dir: Path,
    client_factory: Callable[[str], Any],
    args: argparse.Namespace,
) -> ArmResult:
    """Run a live arm (S5/A1/A3) through ``eess_live`` (real or fake client)."""
    from ..eess_live import live_arm_registry

    arm = live_arm_registry()[arm_key](
        client_factory,
        max_cycles=args.max_cycles,
        harness_seed=args.harness_seed,
        lam=FROZEN_LAM,
        mu=FROZEN_MU,
        lease_ttl_s=FROZEN_LEASE_TTL_S,
    )
    spec_arm = ArmSpec(arm_name=arm_key, claim_id=claim.claim_id, envelope=envelope)
    return arm.run(claim, BudgetLedger(envelope), spec_arm, work_dir)


def _live_client_identity(client_factory: Callable[[str], Any]) -> tuple[str, str, float]:
    """(model, endpoint, temperature) of ONE representative live client.

    A8: the derivation is factored out of the EESS-only branch so the SAME
    live-client identity (same LLMConfig) is recorded for all six live arms —
    S5/A1/A3 and the newly-live S0/S3/S4 — in ``run_metadata.json``.
    """
    probe = client_factory("identity-probe")
    return str(probe.cfg.model), str(probe.cfg.base_url), float(probe.cfg.temperature)


def _llm_investigator_factory(
    client_factory: Callable[[str], Any],
) -> Callable[[InvestigatorConfig], LLMInvestigator]:
    """An LLM investigator factory: fresh ``LLMInvestigator`` per agent.

    Each investigator gets its OWN client built from ``client_factory`` keyed
    by the investigator's ``agent_id`` — the same per-agent fresh-client
    pattern the live EESS arms use, so usage accounting is exact and all
    investigators share the live client's model/temperature/seed. This is the
    A8 same-executor baseline: the arm's existing investigator-factory seam is
    filled with ``LLMInvestigator`` instead of ``DeterministicInvestigator``.
    """

    def factory(cfg: InvestigatorConfig) -> LLMInvestigator:
        return LLMInvestigator(cfg, client_factory(cfg.agent_id))

    return factory


def _run_live_strategy(
    arm_key: str,
    claim: Claim,
    envelope: BudgetEnvelope,
    work_dir: Path,
    client_factory: Callable[[str], Any],
    args: argparse.Namespace,
) -> ArmResult:
    """Run a newly-live strategy arm (S0/S3/S4, A8) on the LIVE LLM path.

    Builds the EXISTING comparators arm (``SingleAgentBaseline`` /
    ``AdaptiveCentralManager`` / ``OpenSharingSwarm``) with an LLM investigator
    factory — the same live ``LLMConfig`` and harness seed as S5 — so the P1
    pair (S5 vs S4) and the RQ2 comparators (S3, S0) are like-for-like
    executors. Deliberately NOT routed through ``eess_live.live_arm_registry``
    (that registry is EESS-lifecycle-specific); the routing stays here. Real
    token accounting applies (usage from the LLM clients); the offline
    nominal ``COST_TOKENS_PER_ARM`` must not apply to these arms.

    ``work_dir`` is the arm's CONTRACT directory ``<out>/run-01``; the arm's
    shared ``run_strategy`` runner writes its own artifacts under
    ``work_dir/run`` (a RunStore layout, i.e. ``<out>/run-01/run``). The RunStore
    is nested INSIDE the contract dir so ``score.discover_runs`` sees exactly one
    run dir per arm (a stray ``<out>/run`` would be discovered as a second,
    contract-less run dir and fail the completeness gate). The P08 contract
    files are written to the same ``work_dir`` (``<out>/run-01``) by
    :func:`_write_live_strategy_artifacts`, which the caller invokes from
    ``run_one_arm`` (so they are written for a completed
    OR an aborted run, exactly as the offline path does).
    """
    ctor = {
        "single_agent": SingleAgentBaseline,
        "adaptive_central": AdaptiveCentralManager,
        "open_sharing_swarm": OpenSharingSwarm,
    }[arm_key]
    arm: Any = ctor(_llm_investigator_factory(client_factory))
    spec_arm = ArmSpec(arm_name=arm_key, claim_id=claim.claim_id, envelope=envelope)
    return arm.run(claim, BudgetLedger(envelope), spec_arm, work_dir)


def _write_live_strategy_artifacts(
    run_dir: Path,
    arm_key: str,
    case_id: str,
    result: ArmResult,
    status: str,
    envelope: BudgetEnvelope,
    harness_seed: int,
) -> None:
    """Write the P08 contract run layout for a live strategy arm (S0/S3/S4).

    Mirrors :func:`_write_offline_artifacts` (same schemas/keys) but the
    ledger carries the arm's REAL LLM token usage (usage_present=true) rather
    than the offline nominal ``COST_TOKENS_PER_ARM``. The arm's own RunStore
    artifacts live under ``work_dir/run`` and remain as supplementary detail;
    these three files (plus the runner's ``run_metadata.json``) are the
    contract surface the scorer reads. ``status`` is the run's terminal status
    ("completed" / "aborted_budget"), same as the offline writer.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    total_tokens = int(getattr(result, "total_tokens", 0) or 0)
    wall = float(getattr(result, "total_wall_s", 0.0) or 0.0)
    n_agents = int(getattr(result, "n_agents", 0) or 1)
    completed = status == "completed"

    (run_dir / "budget_ledger.json").write_text(
        json.dumps(
            {
                "schema": "p08.budget_ledger/1",
                "envelope": {**envelope.to_dict(), "sha256": envelope.sha256()},
                "calls": [
                    {
                        "seq": 1,
                        "agent_id": arm_key,
                        "prompt_tokens": total_tokens,
                        "completion_tokens": 0,
                        "total_tokens": total_tokens,
                        "wall_s": round(wall, 6),
                        "usage_present": True,  # real LLM usage (A8 live arm)
                    }
                ],
                "totals": {
                    "prompt_tokens": total_tokens,
                    "completion_tokens": 0,
                    "total_tokens": total_tokens,
                    "llm_calls": 1,
                    "wall_s": round(wall, 6),
                },
                "overflow_events": [],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    (run_dir / "final_verdict.json").write_text(
        json.dumps(
            {
                "schema": "p08.final_verdict/1",
                "arm": arm_key,
                "case_id": case_id,
                "run_id": f"{arm_key}/run-01",
                "harness_seed": harness_seed,
                "envelope_sha256": envelope.sha256(),
                "n_agents": n_agents,
                "total_tokens": total_tokens,
                "wall_s": round(wall, 6),
                "status": status,
                "verdict": (str(result.verdict_label).lower() if completed else None),
                "defect_class": None,
                "target_artifact": None,
                "confidence": (
                    float(result.detail.get("confidence") or 0.0) if completed else None
                ),
                "hypotheses": [],
                "counterfactual_slots_granted": 0,
                "counterfactual_slots_executed": 0,
                "integrity_rejections": 0,
                "agent_verdicts": [],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    lines = [
        {"seq": 1, "agent_id": None, "type": "trace",
         "payload": {"event": "run_start", "arm": arm_key, "executor": "llm"}},
        {"seq": 2, "agent_id": None, "type": "verdict",
         "payload": {"status": status,
                     "verdict": result.verdict_label if completed else None}},
    ]
    (run_dir / "traces.jsonl").write_text(
        "".join(json.dumps(line, sort_keys=True) + "\n" for line in lines),
        encoding="utf-8",
    )


def run_one_arm(args: argparse.Namespace) -> int:
    """Run one arm on one case and write the contract artifacts. Returns exit code."""
    root = Path.cwd()
    try:
        spec = case_loader.resolve_case(args.case, root)
    except case_loader.CaseNotSupportedError as e:
        print(f"case: {e}", file=sys.stderr)
        return EXIT_REFUSAL

    arm_key = ARM_ALIASES.get(args.arm)
    if arm_key is None:
        print(f"arm: unknown arm {args.arm!r}; expected one of {sorted(ARM_ALIASES)}",
              file=sys.stderr)
        return EXIT_REFUSAL

    # A8 (RC-1, executor parity) + DEFECT C1 FIX (case-conditional live-vs-
    # offline). Membership in LIVE_KEYS only says an arm CAN be live; the arm
    # IS live iff:
    #   - primary case   -> every LIVE_KEYS arm is live (all six, incl. S0/S3/S4);
    #   - secondary case -> ONLY the live-only arms (S5/A1/A3) stay live.
    # S0/S3/S4 therefore run OFFLINE (deterministic, exit 0) on the secondary
    # no-LLM case tox21_ar_agonist — that is the frozen v1.1 RQ4/P4 sub-study,
    # preserved verbatim (test_p08_runner_cli.tox21 offline arms). S5/A1/A3 are
    # live on BOTH cases; the refusal branch below fires exactly for them.
    is_live = arm_key in LIVE_KEYS and (not spec.secondary or arm_key in _LIVE_ONLY_KEYS)

    # Secondary (no-LLM) case: refuse the live-ONLY arms (S5/A1/A3) cleanly
    # (exit 2, not a crash). S0/S3/S4 are no longer live on the secondary case
    # (C1) so they fall through to the offline path instead of refusing.
    if spec.secondary and is_live:
        print(
            f"refusal: live arm {arm_key!r} cannot run the secondary no-LLM case "
            f"{spec.case_id!r} (prereg v1.1 H); use the offline arms",
            file=sys.stderr,
        )
        return EXIT_REFUSAL

    # Same-task (C1): the rooted offline EESS slice is only valid on policy_rag.
    try:
        claim = case_loader.load_arm_claim(spec.case_id, root)
    except case_loader.CaseNotSupportedError as e:
        print(f"case: {e}", file=sys.stderr)
        return EXIT_REFUSAL
    # PREREG-2026-10 v1.2 A6 / CODE-JUDGE-HARNESS item 3: the CLI path runs
    # arms directly (bypassing ComparatorHarness.run), so redact evaluator
    # truth at the CLI level too — before any arm is constructed. Envelope
    # hashing uses claim.statement only, so this does not break the C1
    # shared-envelope-hash contract.
    claim = redact_claim_for_arms(claim)
    try:
        case_loader.assert_same_task(arm_key, spec, claim)
    except case_loader.CaseNotSupportedError as e:
        print(f"same-task: {e}", file=sys.stderr)
        return EXIT_REFUSAL

    envelope = _resolve_envelope(
        spec.case_id, args.envelope_tokens, args.envelope_wall, args.envelope_agents
    )

    # D-10 frozen pin: check BEFORE any run (live path only).
    if args.assert_frozen:
        _assert_frozen(_effective_live_params(args))

    out = Path(args.out)
    # Task spec: --out DIR, each arm writes DIR/run-01 (artifact contract §10.3:
    # S0|S3|.../run-01/). The P08 CONTRACT files (final_verdict / budget_ledger /
    # traces / run_metadata) always live at <out>/run-01, which is the ONLY
    # subdirectory of <out>/ that score.discover_runs must treat as a run dir.
    #
    # work_dir is the arm's working root:
    #  * EESS live arms (S5/A1/A3) nest their internal RunStore inside the
    #    contract dir (out/runs or out/run-01/runs) -> pass work_dir=out as before.
    #  * A8 strategy arms (S0/S3/S4) write their RunStore to <work_dir>/run; we
    #    pass work_dir=<out>/run-01 so that RunStore nests INSIDE the contract
    #    dir (<out>/run-01/run). A stray top-level <out>/run would otherwise be
    #    discovered as a second, contract-less run dir and fail the scorer's
    #    completeness gate (A8 code-judge BLOCKER #1).
    run_dir = out / "run-01"
    if arm_key in _LIVE_STRATEGY_KEYS:
        work_dir = run_dir          # strategy arm: nest RunStore under run-01/
    elif is_live:
        work_dir = out              # EESS arm: unchanged (RunStore already nested)
    else:
        work_dir = run_dir          # offline: contract files written into run-01
    work_dir.mkdir(parents=True, exist_ok=True)

    status = "completed"
    result: Optional[ArmResult] = None
    client_model: Optional[str] = None
    client_endpoint: Optional[str] = None
    client_temperature: Optional[float] = None
    client_factory: Optional[Callable[[str], Any]] = None
    t0 = time.monotonic()
    try:
        if is_live:
            # A8 (executor parity): factor the live-client identity derivation
            # out of the EESS-only branch so it works for ALL six live arms
            # (S5/A1/A3 route through eess_live; S0/S3/S4 route through the
            # comparators arms with an LLM investigator factory).
            if args.client_factory == "fake":
                client_factory = _fake_client
                # Record the fake client's declared identity, not LLMConfig
                # defaults (which point at a real endpoint).
                (
                    client_model,
                    client_endpoint,
                    client_temperature,
                ) = _live_client_identity(client_factory)
            else:  # "live"
                if not os.environ.get("REPLICLAW_LLM_ALLOW_LIVE", ""):
                    print(
                        f"refusal: live arm {arm_key!r} needs REPLICLAW_LLM_ALLOW_LIVE=1 "
                        "(authorized orchestrator, prereg two-key start) or "
                        "--client-factory fake",
                        file=sys.stderr,
                    )
                    return EXIT_REFUSAL
                client_factory = _live_client
                (
                    client_model,
                    client_endpoint,
                    client_temperature,
                ) = _live_client_identity(client_factory)
            if arm_key in _LIVE_STRATEGY_KEYS:
                result = _run_live_strategy(
                    arm_key, claim, envelope, work_dir, client_factory, args
                )
            else:
                result = _run_live(arm_key, claim, envelope, work_dir, client_factory, args)
        else:
            result = _run_offline(arm_key, claim, envelope, work_dir)
    except BudgetOverflow:
        status = "aborted_budget"
    except BudgetExceeded:
        status = "aborted_budget"
    except Exception as exc:  # usage-invalidation / unexpected live failure
        # A live arm whose LLM usage was missing reports invalid_usage.
        from ..eess_live.budget_calls import InvalidUsageError

        if isinstance(exc, InvalidUsageError):
            status = "invalid_usage"
        else:
            raise
    if result is None:
        # The arm raised (aborted_budget / invalid_usage): build a placeholder
        # ArmResult so the contract files still carry a consistent record.
        result = ArmResult(
            arm_name=arm_key,
            claim_id=claim.claim_id,
            verdict_label="ABORTED",
            n_agents=0,
            total_tokens=0,
            total_wall_s=0.0,
            envelope_sha256=envelope.sha256(),
            detail={"aborted": True, "status": status},
        )

    # Propagate a live arm's own terminal status (e.g. invalid_usage).
    live_status = result.detail.get("status") if isinstance(result.detail, dict) else None
    if is_live and live_status in ("aborted_budget", "invalid_usage"):
        status = live_status

    if not is_live:
        _write_offline_artifacts(run_dir, arm_key, spec, result, status, envelope,
                                 args.harness_seed, _tree_sha(root))
    elif arm_key in _LIVE_STRATEGY_KEYS:
        # A8: the newly-live S0/S3/S4 arms write their own P08 contract
        # files (final_verdict / budget_ledger / traces) under run-01, the
        # same layout as the offline arms, with real LLM usage. run_metadata
        # is written below for every arm.
        _write_live_strategy_artifacts(run_dir, arm_key, spec.case_id, result,
                                       status, envelope, args.harness_seed)

    # run_metadata.json — runner CLI (artifact contract §1) with D-10 params.
    effective = _effective_live_params(args) if is_live else {}
    meta = {
        "schema": "p08.run_metadata/1",
        "arm": arm_key,
        "arm_key": arm_key,
        "case_id": spec.case_id,
        "run_id": f"{arm_key}/run-01",
        "harness_seed": args.harness_seed,
        "envelope_sha256": envelope.sha256(),
        "envelope": {**envelope.to_dict(), "sha256": envelope.sha256()},
        "status": status,
        "tree_sha": _tree_sha(root),
        "model": client_model if is_live else "deterministic",
        "endpoint": client_endpoint if is_live else "offline",
        "temperature": client_temperature,  # live client only; null otherwise
        "offline_arm": not is_live,
        "client_factory": "none" if not is_live else args.client_factory,
        # D-10 frozen pin (live path only).
        "lam": effective.get("lam"),
        "mu": effective.get("mu"),
        "max_cycles": effective.get("max_cycles"),
        "lease_ttl_s": effective.get("lease_ttl_s"),
        "start_ts": _now_iso(),
        "end_ts": _now_iso(),
        "wall_s": round(time.monotonic() - t0, 6),
    }
    (run_dir / "run_metadata.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(json.dumps(
        {"arm": arm_key, "case": spec.case_id, "status": status,
         "run_dir": str(run_dir), "wall_s": round(time.monotonic() - t0, 3)},
        sort_keys=True,
    ))
    return EXIT_OK if status == "completed" else EXIT_RUN_ABORTED


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m repliclaw.comparators.runner",
        description="P08 runner: one arm, one case, one run (prereg v1.1 §10.1).",
    )
    parser.add_argument("--arm", required=True,
                        help="S0 S3 S4 S5 A1 A3 or a registry key "
                             "(single_agent/adaptive_central/open_sharing_swarm/eess/"
                             "eess_offline/eess_no_escrow/eess_random_select)")
    parser.add_argument("--case", required=True,
                        help="policy_rag | tox21_ar_agonist (or the case dir)")
    parser.add_argument("--envelope-tokens", type=int, default=None)
    parser.add_argument("--envelope-wall", type=float, default=None)
    parser.add_argument("--envelope-agents", type=int, default=None)
    parser.add_argument("--harness-seed", type=int, default=20261010)
    parser.add_argument("--max-cycles", type=int, default=FROZEN_MAX_CYCLES,
                        help="live-arm cycle cap (D-10 frozen pin = 6)")
    parser.add_argument("--out", required=True,
                        help="run dir; each arm writes <out>/run-01 (artifact §10.3)")
    parser.add_argument("--client-factory", choices=("fake", "live"), default="fake",
                        help="fake=FakeLLMClient (offline) | live=LLMClient (needs key)")
    parser.add_argument("--assert-frozen", action="store_true",
                        help="exit non-zero if an effective live param deviates from D-10")
    args = parser.parse_args(argv)
    return run_one_arm(args)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ComparatorHarness",
    "arm_registry",
    "assert_budget_parity",
    "redact_claim_for_arms",
    "main",
]
