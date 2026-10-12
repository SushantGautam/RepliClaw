"""RepliClaw adapter for the official HiddenBench (ICML 2026) benchmark.

Runs HiddenBench Hidden-Profile tasks under three access-matched arms:

* ``escrow``     — RepliClaw-style: per-agent evidence packets and a
  ranked-answer commitment are held in escrow (commit phase) and revealed
  only before the final vote.
* ``open-share`` — official HiddenBench discussion protocol: agents see
  each other's messages while reasoning.
* ``central``    — one centralized controller receives the pooled
  information directly and decides.

Every result is labeled OBSERVATIONAL / ACCESS-MATCHED (never causal) and,
when the endpoint model is not the benchmark's released baseline,
MODEL-SUBSTITUTION.
"""

from .runner import run_arms  # noqa: F401
