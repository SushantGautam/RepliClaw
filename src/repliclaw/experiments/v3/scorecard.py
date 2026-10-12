"""Comparative arm-vs-arm scorecard (V3 fast-finish sprint).

Consumes per-run artifacts already produced by the existing harnesses and
computes a concise per-arm metric table:

* ``observational`` runs        — telemetry pilot layout (``status.json``
  from ``scripts/pilot_run.py`` / ``telemetry_arms.py``: service-level
  accuracy@5, NO executable interventions).
* ``executable_counterfactual`` — P08/C-EQ layout (``final_verdict.json``
  from ``ceq.py``: real intervention executor, verified counterfactuals).
* ``run.json``                  — tolerant generic fallback for future
  compound-causal runs.

Ground truth for the identification metrics comes from a scorer-side truth
file (``--truth``: ``{"<case_id>": ["cause", ...]}``) or, for telemetry runs,
the run's own ``score.json`` (``true_service``). Runs without resolvable GT
are scored ``null`` for identification but are NEVER dropped from the
failure/cost tables.

HARD RULE: the two evidence classes carry different claim strengths
(observational access-matched diagnosis vs executed counterfactuals). The
scorecard therefore aggregates ONLY within a class and REFUSES to emit a
merged cross-class row (:class:`ScorecardRefusalError`).

No LLM calls, no network, no oracle reads beyond the caller-supplied
scorer-side inputs.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA = "repliclaw.scorecard/1"

CLASS_OBS = "observational"
CLASS_EXEC = "executable_counterfactual"
CLASSES = (CLASS_OBS, CLASS_EXEC)

COMPLETED = "completed"


class ScorecardRefusalError(RuntimeError):
    """Raised when the caller tries to merge the two evidence classes."""


def _refuse_merge(a: str, b: str) -> ScorecardRefusalError:
    return ScorecardRefusalError(
        f"refusing to merge evidence classes {a!r} and {b!r}: observational "
        "(access-matched diagnosis) and executable-counterfactual runs are "
        "different claim strengths; the scorecard aggregates within a class only"
    )


# ---------------------------------------------------------------------------
# one normalized run
# ---------------------------------------------------------------------------


@dataclass
class RunRecord:
    run_path: str
    arm: str
    case_id: str
    seed: int | None
    evidence_class: str
    status: str
    abort_reason: str | None = None
    submitted_ranking: list[str] | None = None
    claimed_cause: str | None = None          # top-1 (or target_artifact)
    tokens: int | None = None
    llm_calls: int | None = None
    tool_calls: int | None = None
    wall_s: float | None = None
    protocol_violations: int = 0
    escrowed: bool | None = None              # a commitment was escrowed
    agent_top1s: list[str] = field(default_factory=list)  # per-agent top-1s
    agent_verdicts: list[str] = field(default_factory=list)
    interventions: dict[str, Any] | None = None  # executable runs only
    gt_set: frozenset[str] | None = None
    truth_source: str | None = None          # "truth_file" | "score.json" | None

    # -- derived identification metrics -------------------------------------
    @property
    def completed(self) -> bool:
        return self.status == COMPLETED

    @property
    def claimed_set(self) -> set[str]:
        if self.submitted_ranking:
            return set(self.submitted_ranking)
        if self.claimed_cause:
            return {self.claimed_cause}
        return set()

    @property
    def top1_hit(self) -> bool | None:
        if self.gt_set is None or not self.completed or not self.claimed_cause:
            return None
        return self.claimed_cause in self.gt_set

    @property
    def exact_set_match(self) -> bool | None:
        if self.gt_set is None or not self.completed or not self.claimed_set:
            return None
        return self.claimed_set == set(self.gt_set)

    @property
    def jaccard(self) -> float | None:
        if self.gt_set is None or not self.completed or not self.claimed_set:
            return None
        union = self.claimed_set | set(self.gt_set)
        if not union:
            return 0.0
        return len(self.claimed_set & set(self.gt_set)) / len(union)

    @property
    def correct(self) -> bool | None:
        """A completed run is 'correct' when its top-1 identifies a true cause."""
        return self.top1_hit

    @property
    def budget_exhausted(self) -> bool:
        return self.status in ("aborted_budget", "refused_ceiling") or (
            bool(self.abort_reason) and "budget" in self.abort_reason.lower()
        )


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _attach_truth(rec: RunRecord, truth: dict[str, list[str]] | None) -> None:
    if truth is not None and rec.case_id in truth:
        rec.gt_set = frozenset(truth[rec.case_id])
        rec.truth_source = "truth_file"
        return
    rec.gt_set = None


# ---------------------------------------------------------------------------
# parsers, one per artifact layout + generic fallback
# ---------------------------------------------------------------------------


def parse_run_dir(path: Path, truth: dict[str, list[str]] | None = None) -> RunRecord | None:
    """Classify + parse one run dir. Returns None when the dir holds no
    recognized artifact (not a run dir)."""
    path = Path(path)
    fv = _read_json(path / "final_verdict.json")
    if fv is not None and fv.get("schema", "").startswith("p08.final_verdict"):
        return _parse_executable(path, fv, truth)
    st = _read_json(path / "status.json")
    if st is not None and ("submitted_ranking" in st or "arm" in st):
        return _parse_telemetry(path, st, truth)
    gj = _read_json(path / "run.json")
    if gj is not None and "arm" in gj and "case_id" in gj:
        return _parse_generic(path, gj, truth)
    return None


def _parse_telemetry(path: Path, st: dict[str, Any],
                     truth: dict[str, list[str]] | None) -> RunRecord:
    rec = RunRecord(
        run_path=str(path),
        arm=str(st.get("arm", "unknown")),
        case_id=str(st.get("case_id", "unknown")),
        seed=st.get("seed"),
        evidence_class=CLASS_OBS,
        status=str(st.get("status", "unknown")),
        abort_reason=st.get("crash_error") if st.get("status") != COMPLETED else None,
        submitted_ranking=list(st["submitted_ranking"]) if st.get("submitted_ranking") else None,
        tokens=st.get("tokens"),
        llm_calls=st.get("llm_calls"),
        tool_calls=st.get("tool_calls"),
        wall_s=st.get("wall_s"),
        protocol_violations=int(st.get("protocol_errors", 0) or 0),
    )
    if rec.submitted_ranking:
        rec.claimed_cause = rec.submitted_ranking[0]
    # escrow ledger: {arm, opaque_case_id, entries:[{agent_id, phase, ranking,...}]}
    escrow_path = st.get("escrow_ledger_path")
    if escrow_path:
        p = Path(escrow_path)
        if not p.is_absolute():
            p = path / p
        ledger = _read_json(p)
        if ledger and ledger.get("entries"):
            latest: dict[str, str] = {}
            for e in ledger["entries"]:
                ranking = e.get("ranking") or []
                if ranking:
                    latest[e.get("agent_id", "?")] = ranking[0]
            rec.agent_top1s = sorted(latest.values())
            rec.escrowed = True
        else:
            rec.escrowed = False
    elif rec.completed:
        rec.escrowed = False
    # GT: truth file first, then the scorer-side score.json
    if truth is not None and rec.case_id in truth:
        _attach_truth(rec, truth)
    else:
        score = _read_json(path / "score.json")
        if score and score.get("true_service"):
            rec.gt_set = frozenset({score["true_service"]})
            rec.truth_source = "score.json"
    return rec


def _parse_executable(path: Path, fv: dict[str, Any],
                      truth: dict[str, list[str]] | None) -> RunRecord:
    rec = RunRecord(
        run_path=str(path),
        arm=str(fv.get("arm", "unknown")),
        case_id=str(fv.get("case_id", "unknown")),
        seed=None,
        evidence_class=CLASS_EXEC,
        status=str(fv.get("status", "unknown")),
        tokens=fv.get("total_tokens"),
        wall_s=fv.get("wall_s"),
        claimed_cause=fv.get("target_artifact") if fv.get("status") == COMPLETED else None,
        protocol_violations=int(fv.get("integrity_rejections", 0) or 0),
    )
    # llm call count: prefer budget ledger, else trace count
    bl = _read_json(path / "budget_ledger.json")
    if bl:
        totals = bl.get("totals") or {}
        rec.llm_calls = totals.get("llm_calls")
    if rec.llm_calls is None and (path / "traces.jsonl").is_file():
        with (path / "traces.jsonl").open(encoding="utf-8") as f:
            rec.llm_calls = sum(
                1 for line in f
                if line.strip() and json.loads(line).get("type") in
                ("llm_call", "consultation", "decision")
            )
    # abort reason from traces (budget_abort / usage_invalid)
    if rec.status != COMPLETED and (path / "traces.jsonl").is_file():
        with (path / "traces.jsonl").open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                ev = json.loads(line)
                if ev.get("type") in ("budget_abort", "usage_invalid"):
                    rec.abort_reason = str(ev.get("payload", {}).get("message", ev["type"]))
                    break
    # per-agent verdicts (conclusions) — consensus input
    for a in fv.get("agent_verdicts") or []:
        rec.agent_verdicts.append(str(a.get("verdict", "")))
    # executed counterfactual slots: one counterfactuals/<arm>.json each
    cf_dir = path / "counterfactuals"
    claimed = int(fv.get("counterfactual_slots_granted", 0) or 0)
    executed = 0
    verified = 0
    flipped = 0
    if cf_dir.is_dir():
        for p in sorted(cf_dir.glob("*.json")):
            doc = _read_json(p)
            if doc is None:
                continue
            executed += 1
            if doc.get("verified"):
                verified += 1
            if doc.get("hypothesis_outcome") == "supported":
                flipped += 1
    rec.interventions = {
        "claimed": claimed,
        "executed": executed,
        "verified": verified,
        "verified_fraction": (verified / executed) if executed else None,
        "flipped": flipped,
        "flipped_fraction": (flipped / executed) if executed else None,
    }
    _attach_truth(rec, truth)
    return rec


def _parse_generic(path: Path, gj: dict[str, Any],
                   truth: dict[str, list[str]] | None) -> RunRecord:
    """Tolerant schema for future compound-causal runs. Required: arm,
    case_id. Everything else optional; missing fields stay null, never crash."""
    ec = str(gj.get("evidence_class", "run.json"))
    if ec not in CLASSES:
        raise ValueError(
            f"run.json at {path}: evidence_class must be one of {CLASSES}, got {ec!r}"
        )
    ranking = gj.get("submitted_ranking") or gj.get("ranking")
    rec = RunRecord(
        run_path=str(path),
        arm=str(gj["arm"]),
        case_id=str(gj["case_id"]),
        seed=gj.get("seed"),
        evidence_class=ec,
        status=str(gj.get("status", "unknown")),
        abort_reason=gj.get("abort_reason"),
        submitted_ranking=list(ranking) if ranking else None,
        claimed_cause=(ranking[0] if ranking else gj.get("target_artifact")
                       or gj.get("verdict_target")),
        tokens=gj.get("tokens_total", gj.get("tokens")),
        llm_calls=gj.get("llm_calls"),
        tool_calls=gj.get("tool_calls"),
        wall_s=gj.get("wall_s"),
        protocol_violations=int(gj.get("protocol_violations", 0) or 0),
        escrowed=gj.get("escrowed"),
        agent_top1s=[a for a in (gj.get("agent_top1s") or []) if isinstance(a, str)],
        agent_verdicts=[a for a in (gj.get("agent_verdicts") or []) if isinstance(a, str)],
    )
    ist = gj.get("intervention_stats")
    if ec == CLASS_EXEC and isinstance(ist, dict):
        executed = int(ist.get("executed", 0) or 0)
        verified = int(ist.get("verified", 0) or 0)
        flipped = int(ist.get("flipped", 0) or 0)
        rec.interventions = {
            "claimed": ist.get("claimed", 0),
            "executed": executed,
            "verified": verified,
            "verified_fraction": (verified / executed) if executed else None,
            "flipped": flipped,
            "flipped_fraction": (flipped / executed) if executed else None,
        }
    if gj.get("cause_set") is not None:
        rec.gt_set = frozenset(gj["cause_set"])
        rec.truth_source = "run.json"
    else:
        _attach_truth(rec, truth)
    return rec


def discover_run_dirs(roots: list[Path]) -> list[Path]:
    """All descendant dirs holding a recognized run artifact, sorted."""
    out: set[Path] = set()
    for root in roots:
        root = Path(root)
        if root.is_file():
            continue
        for name in ("final_verdict.json", "status.json", "run.json"):
            out.update(root.rglob(name))
    run_dirs = {p.parent for p in out}
    return sorted(d for d in run_dirs if parse_run_dir(d, None) is not None)


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------


def _pct(n: int | None, d: int | None) -> float | None:
    if d in (None, 0):
        return None
    if n is None:
        return None
    return n / d


def _mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 6) if xs else None


def _consensus_of(rec: RunRecord) -> tuple[bool, bool | None]:
    """(reached_consensus, consensus_was_wrong).

    Observational: >=2 escrowed agents with identical top-1. Wrong = final
    top-1 misses the GT set. Executable: >=2 agents with identical conclusion
    verdict; wrong = final target misses the GT set."""
    src = rec.agent_top1s if rec.evidence_class == CLASS_OBS else rec.agent_verdicts
    if len(src) < 2 or len(set(src)) != 1:
        return False, None
    wrong: bool | None = None
    if rec.completed and rec.gt_set is not None and rec.claimed_cause:
        wrong = rec.claimed_cause not in rec.gt_set
    return True, wrong


def aggregate_arm(arm: str, runs: list[RunRecord]) -> dict[str, Any]:
    completed = [r for r in runs if r.completed]
    scored = [r for r in completed if r.top1_hit is not None]
    correct = [r for r in scored if r.top1_hit]
    non_comp = [r for r in runs if not r.completed]

    interventions = [r.interventions for r in runs if r.interventions is not None]
    if interventions:
        executed = sum(i["executed"] for i in interventions)
        verified = sum(i["verified"] for i in interventions)
        flipped = sum(i["flipped"] for i in interventions)
        iv: dict[str, Any] = {
            "na": False,
            "claimed": sum(i.get("claimed", 0) or 0 for i in interventions),
            "executed": executed,
            "verified": verified,
            "verified_fraction": _pct(verified, executed),
            "flipped": flipped,
            "flipped_fraction": _pct(flipped, executed),
        }
    else:
        iv = {"na": True, "reason": "observational: no intervention executor"}

    consensus_runs = 0
    false_consensus = 0
    consensus_scored = 0
    for r in runs:
        c, w = _consensus_of(r)
        if c:
            consensus_runs += 1
            if w is not None:
                consensus_scored += 1
                if w:
                    false_consensus += 1

    premature = {
        "count": len(non_comp),
        "reasons": {
            s: sum(1 for r in non_comp if r.status == s)
            for s in sorted({r.status for r in non_comp})
        },
        "no_escrow": sum(1 for r in completed if r.escrowed is False),
    }

    def _sum(key: str) -> float | None:
        vals = [getattr(r, key) for r in runs if getattr(r, key) is not None]
        return sum(vals) if vals else None

    cost = {
        "total_tokens": _sum("tokens"),
        "llm_calls": _sum("llm_calls"),
        "wall_s": round(_sum("wall_s"), 3) if _sum("wall_s") is not None else None,
        "tokens_per_correct_completion": _pct(sum(r.tokens or 0 for r in correct), len(correct)),
        "wall_s_per_correct_completion": _mean([r.wall_s for r in correct if r.wall_s is not None]),
    }
    ttv = [r.wall_s for r in completed if r.wall_s is not None]
    ttv_sorted = sorted(ttv)
    p50 = ttv_sorted[len(ttv_sorted) // 2] if ttv_sorted else None

    return {
        "arm": arm,
        "runs": len(runs),
        "completions": len(completed),
        "identification": {
            "scored_runs": len(scored),
            "top1_hits": len(correct),
            "top1_rate": _pct(len(correct), len(scored)),
            "exact_set_matches": sum(1 for r in scored if r.exact_set_match),
            "exact_set_rate": _pct(sum(1 for r in scored if r.exact_set_match), len(scored)),
            "mean_jaccard": _mean([r.jaccard for r in scored if r.jaccard is not None]),
        },
        "verified_interventions": iv,
        "false_consensus": {
            "consensus_runs": consensus_runs,
            "consensus_scored": consensus_scored,
            "false_consensus_runs": false_consensus,
            "false_consensus_rate": _pct(false_consensus, consensus_scored),
        },
        "premature_stops": premature,
        "cost": cost,
        "time_to_verdict_s": {
            "mean": _mean(ttv),
            "p50": p50,
            "max": max(ttv) if ttv else None,
            "n": len(ttv),
        },
        "failures": {
            "non_completion": len(non_comp),
            "budget_exhaustion": sum(1 for r in runs if r.budget_exhausted),
            "crashes": sum(1 for r in runs if r.status == "crashed"),
            "protocol_violations": sum(1 for r in runs if r.protocol_violations > 0),
        },
    }


def case_pairs(runs: list[RunRecord]) -> list[dict[str, Any]]:
    """CASE-level paired rows (the unit of comparison). One row per
    (case, arm) within the SAME evidence class; never across classes."""
    rows: list[dict[str, Any]] = []
    by_case: dict[str, list[RunRecord]] = {}
    for r in runs:
        by_case.setdefault(r.case_id, []).append(r)
    for case in sorted(by_case):
        for r in sorted(by_case[case], key=lambda x: (x.arm, x.seed or 0)):
            rows.append({
                "case": case,
                "seed": r.seed,
                "arm": r.arm,
                "status": r.status,
                "correct": r.correct,
                "top1": r.claimed_cause,
                "jaccard": r.jaccard,
                "tokens": r.tokens,
                "wall_s": r.wall_s,
                "non_completion": not r.completed,
            })
    return rows


def build_scorecard(runs: list[RunRecord]) -> dict[str, Any]:
    """Aggregate per evidence class. Cross-class merging is refused by design;
    the ``merged_aggregate`` key is always null with the refusal documented."""
    classes: dict[str, Any] = {}
    for ec in CLASSES:
        cls_runs = [r for r in runs if r.evidence_class == ec]
        arms: dict[str, list[RunRecord]] = {}
        for r in cls_runs:
            arms.setdefault(r.arm, []).append(r)
        classes[ec] = {
            "evidence_class": ec,
            "claim_strength": (
                "access-matched observational diagnosis; NOT a causal-intervention claim"
                if ec == CLASS_OBS
                else "executed counterfactuals on a real intervention executor"
            ),
            "runs": len(cls_runs),
            "arms": {a: aggregate_arm(a, rs) for a, rs in sorted(arms.items())},
            "case_pairs": case_pairs(cls_runs),
            "unscored_runs": sum(
                1 for r in cls_runs if r.completed and r.gt_set is None
            ),
        }
    return {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_runs": len(runs),
        "evidence_classes": classes,
        "merged_aggregate": None,
        "refusal": (
            "OBSERVATIONAL and EXECUTABLE-COUNTERFACTUAL rows carry different "
            "claim strengths and are never merged into a single aggregate row; "
            "pair analysis is at case level within one evidence class only"
        ),
    }


def merge_class_summaries(obs: dict[str, Any],
                          exc: dict[str, Any]) -> dict[str, Any]:
    """Explicit refusal point: any attempt to combine the two class
    summaries raises. Kept as a callable so callers/tests can trip it."""
    raise _refuse_merge(
        obs.get("evidence_class", "observational"),
        exc.get("evidence_class", "executable_counterfactual"),
    )


# ---------------------------------------------------------------------------
# markdown rendering
# ---------------------------------------------------------------------------

_COLS = [
    ("runs", "runs"),
    ("completions", "complete"),
    (("identification", "top1_rate"), "top-1"),
    (("identification", "exact_set_rate"), "exact-set"),
    (("identification", "mean_jaccard"), "jaccard"),
    (("verified_interventions", "verified_fraction"), "verified-intv"),
    (("false_consensus", "false_consensus_rate"), "false-cons."),
    (("premature_stops", "count"), "premature"),
    (("cost", "total_tokens"), "tokens"),
    (("cost", "wall_s"), "wall-s"),
    (("cost", "tokens_per_correct_completion"), "tok/correct"),
    (("failures", "budget_exhaustion"), "budget"),
    (("failures", "protocol_violations"), "protocol"),
]


def _get(obj: dict[str, Any], path: tuple[str, ...] | str) -> Any:
    cur: Any = obj
    for key in (path if isinstance(path, tuple) else (path,)):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}" if v <= 1.5 else f"{v:.1f}"
    return str(v)


def render_markdown(scorecard: dict[str, Any]) -> str:
    lines = ["# Arm-vs-arm scorecard", "",
             f"Total runs: {scorecard['total_runs']}  ",
             "Cross-class merging is REFUSED (different claim strengths).", ""]
    for ec in CLASSES:
        block = scorecard["evidence_classes"].get(ec)
        if not block or not block["arms"]:
            continue
        lines.append(f"## {ec} — {block['claim_strength']}")
        lines.append("")
        header = "| arm | " + " | ".join(h for _, h in _COLS) + " |"
        lines.append(header)
        lines.append("|" + "---|" * (len(_COLS) + 1))
        for arm in sorted(block["arms"]):
            a = block["arms"][arm]
            cells = [_fmt(_get(a, key)) for key, _ in _COLS]
            lines.append(f"| {arm} | " + " | ".join(cells) + " |")
        if block["unscored_runs"]:
            lines.append("")
            lines.append(f"_unscored completed runs (no resolvable GT): "
                         f"{block['unscored_runs']}_")
        pairs = block["case_pairs"]
        if pairs:
            lines += ["", "### case-level pairs", "",
                      "| case | seed | arm | status | correct | top-1 | jaccard | tokens | wall-s |",
                      "|---|---|---|---|---|---|---|---|---|"]
            for p in pairs:
                lines.append(
                    f"| {p['case']} | {p['seed']} | {p['arm']} | {p['status']} | "
                    f"{_fmt(p['correct'])} | {p['top1'] or '—'} | {_fmt(p['jaccard'])} | "
                    f"{_fmt(p['tokens'])} | {_fmt(p['wall_s'])} |"
                )
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def load_truth(path: Path) -> dict[str, list[str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): [str(c) for c in v] for k, v in raw.items()}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="RepliClaw arm-vs-arm scorecard")
    ap.add_argument("roots", nargs="+", help="run dirs or trees containing run dirs")
    ap.add_argument("--truth", type=Path, default=None,
                    help="scorer-side truth file: {case_id: [cause,...]}")
    ap.add_argument("--json", type=Path, default=None, help="write scorecard JSON")
    ap.add_argument("--md", type=Path, default=None, help="write markdown table")
    args = ap.parse_args(argv)

    truth = load_truth(args.truth) if args.truth else None
    run_dirs = discover_run_dirs([Path(r) for r in args.roots])
    runs = [r for r in (parse_run_dir(d, truth) for d in run_dirs) if r is not None]
    scorecard = build_scorecard(runs)

    text = json.dumps(scorecard, indent=2, sort_keys=True)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(render_markdown(scorecard), encoding="utf-8")
    if not (args.json or args.md):
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
