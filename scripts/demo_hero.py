#!/usr/bin/env python
"""P09 hero demo — ONE command, fully OFFLINE.

Run from the worktree (or repo) root:

    /Users/sushantgautam/Documents/ScienceClawHackathon/.venv/bin/python scripts/demo_hero.py

No live LLM, no network, no API key. It demonstrates the full hero flow in one
execution by REUSING existing components only (no new science, no new claims):

  1. pins + prints the run-branch SHA and the commit/tree SHA baked into the
     generated artifacts;
  2. runs the P07 vertical slice (``run_slice``) showing:
       claim -> 3 independent investigations -> hash-only prediction
       commitments (escrow) -> sealed reveal vs outcome ->
       evidence-derived need-market reallocation -> provenance-linked verdict;
  3. independently RE-verifies the persisted runs (re-execution + pinned
     ``hashes.json`` compare, the same ``verify_run`` semantics demo_slice uses);
  4. runs ONE offline comparator arm via the runner CLI (S0 single-agent and
     eess_offline RepliClaw slice, --client-factory fake, into
     ``artifacts/demo-hero/<ts>/arms/``) and asserts the two arms'
     ``envelope_sha256`` are identical (C1 matched-budget same-task);
  5. prints an honest summary (what is real offline vs. what is NOT
     demonstrated);
  6. exits 0 only if every step passes and writes
     ``artifacts/demo-hero/<ts>/demo_report.json`` (machine-readable summary).

Determinism claim (stated honestly): the *scientific* substrate — the seeded
SimpleAudit counterfactual outputs and their pinned ``hashes.json`` — is
bit-for-bit reproducible (proven by the ``determinism`` block below). The
*escrow bookkeeping* (per-run UUID packet ids, wall-clock timestamps, the
``prev_event_sha256`` hash chain, and the derived ``evidence_snapshot_sha256``)
intentionally differs across runs; that is reported, not faked.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Make both `repliclaw` (src/) and `demo_slice` (this dir) importable when run
# as a plain script from the worktree root.
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
SCRIPTS = Path(__file__).resolve().parent
for p in (SRC, SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from demo_slice import SEED, _reverify  # noqa: E402  (reused, not forked)

from repliclaw.slice import run_slice  # noqa: E402

# Two offline arms, same case, same envelope (C1 matched-budget same-task).
ARMS = [("S0", "single_agent"), ("eess_offline", "eess_offline")]
CASE = "policy_rag"

# The reproducible *science* fields of the slice (stable across runs).
SCIENCE_KEYS = (
    "case_id", "agent_ids", "predictions_outcome", "stop_reason",
    "published_evidence", "revealed_verified", "revealed_mismatch",
    "choice_trace",
)


# ---------------------------------------------------------------------------
# Git pinning
# ---------------------------------------------------------------------------
def _git(repo: Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=repo, check=True,
            capture_output=True, text=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def pin_repo() -> Dict[str, str]:
    return {
        "branch": _git(REPO_ROOT, "rev-parse", "--abbrev-ref", "HEAD"),
        "commit_sha": _git(REPO_ROOT, "rev-parse", "HEAD"),
        "short_sha": _git(REPO_ROOT, "rev-parse", "--short", "HEAD"),
        "dirty": _git(REPO_ROOT, "status", "--porcelain") != "",
    }


# ---------------------------------------------------------------------------
# Deterministic digest of a *science* subtree (bit-for-bit, no normalization)
# ---------------------------------------------------------------------------
def science_tree_digest(root: Path, subtree: str) -> str:
    """SHA256 over the sorted relative paths + raw bytes of ``root/subtree``.

    The counterfactual runs are seeded and wall-clock-free, so this digest is
    reproducible run-to-run (and identical between the slice and the
    ``eess_offline`` arm, which embeds the same rooted slice)."""
    base = Path(root) / subtree
    acc = hashlib.sha256()
    for p in sorted(base.rglob("*")):
        if p.is_file():
            acc.update(str(p.relative_to(base)).encode("utf-8"))
            acc.update(hashlib.sha256(p.read_bytes()).hexdigest().encode("utf-8"))
    return acc.hexdigest()


# ---------------------------------------------------------------------------
# Arm execution via the runner CLI (a real CLI invocation, --client-factory fake)
# ---------------------------------------------------------------------------
def run_arm_cli(root: Path, rel_out: Path, arm: str) -> Dict[str, Any]:
    out_abs = (root / rel_out).resolve()
    cmd = [
        sys.executable, "-m", "repliclaw.comparators.runner",
        "--arm", arm, "--case", CASE, "--client-factory", "fake",
        "--out", str(out_abs),
    ]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    # The runner prints one JSON line on stdout (stderr carries a harmless
    # runpy RuntimeWarning); parse the last non-empty stdout line.
    payload: Dict[str, Any] = {}
    for line in reversed([ln for ln in proc.stdout.splitlines() if ln.strip()]):
        try:
            payload = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    run_dir = out_abs / "run-01"
    fv_path = run_dir / "final_verdict.json"
    envelope_sha = verdict = status = None
    if fv_path.exists():
        fv = json.loads(fv_path.read_text(encoding="utf-8"))
        envelope_sha = fv.get("envelope_sha256")
        verdict = fv.get("verdict")
        status = fv.get("status")
    return {
        "arm": arm,
        "runner_exit": proc.returncode,
        "runner_payload": payload,
        "run_dir": str(run_dir),
        "envelope_sha256": envelope_sha,
        "verdict": verdict,
        "status": status,
        "stderr_tail": (proc.stderr or "").strip().splitlines()[-1:] or [],
    }


def _science_subtree(run_dir: Path, arm: str) -> str:
    """Where the rooted slice lives inside an arm's run-01 dir."""
    return "eess/runs" if arm == "eess_offline" else "runs"


