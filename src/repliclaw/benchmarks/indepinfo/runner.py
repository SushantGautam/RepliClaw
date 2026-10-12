"""Case runner: commit -> reveal with persisted receipts (indepinfo).

Public entry point for lane D:

    from repliclaw.investigators import LLMClient, LLMConfig

    evidence = Evidence(case_id=..., sources=[...])
    ledger = EscrowLedger(root, worker_id=...)
    vault = PartitionVault(evidence, ledger, case_id)
    client = LLMClient(LLMConfig())  # key via REPLICLAW_LLM_API_KEY
    investigators = [
        PartitionedInvestigator(vault.view_for(agent_id=..., source_id=...),
                                client, InvestigatorConfig(...))
        for ...
    ]
    receipts = run_case(investigators, ledger, case_id, artifacts_dir)
    # receipts: {agent_id: InvestigatorReceipt}; persisted to
    # artifacts_dir/receipts.jsonl + run_summary.json

Lifecycle: every investigator runs its bounded investigation and commits its
sealed packet in the COMMIT phase; then the ledger moves to REVEAL and each
committed packet is revealed (verified against its commitment hash). If any
investigator failed, ALL receipts are persisted first and then
:class:`InvestigatorRunError` is raised — the run is marked failed, never
faked.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

from repliclaw.escrow import EscrowLedger, verify_ledger

from .investigator import InvestigatorReceipt, InvestigatorRunError, PartitionedInvestigator


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_case(
    investigators: Sequence[PartitionedInvestigator],
    ledger: EscrowLedger,
    case_id: str,
    artifacts_dir: Path,
) -> Dict[str, InvestigatorReceipt]:
    """Run all investigators (COMMIT), open the reveal boundary, reveal each
    committed packet, and persist one receipt per investigator.

    Returns ``{agent_id: receipt}``. Raises :class:`InvestigatorRunError`
    (after persisting all receipts) if any investigator failed.
    """
    artifacts_dir = Path(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    receipts: Dict[str, InvestigatorReceipt] = {}
    failures: List[str] = []

    # 1. COMMIT phase: each investigator runs independently and seals.
    for inv in investigators:
        try:
            receipts[inv.view.agent_id] = inv.run()
        except InvestigatorRunError as e:
            if e.receipt is not None:
                receipts[inv.view.agent_id] = e.receipt
            failures.append(f"{inv.view.agent_id}: {e}")

    # 2. REVEAL boundary, then reveal (verify) each committed packet.
    committed = [inv for inv in investigators if inv.packet is not None]
    if committed:
        ledger.open_reveal(case_id)
        for inv in committed:
            assert inv.packet is not None  # filtered above
            result = ledger.reveal(inv.view.agent_id, inv.packet)
            receipts[inv.view.agent_id] = receipts[inv.view.agent_id].model_copy(
                update={"reveal_status": result.status}
            )

    # 3. Persist receipts + summary (always, even on failure).
    _persist(artifacts_dir, case_id, ledger, receipts, failures)

    if failures:
        raise InvestigatorRunError(
            f"{len(failures)} investigator(s) failed: " + "; ".join(failures)
        )
    return receipts


def _persist(
    artifacts_dir: Path,
    case_id: str,
    ledger: EscrowLedger,
    receipts: Dict[str, InvestigatorReceipt],
    failures: List[str],
) -> None:
    receipts_path = artifacts_dir / "receipts.jsonl"
    with receipts_path.open("w", encoding="utf-8") as f:
        for agent_id in sorted(receipts):
            f.write(json.dumps(receipts[agent_id].to_dict(), sort_keys=True) + "\n")
    summary = {
        "case_id": case_id,
        "finished_at": _now_iso(),
        "status": "failed" if failures else "completed",
        "failures": failures,
        "ledger_violations": verify_ledger(ledger.root),
        "investigators": {
            agent_id: {
                "status": r.status,
                "source_id": r.source_id,
                "model_requested": r.model_requested,
                "model_reported": r.model_reported,
                "total_tokens": r.total_tokens,
                "wall_s": r.wall_s,
                "num_llm_calls": r.num_llm_calls,
                "num_tool_calls": r.num_tool_calls,
                "bounds_hit": r.bounds_hit,
                "commitment_sha256": r.commitment_sha256,
                "reveal_status": r.reveal_status,
            }
            for agent_id, r in receipts.items()
        },
    }
    (artifacts_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


__all__ = ["run_case"]
