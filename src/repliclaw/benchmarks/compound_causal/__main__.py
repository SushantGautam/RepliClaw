"""CLI: python -m repliclaw.benchmarks.compound_causal --help."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import BenchmarkSession, generate_dataset, load_dataset, score_predictions


def main() -> None:
    parser = argparse.ArgumentParser(description="CompoundCausal-32 synthetic causal benchmark")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("generate", help="Create 32 cases and private evaluator gold")
    init.add_argument("--out", required=True, type=Path)
    init.add_argument("--seed", type=int, help="DEVELOPMENT ONLY; omit for private random suite")
    demo = sub.add_parser("smoke", help="Execute actual simulated interventions on one case")
    demo.add_argument("--root", required=True, type=Path)
    demo.add_argument("--case", help="opaque case ID; default first generated case")
    demo.add_argument("--out", type=Path, help="write public action trace here")
    score = sub.add_parser("score", help="Evaluator-only; score frozen predictions from JSONL")
    score.add_argument("--root", required=True, type=Path)
    score.add_argument("--predictions", required=True, type=Path)
    score.add_argument("--out", type=Path, help="write evaluation to this file")
    args = parser.parse_args()

    if args.command == "generate":
        manifest = generate_dataset(args.out, seed=args.seed)
        print(json.dumps({"out": str(args.out), **manifest}, indent=2))
        print("WARNING: do not give private/oracles.jsonl to agent sessions.")
        return

    cards, gold = load_dataset(args.root)
    if args.command == "smoke":
        case_id = args.case or next(iter(cards))
        session = BenchmarkSession(cards[case_id], gold[case_id])
        print(json.dumps(session.card(), indent=2))
        # A smoke of executed simulator interventions, NOT an LLM agent run.
        for repairs in ([], ["retrieval"], ["tool_data"], ["policy"], ["judge"], ["retrieval", "judge"]):
            print(json.dumps(session.intervene(repairs), sort_keys=True))
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(session.public_history(), indent=2) + "\n", encoding="utf-8")
        return

    submissions = [json.loads(line) for line in args.predictions.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
    result = score_predictions(gold, submissions)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    print(encoded)


if __name__ == "__main__":
    main()
