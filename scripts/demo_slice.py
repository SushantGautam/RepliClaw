"""P07 vertical-slice demo (runnable, deterministic artifacts).

Run from the worktree root:

    .venv/bin/python scripts/demo_slice.py

It runs the full COMMIT -> REVEAL -> EXECUTE -> RESOLVE slice into a
timestamped artifacts dir, prints the stop reason, the per-agent prediction
verdicts, and the evidence-derived choice-change trace, then independently
re-verifies the persisted runs (re-execution + pinned-artifact hash compare,
the same semantics as ``verify_run``) and prints ``DEMO OK``.

The artifacts themselves are deterministic (the slice pins seed + config and
excludes wall-clock from the hash chain); the timestamp only names the run
directory.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Make `repliclaw` importable when run as a plain script from the worktree root.
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from repliclaw.counterfactual import load_case, load_interventions, run_case  # noqa: E402
from repliclaw.slice import run_slice  # noqa: E402

CASE_ID = "policy_rag_v1"
SEED = 0


def _reverify(run_root: Path) -> bool:
    """Independently re-execute each distinct arm and confirm the pinned
    artifact hashes (``hashes.json``) reproduce (verify_run semantics, never
    self-attestation)."""
    case = load_case(CASE_ID)
    interventions = {i.intervention_id: i for i in load_interventions(CASE_ID)}
    runs_dir = run_root / "runs"
    if not runs_dir.exists():
        return False
    checked = 0
    seen_arms: set[str] = set()
    for hashes_path in sorted(runs_dir.glob("*/*/interventions/*/hashes.json")):
        arm = hashes_path.parent.name
        if arm not in interventions or arm in seen_arms:
            continue
        seen_arms.add(arm)
        pinned = json.loads(hashes_path.read_text(encoding="utf-8"))
        # Re-execute the arm in a clean temp dir and compare pinned hashes.
        with tempfile.TemporaryDirectory(prefix="demo_reverify_") as td:
            re_hashes = run_case(case, interventions[arm], seed=SEED, out_root=Path(td)).artifact_hashes
        if not pinned or re_hashes != pinned:
            return False
        checked += 1
    return checked > 0


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_root = Path("artifacts/demo-slice") / f"run-{ts}"
    run_root.parent.mkdir(parents=True, exist_ok=True)

    print(f"Running P07 slice into {run_root} ...")
    report = run_slice(run_root)
    result = report.result

    print(f"\nstop_reason: {result.stop_reason}")
    print(f"revealed_verified={result.revealed_verified}  "
          f"revealed_mismatch={result.revealed_mismatch}  "
          f"published_evidence={result.published_evidence}")
    print(f"evidence_snapshot_sha256: {result.evidence_snapshot_sha256}")

    print("\nPer-agent prediction verdicts:")
    for agent_id in result.agent_ids:
        v = result.predictions_outcome[agent_id]
        print(f"  {agent_id:<6} {v['hypothesis_id']}  ->  {v['outcome']}")

    print("\nEvidence-derived choice-change trace:")
    if result.choice_trace:
        for entry in result.choice_trace:
            print(f"  cycle {entry['cycle']}: {entry['agent_id']}  "
                  f"{entry['prev_top']}  ->  {entry['new_top']}")
            print(f"      snapshot_sha: {entry.get('snapshot_sha')}")
    else:
        print("  (none)")

    # Independent re-verification of the persisted runs.
    ok = _reverify(run_root)
    print(f"\nIndependent re-execution verification: {'PASS' if ok else 'FAIL'}")

    if result.stop_reason == "all_needs_fulfilled" and ok:
        print("\nDEMO OK")
        return 0
    print("\nDEMO FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
