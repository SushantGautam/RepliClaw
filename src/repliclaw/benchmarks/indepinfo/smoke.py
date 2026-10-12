"""Single live smoke for the indepinfo path (Part C acceptance).

Run:  uv run python -m repliclaw.benchmarks.indepinfo.smoke

One investigator, one small case, real LLM endpoint via
:class:`repliclaw.investigators.LLMClient` (default base_url/model from
``LLMConfig``; the key comes from env ``REPLICLAW_LLM_API_KEY`` with
fallback ``CUSTOM_SIMULACHAT_KEY``). Skips (clear note, exit 0) when no API
key is configured — the smoke is never faked. A live failure exits 1 with
the persisted receipts.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from repliclaw.escrow import EscrowLedger, verify_ledger
from repliclaw.investigators import LLMClient, LLMConfig

from .evidence import Evidence, EvidenceRecord, EvidenceSource
from .investigator import InvestigatorConfig, InvestigatorRunError, PartitionedInvestigator
from .isolation import PartitionVault
from .runner import run_case

AGENT_ID = "inv-smoke-1"
SOURCE_ID = "src-gateway-logs"


def _smoke_evidence() -> Evidence:
    return Evidence(
        case_id="indepinfo-smoke-1",
        case_brief=(
            "Checkout latency spiked for ~20 minutes on 2026-10-11 14:00-14:20 UTC. "
            "Diagnose the most likely root cause from your assigned source only."
        ),
        sources=[
            EvidenceSource(
                source_id=SOURCE_ID,
                name="edge gateway access logs",
                description="Per-request latency and status codes at the edge gateway.",
                records=[
                    EvidenceRecord(
                        record_id="gw-1",
                        data={
                            "ts": "14:02:11Z", "route": "/checkout",
                            "p50_ms": 480, "p99_ms": 3900, "status_5xx_pct": 12.4,
                        },
                    ),
                    EvidenceRecord(
                        record_id="gw-2",
                        data={
                            "ts": "14:05:40Z", "route": "/checkout",
                            "p50_ms": 510, "p99_ms": 4100, "status_5xx_pct": 15.1,
                        },
                    ),
                    EvidenceRecord(
                        record_id="gw-3",
                        data={
                            "ts": "14:12:02Z", "route": "/checkout",
                            "p50_ms": 495, "p99_ms": 3700, "status_5xx_pct": 11.8,
                        },
                    ),
                    EvidenceRecord(
                        record_id="gw-4",
                        data={
                            "ts": "13:58:00Z", "route": "/catalog",
                            "p50_ms": 90, "p99_ms": 210, "status_5xx_pct": 0.2,
                        },
                    ),
                ],
            ),
        ],
    )


def main() -> int:
    cfg = LLMConfig()
    if not cfg.available:
        print("SMOKE SKIPPED: no LLM API key configured in this environment.")
        print("Set REPLICLAW_LLM_API_KEY (or CUSTOM_SIMULACHAT_KEY) to run the live smoke.")
        print(f"(base_url default: {cfg.base_url}; model default: {cfg.model})")
        return 0

    client = LLMClient(cfg)
    print(f"Live smoke: base_url={cfg.base_url} model={cfg.model}")

    evidence = _smoke_evidence()
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    artifacts = Path("artifacts") / "indepinfo" / f"smoke-{ts}"
    ledger = EscrowLedger(artifacts / "ledger", worker_id="indepinfo-smoke")
    vault = PartitionVault(evidence, ledger, evidence.case_id)
    view = vault.view_for(agent_id=AGENT_ID, source_id=SOURCE_ID)
    inv = PartitionedInvestigator(
        view,
        client,
        InvestigatorConfig(max_turns=5, token_budget=12000, wall_deadline_s=120.0),
    )

    try:
        receipts = run_case([inv], ledger, evidence.case_id, artifacts)
    except InvestigatorRunError as e:
        print(f"SMOKE FAILED: {e}")
        print(f"Receipts persisted under {artifacts}")
        return 1

    r = receipts[AGENT_ID]
    violations = verify_ledger(ledger.root)
    summary = {
        "status": r.status,
        "model_requested": r.model_requested,
        "model_reported": r.model_reported,
        "total_tokens": r.total_tokens,
        "wall_s": r.wall_s,
        "num_llm_calls": r.num_llm_calls,
        "num_tool_calls": r.num_tool_calls,
        "bounds_hit": r.bounds_hit,
        "commitment_sha256": r.commitment_sha256,
        "reveal_status": r.reveal_status,
        "transcript_messages": len(r.transcript),
        "ledger_violations": violations,
        "artifacts": str(artifacts),
    }
    print(json.dumps(summary, indent=2))
    ok = (
        r.status == "committed"
        and r.reveal_status == "verified"
        and r.total_tokens > 0
        and len(r.transcript) > 0
        and not violations
    )
    print("SMOKE " + ("PASSED" if ok else "INCOMPLETE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
