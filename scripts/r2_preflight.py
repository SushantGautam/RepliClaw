"""R-2 pre-flight extraction: S4/S3/S0 live-token floors (offline, zero LLM).

Implements the "Extraction + recording" step of
docs/experiments/R2_TOKEN_FLOOR_PREFLIGHT_PROTOCOL.md. The live runs
themselves stay human-gated; this tool only reads the run artifacts the
protocol's runner commands produce and writes ``floor_r2.json``
(schema ``p08.token_floor_r2/1``).

Run layout consumed (one run per arm, exactly what the protocol's runner
loop produces):

    <run-dir>/<arm>/run-01/budget_ledger.json
    <run-dir>/<arm>/run-01/run_metadata.json

with arms: open_sharing_swarm (S4), adaptive_central (S3), single_agent (S0).

Field names come from the actual writers in
src/repliclaw/comparators/runner.py:
  * budget_ledger.json ``totals`` (``_write_offline_artifacts`` ~L331-355,
    ``_write_live_strategy_artifacts`` ~L561-585):
    ``totals.total_tokens``, ``totals.llm_calls``, ``totals.wall_s``
  * run_metadata.json (``run_one_arm`` ~L822-860):
    ``status``, ``arm``, ``harness_seed``, ``tree_sha``,
    ``a9_defect_instruction_sha256``, ``case_id``

Rules (protocol "Acceptance + backstops"):
  * each arm status must be in {completed, aborted_budget} and
    total_tokens > 0, else hard fail (non-zero exit) — the record would be
    meaningless;
  * max_arm_usage_fraction = max(tokens) / per_arm_ceiling (60,000);
  * verdict = "OK" if every arm <= 60% of the per-arm ceiling, else "CHECK"
    (the protocol's >60% flag: reconsider per-run counts before the window).

Usage:
    python scripts/r2_preflight.py --run-dir <dir> --output <floor_r2.json> \
        [--pin <sha>] [--case policy_rag_v1]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "p08.token_floor_r2/1"
EXPECTED_HARNESS_SEED = 20261010  # prereg v1.1 §3.1/§3.2, D-10
PER_ARM_CEILING = 60_000          # A8 per-arm envelope (tokens)
MASTER_CEILING = 10_800_000       # prereg v1.1 §5.1 master ceiling
FLOOR_FLAG_FRACTION = 0.60        # protocol: flag any arm floor > 60%
VALID_STATUSES = ("completed", "aborted_budget")

# Protocol arm order: S4, S3, S0.
ARMS: tuple[tuple[str, str], ...] = (
    ("S4_open_sharing_swarm", "open_sharing_swarm"),
    ("S3_adaptive_central", "adaptive_central"),
    ("S0_single_agent", "single_agent"),
)


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - any read/parse failure is fatal
        errors.append(f"{path}: unreadable/invalid JSON ({exc})")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path}: top-level JSON is not an object")
        return None
    return data


def _extract_arm(
    run_dir: Path,
    arm_key: str,
    errors: list[str],
) -> dict[str, Any] | None:
    """Read one arm's run-01 artifacts; append to ``errors`` on any problem."""
    base = run_dir / arm_key / "run-01"
    if not base.is_dir():
        errors.append(f"missing arm run dir: {base}")
        return None

    ledger = _read_json(base / "budget_ledger.json", errors)
    meta = _read_json(base / "run_metadata.json", errors)

    totals = (ledger or {}).get("totals")
    if not isinstance(totals, dict):
        errors.append(f"{base}/budget_ledger.json: missing 'totals' object")
        totals = {}
    try:
        tokens = int(totals.get("total_tokens", 0))
    except (TypeError, ValueError):
        errors.append(f"{base}/budget_ledger.json: invalid totals.total_tokens")
        tokens = 0
    try:
        llm_calls = int(totals.get("llm_calls", 0))
    except (TypeError, ValueError):
        errors.append(f"{base}/budget_ledger.json: invalid totals.llm_calls")
        llm_calls = 0
    try:
        wall_s = float(totals.get("wall_s", 0.0))
    except (TypeError, ValueError):
        errors.append(f"{base}/budget_ledger.json: invalid totals.wall_s")
        wall_s = 0.0

    status = (meta or {}).get("status")
    if status not in VALID_STATUSES:
        errors.append(
            f"{arm_key}: status {status!r} not in {VALID_STATUSES} "
            f"({base}/run_metadata.json)"
        )
    if tokens <= 0:
        errors.append(f"{arm_key}: total_tokens must be > 0 (got {tokens})")

    # Cross-checks (warnings, not hard fails): metadata identity fields.
    meta_arm = (meta or {}).get("arm")
    if meta_arm is not None and meta_arm != arm_key:
        print(
            f"WARNING: {arm_key}: run_metadata.json arm={meta_arm!r} "
            f"does not match directory name",
            file=sys.stderr,
        )
    seed = (meta or {}).get("harness_seed")
    if seed is not None and seed != EXPECTED_HARNESS_SEED:
        print(
            f"WARNING: {arm_key}: harness_seed={seed!r} != expected "
            f"{EXPECTED_HARNESS_SEED} (prereg D-10)",
            file=sys.stderr,
        )
    if meta is not None and "a9_defect_instruction_sha256" not in meta:
        print(
            f"WARNING: {arm_key}: run_metadata.json lacks "
            f"a9_defect_instruction_sha256 (pre-A9 run?)",
            file=sys.stderr,
        )

    return {
        "tokens": tokens,
        "wall_s": wall_s,
        "llm_calls": llm_calls,
        "status": status,
    }


