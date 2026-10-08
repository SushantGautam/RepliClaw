"""G3 pilot report writer (T0+4) — evidence-only, NO effect claim.

Reads a completed (or stopped) pilot round directory produced by
``scripts/pilot_run.py`` and writes a versioned pilot report
(``pilot_report_round{R}.json`` + ``.md``) with exactly what the frozen
spec §5/T0+4 requires:

* per-arm saturation ``s = k/10`` (saturated = arm succeeded on ALL seeds
  of a case) + the binomial trip probability at the observed s (S-W2-4:
  trip = s >= 3/10 = 0.25, n = 10, p = observed s);
* sigma_D: cases where exactly one arm saturated (dead-contrast
  disclosure: both arms saturating, recorded separately);
* feasibility: per-arm run-level success, crash count by status
  (``aborted_budget`` counted as crash per spec §5 rule 2), cumulative
  round tokens vs the 2,880,000 ceiling, wall time;
* ledger snapshot (every run row, verbatim);
* stop-rule outcomes (last case_check.json + STOP.json if present);
* the MODEL-SUBSTITUTION label; and an explicit "NO effect estimate /
  power claim / superiority statement is reported from this pilot"
  clause (spec §6 no-confirmatory-reuse).

Ground truth is NEVER read here: hits come from the scorer-side
``score.json`` files the driver already wrote (scorer isolation intact).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

ARMS = ("D-E-TELEM", "C-EQ-TELEM")
N_CASES_SEEDS = 2
SAT_THRESHOLD = 0.25
N_CASES = 10
ROUND_TOKEN_CEILING = 2_880_000
NO_EFFECT_CLAUSE = (
    "No effect estimate, power claim, or superiority statement is reported "
    "from this pilot (frozen spec §6 no-confirmatory-reuse clause). Pilot "
    "results cannot be reused as heldout evidence."
)
MODEL_LABEL = (
    "MODEL-SUBSTITUTION (SimulaChat default, Qwen3.8-27B) — NOT the official "
    "released baseline"
)


def _binom_cdf_ge(n: int, p: float, k: int) -> float:
    """P(Bin(n, p) >= k)."""
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    total = 0.0
    for i in range(k, n + 1):
        total += math.comb(n, i) * p ** i * (1 - p) ** (n - i)
    return min(1.0, total)


def load_runs(round_dir: Path) -> list[dict[str, Any]]:
    ledger_path = round_dir / "ledger.jsonl"
    if not ledger_path.is_file():
        return []
    runs = []
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                runs.append(json.loads(line))
    return runs


def _classify_cause(r: dict[str, Any], round_dir: Path) -> str:
    """Crash-cause attribution (Science Judge note, no causal claim):
    budget-exhaustion vs model protocol violation vs other-harness."""
    status = r.get("status", "")
    if status == "aborted_budget":
        return "budget_exhaustion"
    # run_path is relative to the run dir (parent of round dir): "round1/<case>/seed<s>/<arm>"
    p = round_dir.parent / r.get("run_path", "") / "status.json"
    if p.is_file():
        d = json.loads(p.read_text())
        err = str(d.get("crash_error") or d.get("error") or "")
        if "AgentProtocolError" in err or "malformed action" in err:
            return "protocol_violation"
        if "prompt-volume" in err:
            return "volume_canary_harness"
        if int(d.get("protocol_errors") or 0) > 0:
            return "protocol_violation"
    return "other_harness"


def per_arm_stats(runs: list[dict[str, Any]], round_dir: Path) -> dict[str, Any]:
    """Per-arm stats. Crash rate uses the FULL cohort denominator
    (TOTAL_CASES x N_CASES_SEEDS = 20), spec §5 rule 2 verbatim — the
    same denominator as the driver (code-judge observation on the
    earlier running-denominator version)."""
    out: dict[str, Any] = {}
    cohort = N_CASES * N_CASES_SEEDS
    for arm in ARMS:
        arm_runs = [r for r in runs if r.get("arm") == arm]
        by_case: dict[str, dict[str, Any]] = {}
        for r in arm_runs:
            by_case.setdefault(r["case"], {})[str(r["seed"])] = r
        sat_cases = []
        run_successes = 0
        crashes_by_status: dict[str, int] = {}
        crashes_by_cause: dict[str, int] = {}
        hits = 0
        scoreable = 0
        for case, seeds in sorted(by_case.items()):
            all_success = (
                len(seeds) == N_CASES_SEEDS
                and all(s.get("hit") is True for s in seeds.values())
            )
            if all_success:
                sat_cases.append(case)
            for s in seeds.values():
                status = s.get("status", "")
                if status == "completed":
                    run_successes += 1
                    if s.get("hit") is True:
                        hits += 1
                    if s.get("hit") is not None:
                        scoreable += 1
                else:
                    crashes_by_status[status] = crashes_by_status.get(status, 0) + 1
                    cause = _classify_cause(s, round_dir)
                    crashes_by_cause[cause] = crashes_by_cause.get(cause, 0) + 1
        s_val = len(sat_cases) / N_CASES
        crashes = len(arm_runs) - run_successes
        out[arm] = {
            "n_runs": len(arm_runs),
            "run_successes": run_successes,
            "saturation_cases": sat_cases,
            "s": s_val,
            "binom_trip_probability_at_observed_s": round(
                _binom_cdf_ge(N_CASES, s_val, 3), 6
            ),
            "crashes_by_status": crashes_by_status,
            "crashes_by_cause": crashes_by_cause,
            "crash_rate_full_cohort": crashes / cohort,
            "hits": hits,
            "scoreable_runs": scoreable,
            "cumulative_tokens": sum(int(r.get("tokens") or 0) for r in arm_runs),
            "cumulative_wall_s": round(
                sum(float(r.get("wall_s") or 0.0) for r in arm_runs), 1
            ),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--round-dir", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=None,
                    help="report path (default: <round-dir>/pilot_report_round{R}.json/.md)")
    args = ap.parse_args()

    round_dir: Path = args.round_dir
    m = round_dir.name
    r = int(m.replace("round", "")) if m.startswith("round") else 1
    runs = load_runs(round_dir)
    if not runs:
        print(f"no ledger found in {round_dir}", file=sys.stderr)
        return 1

    stats = per_arm_stats(runs, round_dir)
    sat = {a: set(stats[a]["saturation_cases"]) for a in ARMS}
    cases_seen = sorted({run["case"] for run in runs})
    sigma_d = sorted((sat[ARMS[0]] - sat[ARMS[1]]) | (sat[ARMS[1]] - sat[ARMS[0]]))
    dead_contrast = sorted(sat[ARMS[0]] & sat[ARMS[1]])
    neither = sorted(set(cases_seen) - (sat[ARMS[0]] | sat[ARMS[1]]))

    stop_outcomes: dict[str, Any] = {"tripped": False, "stop": None}
    stop_file = round_dir / "STOP.json"
    if stop_file.is_file():
        stop_outcomes["tripped"] = True
        stop_outcomes["stop"] = json.loads(stop_file.read_text())
    case_checks = sorted(round_dir.glob("*/case_check.json"))
    last_check = (
        json.loads(case_checks[-1].read_text()) if case_checks else None
    )
    if last_check is not None:
        stop_outcomes["last_case_check"] = {
            "case": case_checks[-1].parent.name,
            "checks": {
                k: {"tripped": v.get("tripped")}
                for k, v in last_check.items()
                if isinstance(v, dict) and "tripped" in v
            },
        }

    report = {
        "round": r,
        "model_label": MODEL_LABEL,
        "arms": list(ARMS),
        "n_cases": N_CASES,
        "seeds": sorted({str(run["seed"]) for run in runs}),
        "cases_seen": cases_seen,
        "no_effect_claim": NO_EFFECT_CLAUSE,
        "crash_cause_note": (
            "Crash causes are tabulated for disclosure; stop-2 is a "
            "feasibility instrument whose crash class is cause-agnostic "
            "by frozen spec (harness error, abort, or timeout). No causal "
            "'model capability' attribution is claimed here; a majority-"
            "protocol attribution would route to the frozen contingency "
            "(human decision on a stronger model), not to a capability "
            "verdict in this report."
        ),
        "sigma_d_cases": sigma_d,
        "dead_contrast_both_saturated": dead_contrast,
        "neither_saturated": neither,
        "per_arm": stats,
        "round_cumulative_tokens": sum(
            stats[a]["cumulative_tokens"] for a in ARMS
        ),
        "round_token_ceiling": ROUND_TOKEN_CEILING,
        "stop_outcomes": stop_outcomes,
        "ledger_snapshot": runs,
    }

    out_json = args.out or round_dir / f"pilot_report_round{r}.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md = out_json.with_suffix(".md")
    md.write_text(render_md(report), encoding="utf-8")
    print(f"pilot report: {out_json}")
    print(f"pilot report (md): {md}")
    return 0


def render_md(rep: dict[str, Any]) -> str:
    lines = [
        f"# G3 pilot report — round {rep['round']}",
        "",
        f"**Model:** {rep['model_label']}",
        "",
        f"> {rep['no_effect_claim']}",
        "",
        "## Per-arm saturation (S-W2-4 disclosure)",
        "",
        "| Arm | s | trip P | successes | crash rate (/20) | crashes (by cause) | tokens | wall (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for a in rep["arms"]:
        s = rep["per_arm"][a]
        causes = ", ".join(f"{k}={v}" for k, v in s["crashes_by_cause"].items()) or "0"
        lines.append(
            f"| {a} | {s['s']:.2f} | {s['binom_trip_probability_at_observed_s']} "
            f"| {s['run_successes']}/{s['n_runs']} | {s['crash_rate_full_cohort']:.2f} "
            f"| {causes} | {s['cumulative_tokens']:,} | {s['cumulative_wall_s']:,.1f} |"
        )
    lines += [
        "",
        f"> {rep['crash_cause_note']}",
    ]
    lines += [
        "",
        "## Contrast (disclosure, not a separate stop)",
        "",
        f"- σ̂_D (exactly one arm saturated): {len(rep['sigma_d_cases'])} — {rep['sigma_d_cases'] or '[]'}",
        f"- dead contrast (both saturated): {len(rep['dead_contrast_both_saturated'])} — "
        f"{rep['dead_contrast_both_saturated'] or '[]'}",
        f"- neither saturated: {len(rep['neither_saturated'])} — {rep['neither_saturated'] or '[]'}",
        "",
        "## Budget",
        "",
        f"- round cumulative tokens: {rep['round_cumulative_tokens']:,} / {rep['round_token_ceiling']:,} ceiling",
        "",
        "## Stop outcomes",
        "",
    ]
    so = rep["stop_outcomes"]
    if so["tripped"]:
        stop = so.get("stop") or {}
        tripped = stop.get("tripped")
        names = ", ".join(tripped) if isinstance(tripped, list) else str(tripped or "?")
        if "stop2_crash" in names:
            lines.append(f"- **TRIPPED**: {names} — FEASIBILITY-FAILED (cause-mixed; see cause table)")
        else:
            lines.append(f"- **TRIPPED**: {names}")
    else:
        lines.append("- no stop tripped")
    lc = so.get("last_case_check")
    if lc:
        checks = ", ".join(
            f"{k}={'TRIPPED' if v['tripped'] else 'ok'}"
            for k, v in lc["checks"].items()
        )
        lines.append(f"- last case check ({lc['case']}): {checks}")
    lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
