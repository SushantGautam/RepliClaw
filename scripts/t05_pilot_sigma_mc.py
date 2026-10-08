#!/usr/bin/env python3
"""T0+5 — pilot-σ MC variant cell set (SIMULATION-ONLY).

Frozen-protocol basis (quoted):

* g3_pilot_spec_draft.md T0+5 (timeline row, §8): "Pilot-σ MC variant cell
  set (10-line extension of `monte_carlo_power.py`, sha-pinned per C-SCI-2)
  recomputes power at σ̂_D for the candidate (N=24, k∈{2,3,4}, MDE
  0.15/0.20) cells".
* monte_carlo_power_v3.md §3.2 item 3: "prereg must state 'with N=24, k=4,
  mid variance, the design has 84% power for Δ=0.20; the maximum Δ
  detectable at 80% power is ≈ 0.18', recomputed with pilot σ̂_D via this
  MC script (seed scheme + cells are reproducible; a pilot-σ variant cell
  set is a 10-line extension, to be run post-pilot, before prereg
  freeze)".
* g3_pilot_spec_draft.md §6 freeze table (Before column, estimator
  definitions): "σ̂_D computed on paired per-case differences, k=2,
  cluster=case; … ITT (failed runs = non-success)".
* statistical_protocol_v3.md §4.1: "the between-case variance of the
  paired difference σ²_D = Var_c(d_c)".

Therefore T0+5 = the MC power/sigma grid keyed on the OBSERVED pilot
contrast σ̂_D: the same frozen generator + frozen CI step, with the
between-case distribution of p_c scaled so its variance equals σ̂_D,
evaluated on the T0+5 candidate cells (N=24, k∈{2,3,4}, Δ ∈ {0, 0.15,
0.20}) plus a per-k maximum-detectable-Δ-at-80% search (Δ step 0.01).

INPUT — the pilot report file (pilot_report_round{R}.json as written by
scripts/pilot_report.py). Round 1's disclosure exists (round1 report,
stop-2 tripped, FEASIBILITY-FAILED). ROUND-2 INPUT ARRIVES POST-RUN: the
round-2 report file is passed as the same positional argument; this
script treats any round report identically and records its path + sha256
in the output meta (both rounds' inputs are thereby carried in the
frozen way the protocol permits: per-round σ̂_D, per-round cell set,
disclosed in the report).

Pilot-side σ̂_D estimation (evaluator-isolated, pilot_report.py pattern):
reads ONLY the round's ``ledger.jsonl`` (status/tokens), per-run
``status.json`` (status), and scorer-side ``score.json`` (``hit``).
Ground truth is NEVER read: ``true_service`` in score.json is written by
the scorer and is never consumed here; ``manifest.py`` /
``heldout_ground_truth`` / ``cases.parquet`` are never imported/opened.
A case enters the paired-contrast set only if BOTH arms have all k
seed runs ``completed`` with ``hit`` not None (spec §6 estimator
definition: paired per-case differences, k=2, ITT). Saturated cases
(arm hit on all k seeds) are disclosed, and the per-arm s + dead-contrast
figures are re-emitted from the ledger, mirroring the T0+4 report.
Spec §2 fallback: minimum viable paired-contrast set is n = 8; below
that the script writes a DETERMINISTIC INSUFFICIENT-ESTIMATE artifact
(no MC numbers, no fabricated σ̂_D) and exits 0 — that is the actual
round-1 outcome (1 paired-contrast case), by design, not an error.

Frozen constants (INHERITED, unchanged — statistical_protocol_v3.md
§2.2, FROZEN-CONSTANTS appendix, monte_carlo_power_v3.md §1.1):
* CI step: the PINNED L5 ``cluster_bootstrap_ci`` (B=10,000,
  ``numpy.random.default_rng(20261009)``, PCG64, percentile 95%) —
  imported from ``src/repliclaw/benchmarks/common/cluster_bootstrap.py``,
  called verbatim once per MC rep; never re-implemented.
* Per-cell MC seed: ``numpy default_rng(20261009 + cell_index)``.
  Stored-grid cells keep their 254-run index (mc_rule015.py convention);
  pilot-σ cells are NEW cells (their between-case distribution depends
  on the observed σ̂_D) and extend from index 254 in deterministic cell
  order, documented in the output meta.

Pilot-σ between-case distribution (conservative reading, documented):
  p_c ~ U[0.35 − σ̂_D/2, 0.35 + σ̂_D/2] (uniform, as in the frozen
  generator; midpoint 0.35 = midpoint of the frozen 'mid' band
  U[0.05, 0.65]; σ_Δ set exactly to σ̂_D). D-E: min(1, p_c + Δ); C-EQ:
  p_c. No saturation cells in this variant: real-round saturation is the
  S-sat gate's job (monte_carlo_power_v3.md §4), and the generator's
  Δ>0 rows in the stored grid are the no-saturation rows.
AMBIGUITY FLAG (orchestrator decision): the retired §4.2 formula
  carried an "inflate σ̂_D · 1.3 unless n_pilot ≥ 12" cushion. The MC
  grid is the sole power authority (D-V3-008) and its cells are defined
  by an explicit p_c distribution, so this script does NOT apply the
  1.3 factor to the MC cells; instead the σ̂_D-variant cells are
  bracketed against the stored grid's 'low' (σ_Δ≈0.12) and 'mid'
  (σ_Δ≈0.18) rows for the same (N, k, Δ) so the prereg can cite the
  honest range. If the program wants 1.3 inside the MC, that is a
  versioned amendment (new σ̂_D×1.3 cell set), not a silent input.

Reproduction gate (like mc_rule015.py, before any pilot-σ numbers):
byte-compare the pinned L5 against the scratch reference, then re-run
one STORED-grid cell verbatim (N=24, k=2, Δ=0.15, 'mid', no-sat;
254-run index 27) at R=10,000 and require EXACT match of the stored
values (power_lo_gt_0, power_a1_floor, theta_achieved) in
monte_carlo_power_v3_results.json. Any mismatch aborts with no output
written.

SIMULATION-ONLY: synthetic Bernoulli data; no live RepliClaw outcome
data enters the MC; no effect claim is made from this artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]  # noqa: E402
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from repliclaw.benchmarks.common import cluster_bootstrap as cb  # noqa: E402  # pinned L5

# ---- frozen constants (must match the 254-cell run; asserted) ----
assert cb.N_BOOT == 10_000, "frozen B changed"
assert cb.BOOTSTRAP_SEED == 20261009, "frozen bootstrap seed changed"
MC_SEED_BASE = 20261009
R_REPS = 10_000
N_HELDOUT = 24
KS = (2, 3, 4)
MDES = (0.15, 0.20)
SEARCH_DELTAS = tuple(round(0.05 + 0.01 * i, 2) for i in range(46))  # 0.05..0.50
A1_FLOOR = 0.10  # scratch mc_rule015 A1 floor rule (rule_a1), for disclosure
MIN_VIABLE = 8  # spec §2 fallback: below n=8 σ̂_D too coarse
P_C_MIDPOINT = 0.35  # midpoint of the frozen 'mid' band U[0.05, 0.65]

SCRATCH = Path("/Users/sushantgautam/Documents/stg2-worktrees/statistics")
STORED = SCRATCH / "monte_carlo_power_v3_results.json"
# 254-run index of (N=24, k=2, d=0.15, mid, none, 0.0) — verified present.
REPRO_KEY = (24, 2, 0.15, "mid", "none", 0.0)
NEW_CELL_BASE = 254  # pilot-σ cells extend the 254-run index space

OUTPUT_DIR = REPO_ROOT / "docs" / "next_stage" / "data"
MODEL_LABEL = ("MODEL-SUBSTITUTION — pilot run model; NOT the official "
               "released baseline")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin_equivalence() -> str:
    """Prove the imported L5 is byte-identical to the scratch copy that
    produced the 254-cell grid (mc_rule015.py convention)."""
    src = REPO_ROOT / "src/repliclaw/benchmarks/common/cluster_bootstrap.py"
    ref = SCRATCH / "cluster_bootstrap.py"
    s_src, s_ref = sha256_file(src), sha256_file(ref)
    assert s_src == s_ref, f"L5 pin drifted: {s_src[:12]} vs {s_ref[:12]}"
    print(f"L5 pin sha256 == scratch reference: {s_src[:16]}… OK", flush=True)
    return s_src


def load_ledger(round_dir: Path) -> list[dict[str, Any]]:
    ledger = round_dir / "ledger.jsonl"
    if not ledger.is_file():
        raise SystemExit(f"no ledger.jsonl in {round_dir}")
    with open(ledger, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _run_dir(round_dir: Path, r: dict[str, Any]) -> Path:
    # run_path is relative to the run dir (parent of the round dir),
    # exactly as pilot_report.py reads it.
    return round_dir.parent / str(r.get("run_path", ""))


def pilot_side_summary(
    round_dir: Path,
    runs: list[dict[str, Any]],
    k: int = 2,
    n_cohort: int = 10,
) -> dict[str, Any]:
    """Pilot-side quantities from ledger/STOP/case files ONLY
    (evaluator isolation: pilot_report.py pattern)."""
    per_arm: dict[str, Any] = {}
    case_arm_seeds: dict[str, dict[str, dict[str, Any]]] = {}
    for r in runs:
        case_arm_seeds.setdefault(str(r["case"]), {}).setdefault(
            str(r["arm"]), {})[str(r["seed"])] = r
    arms: list[str] = sorted({str(r["arm"]) for r in runs if r.get("arm")})
    for arm in arms:
        sat: list[str] = []
        n_crash = 0
        n_runs = 0
        for case in sorted(case_arm_seeds):
            seeds = case_arm_seeds[case].get(arm, {})
            if not seeds:
                continue
            all_hit = len(seeds) == k and all(
                s.get("hit") is True for s in seeds.values())
            if all_hit:
                sat.append(case)
        for case in sorted(case_arm_seeds):
            for s in case_arm_seeds[case].get(arm, {}).values():
                n_runs += 1
                if s.get("status") != "completed":
                    n_crash += 1
        s_val = len(sat) / n_cohort
        per_arm[arm] = {
            "s": round(s_val, 6),
            "saturation_cases": sat,
            "crash_rate_full_cohort": round(n_crash / (n_cohort * k), 6),
            "n_runs": n_runs,
        }
    def _saturated(case: str, arm: str) -> bool:
        return (len(case_arm_seeds[case].get(arm, {})) == k
                and all(s.get("hit") is True
                        for s in case_arm_seeds[case].get(arm, {}).values()))

    cases_sorted = sorted(case_arm_seeds)
    both_sat = [c for c in cases_sorted
                if len(arms) == 2 and all(_saturated(c, a) for a in arms)]
    one_sat = [c for c in cases_sorted
               if len(arms) == 2
               and len([a for a in arms if _saturated(c, a)]) == 1]
    return {
        "per_arm": per_arm,
        "both_saturated": both_sat,
        "exactly_one_saturated": one_sat,
    }


def paired_diffs(
    round_dir: Path, k: int = 2, planned_seeds: list[str] | None = None,
) -> dict[str, Any]:
    """Per-case paired difference d_c = p_c(D-E) − p_c(C-EQ), ITT
    (frozen estimator definition, spec §6: 'ITT (failed runs =
    non-success)').

    p_c(arm) = seed-pooled success rate over the k planned seed runs;
    a seed run counts as a success ONLY if status == 'completed' AND
    the scorer-side score.json says hit == True; ANY other outcome
    (crash, abort, no run recorded, missing/None hit) counts as a
    non-success = 0 — never excluded (ITT). A case enters the
    paired-contrast set only if it was OBSERVED by the pilot, i.e. has
    at least one recorded run in each arm; cases with zero runs in an
    arm (pilot stopped before reaching it) are not observed and are
    listed, not imputed.

    Read surface mirrors pilot_report.py exactly (ledger.jsonl, per-run
    status.json, scorer-side score.json 'hit'). Ground truth is never
    read: score.json's true_service is never consumed;
    manifest/heldout_ground_truth/cases.parquet are never opened.

    ``planned_seeds`` = the round's k planned seed ids (from the round's
    pilot report 'seeds' field); every planned seed run that has no
    ledger row or no completed+hit outcome is a non-success."""
    runs = load_ledger(round_dir)
    case_arm: dict[str, dict[str, dict[str, Any]]] = {}
    for r in runs:
        case_arm.setdefault(r["case"], {}).setdefault(
            str(r.get("arm")), {})[str(r.get("seed"))] = r
    if planned_seeds is None:  # fall back to observed union
        planned_seeds = sorted({str(s)
                                for a in case_arm.values()
                                for seeds in a.values() for s in seeds})
    d: dict[str, float] = {}
    detail: dict[str, Any] = {}
    excluded: dict[str, str] = {}
    for case in sorted(case_arm):
        arms_present = case_arm[case]
        if "D-E-TELEM" not in arms_present or "C-EQ-TELEM" not in arms_present:
            excluded[case] = f"arms with runs: {sorted(arms_present)}"
            continue
        vals: dict[str, float] = {}
        per_seed: dict[str, Any] = {}
        for arm in ("D-E-TELEM", "C-EQ-TELEM"):
            n_success = 0
            seeds_detail: dict[str, Any] = {}
            for seed in planned_seeds:  # the k planned seed runs
                run = arms_present[arm].get(str(seed))
                if run is None:
                    seeds_detail[str(seed)] = "no_run"
                    continue
                status: Any = run.get("status")
                hit: Any = None
                if status == "completed":
                    score = _run_dir(round_dir, run) / "score.json"
                    if score.is_file():
                        hit = json.loads(score.read_text()).get("hit")
                success = status == "completed" and hit is True
                if success:
                    n_success += 1
                seeds_detail[str(seed)] = (
                    "hit" if success else f"status={status},hit={hit}")
            vals[arm] = n_success / len(planned_seeds)
            per_seed[arm] = seeds_detail
        d[case] = round(vals["D-E-TELEM"] - vals["C-EQ-TELEM"], 6)
        detail[case] = {"p_c": {a: round(v, 6) for a, v in vals.items()},
                        "seeds": per_seed}
    return {"d": d, "excluded": excluded, "detail": detail}


def sigma_d_hat(d: dict[str, float]) -> float | None:
    """σ̂_D = sample std of the per-case paired differences (n−1).
    None when < 2 cases (variance undefined)."""
    xs = list(d.values())
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def generate_pilot_sigma(
    rng: np.random.Generator, n: int, k: int, delta: float, sigma2: float,
) -> np.ndarray:
    """One MC table of R_REPS datasets -> per-case diffs d (R, N).
    Identical RNG draw order to the frozen scratch generator
    (monte_carlo_power.py): uniform(p_c) -> random(mask) -> random(de)
    -> random(ceq). The mask draw is consumed even for no-saturation
    cells (s=0.0 -> all False), matching the frozen generator exactly;
    p_c ~ U[midpoint−σ/2, midpoint+σ/2] replaces the frozen low/mid
    bands (the only change in this 10-line extension)."""
    lo = max(0.0, P_C_MIDPOINT - sigma2 / 2.0)
    hi = min(1.0, P_C_MIDPOINT + sigma2 / 2.0)
    q = rng.uniform(lo, hi, size=(R_REPS, n))
    mask = rng.random((R_REPS, n)) < 0.0  # frozen draw order; s=0.0 no-sat
    p_ceq = q
    p_de = np.where(mask, 1.0, q + delta)
    p_de = np.clip(p_de, 0.0, 1.0)
    s_de = (rng.random((R_REPS, n, k)) < p_de[:, :, None]).sum(axis=2)
    s_ceq = (rng.random((R_REPS, n, k)) < p_ceq[:, :, None]).sum(axis=2)
    return (s_de - s_ceq) / k


def run_cell(
    cell: dict[str, Any], index: int, sigma2: float,
) -> dict[str, Any]:
    rng = np.random.default_rng(MC_SEED_BASE + index)  # frozen scheme
    d = generate_pilot_sigma(rng, cell["N"], cell["k"], cell["delta"], sigma2)
    hits = 0
    a1 = 0
    theta_sum = 0.0
    lo_sum = 0.0
    t0 = time.time()
    for r in range(R_REPS):
        lo, _hi, th = cb.cluster_bootstrap_ci(d[r])
        if lo > 0:
            hits += 1
            if th >= A1_FLOOR:
                a1 += 1
        theta_sum += th
        lo_sum += lo
        if (r + 1) % 2500 == 0:
            el = time.time() - t0
            print(f"  cell idx={index} rep {r + 1}/{R_REPS} "
                  f"(~{el / (r + 1) * (R_REPS - r - 1):.0f}s left) "
                  f"power={hits / (r + 1):.3f}", flush=True)
    p = hits / R_REPS
    pa1 = a1 / R_REPS
    return {
        **cell,
        "index": index,
        "mc_seed": MC_SEED_BASE + index,
        "R": R_REPS,
        "power_lo_gt_0": round(p, 5),
        "power_lo_gt_0_se": round(
            float(np.sqrt(p * (1.0 - p) / (R_REPS - 1))), 5),
        "power_a1_floor": round(pa1, 5),
        "power_a1_floor_se": round(
            float(np.sqrt(pa1 * (1.0 - pa1) / (R_REPS - 1))), 5),
        "theta_achieved": round(float(d.mean()), 5),
        "theta_mean_of_boot": round(theta_sum / R_REPS, 5),
        "lo_mean": round(lo_sum / R_REPS, 5),
    }


def stored_grid_cells() -> list[dict[str, Any]]:
    """Rebuild the 254-cell grid order verbatim (mc_rule015.py
    convention) so the stored lookup and index assignment are exact."""
    variances = ("low", "mid")
    cells: list[dict[str, Any]] = []
    for delta in (0.00, 0.10, 0.15, 0.20, 0.30):
        for n in (12, 16, 20, 24, 30):
            for var in variances:
                cells.append(dict(N=n, k=2, delta=delta,
                                  variance=var, sat="none", s=0.0))
    for delta in (0.15, 0.20, 0.30):
        for n in (12, 16, 20, 24, 30):
            for var in variances:
                for sat, s in (("both", 0.25), ("both", 0.50), ("both", 0.75),
                               ("de_only", 0.25), ("de_only", 0.50),
                               ("de_only", 0.75)):
                    cells.append(dict(N=n, k=2, delta=delta,
                                      variance=var, sat=sat, s=s))
    for n in (12, 24):
        for var in variances:
            for sat, s in (("both", 0.50), ("both", 0.75), ("de_only", 0.50)):
                cells.append(dict(N=n, k=2, delta=0.0,
                                  variance=var, sat=sat, s=s))
    for delta in (0.15, 0.20):
        for n in (16, 20, 24):
            for k in (3, 4):
                cells.append(dict(N=n, k=k, delta=delta,
                                  variance="mid", sat="none", s=0.0))
    assert len(cells) == 254, len(cells)
    return cells


def run_reproduction_gate() -> None:
    """Re-run stored cell (254-run index of REPRO_KEY) at R=10,000 with
    the FROZEN 'mid' band (the generator's own 'mid' distribution,
    U[0.05, 0.65]) and require an exact match of the stored values."""
    stored = {
        (c["N"], c["k"], c["delta"], c["variance"], c["sat"], c["s"]): c
        for c in json.loads(STORED.read_text())["cells"]
    }
    assert REPRO_KEY in stored, "repro cell missing from stored results"
    idx = stored[REPRO_KEY]["index"]
    rng = np.random.default_rng(MC_SEED_BASE + idx)
    lo, hi = 0.05, 0.65  # frozen 'mid' band
    n, k = 24, 2
    q = rng.uniform(lo, hi, size=(R_REPS, n))
    rng.random((R_REPS, n))  # frozen draw order: mask draw consumed (s=0.0 no-sat)
    p_de = np.clip(q + REPRO_KEY[2], 0.0, 1.0)
    s_de = (rng.random((R_REPS, n, k)) < p_de[:, :, None]).sum(axis=2)
    s_ceq = (rng.random((R_REPS, n, k)) < q[:, :, None]).sum(axis=2)
    d = (s_de - s_ceq) / k
    hits = 0
    a1 = 0
    theta_sum = 0.0
    for r in range(R_REPS):
        lo_ci, _hi_ci, th = cb.cluster_bootstrap_ci(d[r])
        if lo_ci > 0:
            hits += 1
            if th >= 0.10:
                a1 += 1
        theta_sum += th
    got = (round(hits / R_REPS, 5), round(a1 / R_REPS, 5),
           round(float(d.mean()), 5))
    ref = stored[REPRO_KEY]
    want = (ref["power_lo_gt_0"], ref["power_a1_floor"],
            ref["theta_achieved"])
    print(f"REPRODUCTION GATE: stored cell index {idx} "
          f"(N=24 k=2 d=0.15 mid no-sat), R={R_REPS} …", flush=True)
    print(f"  stored:     {want}", flush=True)
    print(f"  recomputed: {got}", flush=True)
    assert got == want, (
        f"REPRO FAILED: {got} != {want} — STOP, do not write pilot-σ "
        f"results (numpy {np.__version__}); report to orchestrator.")
    print(f"  REPRODUCTION OK (exact match, numpy {np.__version__})",
          flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="T0+5 pilot-σ MC variant")
    ap.add_argument("pilot_report", type=Path,
                    help="pilot_report_round{R}.json (round 1 now; round 2 "
                         "arrives post-run — same interface, recorded in "
                         "meta with path + sha256)")
    ap.add_argument("--out", type=Path, default=None,
                    help="output JSON path (default "
                         "docs/next_stage/data/t05_pilot_sigma_mc_<round>.json)")
    args = ap.parse_args()

    report_path = args.pilot_report
    if not report_path.is_file():
        raise SystemExit(f"pilot report not found: {report_path}")
    report = json.loads(report_path.read_text())
    round_id = str(report.get("round", "unknown"))
    round_dir = report_path.parent
    out_path = args.out or (
        OUTPUT_DIR / f"t05_pilot_sigma_mc_round{round_id}.json")

    print(f"round {round_id} report: {report_path} "
          f"sha256={sha256_file(report_path)[:16]}…", flush=True)
    pin_equivalence()
    summary = pilot_side_summary(round_dir, load_ledger(round_dir))
    pairs = paired_diffs(round_dir, planned_seeds=[str(s)
                                                    for s in report.get("seeds", [])]
                         or None)
    sigma2 = sigma_d_hat(pairs["d"])
    n_pairs = len(pairs["d"])

    meta = {
        "label": ("T0+5 pilot-σ variant cell set (SIMULATION-ONLY: "
                  "synthetic Bernoulli data; power of the frozen "
                  "one-sided percentile-bootstrap rule; no live "
                  "RepliClaw outcome data enters the MC)"),
        "protocol_basis": ("g3_pilot_spec_draft.md T0+5 row; "
                           "monte_carlo_power_v3.md §3.2 item 3; "
                           "spec §6 estimator definitions; "
                           "statistical_protocol_v3.md §4.1"),
        "pilot_report": {"path": str(report_path),
                         "sha256": sha256_file(report_path),
                         "round": round_id,
                         "model_label": report.get("model_label") or MODEL_LABEL},
        "round2_note": ("round-2 input arrives post-run: pass the round-2 "
                        "pilot_report_round2.json to the same script; "
                        "per-round σ̂_D and per-round cell set are "
                        "disclosed in the output"),
        "ci_step": (f"pinned L5 cluster_bootstrap_ci verbatim, B={cb.N_BOOT}, "
                    f"seed={cb.BOOTSTRAP_SEED} (PCG64), percentile 95%"),
        "mc_seed_scheme": (f"default_rng({MC_SEED_BASE} + cell_index); "
                           "pilot-σ cells are new cells extending from "
                           f"index {NEW_CELL_BASE} in deterministic order"),
        "reps_per_cell": R_REPS,
        "sigma2_dist": (f"p_c ~ U[{P_C_MIDPOINT}−σ̂_D/2, "
                        f"{P_C_MIDPOINT}+σ̂_D/2], clipped to [0,1]; "
                        "D-E: min(1, p_c+Δ); no-saturation rows"),
        "inflation_1_3": ("NOT applied to MC cells (retired §4.2 formula "
                          "constant; MC grid is sole power authority per "
                          "D-V3-008) — bracketed against stored 'low' and "
                          "'mid' rows instead; FLAGGED for orchestrator"),
        "numpy_version": np.__version__,
    }
    print(f"pilot-side: n paired-contrast cases = {n_pairs}, σ̂_D = "
          f"{sigma2}", flush=True)
    print(json.dumps(summary, indent=1), flush=True)

    artifact: dict[str, Any] = {
        "meta": meta,
        "pilot_side": {
            "sigma_d_cases_paired": pairs["d"],
            "excluded_cases": pairs["excluded"],
            "sigma2_hat": sigma2,
            **summary,
            "no_effect_claim": report.get("no_effect_claim"),
        },
    }

    if sigma2 is None or n_pairs < MIN_VIABLE:
        artifact["cells"] = []
        artifact["insufficient_estimate"] = (
            f"n paired-contrast cases = {n_pairs} < minimum viable "
            f"{MIN_VIABLE} (spec §2 fallback); σ̂_D "
            f"{'undefined (n<2)' if sigma2 is None else 'underdetermined'} — "
            "no pilot-σ MC cells computed, none fabricated. Round report "
            "still records the pilot-side disclosure above.")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=1))
        print(f"INSUFFICIENT ESTIMATE (deterministic artifact): "
              f"{out_path}", flush=True)
        return 0

    run_reproduction_gate()

    stored = json.loads(STORED.read_text())
    stored_lookup: dict[tuple[int, int, float], dict[str, dict[str, Any]]] = {}
    for c in stored["cells"]:
        if c["sat"] != "none":
            continue
        stored_lookup.setdefault((int(c["N"]), int(c["k"]), float(c["delta"])), {})
        stored_lookup[(int(c["N"]), int(c["k"]), float(c["delta"]))][
            c["variance"]] = c
    bracket: dict[tuple[int, int, float], list[dict[str, Any]]] = {}
    for key, vars_ in stored_lookup.items():
        bracket.setdefault(key, []).extend(vars_.values())

    # Deterministic pilot-σ cell order: k-major, then Δ (0, MDEs), then
    # the 80%-power search Δs in order.
    order: list[tuple[int, Any]] = []
    for k in KS:
        order.append((k, 0.0))
        for mde in MDES:
            order.append((k, mde))
        for dlt in SEARCH_DELTAS:
            order.append((k, dlt))
    cells: list[dict[str, Any]] = [
        dict(N=N_HELDOUT, k=k, delta=d) for k, d in order]

    results: list[dict[str, Any]] = []
    for ci, cell in enumerate(cells):
        idx = NEW_CELL_BASE + ci
        print(f"cell {ci + 1}/{len(cells)}: N={cell['N']} k={cell['k']} "
              f"Δ={cell['delta']:.2f} idx={idx} …", flush=True)
        res = run_cell(cell, idx, sigma2)
        # stored-grid bracket at same (N, k, Δ), no-saturation rows
        br = bracket.get((cell["N"], cell["k"], cell["delta"]), [])
        res["stored_grid_bracket"] = [
            {"variance": b["variance"], "stored_index": b["index"],
             "power_lo_gt_0": b["power_lo_gt_0"]}
            for b in br if b["variance"] in ("low", "mid")]
        results.append(res)
        meta["results_written_so_far"] = ci + 1
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(
            {"meta": meta, "pilot_side": artifact["pilot_side"],
             "cells": results}, indent=1))

    # max Δ detectable at 80% power per k (nearest search Δ with power ≥ 0.80)
    max_d80 = {}
    for k in KS:
        best = None
        for res in results:
            if res["k"] != k or res["delta"] == 0.0:
                continue
            if res["power_lo_gt_0"] >= 0.80:
                if best is None or res["delta"] < best["delta"]:
                    best = res
        max_d80[str(k)] = (best["delta"] if best else
                           f"< {SEARCH_DELTAS[0]:.2f} (power < 0.80 on "
                           f"all searched Δ)")
    artifact["cells"] = results
    artifact["max_delta_detectable_at_80_power"] = max_d80
    out_path.write_text(json.dumps(artifact, indent=1))
    print(f"DONE: {len(results)} pilot-σ cells x {R_REPS} reps -> "
          f"{out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
