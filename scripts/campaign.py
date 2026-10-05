#!/usr/bin/env python3
"""P08 live-campaign runner (prereg v1.1 §3.1 primary matrix + v1.2 A1/A7).

The frozen campaign is SIX primary arms x N runs on case policy_rag_v1:

    S0 single_agent, S3 adaptive_central, S4 open_sharing_swarm,
    S5 eess, A1 eess_no_escrow, A3 eess_random_select

This script is the ONE-COMMAND LAUNCH for the live window. It:

1. invokes the frozen arm runner IN-PROCESS (``comparators.runner.run_one_arm``)
   per (arm, run) — every D-10 parameter, the ``--assert-frozen`` pin check and
   the two-key live gate (REPLICLAW_LLM_ALLOW_LIVE) are enforced by the runner
   itself; this harness never flips that gate;
2. stages each run at ``<staging>/<LABEL>/run-NNN`` and flattens the runner's
   ``run-01`` contract dir into the scorer layout ``<root>/<LABEL>/run-NNN``
   (``score.discover_runs`` maps run-root subdirs -> arms; the scorer keys the
   P1/RQ2 pairs off the S-label subdir names S5/S4/S3/S0);
3. enforces the 10.8M master token ceiling (prereg v1.1 §5.1) across the whole
   campaign — it stops launching further runs when remaining envelope +
   projected floor would breach the ceiling (the per-arm 60k envelope is
   enforced by the runner itself);
4. is resumable: a run dir that already carries final_verdict.json +
   budget_ledger.json is reused (its tokens count toward the ceiling) instead
   of re-run — the live window is short and re-running completed runs wastes
   budget;
5. writes ``<root>/campaign_manifest.json`` (provenance: pin, case, arms,
   seed, client factory, per-run status, token cumulative) and then hands off
   to the frozen scorer (``repliclaw.p08.score``), which opens the sealed
   oracle ONLY after its completeness gate.

Nothing here reads the sealed oracle or touches experiment truth. Offline
verification uses ``--client-factory fake`` (zero tokens, no live gate).

Exit codes: 0 clean campaign (+ scored); 2 live gate refusal (no
REPLICLAW_LLM_ALLOW_LIVE); 3 at least one run aborted/invalid (scored anyway,
the scorer reports voided/aborted arms); 4 master-ceiling stop; 5 at least one
run errored (an unexpected runner exception, recorded per-run and the campaign
continued); 1 scorer error.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from repliclaw.comparators import runner as _runner

# PREREG v1.1 §3.1 primary live matrix (arm label -> registry key).
PRIMARY_ARMS: dict[str, str] = {
    "S0": "single_agent",
    "S3": "adaptive_central",
    "S4": "open_sharing_swarm",
    "S5": "eess",
    "A1": "eess_no_escrow",
    "A3": "eess_random_select",
}

MASTER_TOKEN_CEILING = 10_800_000  # prereg v1.1 §5.1 (A7: unchanged by v1.2)

EXIT_OK = 0
EXIT_SCORER_ERROR = 1
EXIT_LIVE_REFUSAL = 2
EXIT_RUN_INCOMPLETE = 3
EXIT_MASTER_CEILING = 4
EXIT_RUN_ERROR = 5


def _ns(
    *,
    arm: str,
    case: str,
    out: Path,
    harness_seed: int,
    client_factory: str,
    assert_frozen: bool,
    max_cycles: int,
    envelope_tokens: int | None,
    envelope_wall: float | None,
    envelope_agents: int | None,
) -> argparse.Namespace:
    """The exact field set run_one_arm consumes (mirrors runner.main())."""
    return argparse.Namespace(
        arm=arm,
        case=case,
        envelope_tokens=envelope_tokens,
        envelope_wall=envelope_wall,
        envelope_agents=envelope_agents,
        harness_seed=harness_seed,
        max_cycles=max_cycles,
        out=str(out),
        client_factory=client_factory,
        assert_frozen=assert_frozen,
    )


def _run_completed(run_dir: Path) -> bool:
    """A completed run dir has both contract truth files (status any)."""
    return (run_dir / "final_verdict.json").is_file() and (
        run_dir / "budget_ledger.json"
    ).is_file()


def _run_tokens(run_dir: Path) -> int:
    try:
        ledger = json.loads((run_dir / "budget_ledger.json").read_text(encoding="utf-8"))
        return int((ledger.get("totals") or {}).get("total_tokens", 0))
    except Exception:
        return 0


def _run_status(run_dir: Path) -> str | None:
    try:
        fv = json.loads((run_dir / "final_verdict.json").read_text(encoding="utf-8"))
        return fv.get("status")
    except Exception:
        return None


def _flatten_run(inner: Path, run_dir: Path) -> None:
    """Move the runner's <stage>/run-01 contract content into run_dir.

    Crash-recovery safe (M1): a re-run after a partial flatten can find an
    existing NON-EMPTY dir child at the target (os.replace over a directory
    raises ENOTEMPTY on POSIX). A leftover dir can only belong to a not-yet
    complete run — a complete run is never re-flattened (phase 1/2
    ``continue``) — so removing it before the replace is always safe.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    if not inner.is_dir():
        return
    for name in os.listdir(inner):
        target = run_dir / name
        if target.is_dir():
            shutil.rmtree(target)
        os.replace(inner / name, target)
    inner.rmdir()


