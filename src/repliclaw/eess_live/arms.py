"""Comparator-arm adapters for the live EESS lifecycle (P08 contract §2/§3/§4).

Three live arms share ONE lifecycle (:class:`LiveEESSOrchestrator`); they
differ only in plumbing, exactly as preregistered (PREREG-2026-10 §3):

* ``S5`` (``eess_live_s5``)     — EscrowedEscrow + LocalEigPolicy (canonical)
* ``A1`` (``a1_no_escrow``)     — PassThroughEscrow + LocalEigPolicy
* ``A3`` (``a3_random_select``) — EscrowedEscrow + RandomPolicy

Each ``run()`` writes the full P08 artifact set for one run directory
(``final_verdict.json``, ``budget_ledger.json``, ``traces.jsonl``,
``counterfactuals/``) and returns the common ``ArmResult`` schema so the
matched-budget parity check (identical ``envelope_sha256`` across arms)
applies to the live arms exactly as it does to the offline arms.

``run_metadata.json`` is written by the runner CLI, not by the arm
(contract §1 — the arm's artifacts must carry no run-level provenance that
only the harness knows).

Arm-side code NEVER reads an oracle (contract §5; M4 leakage grep).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ..comparators.arms import ArmResult, ArmSpec
from ..comparators.budget import BudgetLedger, BudgetRecord
from ..models import Claim
from ..needmarket.policy import LocalEigPolicy, RandomPolicy
from .escrow import EscrowedEscrow, LiveEscrow, PassThroughEscrow
from .orchestrator import LiveEESSOrchestrator, LiveRunResult

FINAL_VERDICT_KEYS = [
    "schema",
    "arm",
    "case_id",
    "run_id",
    "harness_seed",
    "envelope_sha256",
    "n_agents",
    "total_tokens",
    "wall_s",
    "status",
    "verdict",
    "defect_class",
    "target_artifact",
    "confidence",
    "hypotheses",
    "counterfactual_slots_granted",
    "counterfactual_slots_executed",
    "integrity_rejections",
    "agent_verdicts",
    # Documented extension (P08 build note, judge item 7): per-call usage
    # presence + totals so "usage missing => void" is checkable from artifact.
    "usage",
]


def write_counterfactuals(orch: LiveEESSOrchestrator, result: LiveRunResult, run_dir: Path) -> None:
    """One file per EXECUTED counterfactual slot (contract §1/§4).

    Contents are the verified run's measured effect plus the corresponding
    committed-packet fields — the arm's own output, never oracle fields.
    """
    cf_dir = run_dir / "counterfactuals"
    cf_dir.mkdir(parents=True, exist_ok=True)
    for arm, run in sorted(orch.run_cache.items()):
        hyp = next((h for h in result.hypotheses if h.get("counterfactual_slot") == arm), None)
        doc = {
            "schema": "p08.counterfactual/1",
            "arm": arm,
            "run_id": run.run_id,
            "case_id": run.case_id,
            "seed": run.seed,
            "verified": bool(run.artifact_hashes),
            "severity": run.severity,
            "token_counts": run.token_counts,
            "provenance": {
                "config_sha256": run.config_sha256,
                "case_sha256": run.case_sha256,
                "artifact_hashes": run.artifact_hashes,
            },
            "hypothesis_id": hyp["id"] if hyp else None,
            "hypothesis_outcome": hyp["outcome"] if hyp else None,
        }
        (cf_dir / f"{arm}.json").write_text(
            json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8"
        )


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


class EESSLiveArm:
    """One live EESS arm (S5/A1/A3) under the ``ComparatorArm`` protocol.

    ``client_factory(agent_id)`` builds the per-agent LLM client — a fresh
    client per agent so snapshot-delta usage accounting is exact. Tests pass
    a :class:`FakeLLMClient` factory (no network); P08b passes a real
    ``LLMClient`` factory. The optional ``investigator_factory`` is accepted
    for constructor-signature compatibility with the offline registry but is
    unused: the live arms are driven by an LLM *client* factory, not the
    offline investigator factory the :class:`ComparatorHarness` hands its
    arms.
    """

    arm_label: str = "S5"
    strategy: str = "eess_live_s5"
    escrow_kind: str = "escrowed"
    policy_kind: str = "eig"
    n_agents = 3
    harness_seed: int = 20261010

    def __init__(
        self,
        client_factory: Callable[[str], Any],
        *,
        investigator_factory: Optional[Callable] = None,
        max_cycles: int = 2,
        harness_seed: int = 20261010,
    ) -> None:
        self._client_factory = client_factory
        self._investigator_factory = investigator_factory  # signature parity only
        self._max_cycles = max_cycles
        self.harness_seed = int(harness_seed)

    # -- ComparatorArm --------------------------------------------------------
    def name(self) -> str:
        return self.arm_label

    def run(
        self,
        claim: Claim,
        ledger: BudgetLedger,
        spec: ArmSpec,
        work_dir: Path,
    ) -> ArmResult:
        work_dir = Path(work_dir)
        run_dir = work_dir / f"{self.arm_label}/run-01"
        run_dir.mkdir(parents=True, exist_ok=True)

        escrow = self._build_escrow(run_dir)
        orch = LiveEESSOrchestrator(
            claim=claim,
            out_root=run_dir,
            escrow=escrow,
            policy_factory=lambda _a: self._build_policy(),
            client_factory=self._client_factory,
            envelope=spec.envelope,
            harness_seed=self.harness_seed,
            max_cycles=self._max_cycles,
        )
        t0 = time.monotonic()
        result = orch.run()
        wall = max(0.0, time.monotonic() - t0)

        # Usage-invalidation (judge item 7 / Q13): any call without reported
        # usage voids the run — it is never zero-filled and is excluded from
        # M1 by the scorer.
        status = result.status
        if status == "completed" and not result.usage.get("usage_present_all_calls", True):
            status = "invalid_usage"
            orch.ledger.record_overflow(
                "a call reported no usage fields; run invalidated (never zero-filled)",
                kind="invalid_usage",
            )
            result.traces.append(
                {
                    "seq": len(result.traces) + 1,
                    "ts": _now_iso(),
                    "agent_id": None,
                    "type": "usage_invalid",
                    "payload": {"kind": "invalid_usage"},
                }
            )
            result.budget_ledger = orch.ledger.to_contract_dict()

        self._write_artifacts(orch, result, spec, run_dir, status, wall)

        # Report consumption to the shared matched-budget ledger (raises on
        # overrun — parity is never faked). The orchestrator already enforced
        # the same envelope per-call, so this is an aggregation, not a gate.
        tokens = orch.ledger.total_tokens
        n_agents = max(1, orch.ledger.distinct_agents)
        if tokens > 0 or wall > 0:
            ledger.record(
                BudgetRecord(
                    agent_id=f"{self.arm_label}-arm",
                    tokens=tokens,
                    wall_s=wall,
                    n_agents=0,  # distinct-agent cap already enforced per-call
                )
            )

        return ArmResult(
            arm_name=self.arm_label,
            claim_id=claim.claim_id,
            verdict_label=result.verdict or "uncertain",
            n_agents=n_agents,
            total_tokens=tokens,
            total_wall_s=wall,
            envelope_sha256=spec.envelope.sha256(),
            detail={
                "strategy": self.strategy,
                "eess_live": True,
                "status": status,
                "confidence": result.confidence,
                "defect_class": result.defect_class,
                "target_artifact": result.target_artifact,
                "slots_granted": result.counterfactual_slots_granted,
                "slots_executed": result.counterfactual_slots_executed,
                "integrity_rejections": result.integrity_rejections,
                "llm_calls": result.usage.get("totals", {}).get("llm_calls", 0),
                "run_dir": str(run_dir),
            },
        )

    # -- seams -----------------------------------------------------------------
    def _build_escrow(self, run_dir: Path) -> LiveEscrow:
        if self.escrow_kind == "pass_through":
            return PassThroughEscrow()
        return EscrowedEscrow(run_dir / "escrow", worker_id=f"live-{self.arm_label}")

    def _build_policy(self) -> Any:
        if self.policy_kind == "random":
            return RandomPolicy()
        return LocalEigPolicy({})

    @staticmethod
    def _write_artifacts(
        orch: LiveEESSOrchestrator,
        result: LiveRunResult,
        spec: ArmSpec,
        run_dir: Path,
        status: str,
        wall: float,
    ) -> None:
        run_id = f"{spec.arm_name}/run-01"
        final_verdict: Dict[str, Any] = {
            "schema": "p08.final_verdict/1",
            "arm": spec.arm_name,
            "case_id": orch.case.case_id,
            "run_id": run_id,
            "harness_seed": orch.harness_seed,
            "envelope_sha256": spec.envelope.sha256(),
            "n_agents": result.n_agents,
            "total_tokens": result.total_tokens,
            "wall_s": round(wall, 6),
            "status": status,
            "verdict": result.verdict if status == "completed" else None,
            "defect_class": result.defect_class if status == "completed" else None,
            "target_artifact": result.target_artifact if status == "completed" else None,
            "confidence": result.confidence if status == "completed" else None,
            "hypotheses": result.hypotheses,
            "counterfactual_slots_granted": result.counterfactual_slots_granted,
            "counterfactual_slots_executed": result.counterfactual_slots_executed,
            "integrity_rejections": result.integrity_rejections,
            "agent_verdicts": result.agent_verdicts,
            # Documented extension (P08 build note): per-call usage presence +
            # totals, so the scorer can enforce "usage missing => void" from
            # the artifact alone (contract §3's per-call usage_present flag).
            "usage": result.usage,
        }
        assert set(final_verdict) == set(FINAL_VERDICT_KEYS), (
            set(final_verdict) ^ set(FINAL_VERDICT_KEYS)
        )
        (run_dir / "final_verdict.json").write_text(
            json.dumps(final_verdict, indent=2, sort_keys=True), encoding="utf-8"
        )
        (run_dir / "budget_ledger.json").write_text(
            json.dumps(result.budget_ledger, indent=2, sort_keys=True), encoding="utf-8"
        )
        with (run_dir / "traces.jsonl").open("w", encoding="utf-8") as f:
            for ev in result.traces:
                f.write(
                    json.dumps(
                        {
                            "seq": ev["seq"],
                            "ts": ev.get("ts", _now_iso()),
                            "agent_id": ev.get("agent_id"),
                            "type": ev["type"],
                            "payload": ev["payload"],
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
        write_counterfactuals(orch, result, run_dir)


class EESSLiveS5Arm(EESSLiveArm):
    """S5 — the canonical live EESS arm (escrow + local EIG ranking)."""

    arm_label = "S5"
    strategy = "eess_live_s5"
    escrow_kind = "escrowed"
    policy_kind = "eig"


class EESSNoEscrowArm(EESSLiveArm):
    """A1 — identical to S5 with the escrow replaced by a pass-through
    (prereg §3: the single-factor "no escrow" ablation)."""

    arm_label = "A1"
    strategy = "a1_no_escrow"
    escrow_kind = "pass_through"
    policy_kind = "eig"


class EESSRandomSelectArm(EESSLiveArm):
    """A3 — identical to S5 with need-ranking replaced by a seeded uniform
    random policy (prereg §3: the single-factor "random selection" ablation)."""

    arm_label = "A3"
    strategy = "a3_random_select"
    escrow_kind = "escrowed"
    policy_kind = "random"


__all__ = [
    "EESSLiveArm",
    "EESSLiveS5Arm",
    "EESSNoEscrowArm",
    "EESSRandomSelectArm",
    "write_counterfactuals",
]
