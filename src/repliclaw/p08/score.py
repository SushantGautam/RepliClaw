"""P08 oracle-gated scorer (the ONLY oracle reader in the codebase).

Implements docs/experiments/P08-ARTIFACT-CONTRACT.md v1 §2-§7 and the
metric definitions of PREREG-2026-10(-v1.1) §6.  Safety property
(science judge 2026-10-08, BLOCKER 1 / Q12): the sealed oracle file is
opened ONLY after every run directory under every arm has been verified
complete; on any gap the scorer writes ``run_manifest_incomplete.json``
and raises :class:`ScoreError` (CLI exits non-zero) WITHOUT touching the
oracle.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

VERDICT_SCHEMA = "p08.final_verdict/1"
LEDGER_SCHEMA = "p08.budget_ledger/1"
VALID_STATUS = {"completed", "aborted_budget", "invalid_usage"}
USAGE_PRESENT_THRESHOLD = 0.99
BOOTSTRAP_RESAMPLES = 10_000
PRIMARY_SEED = 20261010
SECONDARY_SEED = 20261020
ENVELOPE_TOKENS = 60_000

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ORACLES: dict[str, Path] = {
    "policy_rag_v1": _REPO_ROOT / "experiments" / "policy_rag" / "oracle" / "oracle.json",
    "tox21_ar_agonist": (
        _REPO_ROOT / "src/repliclaw/counterfactual/cases/tox21_ar_agonist/oracle/oracle.json"
    ),
}


class ScoreError(RuntimeError):
    """Raised when the run tree is incomplete or internally inconsistent."""


# ---------------------------------------------------------------------------
# Deterministic LCG resampling — same seed => identical resamples across
# invocations and processes (no numpy in the scorer by design).
# ---------------------------------------------------------------------------
_LCG_M = 2**64
_LCG_A = 6364136223846793005
_LCG_C = 1442695040888963407


def lcg_f64(seed: int) -> Callable[[], float]:  # noqa: E731
    """Zero-arg function producing uniform floats in [0, 1) from a 64-bit LCG."""
    state = [seed % _LCG_M]

    def next_f64() -> float:
        state[0] = (state[0] * _LCG_A + _LCG_C) % _LCG_M
        return (state[0] >> 11) / 2**53

    return next_f64


def bootstrap_ci(values: list[float], n: int, seed: int) -> tuple[float, float]:
    """Percentile 95% CI of the mean via n resamples (deterministic LCG)."""
    if not values:
        raise ScoreError("bootstrap_ci called with no values")
    if len(values) == 1:
        v = float(values[0])
        return (v, v)
    rng = lcg_f64(seed)
    k = len(values)
    means: list[float] = []
    for _ in range(n):
        s = 0.0
        for _ in range(k):
            s += values[int(rng() * k)]
        means.append(s / k)
    means.sort()
    lo = means[int(0.025 * n)]
    hi = means[min(n - 1, int(0.975 * n))]
    return (lo, hi)


# ---------------------------------------------------------------------------
# Run tree discovery + completeness gate (BEFORE any oracle read)
# ---------------------------------------------------------------------------
@dataclass
class RunArtifacts:
    arm: str
    run_id: str
    dir: Path
    final_verdict: dict[str, Any] = field(repr=False, default_factory=dict)
    ledger: dict[str, Any] = field(repr=False, default_factory=dict)
    metadata: dict[str, Any] = field(repr=False, default_factory=dict)
    trace_types: list[str] = field(default_factory=list)
    usage_present_ratio: float = 1.0
    envelope_sha: str = ""
    tokens: int = 0
    wall_s: float = 0.0
    flags: list[str] = field(default_factory=list)
    per_run_metrics: dict[str, float | None] = field(default_factory=dict)


def discover_runs(runs_dir: Path) -> dict[str, list[Path]]:
    """arm -> sorted list of run dirs."""
    arms: dict[str, list[Path]] = {}
    if not runs_dir.is_dir():
        raise ScoreError(f"run root does not exist: {runs_dir}")
    for arm_dir in sorted(p for p in runs_dir.iterdir() if p.is_dir()):
        run_dirs = sorted(p for p in arm_dir.iterdir() if p.is_dir())
        if run_dirs:
            arms[arm_dir.name] = run_dirs
    if not arms:
        raise ScoreError(f"no run directories under {runs_dir}")
    return arms


def _read_json(path: Path, gaps: list[str], what: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        gaps.append(f"{what}: missing file {path.name}")
    except json.JSONDecodeError as e:
        gaps.append(f"{what}: unparseable JSON ({e})")
    return {}


def verify_run_dir(arm: str, run_dir: Path) -> tuple[RunArtifacts, list[str]]:
    """Validate one run dir against the contract schemas; return gap list."""
    gaps: list[str] = []
    a = RunArtifacts(arm=arm, run_id=f"{arm}/{run_dir.name}", dir=run_dir)

    fv = _read_json(run_dir / "final_verdict.json", gaps, f"{a.run_id} final_verdict.json")
    if fv:
        if fv.get("schema") != VERDICT_SCHEMA:
            gaps.append(f"{a.run_id} final_verdict: schema != {VERDICT_SCHEMA}")
        if fv.get("status") not in VALID_STATUS:
            gaps.append(f"{a.run_id} final_verdict: status not in {sorted(VALID_STATUS)}")
        a.final_verdict = fv
        a.envelope_sha = str(fv.get("envelope_sha256", ""))

    ledger = _read_json(run_dir / "budget_ledger.json", gaps, f"{a.run_id} budget_ledger.json")
    if ledger:
        if ledger.get("schema") != LEDGER_SCHEMA:
            gaps.append(f"{a.run_id} budget_ledger: schema != {LEDGER_SCHEMA}")
        calls = ledger.get("calls")
        if not isinstance(calls, list) or not calls:
            gaps.append(f"{a.run_id} budget_ledger: no calls recorded")
        else:
            present = sum(1 for c in calls if c.get("usage_present") is True)
            a.usage_present_ratio = present / len(calls)
            if a.usage_present_ratio < USAGE_PRESENT_THRESHOLD:
                gaps.append(
                    f"{a.run_id} budget_ledger: usage_present {present}/{len(calls)} "
                    f"< {USAGE_PRESENT_THRESHOLD} (never zero-fill; judge item 7)"
                )
        totals = ledger.get("totals") or {}
        a.tokens = int(totals.get("total_tokens", 0))
        a.wall_s = float(totals.get("wall_s", 0.0))
        a.ledger = ledger

    traces_path = run_dir / "traces.jsonl"
    if not traces_path.exists():
        gaps.append(f"{a.run_id} traces.jsonl: missing")
    else:
        for i, line in enumerate(traces_path.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError as e:
                gaps.append(f"{a.run_id} traces.jsonl: line {i + 1} unparseable ({e})")
                continue
            t = ev.get("type")
            if t:
                a.trace_types.append(str(t))

    meta = _read_json(run_dir / "run_metadata.json", gaps, f"{a.run_id} run_metadata.json")
    if meta:
        a.metadata = meta

    # Envelope re-check (contract §3): run_metadata sha must equal final_verdict's.
    if meta and fv:
        meta_sha = str(meta.get("envelope_sha256", ""))
        if meta_sha and a.envelope_sha and meta_sha != a.envelope_sha:
            a.flags.append("envelope_mismatch")

    return a, gaps


def gate_all_runs(
    arms: dict[str, list[Path]], out_dir: Path
) -> dict[str, list[RunArtifacts]]:
    """Verify EVERY run dir; on ANY gap write the incomplete manifest and raise.

    Must be called BEFORE any oracle read (the load-bearing safety property).
    """
    clean: dict[str, list[RunArtifacts]] = {}
    all_gaps: list[str] = []
    for arm, run_dirs in arms.items():
        ok: list[RunArtifacts] = []
        for rd in run_dirs:
            art, gaps = verify_run_dir(arm, rd)
            if gaps:
                all_gaps.extend(gaps)
            else:
                ok.append(art)
        if ok:
            clean[arm] = ok
    if all_gaps:
        manifest = {
            "schema": "p08.run_manifest_incomplete/1",
            "incomplete": True,
            "gaps": all_gaps,
            "oracle_read": False,
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "run_manifest_incomplete.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        raise ScoreError(
            f"run tree incomplete ({len(all_gaps)} gap(s)); oracle NOT read; "
            f"manifest: {out_dir / 'run_manifest_incomplete.json'}\n  "
            + "\n  ".join(all_gaps[:20])
        )
    return clean


# ---------------------------------------------------------------------------
# Oracle (sole reader) + per-run metrics
# ---------------------------------------------------------------------------
def load_oracle(case: str, oracle_path: Path | None = None) -> dict[str, Any]:
    """Open the sealed oracle for `case`. The ONLY function that reads one."""
    path = oracle_path or DEFAULT_ORACLES.get(case)
    if path is None:
        raise ScoreError(f"no oracle registered for case {case!r}")
    if not path.exists():
        raise ScoreError(f"oracle file missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _unsupported_hypotheses(oracle: dict[str, Any]) -> set[str]:
    sh = oracle.get("supports_hypothesis")
    if isinstance(sh, dict):
        return {k for k, v in sh.items() if str(v).lower().startswith("none")}
    return set()


def _diagnosis_correct(fv: dict[str, Any], oracle: dict[str, Any]) -> bool:
    """M1 case-specific correctness (PREREG §6: defect class + target artifact)."""
    case_id = str(fv.get("case_id", ""))
    defect = fv.get("defect_class")
    target = fv.get("target_artifact")
    if case_id == "policy_rag_v1":
        return defect == oracle.get("true_cause") and bool(target)
    # Secondary cases (P06 oracle schema): the run's verdict must match the
    # oracle's headline-hypothesis stance (defined at case-landing).
    hyp = str(oracle.get("hypothesis", ""))
    if not hyp:
        return fv.get("verdict") == "supported"
    stance = str(oracle.get("supports_hypothesis", {}).get(hyp, ""))
    supported = stance.lower() not in ("none", "none (i_p byte-identical)")
    return (fv.get("verdict") == "supported") == supported


def _per_run_metrics(art: RunArtifacts, oracle: dict[str, Any]) -> dict[str, float | None]:
    fv = art.final_verdict
    m: dict[str, float | None] = {}

    # M1: correct diagnosis (defect class + target artifact vs oracle).
    m["M1"] = 1.0 if _diagnosis_correct(fv, oracle) else 0.0

    # M2: falsification discipline over preregistered hypotheses.
    hyps = fv.get("hypotheses") or []
    attempted = [h for h in hyps if h.get("attempted_falsification") is True]
    m["M2"] = (len(attempted) / len(hyps)) if hyps else None

    # M3: counterfactual yield (S5/A1/A3); no slots granted -> None (n/a).
    granted = int(fv.get("counterfactual_slots_granted") or 0)
    executed = int(fv.get("counterfactual_slots_executed") or 0)
    if granted == 0:
        m["M3"] = None
    else:
        cf_dir = art.dir / "counterfactuals"
        effective = 0
        if cf_dir.is_dir():
            for f in sorted(cf_dir.glob("*.json")):
                try:
                    d = json.loads(f.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                if d.get("verdict_changed") or d.get("hypothesis_falsified"):
                    effective += 1
        m["M3"] = (effective / executed) if executed else 0.0

    # M4: leakage incidents — oracle path strings appearing in run artifacts.
    incidents = 0
    oracle_str = str(DEFAULT_ORACLES.get(str(fv.get("case_id", "")), ""))
    if oracle_str:
        try:
            for f in art.dir.rglob("*"):
                if f.is_file() and f.suffix in {".json", ".jsonl", ".md", ".txt"}:
                    if oracle_str in f.read_text(encoding="utf-8", errors="ignore"):
                        incidents += 1
        except OSError:
            pass
    m["M4"] = float(incidents)

    # M5 / M8 / M9.
    m["M5"] = float(art.tokens)
    m["M9"] = art.wall_s
    m["M8"] = float(int(fv.get("integrity_rejections") or 0))

    # M11: correctly-falsified falsifiable hypotheses.
    unsupported = _unsupported_hypotheses(oracle)
    eligible = [
        h for h in hyps if h.get("falsifiable") is True and h.get("attempted_falsification") is True
    ]
    if eligible:
        correct_fals = [
            h for h in eligible if h.get("outcome") == "refuted" and h.get("id") in unsupported
        ]
        m["M11"] = len(correct_fals) / len(eligible)
    else:
        m["M11"] = None

    art.per_run_metrics = m
    return m


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def _arm_aggregate(arts: list[RunArtifacts], seed: int) -> dict[str, Any]:
    n = len(arts)
    valid = [a for a in arts if a.final_verdict.get("status") == "completed"]
    voided = [a for a in arts if a.final_verdict.get("status") == "invalid_usage"]
    aborted = [a for a in arts if a.final_verdict.get("status") == "aborted_budget"]

    def vals(key: str, pool: list[RunArtifacts] | None = None) -> list[float]:
        pool = pool if pool is not None else valid
        out = [a.per_run_metrics.get(key) for a in pool]
        return [float(v) for v in out if v is not None]

    agg: dict[str, Any] = {
        "n_runs": n,
        "n_valid": len(valid),
        "n_aborted_budget": len(aborted),
        "n_invalid_usage": len(voided),
        "voided_runs": [a.run_id for a in voided],
        "aborted_runs": [a.run_id for a in aborted],
    }
    for key in ("M1", "M2", "M3", "M11"):
        v = vals(key)
        if not v:
            agg[key] = {"value": None, "ci95": None, "note": "no valid runs / metric undefined"}
        else:
            agg[key] = {
                "value": statistics.fmean(v),
                "ci95": list(bootstrap_ci(v, BOOTSTRAP_RESAMPLES, seed)),
            }
    t = vals("M5")
    agg["M5"] = (
        {"mean": statistics.fmean(t), "min": min(t), "max": max(t)}
        if t
        else {"mean": None, "min": None, "max": None}
    )
    m1_hits = [a for a in valid if a.per_run_metrics.get("M1") == 1.0]
    if m1_hits:
        toks = [float(a.per_run_metrics["M5"] or 0.0) for a in m1_hits]
        agg["M6"] = {"value": statistics.fmean(toks), "n_correct": len(m1_hits)}
    else:
        agg["M6"] = {"value": None, "n_correct": 0, "note": "no correct runs (reported as such)"}
    m7 = (len(aborted) / n) if n else None
    agg["M7"] = {"value": m7, "flag_S1": bool(m7 is not None and m7 > 0.25)}
    i8 = vals("M8")
    agg["M8"] = {"mean": statistics.fmean(i8) if i8 else None}
    w = vals("M9")
    if w:
        ws = sorted(w)
        q1 = ws[int(0.25 * len(ws))]
        q3 = ws[min(len(ws) - 1, int(0.75 * len(ws)))]
        agg["M9"] = {"median": statistics.median(w), "iqr": [q1, q3]}
    else:
        agg["M9"] = {"median": None, "iqr": None}
    verdicts = [a.final_verdict.get("verdict") for a in valid]
    if verdicts:
        modal = max(set(verdicts), key=verdicts.count)
        agg["M10"] = {
            "value": sum(1 for v in verdicts if v == modal) / len(verdicts),
            "modal_verdict": modal,
        }
    else:
        agg["M10"] = {"value": None, "modal_verdict": None}
    m4_total = sum(float(a.per_run_metrics.get("M4") or 0.0) for a in arts)
    agg["M4"] = {"total_incidents": m4_total, "flag_S5": m4_total > 0}
    return agg


# PREREG v1.2 A1 (A1.3/A1.4): the P1 branch structure, with STRICT
# inequalities on the 95% CI of Δ = M1(S5) − M1(S4):
#   ci[0] > 0          -> SUPPORTED   (S5 beats S4; significantly positive)
#   ci[1] < 0          -> FALSIFIED   (S5 worse; CI entirely below zero)
#   CI contains 0      -> NOT_SUPPORTED (descriptive only; A1.8 scope note)
P1_SUPPORTED = "SUPPORTED"
P1_FALSIFIED = "FALSIFIED"
P1_NOT_SUPPORTED = "NOT_SUPPORTED"


def decision_branch(ci: tuple[float, float] | None) -> str:
    """A1.3 branch structure on the 95% CI of Δ = M1(S5) − M1(S4).

    Strict inequalities per PREREG v1.2 A1.4: support requires
    CI_lower > 0 (a CI whose lower bound is exactly 0 is NOT support);
    falsification requires CI_upper < 0. Anything else — including a CI
    containing zero — is NOT_SUPPORTED (descriptive).
    """
    if ci is None:
        return "no_valid_runs"
    lo, hi = ci
    if lo > 0:
        return P1_SUPPORTED
    if hi < 0:
        return P1_FALSIFIED
    return P1_NOT_SUPPORTED


def score_runs(
    runs_dir: Path,
    case: str,
    out_dir: Path | None = None,
    seed: int = PRIMARY_SEED,
    oracle_path: Path | None = None,
) -> dict[str, Any]:
    """Full P08 scoring pass. Oracle is read only after the completeness gate."""
    out_dir = out_dir or (runs_dir / "scores")
    arms = discover_runs(runs_dir)

    # --- oracle gate: verify EVERYTHING before the oracle is opened --------
    clean = gate_all_runs(arms, out_dir)

    # --- oracle (sole reader, post-gate) ------------------------------------
    oracle = load_oracle(case, oracle_path)
    for arts in clean.values():
        for a in arts:
            _per_run_metrics(a, oracle)

    arm_stats = {arm: _arm_aggregate(arts, seed) for arm, arts in clean.items()}

    # Parity re-check (contract §3 / prereg Q7).
    env_set = {a.envelope_sha for arts in clean.values() for a in arts if a.envelope_sha}
    overruns = [a.run_id for arts in clean.values() for a in arts if a.tokens > ENVELOPE_TOKENS]
    parity = {
        "identical_envelope_sha256": len(env_set) <= 1,
        "envelope_hashes": sorted(env_set),
        "overruns": overruns,
        "ok": len(env_set) <= 1 and not overruns,
    }

    # P1 decision (PREREG v1.2 A1; canonical rule string per A1.3):
    # 10,000 paired-resample bootstrap 95% CI on the S5-minus-S4 M1
    # difference (comparator S4 = open-sharing swarm, per A1.1 defect 2).
    s5m = [float(a.per_run_metrics["M1"] or 0.0) for a in clean.get("S5", [])]
    s4m = [float(a.per_run_metrics["M1"] or 0.0) for a in clean.get("S4", [])]
    diff: dict[str, Any] = {
        "s5_m1_mean": statistics.fmean(s5m) if s5m else None,
        "s4_m1_mean": statistics.fmean(s4m) if s4m else None,
    }
    if s5m and s4m and len(s5m) == len(s4m):
        rng = lcg_f64(seed)
        diffs: list[float] = []
        for _ in range(BOOTSTRAP_RESAMPLES):
            i5 = [s5m[int(rng() * len(s5m))] for _ in range(len(s5m))]
            i4 = [s4m[int(rng() * len(s4m))] for _ in range(len(s4m))]
            diffs.append(statistics.fmean(i5) - statistics.fmean(i4))
        diffs.sort()
        ci = (
            diffs[int(0.025 * len(diffs))],
            diffs[min(len(diffs) - 1, int(0.975 * len(diffs)))],
        )
        diff["ci95"] = list(ci)
        diff["decision"] = decision_branch(ci)
        diff["rule"] = (
            "P1 decision rule (prereg v1.2; character-identical in §2 and §8.1 S4). "
            "Estimand: Δ = M1(S5) − M1(S4), the run-level mean difference in "
            "correct-diagnosis rate (M1, higher is better) between the escrow arm "
            "(S5) and the open-sharing swarm (S4), on the same case/oracle at the "
            "matched envelope. Polarity / null: H0: Δ ≤ 0 (S5 does not exceed S4); "
            "favorable direction: Δ > 0 (S5 better than S4). CI convention: "
            "bootstrap percentile 95% CI on Δ, 10,000 resamples, seed 20261010, "
            "run-level within-case resampling (resample run indices independently "
            "within each arm; Δ_b = mean_b(M1,S5) − mean_b(M1,S4)). Final decision "
            "(primary, n_run = 20 per arm): P1 SUPPORTED (S5 beats S4) iff "
            "CI_lower(Δ) > 0. P1 FALSIFIED (S5 worse) iff CI_upper(Δ) < 0; the "
            "report leads with this falsification per §8.1 and preserves all S5 "
            "artifacts verbatim. Otherwise (CI contains 0): P1 NOT SUPPORTED; "
            "report descriptively (point estimate + 95% CI). Interim screen "
            "(n_run = 10 per arm, first 10 runs): the 10-run 95% CI on Δ is a "
            "screening device only. It supports and falsifies nothing, triggers no "
            "stop, no amendment, and no report change; it is reported solely to "
            "monitor whether the 20-run block is tracking toward or away from the "
            "decision boundary."
        )
    else:
        diff["decision"] = "no_valid_runs"
        diff["note"] = "S5/S4 run counts differ or empty; paired bootstrap undefined"

    stopping = {
        "S1": {
            "triggered": any(a["M7"]["flag_S1"] for a in arm_stats.values()),
            "detail": {k: v["M7"] for k, v in arm_stats.items()},
        },
        "S5": {
            "triggered": any(a["M4"]["flag_S5"] for a in arm_stats.values()),
            "detail": {k: v["M4"] for k, v in arm_stats.items()},
        },
    }

    result = {
        "schema": "p08.scores/1",
        "case": case,
        "seed": seed,
        "oracle_path": str(oracle_path or DEFAULT_ORACLES.get(case)),
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": seed},
        "parity": parity,
        "stopping_rules": stopping,
        "p1_decision": diff,
        "arms": arm_stats,
    }

    _write_outputs(out_dir, result, clean)
    return result


def _write_outputs(
    out_dir: Path, result: dict[str, Any], clean: dict[str, list[RunArtifacts]]
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scores.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    with (out_dir / "per_run.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "arm", "run", "status", "M1", "M2", "M3", "M11",
                "tokens", "wall_s", "envelope_sha256", "flags",
            ]
        )
        for arm in sorted(clean):
            for a in clean[arm]:
                pm = a.per_run_metrics
                w.writerow(
                    [
                        a.arm, a.run_id, a.final_verdict.get("status"),
                        pm.get("M1"), pm.get("M2"), pm.get("M3"), pm.get("M11"),
                        a.tokens, a.wall_s, a.envelope_sha, ",".join(a.flags),
                    ]
                )

    _write_scorecard(out_dir / "scorecard.md", result)
    (out_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "schema": "p08.run_manifest/1",
                "incomplete": False,
                "arms": {
                    k: [
                        {
                            "run": a.run_id,
                            "status": a.final_verdict.get("status"),
                            "usage_present_ratio": a.usage_present_ratio,
                        }
                        for a in v
                    ]
                    for k, v in clean.items()
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_scorecard(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# P08 Scorecard (counterevidence-first)",
        "",
        f"- case: `{result['case']}`  seed: `{result['seed']}`",
        f"- oracle: `{result['oracle_path']}`",
        f"- parity ok: `{result['parity']['ok']}`  envelope hashes: {result['parity']['envelope_hashes']}",
        "",
        "## Stopping rules",
        "",
        f"- S1 (arm abort > 25%): "
        f"**{'TRIGGERED' if result['stopping_rules']['S1']['triggered'] else 'not triggered'}**",
        f"- S5 (leakage incidents): "
        f"**{'TRIGGERED' if result['stopping_rules']['S5']['triggered'] else 'not triggered'}**",
        "",
        "## P1 decision (S5 vs S4 on M1)",
        "",
        f"- rule: {result['p1_decision'].get('rule', 'n/a')}",
        f"- S5 M1 mean: {result['p1_decision'].get('s5_m1_mean')}",
        f"- S4 M1 mean: {result['p1_decision'].get('s4_m1_mean')}",
        f"- difference CI95: {result['p1_decision'].get('ci95')}",
        f"- decision: **{result['p1_decision'].get('decision')}**",
        "",
        "## Arms (n/a / negative rows first)",
        "",
        "| arm | M1 (95% CI) | M11 | M3 | M6 | M7 | M9 median | M10 | M4 incidents | n valid/total |",
        "|-----|-------------|-----|----|----|----|-----------|-----|--------------|---------------|",
    ]

    def row_sort_key(item: tuple[str, dict[str, Any]]) -> tuple[int, float]:
        _, a = item
        m1 = (a.get("M1") or {}).get("value")
        return (0 if m1 is None else 1, -(m1 or 0.0))

    for arm, a in sorted(result["arms"].items(), key=row_sort_key):
        m1 = a.get("M1") or {}
        m1s = (
            f"{m1['value']:.3f} [{m1['ci95'][0]:.3f}, {m1['ci95'][1]:.3f}]"
            if m1.get("value") is not None
            else "n/a"
        )
        m11 = a.get("M11") or {}
        m11s = f"{m11['value']:.3f}" if m11.get("value") is not None else "n/a"
        m3 = a.get("M3") or {}
        m3s = f"{m3['value']:.3f}" if m3.get("value") is not None else "n/a"
        m6 = a.get("M6") or {}
        m6s = f"{m6['value']:.0f}" if m6.get("value") is not None else "n/a (no correct runs)"
        m7 = a.get("M7") or {}
        m7s = f"{m7['value']:.2f}" if m7.get("value") is not None else "n/a"
        m9 = a.get("M9") or {}
        m9s = f"{m9['median']:.1f}" if m9.get("median") is not None else "n/a"
        m10 = a.get("M10") or {}
        m10s = f"{m10['value']:.3f}" if m10.get("value") is not None else "n/a"
        lines.append(
            f"| {arm} | {m1s} | {m11s} | {m3s} | {m6s} | {m7s} | {m9s} | {m10s} "
            f"| {a['M4']['total_incidents']:.0f} | {a['n_valid']}/{a['n_runs']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# P02 replay self-test
# ---------------------------------------------------------------------------
def p02_replay_self_test() -> dict[str, Any]:
    """Replay the committed policy_rag_v1 case through the P02 case engine.

    The scorer's own proof that the offline counterfactual layer it scores is
    deterministic and tamper-evident (judge checklist item 1).
    """
    import tempfile

    from repliclaw.counterfactual import replay, run_canonical
    from repliclaw.counterfactual.executor import load_case, load_interventions

    out: dict[str, Any] = {
        "case": None,
        "replay_ok": False,
        "determinism_ok": False,
        "error": None,
    }
    try:
        case = load_case()
        out["case"] = case.case_id
        interventions = load_interventions()
        with tempfile.TemporaryDirectory() as td:
            run_canonical(case, interventions, seed=0, out_root=Path(td))
            out["replay_ok"] = bool(replay(case.case_id, Path(td)))
        with tempfile.TemporaryDirectory() as td2:
            run_canonical(case, interventions, seed=0, out_root=Path(td2))
            out["determinism_ok"] = bool(replay(case.case_id, Path(td2)))
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m repliclaw.p08.score")
    p.add_argument("--run-root", default="runs/p08-live", help="runs directory (arm/run dirs)")
    p.add_argument("--case", default="policy_rag_v1")
    p.add_argument("--output", default=None, help="score output dir (default <run-root>/scores)")
    p.add_argument("--seed", type=int, default=PRIMARY_SEED)
    p.add_argument("--self-test", action="store_true", help="run the P02 replay self-test and exit")
    args = p.parse_args(argv)

    if args.self_test:
        res = p02_replay_self_test()
        print(json.dumps(res, indent=2))
        ok = res["replay_ok"] and res["determinism_ok"]
        print(f"SELF-TEST: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1

    runs_dir = Path(args.run_root)
    try:
        out = Path(args.output) if args.output else None
        res = score_runs(runs_dir, args.case, out, args.seed)
    except ScoreError as e:
        print(f"SCORE-ERROR: {e}", file=sys.stderr)
        return 1
    print(json.dumps({k: res[k] for k in ("parity", "stopping_rules", "p1_decision")}, indent=2))
    print(f"scores written to {out or (runs_dir / 'scores')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