# ---------------------------------------------------------------------------
# Slice verification
# ---------------------------------------------------------------------------
def verify_slice(run_root: Path) -> bool:
    ok = _reverify(run_root)
    print(f"\nIndependent re-execution verification (slice): {'PASS' if ok else 'FAIL'}")
    return ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_root = REPO_ROOT / "artifacts" / "demo-hero" / f"run-{ts}"
    run_root.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("P09 HERO DEMO — one command, fully OFFLINE (no live LLM / no network)")
    print("=" * 72)

    # ---- 1. Pin + print the run-branch SHA and artifact commit SHAs --------
    pin = pin_repo()
    print(f"\n[1] run-branch : {pin['branch']} @ {pin['commit_sha'][:12]}")
    print(f"    tree dirty : {pin['dirty']}   "
          f"(committed tree is what the artifacts pin)")

    # ---- 2. Vertical slice: claim -> investigations -> escrow -> reveal ----
    slice_root = run_root / "slice"
    slice_root.mkdir(parents=True, exist_ok=True)
    print(f"\n[2] Running P07 vertical slice into {slice_root.relative_to(REPO_ROOT)} ...")
    report = run_slice(slice_root)
    res = report.result

    print(f"    stop_reason           : {res.stop_reason}")
    print(f"    revealed_verified     : {res.revealed_verified}")
    print(f"    revealed_mismatch     : {res.revealed_mismatch}")
    print(f"    published_evidence    : {res.published_evidence}")
    print(f"    evidence_snapshot_sha : {res.evidence_snapshot_sha256}")
    print("    per-agent prediction verdicts (sealed reveal vs outcome):")
    for agent_id in res.agent_ids:
        v = res.predictions_outcome[agent_id]
        print(f"      {agent_id:<6} {v['hypothesis_id']}  ->  {v['outcome']}")
    print("    evidence-derived choice-change trace (need-market reallocation):")
    if res.choice_trace:
        for entry in res.choice_trace:
            print(f"      cycle {entry['cycle']}: {entry['agent_id']}  "
                  f"{entry['prev_top']}  ->  {entry['new_top']}")
    else:
        print("      (none)")

    # ---- 3. Independent re-verification of the persisted slice runs --------
    print("\n[3] Re-executing persisted arms and comparing pinned hashes.json ...")
    slice_ok = verify_slice(slice_root)

    # ---- 4. One offline comparator arm per arm (S0 + eess_offline), C1 -----
    print(f"\n[4] Running offline comparator arms via the runner CLI into "
          f"{(run_root / 'arms').relative_to(REPO_ROOT)}/ ...")
    arms: Dict[str, Dict[str, Any]] = {}
    for arm, _ in ARMS:
        rel_out = run_root / "arms" / arm
        info = run_arm_cli(REPO_ROOT, rel_out, arm)
        arms[arm] = info
        print(f"    {arm:<14} runner_exit={info['runner_exit']}  "
              f"status={info['status']}  verdict={info['verdict']}")
        print(f"    {arm:<14} envelope_sha256={info['envelope_sha256']}")

    env_s0 = arms["S0"]["envelope_sha256"]
    env_eess = arms["eess_offline"]["envelope_sha256"]
    c1_ok = bool(env_s0) and env_s0 == env_eess
    print(f"\n    C1 matched-budget same-task: envelope_sha256 identical = {c1_ok}")
    print(f"      S0            : {env_s0}")
    print(f"      eess_offline  : {env_eess}")
    if arms["S0"]["verdict"] != arms["eess_offline"]["verdict"]:
        print(f"    (honest) arms DISAGREE: S0={arms['S0']['verdict']} vs "
              f"eess_offline={arms['eess_offline']['verdict']} — displayed, not hidden.")

    # ---- 5. Determinism: reproducible science vs. honest escrow variance ---
    print("\n[5] Determinism (what is reproducible, bit-for-bit):")
    slice_science_digest = science_tree_digest(slice_root, "runs")
    print(f"    slice runs/ digest            : {slice_science_digest[:16]}...")
    eess_science_digest = science_tree_digest(
        Path(arms["eess_offline"]["run_dir"]), "eess/runs")
    print(f"    eess_offline eess/runs digest : {eess_science_digest[:16]}...")
    same_science = slice_science_digest == eess_science_digest
    print(f"    slice.runs == eess_offline.runs (same rooted slice) : {same_science}")

    # The full slice_result.json (incl. the run-specific snapshot) for reference.
    full_slice_result = json.loads((slice_root / "slice_result.json").read_text("utf-8"))
    # Stable *science* fields (reproducible across runs). choice_trace is kept
    # but its run-specific ``snapshot_sha`` (derived from the wall-clock-tainted
    # evidence view) is stripped so this block stays reproducible; the reallocation
    # DIRECTION (prev_top -> new_top, cycle, agent) is the reproducible fact.
    stable_choice_trace = [
        {k: v for k, v in entry.items() if k != "snapshot_sha"}
        for entry in res.choice_trace
    ]
    stable_science = {
        k: (stable_choice_trace if k == "choice_trace" else res.to_dict()[k])
        for k in SCIENCE_KEYS if k in res.to_dict()
    }

    # ---- 6. Honest summary -------------------------------------------------
    real = [
        "offline deterministic substrate: seeded SimpleAudit counterfactual runs "
        "(runs/**) and their pinned hashes.json are bit-for-bit reproducible and "
        "identical between the slice and the eess_offline arm",
        "escrow integrity: hash-only prediction commitments are sealed and "
        "reveal-verified against the committed commitment_sha256 "
        f"({res.revealed_verified}/{len(res.agent_ids)} verified, "
        f"{res.revealed_mismatch} mismatch)",
        "independent re-verification: persisted arms are re-executed and the "
        "pinned artifact hashes re-derived and compared (never self-attested)",
        "matched-budget same-task comparison structure (C1): two offline arms "
        "share one envelope hash under --client-factory fake",
    ]
    not_demonstrated = [
        "live-LLM performance claims (no live model / API key / network here); "
        "the live arm S5/A1/A3 and any live-vs-offline performance gap are OUT of "
        "scope for this offline run",
        "bulk S5 (full EESS) campaign run — only the offline eess_offline slice is "
        "shown; a full multi-agent live EESS run is not demonstrated",
        "byte-identity of the WHOLE run directory across runs: the escrow "
        "bookkeeping (per-run UUID packet ids, wall-clock timestamps, the "
        "prev_event_sha256 hash chain, and the derived evidence_snapshot_sha256) "
        "intentionally differs run-to-run — only the science subtree + pinned "
        "hashes.json are reproducible",
        "third-party / other-team verify() integration is NOT shown (label bonus "
        "unachieved in this offline slice)",
        "the slice produces per-hypothesis supported/refuted outcomes, not a "
        "single calibrated confidence score; the comparator arms' verdicts are "
        "shown, and where they disagree the disagreement is displayed honestly",
    ]
    print("\n[6] HONEST SUMMARY")
    print("    REAL (demonstrated offline, reproducible):")
    for r in real:
        print(f"      + {r}")
    print("    NOT demonstrated offline (not faked):")
    for r in not_demonstrated:
        print(f"      - {r}")

    # ---- 7. Write the machine-readable report ------------------------------
    report_doc = {
        "schema": "p09.demo_report/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_root": str(run_root),
        "ts": ts,
        "offline": True,
        "client_factory": "fake",
        "pin": pin,
        "case": CASE,
        "seed": SEED,
        "arms_run": [a for a, _ in ARMS],
        "slice": {
            "run_root": str(slice_root),
            "stop_reason": res.stop_reason,
            "revealed_verified": res.revealed_verified,
            "revealed_mismatch": res.revealed_mismatch,
            "published_evidence": res.published_evidence,
            "evidence_snapshot_sha256": res.evidence_snapshot_sha256,
            "predictions_outcome": res.predictions_outcome,
            "choice_trace": res.choice_trace,
            "stable_science": stable_science,
            "science_runs_digest": slice_science_digest,
            "full_slice_result": full_slice_result,
        },
        "arms": {
            arm: {
                "run_dir": info["run_dir"],
                "runner_exit": info["runner_exit"],
                "status": info["status"],
                "verdict": info["verdict"],
                "envelope_sha256": info["envelope_sha256"],
            } for arm, info in arms.items()
        },
        "eess_offline_science_runs_digest": eess_science_digest,
        "determinism": {
            "science_runs_slice": slice_science_digest,
            "science_runs_eess_offline": eess_science_digest,
            "slice_runs_equal_eess_runs": same_science,
            "note": "the seeded science subtree (runs/**) is bit-for-bit "
                    "reproducible and identical between the slice and the "
                    "eess_offline arm; the escrow bookkeeping (uuid packet "
                    "ids, timestamps, prev_event_sha256 chain, "
                    "evidence_snapshot_sha256) intentionally differs per run",
        },
        "verification": {
            "slice_reverify": slice_ok,
            "c1_envelope_identical": c1_ok,
            "envelope_sha256": {"S0": env_s0, "eess_offline": env_eess},
        },
        "honest": {
            "real": real,
            "not_demonstrated": not_demonstrated,
        },
    }
    report_path = run_root / "demo_report.json"
    report_path.write_text(
        json.dumps(report_doc, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\n    report written: {report_path.relative_to(REPO_ROOT)}")

    # ---- 8. Gate -----------------------------------------------------------
    all_ok = (
        res.stop_reason == "all_needs_fulfilled"
        and res.revealed_mismatch == 0
        and slice_ok
        and c1_ok
        and all(arms[a]["runner_exit"] == 0 for a, _ in ARMS)
        and same_science
    )
    print("\n" + "=" * 72)
    if all_ok:
        print("DEMO OK")
    else:
        print("DEMO FAILED")
    print("=" * 72)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