def _cleanup_stage(stage: Path) -> None:
    if stage.exists():
        shutil.rmtree(stage, ignore_errors=True)


def _write_manifest(
    root: Path,
    case: str,
    arms: list[str],
    runs_per_arm: int,
    harness_seed: int,
    client_factory: str,
    master_ceiling: int,
    results: dict[str, list[dict]],
    pin: str,
    started: str,
    max_cycles: int,
    envelope: dict | None,
) -> None:
    manifest = {
        "schema": "p08.campaign_manifest/1",
        "case_id": case,
        "arms": {label: PRIMARY_ARMS[label] for label in arms},
        "runs_per_arm": runs_per_arm,
        "harness_seed": harness_seed,
        "client_factory": client_factory,
        "assert_frozen": True,
        "max_cycles": max_cycles,
        "envelope_override": envelope,
        "master_token_ceiling": master_ceiling,
        "pin": pin,
        "started_utc": started,
        "ended_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runs": {
            label: results[label]
            for label in arms
            if label in results
        },
    }
    (root / "campaign_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )


def run_campaign(
    *,
    out_root: Path,
    case: str = "policy_rag",
    case_id: str = "policy_rag_v1",
    client_factory: str = "fake",
    runs_per_arm: int = 20,
    arms: list[str] | None = None,
    harness_seed: int = 20261010,
    assert_frozen: bool = True,
    max_cycles: int = _runner.FROZEN_MAX_CYCLES,
    master_token_ceiling: int = MASTER_TOKEN_CEILING,
    envelope: tuple[int | None, float | None, int | None] = (None, None, None),
    resume: bool = True,
    score: bool = True,
    dry_run: bool = False,
    verbose: bool = True,
) -> int:
    """Execute the campaign. Returns a process exit code (see module doc)."""
    arms = list(arms) if arms else list(PRIMARY_ARMS)
    unknown = [a for a in arms if a not in PRIMARY_ARMS]
    if unknown:
        print(f"campaign: unknown arm labels {unknown}; "
              f"expected one of {sorted(PRIMARY_ARMS)}", file=sys.stderr)
        return EXIT_SCORER_ERROR

    live_wanted = client_factory == "live"
    if live_wanted and not dry_run and not os.environ.get("REPLICLAW_LLM_ALLOW_LIVE", ""):
        print(
            "campaign: REFUSAL — live arms need REPLICLAW_LLM_ALLOW_LIVE=1 "
            "(authorized orchestrator, prereg two-key start). Record the "
            "human authorization first, then re-run. (--client-factory fake "
            "runs the identical pipeline offline for verification.)",
            file=sys.stderr,
        )
        return EXIT_LIVE_REFUSAL

    pin = ""
    if not dry_run:
        try:
            pin = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, check=False,
            ).stdout.strip()
        except FileNotFoundError:  # pragma: no cover
            pin = "git-unavailable"

    # Scorer layout: <out>/<LABEL>/run-NNN; the runner stages at
    # <out>/staging/<LABEL>/run-NNN and is flattened per run (see below).
    root = out_root
    staging = out_root / "staging"
    root.mkdir(parents=True, exist_ok=True)

    # The master-ceiling pre-check must never use an envelope floor SMALLER
    # than the actual per-run envelope, or it would admit runs past the
    # ceiling (m3). The frozen campaign uses the 60k default.
    envelope_floor = 60_000
    if envelope[0] is not None:
        envelope_floor = max(envelope_floor, int(envelope[0]))

    if dry_run:
        total = sum(runs_per_arm for _ in arms)
        print(json.dumps({
            "dry_run": True,
            "case": case_id,
            "arms": {a: PRIMARY_ARMS[a] for a in arms},
            "runs_per_arm": runs_per_arm,
            "total_runs": total,
            "client_factory": client_factory,
            "harness_seed": harness_seed,
            "master_token_ceiling": master_token_ceiling,
            "root": str(root),
            "live_gate": "SET" if os.environ.get("REPLICLAW_LLM_ALLOW_LIVE", "") else "NOT SET (live would refuse)",
        }, indent=2, sort_keys=True))
        return EXIT_OK

    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results: dict[str, list[dict]] = {}
    cumulative_tokens = 0
    stopped_master = False
    any_incomplete = False

    # ---- phase 1: existing runs (resume) — count their tokens ------------
    if resume:
        for label in arms:
            arm_root = root / label
            if not arm_root.is_dir():
                continue
            for i in range(1, runs_per_arm + 1):
                run_dir = arm_root / f"run-{i:03d}"
                if _run_completed(run_dir):
                    tokens = _run_tokens(run_dir)
                    cumulative_tokens += tokens
                    results.setdefault(label, []).append({
                        "run": f"run-{i:03d}",
                        "status": _run_status(run_dir) or "unknown",
                        "tokens": tokens,
                        "note": "reused (resume)",
                    })
        if verbose:
            print(json.dumps({"resumed_tokens": cumulative_tokens,
                              "resumed_runs": {k: len(v) for k, v in results.items()}}))

    # ---- phase 2: launch the missing runs --------------------------------
    for label in arms:
        arm_root = root / label
        arm_root.mkdir(parents=True, exist_ok=True)
        results.setdefault(label, [])
        for i in range(1, runs_per_arm + 1):
            run_dir = arm_root / f"run-{i:03d}"
            if _run_completed(run_dir):
                continue  # counted in phase 1
            entry = {"run": f"run-{i:03d}", "status": None, "tokens": 0, "note": None}
            results[label].append(entry)

            if stopped_master:
                entry["status"] = "skipped_master_ceiling"
                if verbose:
                    print(f"{label}/{entry['run']}: SKIPPED (master ceiling)")
                continue

            # Master-ceiling check BEFORE launching (envelope floor).
            # The flagged run is SKIPPED, not launched (prereg v1.1 §5.1:
            # "further runs are skipped").
            if cumulative_tokens + envelope_floor > master_token_ceiling:
                stopped_master = True
                entry["status"] = "skipped_master_ceiling"
                entry["note"] = (f"master ceiling {master_token_ceiling} "
                                 f"reached (used {cumulative_tokens})")
                if verbose:
                    print(f"{label}/{entry['run']}: SKIPPED (master ceiling)")
                continue

            stage = staging / label / f"run-{i:03d}"
            if stage.exists():
                shutil.rmtree(stage)
            stage.mkdir(parents=True, exist_ok=True)

            try:
                rc = _runner.run_one_arm(_ns(
                    arm=PRIMARY_ARMS[label],
                    case=case,
                    out=stage,
                    harness_seed=harness_seed,
                    client_factory=client_factory,
                    assert_frozen=assert_frozen,
                    max_cycles=max_cycles,
                    envelope_tokens=envelope[0],
                    envelope_wall=envelope[1],
                    envelope_agents=envelope[2],
                ))
            except BaseException as exc:  # noqa: BLE001 - one bad run must not
                # kill the remaining runs of a live campaign; record + continue.
                # SystemExit(2) is a clean runner refusal, not an error.
                if isinstance(exc, SystemExit):
                    rc = int(exc.code or _runner.EXIT_REFUSAL)
                else:
                    entry["status"] = f"error:{type(exc).__name__}"
                    entry["note"] = (f"runner raised {type(exc).__name__}: "
                                     f"{exc}")
                    if verbose:
                        print(f"{label}/{entry['run']}: ERROR {type(exc).__name__}")
                    _cleanup_stage(stage)
                    continue

            # The runner names its run dir after its own 1-based idx and the
            # harness passes exactly one run per stage, so it is always
            # <stage>/run-01; move that content into the scorer's home
            # <root>/<LABEL>/run-NNN/.
            _flatten_run(stage / "run-01", run_dir)

            if rc == _runner.EXIT_OK:
                entry["status"] = _run_status(run_dir) or "completed"
                entry["tokens"] = _run_tokens(run_dir)
                cumulative_tokens += entry["tokens"]
                entry["note"] = None
            elif rc == _runner.EXIT_REFUSAL:
                entry["status"] = "refused"
                entry["note"] = "runner refusal (live gate / case constraint)"
            else:  # EXIT_RUN_ABORTED or other non-zero
                entry["status"] = _run_status(run_dir) or "incomplete"
                entry["note"] = f"runner exit {rc}"
            if verbose:
                print(json.dumps({"arm": label, **entry,
                                  "cumulative_tokens": cumulative_tokens}))
            _cleanup_stage(stage)

        # remove an empty per-label staging dir (fully flattened away)
        stage_label = staging / label
        if stage_label.is_dir() and not any(stage_label.iterdir()):
            stage_label.rmdir()

    # remove the (now empty) staging root if fully flattened away
    if staging.is_dir() and not any(staging.iterdir()):
        staging.rmdir()

    # ---- phase 3: summary --------------------------------------------------
    n_ok = sum(1 for r in results.values() for e in r
               if e["status"] in ("completed", "aborted_budget", "invalid_usage"))
    n_aborted = sum(1 for r in results.values() for e in r
                    if e["status"] in ("aborted_budget", "invalid_usage"))
    n_refused = sum(1 for r in results.values() for e in r if e["status"] == "refused")
    n_errors = sum(1 for r in results.values() for e in r
                   if e["status"] and e["status"].startswith("error:"))
    n_missing = sum(1 for r in results.values() for e in r
                    if e["status"] in (None, "incomplete", "skipped_master_ceiling")
                    or (e["status"] and e["status"].startswith("error:")))
    summary = {
        "schema": "p08.campaign_summary/1",
        "case_id": case_id,
        "pin": pin,
        "total_runs": sum(len(r) for r in results.values()),
        "completed_or_recorded": n_ok,
        "aborted_or_invalid": n_aborted,
        "refused": n_refused,
        "errored": n_errors,
        "missing_or_skipped": n_missing,
        "cumulative_tokens": cumulative_tokens,
        "master_token_ceiling": master_token_ceiling,
        "stopped_master_ceiling": stopped_master,
    }
    (root / "campaign_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    _write_manifest(root, case_id, arms, runs_per_arm, harness_seed,
                    client_factory, master_token_ceiling, results, pin, started,
                    max_cycles,
                    {"tokens": envelope[0], "wall_s": envelope[1],
                     "agents": envelope[2]} if any(envelope) else None)
    if verbose:
        print(json.dumps({"summary": summary}))

    if n_refused:
        return EXIT_LIVE_REFUSAL
    if n_errors:
        # Loud, not silent: a run that raised is recorded in the manifest
        # (status "error:<ExcName>") and the campaign continues, but the
        # exit code tells the operator the run set is not clean.
        return EXIT_RUN_ERROR
    if stopped_master:
        return EXIT_MASTER_CEILING
    if n_missing:
        any_incomplete = True

    # ---- phase 4: hand off to the frozen scorer ----------------------------
    if score and not n_missing and not n_refused:
        if verbose:
            print("campaign: invoking scorer (oracle opens post-gate)...")
        rc = subprocess.run(
            [sys.executable, "-m", "repliclaw.p08.score",
             "--run-root", str(root), "--case", case_id],
            check=False,
        )
        if rc.returncode != 0:
            return EXIT_SCORER_ERROR
    elif score:
        print("campaign: score skipped (missing or refused runs) — "
              "complete the set and re-run (resume counts finished runs).",
              file=sys.stderr)

    return EXIT_RUN_INCOMPLETE if any_incomplete else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python scripts/campaign.py",
        description="P08 live campaign: 6 primary arms x N runs -> scorer "
                    "(prereg v1.1 §3.1; v1.2 A1/A7).",
    )
    p.add_argument("--case", default="policy_rag",
                   help="runner case name (canonical, not a path)")
    p.add_argument("--case-id", default="policy_rag_v1",
                   help="scorer case id for the oracle lookup")
    p.add_argument("--client-factory", choices=("fake", "live"), default="fake")
    p.add_argument("--runs-per-arm", type=int, default=20)
    p.add_argument("--arms", nargs="+", default=None,
                   help="subset of S0 S3 S4 S5 A1 A3 (default: all six)")
    p.add_argument("--out", required=True, help="campaign dir (root+staging inside)")
    p.add_argument("--harness-seed", type=int, default=20261010)
    p.add_argument("--max-cycles", type=int, default=_runner.FROZEN_MAX_CYCLES)
    p.add_argument("--master-token-ceiling", type=int, default=MASTER_TOKEN_CEILING)
    p.add_argument("--envelope-tokens", type=int, default=None)
    p.add_argument("--envelope-wall", type=float, default=None)
    p.add_argument("--envelope-agents", type=int, default=None)
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--no-score", action="store_true")
    p.add_argument("--no-assert-frozen", action="store_true",
                   help="disable the D-10 pin check (NOT for the campaign)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    return run_campaign(
        out_root=Path(args.out),
        case=args.case,
        case_id=args.case_id,
        client_factory=args.client_factory,
        runs_per_arm=args.runs_per_arm,
        arms=args.arms,
        harness_seed=args.harness_seed,
        assert_frozen=not args.no_assert_frozen,
        max_cycles=args.max_cycles,
        master_token_ceiling=args.master_token_ceiling,
        envelope=(args.envelope_tokens, args.envelope_wall, args.envelope_agents),
        resume=not args.no_resume,
        score=not args.no_score,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
