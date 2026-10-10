#!/usr/bin/env python3
"""AMEND_V3_2 (approved D-V3-017) — parallel pilot driver (round 4 surface).

A thin CONCURRENT wrapper over the frozen single-run path in
``pilot_run.py``. Every run executes through the SAME ``perform_case``
function as the sequential driver (same arm code, same status.json
layout, same scorer, same ledger line schema); the only differences are
scheduling (a bounded worker pool over cases) and a run-level
retry-once on unexpected exceptions.

Provenance: each run's status.json is stamped with a ``parallel``
section (driver sha, git rev, concurrency) after the pool joins; the
round dir gains a ``parallel_meta.json`` (driver name + sha, git rev,
concurrency, V3.2 constants, model, label) written at start. Per-run
retry counts are ledgered (``driver_failure`` flag) but not stamped
per run. (Post-round doc correction per science-judge C3 note,
recorded in v32_prereg_freeze.md "Post-round documentation
corrections"; the frozen launch hash is 5b9094d5c588d6b4206311fd4c6935b51d33babc88490216da2b979c1f4a02fb.)

Stop-rule semantics are UNCHANGED (evaluate_stop_rules between cases,
full-cohort denominators). On a trip: workers stop CLAIMING new cases,
in-flight runs finish and are recorded, STOP.json is written, exit 10.

Usage:
    python scripts/pilot_parallel.py run --round 4 \
        --out .artifacts/rcaeval/pilot/run_v32 --autonomous --concurrency 6 \
        [--fake] [--max-cases N] [--label "..."]

--max-cases N = the first N DISTINCT cases (not a row projection).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

# AMEND_V3_2 (B1-B4) constants are read through the frozen modules so the
# single source of truth (telemetry_arms / telemetry / pilot_run) governs.
import pilot_run as pr  # noqa: E402

from repliclaw.experiments.v3 import telemetry as _tel  # noqa: E402
from repliclaw.experiments.v3.telemetry_arms import PROMPT_VOLUME_CEIL as _PROMPT_VOLUME_CEIL  # noqa: E402
from repliclaw.experiments.v3.telemetry_arms import PROMPT_VOLUME_FLOOR as _PROMPT_VOLUME_FLOOR  # noqa: E402

EXIT_OK = 0
EXIT_STOP_TRIP = 10
EXIT_FAILED_RUN = 2
EXIT_REFUSED = 1


def _git_rev() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _driver_sha256() -> str:
    import hashlib

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _run_one(
    *,
    case: str,
    seed: int,
    arm: str,
    client: Any,
    registry: Any,
    out_root: Path,
    round_no: int,
    label: str,
    model: str,
    index_df: Any,
    index_sha: str,
    ledger: list,
    ledger_lock: threading.Lock,
    round_dir: Path,
    parallel_meta: dict[str, Any],
    worker_id: str,
) -> dict[str, Any]:
    """One run through the SAME perform_case path as the sequential
    driver, with retry-once on unexpected exceptions. Returns a summary
    dict (status/attempt/exit code from perform_case).

    TOCTOU safety (code-judge SHOULD-FIX #2): the caller reserves
    ``MAX_TOKENS_PER_RUN`` of ceiling headroom under ``ledger_lock``
    before invoking this (see ``case_worker``); this function releases it
    in a finally. The per-run ``ceiling_would_breach`` check inside
    ``perform_case`` then sees a consistent (possibly over-conservative)
    ledger+reservation view and can never race into a false refusal."""
    run_dir = pr.run_dir_for(out_root, round_no, case, seed, arm)
    attempts = 0
    last_exc: Exception | None = None
    while attempts < 2:
        attempts += 1
        try:
            # autonomous=False: perform_case must NOT write STOP.json itself
            # (a concurrent case may have legitimately appended after the
            # run started, so its case-completion view can be stale); the
            # case worker below re-evaluates stop rules under ledger_lock
            # after each of the case's runs and owns STOP.json writing.
            rc = pr.perform_case(
                case=case, seed=seed, arm=arm, client=client,
                registry=registry, out_root=out_root, round_no=round_no,
                label=label, model=model, index_df=index_df, index_sha=index_sha,
                ledger=ledger, max_cases=parallel_meta["max_cases"],
                autonomous=False, lock=ledger_lock,
            )
            return {"case": case, "seed": seed, "arm": arm, "attempt": attempts,
                    "rc": rc, "exception": None}
        except Exception as exc:  # noqa: BLE001 — run-level isolation
            last_exc = exc
            sys.stderr.write(
                f"[parallel] {case} seed{seed} {arm} attempt {attempts} "
                f"raised {type(exc).__name__}: {exc}\n"
            )
    sys.stderr.write(
        f"[parallel] {case} seed{seed} {arm} FAILED after 2 attempts: "
        f"{type(last_exc).__name__}: {last_exc}\n"
    )
    # Record the failure in the ledger (status "crashed") so the stop
    # rules see it, mirroring a crashed arm run — but flag it as a
    # driver-level failure, distinct from arm-level crash statuses.
    run_path = str(run_dir.relative_to(out_root))
    with ledger_lock:
        ledger.append(pr.RunRecord(
            run_path=run_path, case=case, seed=seed, arm=arm,
            status="crashed", tokens=0, wall_s=0.0, hit=None,
        ))
        pr.append_ledger(round_dir, {
            "run_path": run_path, "case": case, "seed": seed, "arm": arm,
            "status": "crashed", "tokens": 0, "wall_s": 0.0, "hit": None,
            "driver_failure": repr(last_exc),
        })
    return {"case": case, "seed": seed, "arm": arm, "attempt": attempts,
            "rc": EXIT_FAILED_RUN, "exception": repr(last_exc)}


def cmd_run(args: argparse.Namespace) -> int:
    out_root = Path(args.out)
    round_dir = out_root / f"round{args.round_no}"
    # DEFECT FIX (post-round-4, code-judge-r4 SHOULD-FIX): explicit closed
    # round guard — a STOP.json means the round is over; the pre-fix refusal
    # only happened incidentally (non-completed status.json files).
    if (round_dir / "STOP.json").is_file():
        print(
            f"REFUSED: {round_dir} contains STOP.json — the round is closed "
            "after a stop-rule trip. Do not relaunch; a new round is a new "
            "round number (and, for a changed instrument, a new freeze).",
            file=sys.stderr,
        )
        return EXIT_STOP_TRIP
    round_dir.mkdir(parents=True, exist_ok=True)

    # Refusals identical to the sequential driver. NOTE: --max-cases means
    # the first N DISTINCT cases here (intuitive), unlike the sequential
    # driver's row-projection quirk — the parallel driver is the surface
    # for the live round-4 run, so the semantics are made unambiguous.
    case_ids = sorted({row["case"] for row in pr.build_plan()})
    if args.max_cases is not None:
        case_ids = case_ids[: args.max_cases]

    code = pr.check_frozen_ids_and_manifest(pr.MANIFEST_PATH)
    if code != EXIT_OK:
        return code

    index_path = Path(args.cases_index)
    index_sha = ""
    index_df = None
    if not args.no_index:
        if not index_path.is_file():
            print(f"ERROR: cases index missing: {index_path}", file=sys.stderr)
            return EXIT_REFUSED
        index_df = pr.load_cases_index(index_path)
        index_sha = pr.verify_cases_index(index_path)

    # Resume: the round dir must contain ONLY completed runs (or be empty)
    # — partial/crashed state from a killed parallel run is not resumable
    # through this driver; clear the round dir manually and relaunch.
    ledger = pr.load_ledger(round_dir)
    if ledger:
        for rec in ledger:
            run_dir = out_root / rec.run_path
            if not pr._run_already_done(run_dir):
                print(
                    f"REFUSED: round dir has incomplete record {rec.run_path}; "
                    "parallel driver does not resume partial state. Clear the "
                    "round dir and relaunch.",
                    file=sys.stderr,
                )
                return EXIT_REFUSED

    if args.fake:
        client = pr.build_fake_client()
        model = "fake-scripted"
    else:
        if not pr.provider_env_complete():
            print("ERROR: provider env incomplete", file=sys.stderr)
            return EXIT_REFUSED
        client = pr.build_simula_client()
        model = os.environ.get("SIMULACHAT_MODEL", "").strip() or "default"

    registry = pr.PilotCaseRegistry(data_root=pr.DEFAULT_PILOT_DATA_ROOT)
    missing = pr.preflight(registry, case_ids)
    if missing:
        print(f"REFUSED: case data missing for: {missing}", file=sys.stderr)
        return EXIT_REFUSED

    label = args.label or (
        "MODEL-SUBSTITUTION (SimulaChat default, Qwen3.8-27B) — NOT the "
        "official released baseline; parallel V3.2 (AMEND_V3_2)"
    )

    parallel_meta = {
        "driver": "pilot_parallel.py (AMEND_V3_2)",
        "driver_sha256": _driver_sha256(),
        "git_rev": _git_rev(),
        "concurrency": args.concurrency,
        "max_cases": args.max_cases if args.max_cases is not None else len(case_ids),
        "v32_constants": {
            "max_tokens_per_run": pr.MAX_TOKENS_PER_RUN,
            "max_tool_calls": _tel.MAX_TOOL_CALLS,
            "round_token_ceiling": pr.ROUND_TOKEN_CEILING,
            "prompt_volume_band": [_PROMPT_VOLUME_FLOOR, _PROMPT_VOLUME_CEIL],
        },
        "started": pr._utc_now_iso(),
        "model": model,
        "label": label,
    }
    pr._write_json(round_dir / "parallel_meta.json", parallel_meta)

    # Case-level claim queue: workers pull the next incomplete case.
    case_queue = list(case_ids)
    queue_lock = threading.Lock()
    ledger_lock = threading.Lock()
    stop_claims = threading.Event()
    trip_info: dict[str, Any] = {}
    # Code-judge SHOULD-FIX #2 (TOCTOU): reserve MAX_TOKENS_PER_RUN of
    # ceiling headroom per in-flight run under ledger_lock, so the
    # per-run ceiling check in perform_case can never see a stale ledger
    # and false-refuse (or race into a start that the accounting then
    # records as a breach) while other workers append concurrently.
    reservations = 0

    def next_case() -> str | None:
        with queue_lock:
            if stop_claims.is_set() or not case_queue:
                return None
            case = case_queue.pop(0)
            # Skip cases already fully recorded (resume tolerance).
            needed = {(s, a) for s in pr.PILOT_SEEDS for a in pr.ARM_ORDER}
            have = {(r.seed, r.arm) for r in ledger if r.case == case}
            if needed <= have:
                return next_case()
            return case

    def case_worker(worker_id: str) -> None:
        nonlocal reservations
        while not stop_claims.is_set():
            case = next_case()
            if case is None:
                return
            for seed in pr.PILOT_SEEDS:
                for arm in pr.ARM_ORDER:
                    if stop_claims.is_set():
                        break
                    # TOCTOU-safe pre-claim ceiling gate (code-judge
                    # SHOULD-FIX #2): reserve this run's worst-case 150K
                    # under ledger_lock and project cumulative + ALL
                    # in-flight reservations against the round ceiling.
                    # perform_case's internal check is an unchanged
                    # sequential-semantics backstop; this projection is
                    # the authoritative gate under parallelism.
                    with ledger_lock:
                        reservations += 1
                        projected = (pr.cumulative_tokens(ledger)
                                     + reservations * pr.MAX_TOKENS_PER_RUN)
                        would_breach = projected > pr.ROUND_TOKEN_CEILING
                    if would_breach:
                        run_dir_b = pr.run_dir_for(out_root, args.round_no,
                                                   case, seed, arm)
                        with ledger_lock:
                            pr.append_ledger(round_dir, {
                                "run_path": str(run_dir_b.relative_to(out_root)),
                                "case": case, "seed": seed, "arm": arm,
                                "status": "refused_ceiling", "tokens": 0,
                                "wall_s": 0.0, "hit": None,
                                "driver": "pilot_parallel pre-claim gate",
                            })
                            checks = pr.evaluate_stop_rules(
                                ledger, pr._cases_completed(ledger))
                        trip_info["tripped"] = [
                            name for name, section in (
                                ("stop1_ssat", checks["stop1_ssat"]),
                                ("stop2_crash", checks["stop2_crash"]),
                                ("stop3_tokens", checks["stop3_tokens"]),
                                ("stop4_floor", checks["stop4_floor"]),
                            ) if section["tripped"]
                        ] or ["stop3 pre-emptive ceiling breach"]
                        trip_info["checks"] = checks
                        stop_claims.set()
                        return
                    try:
                        summary = _run_one(
                            case=case, seed=seed, arm=arm, client=client,
                            registry=registry, out_root=out_root,
                            round_no=args.round_no, label=label, model=model,
                            index_df=index_df, index_sha=index_sha,
                            ledger=ledger, ledger_lock=ledger_lock,
                            round_dir=round_dir, parallel_meta=parallel_meta,
                            worker_id=worker_id,
                        )
                    finally:
                        with ledger_lock:
                            reservations -= 1
                    # Code-judge SHOULD-FIX #1: a stop-trip return from
                    # perform_case (rc 10, e.g. pre-emptive ceiling
                    # refusal with autonomous=False) must be surfaced as
                    # a TRIP, not silently treated as "case done" and
                    # exit 3 PAUSE.
                    if summary.get("rc") == EXIT_STOP_TRIP:
                        with ledger_lock:
                            checks = pr.evaluate_stop_rules(
                                ledger, pr._cases_completed(ledger))
                        trip_info["tripped"] = [
                            name for name, section in (
                                ("stop1_ssat", checks["stop1_ssat"]),
                                ("stop2_crash", checks["stop2_crash"]),
                                ("stop3_tokens", checks["stop3_tokens"]),
                                ("stop4_floor", checks["stop4_floor"]),
                            ) if section["tripped"]
                        ] or ["stop3 pre-emptive ceiling breach"]
                        trip_info["checks"] = checks
                        stop_claims.set()
                        return
            # Case-level bookkeeping under the lock: this worker owns the
            # case, so after its 4 runs the case is complete IFF all 4
            # (seed, arm) pairs are in the ledger (they are, from this
            # worker's runs or resume skips).
            with ledger_lock:
                case_done = pr._case_complete(ledger, case, parallel_meta["max_cases"])
                if case_done:
                    pr._write_case_check(round_dir / case, ledger, case)
                checks = pr.evaluate_stop_rules(ledger, pr._cases_completed(ledger))
                trip_flags = [
                    name for name, section in (
                        ("stop1_ssat", checks["stop1_ssat"]),
                        ("stop2_crash", checks["stop2_crash"]),
                        ("stop3_tokens", checks["stop3_tokens"]),
                        ("stop4_floor", checks["stop4_floor"]),
                    ) if section["tripped"]
                ]
            if not case_done:
                continue  # paused by a refusal/skip; queue has advanced
            if checks["any_tripped"] or trip_flags:
                trip_info["tripped"] = [
                    name for name, section in (
                        ("stop1_ssat", checks["stop1_ssat"]),
                        ("stop2_crash", checks["stop2_crash"]),
                        ("stop3_tokens", checks["stop3_tokens"]),
                        ("stop4_floor", checks["stop4_floor"]),
                    ) if section["tripped"]
                ]
                trip_info["checks"] = checks
                stop_claims.set()

    wall_start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(case_worker, f"w{i + 1}") for i in range(args.concurrency)
        ]
        for fut in futures:
            exc = fut.result()
            if exc is not None:
                raise exc

    # Stamp parallel provenance onto every status.json in this round
    # (layout: {case}/seed{S}/{arm}/status.json).
    for status_path in round_dir.glob("*/*/*/status.json"):
        obj = json.loads(status_path.read_text(encoding="utf-8"))
        obj["parallel"] = {
            "driver_sha256": _driver_sha256(),
            "git_rev": _git_rev(),
            "concurrency": args.concurrency,
        }
        pr._write_json(status_path, obj)

    parallel_meta["finished"] = pr._utc_now_iso()
    parallel_meta["wall_s"] = round(time.monotonic() - wall_start, 1)
    pr._write_json(round_dir / "parallel_meta.json", parallel_meta)

    if trip_info:
        pr._write_stop(round_dir, trip_info["checks"], trip_info["tripped"])
        return EXIT_STOP_TRIP

    # Done: all planned runs recorded.
    done = sum(1 for r in ledger)
    planned = len(case_ids) * 4
    if done < planned:
        print(f"PAUSE: {done}/{planned} runs recorded", file=sys.stderr)
        return 3
    print(f"OK: {done}/{planned} runs recorded; round dir {round_dir}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parallel pilot driver (AMEND_V3_2)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run", help="Run the full round with a bounded pool")
    p.add_argument("--round", dest="round_no", type=int, required=True)
    p.add_argument("--out", type=str, required=True)
    p.add_argument("--concurrency", type=int, default=6)
    p.add_argument("--fake", action="store_true", help="offline scripted client")
    p.add_argument("--max-cases", type=int, default=None)
    p.add_argument("--no-index", action="store_true")
    p.add_argument("--cases-index", type=str,
                   default=str(pr.DEFAULT_CASES_INDEX))
    p.add_argument("--label", type=str, default="")
    p.set_defaults(func=cmd_run)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
