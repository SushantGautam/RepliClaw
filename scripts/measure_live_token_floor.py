"""Measure the live-LLM S5 token floor (prereg v1.1 §5.1, judge Q6 / item F).

Runs ONE real live-LLM S5 execution through ``EESSLiveS5Arm`` with the frozen
§3.1 hyperparameters (λ=μ=0.5, max_cycles=6, offer TTL=120 s) under the 60k
token / 900 s / 3-agent envelope, and writes ``artifacts/p08/live_token_floor/
floor.json`` with the measured floor plus a re-derivation of the headroom
against the committed 60,000-token per-arm ceiling.

This is the single authorized live-key measurement for pre-flight. It is NOT
a campaign run: one arm, one run, oracle never read.

Usage:  python scripts/measure_live_token_floor.py [--work-dir PATH]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from repliclaw.comparators.arms import ArmSpec
from repliclaw.comparators.budget import BudgetEnvelope, BudgetLedger
from repliclaw.eess_live import (
    CASE_ID,
    EESSLiveS5Arm,
)
from repliclaw.investigators import LLMClient
from repliclaw.models import Claim

# Frozen §3.1 values (prereg v1.1, D-10). The arm ctor takes max_cycles; the
# policy weights come via _build_policy and the offer TTL via the broker
# constant — both patched here for the measurement so the run dir records the
# frozen values. The permanent wiring lands on p08/runner-cli.
LAMBDA_ = 0.5
MU_ = 0.5
MAX_CYCLES_ = 6
LEASE_TTL_S_ = 120.0


def _frozen_claim() -> Claim:
    return Claim(
        claim_id="claim_floor_s5",
        statement="The baseline policy-RAG system fails to cite the controlling provision.",
        domain="policy_rag",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", default="artifacts/p08/live_token_floor/work")
    parser.add_argument("--seed", type=int, default=20261010)
    args = parser.parse_args()

    # Pin the frozen values onto the modules BEFORE the arm builds the
    # orchestrator (TTL is read at broker construction inside orch.run()).
    import repliclaw.eess_live.orchestrator as orch_mod
    from repliclaw.needmarket.policy import LocalEigPolicy

    orig_ttl = orch_mod.LEASE_TTL_S
    orch_mod.LEASE_TTL_S = LEASE_TTL_S_
    orig_build = EESSLiveS5Arm._build_policy

    def _build_policy(self: Any) -> Any:  # frozen λ/μ
        return LocalEigPolicy({}, lam=LAMBDA_, mu=MU_)

    setattr(EESSLiveS5Arm, "_build_policy", _build_policy)  # type: ignore[attr-defined]

    def _client_factory(_agent_id: str) -> LLMClient:
        return LLMClient()

    try:
        arm = EESSLiveS5Arm(
            _client_factory,
            max_cycles=MAX_CYCLES_,
            harness_seed=args.seed,
        )
        env = BudgetEnvelope(max_tokens=60_000, max_wall_s=900.0, max_agents=3)
        spec = ArmSpec(arm_name="eess", claim_id="claim_floor_s5", envelope=env)
        # arm.run() appends its own run-01/ (contract layout work_dir/run-NN).
        work = Path(args.work_dir)
        work.mkdir(parents=True, exist_ok=True)

        t0 = time.monotonic()
        result = arm.run(_frozen_claim(), BudgetLedger(env), spec, work)
        wall_outside = time.monotonic() - t0

        run_dir = work / "run-01"
        fv_path = run_dir / "final_verdict.json"
        fv = json.loads(fv_path.read_text()) if fv_path.exists() else {}
        bl_path = run_dir / "budget_ledger.json"
        bl = json.loads(bl_path.read_text()) if bl_path.exists() else {}

        tokens = int(result.total_tokens)
        per_agent = sorted(
            (
                {
                    "agent_id": e.get("agent_id"),
                    "llm_calls": e.get("llm_calls", 0),
                    "total_tokens": e.get("total_tokens", 0),
                }
                for e in bl.get("agents", [])
            ),
            key=lambda a: a["agent_id"] or "",
        )

        out_dir = Path("artifacts/p08/live_token_floor")
        out_dir.mkdir(parents=True, exist_ok=True)
        floor = {
            "schema": "p08.live_token_floor/1",
            "harness_seed": args.seed,
            "case_id": CASE_ID,
            "arm": "S5",
            "live_llm": True,
            "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "frozen_params": {
                "lambda": LAMBDA_,
                "mu": MU_,
                "max_cycles": MAX_CYCLES_,
                "offer_ttl_s": LEASE_TTL_S_,
            },
            "envelope": {"max_tokens": 60_000, "max_wall_s": 900.0, "max_agents": 3},
            "status": fv.get("status") or ("completed" if result.total_tokens > 0 else "failed"),
            "verdict": fv.get("verdict"),
            "measured_floor_tokens": tokens,
            "measured_wall_s": round(wall_outside, 1),
            "per_agent": per_agent,
            "headroom": {
                "committed_ceiling_tokens": 60_000,
                "measured_usage_fraction": round(tokens / 60_000, 4),
                "margin_x": round(60_000 / tokens, 2) if tokens else None,
            },
            "work_dir": str(work),
        }
        (out_dir / "floor.json").write_text(json.dumps(floor, indent=2) + "\n")
        print(json.dumps(floor, indent=2))
        ok = tokens > 0 and fv.get("status") in {"completed", "aborted_budget"}
        print(
            f"\nFLOOR MEASURED: {tokens} tokens / {wall_outside:.1f}s "
            f"({floor['headroom']['margin_x']}x margin vs 60k) "
            f"status={fv.get('status')} -> {'OK' if ok else 'CHECK'}"
        )
        return 0 if ok else 1
    finally:
        orch_mod.LEASE_TTL_S = orig_ttl
        setattr(EESSLiveS5Arm, "_build_policy", orig_build)  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