def _default_pin(repo_root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:  # noqa: BLE001 - fall back to unknown
        pass
    return "unknown"


def build_floor_record(
    run_dir: Path,
    pin: str,
    case_id: str,
    errors: list[str],
) -> dict[str, Any]:
    """Assemble the floor_r2.json record from the run tree."""
    arms: dict[str, Any] = {}
    for label, arm_key in ARMS:
        entry = _extract_arm(run_dir, arm_key, errors)
        if entry is not None:
            arms[label] = entry

    tokens = [a["tokens"] for a in arms.values() if isinstance(a.get("tokens"), int)]
    max_fraction = (max(tokens) / PER_ARM_CEILING) if tokens else None
    verdict = (
        "OK"
        if tokens and all(t / PER_ARM_CEILING <= FLOOR_FLAG_FRACTION for t in tokens)
        else "CHECK"
    )

    return {
        "schema": SCHEMA,
        "date": datetime.now(timezone.utc).isoformat(),
        "pin": pin,
        "harness_seed": EXPECTED_HARNESS_SEED,
        "case_id": case_id,
        "arms": arms,
        "headroom": {
            "per_arm_ceiling": PER_ARM_CEILING,
            "master_ceiling": MASTER_CEILING,
            "max_arm_usage_fraction": max_fraction,
            "verdict": verdict,
        },
    }


def write_atomic(path: Path, record: dict[str, Any]) -> None:
    """Write JSON (2-space indent, trailing newline) via tmp + replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
            fh.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/r2_preflight.py",
        description="R-2 pre-flight: extract S4/S3/S0 token floors into "
        "floor_r2.json (offline, zero LLM).",
    )
    parser.add_argument("--run-dir", required=True,
                        help="Run root containing <arm>/run-01/ for each of "
                             "open_sharing_swarm, adaptive_central, single_agent")
    parser.add_argument("--output", required=True,
                        help="Path to write floor_r2.json")
    parser.add_argument("--pin", default=None,
                        help="git tree sha to record (default: git rev-parse "
                             "HEAD of this repo)")
    parser.add_argument("--case", default="policy_rag_v1",
                        help="Case id to record (default: policy_rag_v1)")
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: --run-dir is not a directory: {run_dir}", file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parent.parent
    pin = args.pin or _default_pin(repo_root)

    errors: list[str] = []
    record = build_floor_record(run_dir, pin, args.case, errors)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(
            f"ERROR: {len(errors)} problem(s) — floor record would be "
            f"meaningless; refusing to write {args.output}",
            file=sys.stderr,
        )
        return 1

    write_atomic(Path(args.output), record)
    headroom = record["headroom"]
    print(json.dumps(
        {"wrote": str(args.output),
         "max_arm_usage_fraction": headroom["max_arm_usage_fraction"],
         "verdict": headroom["verdict"]},
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
