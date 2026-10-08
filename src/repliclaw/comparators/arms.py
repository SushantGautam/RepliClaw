"""Common arm interface + result schema for P05 comparators.

Every comparator arm — the EESS swarm and its baselines — is a
``ComparatorArm`` that runs one claim under a shared ``BudgetEnvelope`` and
returns a comparable, frozen ``ArmResult``. Keeping the result schema
identical across arms is what makes the comparison honest: the benchmark can
line up correctness, cost, and latency on equal footing.

The arms deliberately do NOT re-implement the scientific task or the verdict
engine. They reuse the shared ``run_strategy`` runner (which already wraps the
five coordination baselines over ONE shared task interface) so that the only
thing that differs between arms is the COORDINATION REGIME, never the code
(DECISIONS.md: baselines differ only in coordination regime, not code).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Protocol, runtime_checkable

from ..models import Claim, InvestigatorConfig
from ..strategies import run_strategy
from .budget import BudgetEnvelope, BudgetLedger, BudgetRecord


@dataclass(frozen=True)
class ArmSpec:
    """The declaration handed to an arm: which arm, which claim, which budget."""

    arm_name: str
    claim_id: str
    envelope: BudgetEnvelope


@dataclass(frozen=True)
class ArmResult:
    """A comparable, tamper-evident record of one arm's run.

    ``envelope_sha256`` is the content hash of the envelope the arm was
    actually given — the parity check compares these across arms to prove the
    comparison ran at matched budgets.
    """

    arm_name: str
    claim_id: str
    verdict_label: str
    n_agents: int
    total_tokens: int
    total_wall_s: float
    envelope_sha256: str
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "arm_name": self.arm_name,
            "claim_id": self.claim_id,
            "verdict_label": self.verdict_label,
            "n_agents": self.n_agents,
            "total_tokens": self.total_tokens,
            "total_wall_s": round(self.total_wall_s, 6),
            "envelope_sha256": self.envelope_sha256,
            "detail": self.detail,
        }


@runtime_checkable
class ComparatorArm(Protocol):
    """Interface every comparator arm implements."""

    def name(self) -> str: ...

    def run(
        self,
        claim: Claim,
        ledger: BudgetLedger,
        spec: ArmSpec,
        work_dir: Path,
    ) -> ArmResult: ...


class ArmRunner:
    """Base class: runs a named strategy under a shared envelope + ledger.

    Subclasses pick a strategy name and (optionally) how many investigators
    the strategy deploys. The runner:

    1. runs the strategy via the shared ``run_strategy`` runner;
    2. records the observed consumption against the ledger (which raises
       ``BudgetOverflow`` if the arm overruns the shared envelope);
    3. returns a frozen ``ArmResult`` carrying the envelope's content hash.

    Wall-clock is measured with a deterministic floor (0.0) so the offline
    suite is reproducible; the ledger's wall cap is still enforced from the
    measured value.
    """

    strategy: str = ""
    n_agents: int = 1
    # The arm's own label (defaults to the strategy name). Subclasses that
    # wrap a strategy under a distinct comparator name override this.
    arm_label: str = ""

    def __init__(self, investigator_factory: Callable[[InvestigatorConfig], Any]):
        self._factory = investigator_factory

    def name(self) -> str:
        return self.arm_label or self.strategy

    def run(
        self,
        claim: Claim,
        ledger: BudgetLedger,
        spec: ArmSpec,
        work_dir: Path,
    ) -> ArmResult:
        work_dir = Path(work_dir)
        t0 = time.monotonic()
        res = run_strategy(self.strategy, claim, self._factory, work_dir)
        wall = max(0.0, time.monotonic() - t0)
        n_agents = len({e.agent_id for e in res.evidence}) or 1
        # Record the arm's observed consumption against the shared envelope.
        # The ledger raises BudgetOverflow if any cap would be exceeded.
        ledger.record(
            BudgetRecord(
                agent_id=f"{self.strategy}-arm",
                tokens=res.usage.total_tokens,
                wall_s=wall,
                n_agents=n_agents,
            )
        )
        return ArmResult(
            arm_name=self.name(),
            claim_id=claim.claim_id,
            verdict_label=res.verdict.label.value,
            n_agents=n_agents,
            total_tokens=res.usage.total_tokens,
            total_wall_s=wall,
            envelope_sha256=spec.envelope.sha256(),
            detail={
                "strategy": self.strategy,
                "n_evidence": len(res.evidence),
                "n_needs": len(res.needs),
                "confidence": res.verdict.confidence,
                "agreement": res.agreement,
                "errors": res.errors,
            },
        )


__all__ = ["ArmResult", "ArmSpec", "ArmRunner", "ComparatorArm"]
