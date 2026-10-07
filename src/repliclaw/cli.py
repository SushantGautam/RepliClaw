"""RepliClaw command-line interface (AC02 / AC13 / AC16).

Commands:
    repliclaw verify --claim "..." [--data '{...}'] [--artifact f ...]
                     [--backend deterministic|llm] [--out DIR] [--json]
    repliclaw benchmark [--out DIR] [--backend deterministic|llm]
                        [--strategies repl_claw,single_agent,...]

`verify` is the cross-team surface: submit a claim (with optional bundled data
and artifact references) and receive a provenance-linked report. `benchmark`
runs the controlled known-answer evaluation across all baselines and writes
CSV/JSON/Markdown outputs under `artifacts/` (AC16).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _parse_data(raw: str | None):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--data is not valid JSON: {exc}")


def _load_artifact(path: str):
    p = Path(path)
    if not p.exists():
        return {"ref": str(path)}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ref": str(path), "text": p.read_text(encoding="utf-8", errors="replace")}


def cmd_verify(args) -> int:
    from repliclaw import verify

    claim = {
        "statement": args.claim,
        "domain": args.domain or "general",
        "data": _parse_data(args.data),
        "reference_truth": args.reference_truth,
        "seeded_fault": args.seeded_fault,
    }
    artifacts = [_load_artifact(a) for a in (args.artifact or [])]
    config = {
        "backend": args.backend,
        "run_root": args.out or str(Path("artifacts") / "verify"),
    }
    if args.max_followup_rounds is not None:
        config["max_followup_rounds"] = args.max_followup_rounds
    if args.min_independent is not None:
        config["min_independent"] = args.min_independent

    report = verify(claim, artifacts=artifacts or None, config=config)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"CLAIM:   {claim['statement']}")
        print(f"VERDICT: {report.verdict_label}  (confidence {report.verdict_confidence:.3f})")
        print(f"BACKEND: {args.backend}")
        print(f"EVIDENCE: {report.n_evidence} items from {report.n_independent} independent agents")
        print(f"NEEDS:   {report.n_needs} follow-up need(s) generated")
        print(f"USAGE:   {report.usage.get('llm_calls', 0)} LLM calls, {report.usage.get('total_tokens', 0)} tokens")
        print(f"REASONING: {report.reasoning}")
        print(f"REPORT:  {report.report_path}")
        print(f"RUN DIR: {report.run_dir}")
    return 0


def cmd_benchmark(args) -> int:
    from repliclaw.benchmark import run_benchmark
    from repliclaw.verify import make_investigator_factory

    strategies = [s.strip() for s in args.strategies.split(",")] if args.strategies else None
    factory = make_investigator_factory(args.backend)
    rep = run_benchmark(
        out_dir=Path(args.out) / "benchmark",
        investigator_factory=factory,
        strategies=strategies,
    )
    print(f"Benchmark complete: {rep['n_tasks']} tasks x {rep['n_strategies']} strategies")
    print()
    print(f"{'strategy':16s} {'correct':>8s} {'false-acc':>10s} {'false-rej':>10s} "
          f"{'inconcl':>8s} {'recovery':>9s} {'agents':>7s}")
    for strat, m in rep["per_strategy"].items():
        c = m["correctness"]
        rec = m["recovery"]["recovery_rate"]
        rec_s = f"{rec:.3f}" if rec is not None else "n/a"
        print(f"{strat:16s} {c['correctness']:8.3f} {c['false_accept_rate']:10.3f} "
              f"{c['false_reject_rate']:10.3f} {c['inconclusive_rate']:8.3f} {rec_s:>9s} "
              f"{m['avg_agents']:7d}")
    outdir = Path(args.out) / "benchmark"
    print()
    print(f"Outputs: {outdir/'benchmark_report.md'}")
    print(f"         {outdir/'benchmark_results.csv'}")
    print(f"         {outdir/'benchmark_report.json'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="repliclaw", description="RepliClaw verification CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("verify", help="Verify a scientific claim (cross-team surface)")
    pv.add_argument("--claim", required=True, help="The claim statement to verify")
    pv.add_argument("--data", help="JSON blob of bundled structured data")
    pv.add_argument("--artifact", action="append",
                    help="Path to an artifact file to bundle (repeatable)")
    pv.add_argument("--domain", default=None, help="Claim domain (default: general)")
    pv.add_argument("--reference_truth", default=None,
                    choices=[None, "supported", "refuted"],
                    help="Ground truth (benchmark/demo only; does not influence the verdict)")
    pv.add_argument("--seeded_fault", default=None, help="Fault-mode tag (benchmark/demo only)")
    pv.add_argument("--backend", default="deterministic",
                    choices=["deterministic", "llm"],
                    help="Investigator backend (default: deterministic, hermetic)")
    pv.add_argument("--out", default=None, help="Run output root (default: artifacts/verify)")
    pv.add_argument("--max_followup_rounds", type=int, default=None)
    pv.add_argument("--min_independent", type=int, default=None)
    pv.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    pv.set_defaults(func=cmd_verify)

    pb = sub.add_parser("benchmark", help="Run the controlled known-answer benchmark")
    pb.add_argument("--out", default="artifacts", help="Output root (default: artifacts)")
    pb.add_argument("--backend", default="deterministic", choices=["deterministic", "llm"])
    pb.add_argument("--strategies", default=None,
                    help="Comma-separated subset (default: all five)")
    pb.set_defaults(func=cmd_benchmark)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
