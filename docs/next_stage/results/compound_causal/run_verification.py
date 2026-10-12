#!/usr/bin/env python3
"""Verification runner for the compound-causal case lane.

Deliverable of lane-compound-causal: two NEW frozen counterfactual cases on
the existing case-agnostic executable environment
(:mod:`repliclaw.counterfactual.cases._base`):

* ``flowmeter_single_cause_v1`` -- SINGLE-CAUSE: exactly one latent cause
  (stale pulse calibration); fixing it and it alone makes the target pass.
* ``drift_sign_and_v1`` -- COMPOUND (AND-interaction): two latent causes
  (correction sign error x uncalibrated instrument); the failure manifests
  only when BOTH are present; each single fix alone is verified to PASS.

What this script does (real reruns, no LLM, offline):
1. Loads both cases and their frozen data (recorded sha256).
2. Runs the FULL rerun matrix -- every arm of every case -- through the
   existing executor (:func:`_base.run_canonical`), persisting the
   deterministic per-arm artifacts + case manifest under
   ``artifacts/<case_id>/``.
3. Replays each case (:func:`_base.replay`): stored arm files match their
   pinned sha256 AND a clean re-execution reproduces every pinned hash.
4. Oracle-leak check: scans every persisted artifact for the sealed
   ground-truth field names (each case's ``public_judgment_drop``) and the
   oracle schema marker; any hit FAILS the run.
5. Writes ``verification_matrix.json`` / ``.md``: case x intervention ->
   OBSERVED outcome (measured value + severity), compared against the
   pre-declared requirement pattern. Observed values are recorded as
   produced -- a mismatch with the requirement is reported as-is, never
   silently "fixed".

Usage (from the worktree root)::

    uv run python docs/next_stage/results/compound_causal/run_verification.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = Path(__file__).resolve().parent
ARTIFACTS = OUT_DIR / "artifacts"

# Pre-declared requirement pattern (structural claim under test), keyed by
# arm_id. The runner records the OBSERVED outcome and flags any deviation.
REQUIRED: dict[str, dict[str, str]] = {
    "flowmeter_single_cause_v1": {
        "I0_baseline": "mismatch",        # as-shipped: the one latent cause present
        "I1_fix_calibration": "pass",     # THE causal fix (the only fix that passes)
        "I2_account_dropped": "mismatch",  # plausible non-cause: no-op on this data
    },
    "drift_sign_and_v1": {
        "I0_baseline": "mismatch",  # BOTH causes present -> failure
        "I1_fix_sign": "pass",      # fix cause A alone (B present) -> no failure
        "I2_recalibrate": "pass",   # fix cause B alone (A present) -> no failure
        "I3_fix_both": "pass",      # both fixed (sanity) -> no failure
    },
}

MEASURED_KEY = {
    "flowmeter_single_cause_v1": "total_volume_liters",
    "drift_sign_and_v1": "mean_concentration_umg_ml",
}


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def load_cases():
    from repliclaw.counterfactual.cases.drift_sign_and import load_case as d
    from repliclaw.counterfactual.cases.flowmeter_single_cause import load_case as f

    return [f(), d()]


def run_matrix(case, out_root: Path) -> dict:
    from repliclaw.counterfactual.cases._base import replay, run_canonical

    import shutil
    if out_root.exists():
        shutil.rmtree(out_root)
    runs = run_canonical(case, out_root, seed=0)
    authentic = replay(case, out_root)
    rows = []
    for arm_id in sorted(runs):
        r = runs[arm_id]
        measured = r.target_output[MEASURED_KEY[case.case_id]]
        required = REQUIRED[case.case_id][arm_id]
        rows.append(
            {
                "case_id": case.case_id,
                "case_sha256": r.case_sha256,
                "arm_id": arm_id,
                "intervention": case.effective_config(arm_id)["intervention"],
                "config_sha256": r.config_sha256,
                "seed": r.seed,
                "measured": measured,
                "observed_severity": r.severity,
                "required_severity": required,
                "meets_requirement": r.severity == required,
                "artifact_hashes": r.artifact_hashes,
            }
        )
    return {"rows": rows, "authentic_replay": authentic}


def leak_check(case, out_root: Path) -> list:
    """Scan every persisted artifact for sealed ground-truth field names."""
    hidden = set(case.public_judgment_drop) | {"repliclaw.sealed_oracle"}
    hits = []
    for path in sorted(out_root.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for key in sorted(hidden):
            if key in text:
                hits.append(f"{path.relative_to(out_root)}: {key}")
    return hits


def main() -> int:
    cases = load_cases()
    matrix: dict[str, dict] = {}
    leaks: dict[str, list] = {}
    ok = True

    for case in cases:
        out_root = ARTIFACTS / case.case_id
        result = run_matrix(case, out_root)
        leaks[case.case_id] = leak_check(case, out_root)
        matrix[case.case_id] = {
            "case_sha256": case.case_sha256(),
            "authentic_replay": result["authentic_replay"],
            "leak_check_hits": leaks[case.case_id],
            "rows": result["rows"],
        }
        for row in result["rows"]:
            flag = "OK " if row["meets_requirement"] else "DEV"
            print(
                f"[{flag}] {row['case_id']} {row['arm_id']:18s} "
                f"measured={row['measured']!r} observed={row['observed_severity']}"
                f" required={row['required_severity']}"
            )
        print(f"      replay authentic: {result['authentic_replay']}")
        print(f"      leak check hits: {len(leaks[case.case_id])}")
        ok = ok and result["authentic_replay"] and not leaks[case.case_id] and all(
            r["meets_requirement"] for r in result["rows"]
        )

    # -- write the verification artifacts ---------------------------------
    meta = {
        "schema": "repliclaw.verification_matrix/v1",
        "lane": "lane-compound-causal",
        "repo_sha": _git_sha(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": 0,
        "runtime": {"offline": True, "deterministic": True, "llm_calls": 0},
        "executor": "repliclaw.counterfactual.cases._base (run_canonical + replay)",
        "required_pattern": REQUIRED,
        "cases": matrix,
        "all_requirements_met": bool(ok),
    }
    (OUT_DIR / "verification_matrix.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# Compound-causal verification matrix",
        "",
        f"Repo SHA: `{meta['repo_sha']}`; seed 0; offline deterministic executor "
        "(`_base.run_canonical` + `_base.replay`); 0 LLM calls.",
        "",
        "OBSERVED outcomes from actual target reruns (not expected values).",
        "",
        "| case | arm | intervention | measured | observed | required | meets |",
        "|---|---|---|---|---|---|---|",
    ]
    for case_id, m in sorted(matrix.items()):
        for r in m["rows"]:
            lines.append(
                f"| {case_id} | {r['arm_id']} | {r['intervention']} "
                f"| {r['measured']} | {r['observed_severity']} "
                f"| {r['required_severity']} | {'yes' if r['meets_requirement'] else '**NO**'} |"
            )
    lines += [
        "",
        "| case | case_sha256 | replay authentic | leak-check hits |",
        "|---|---|---|---|",
    ]
    for case_id, m in sorted(matrix.items()):
        lines.append(
            f"| {case_id} | `{m['case_sha256'][:16]}…` "
            f"| {'yes' if m['authentic_replay'] else '**NO**'} "
            f"| {len(m['leak_check_hits'])} |"
        )
    lines += [
        "",
        "Requirement structure: single-cause case -- exactly one latent cause; only "
        "I1_fix_calibration passes, the plausible non-cause I2_account_dropped still "
        "fails. AND case -- failure only with BOTH causes; each single fix (I1, I2) "
        "passes; both-fix sanity (I3) passes.",
        "",
        "Artifacts: `artifacts/<case_id>/{manifest.json,interventions/<arm>/…}`; "
        "hidden-field documentation: `HIDDEN_FIELDS.md`.",
        "",
        f"**ALL REQUIREMENTS MET: {str(bool(ok)).lower()}**",
        "",
    ]
    (OUT_DIR / "verification_matrix.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nverification_matrix.json/md written under {OUT_DIR}")
    print(f"ALL REQUIREMENTS MET: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
