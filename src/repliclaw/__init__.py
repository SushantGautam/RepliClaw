"""RepliClaw — decentralized blind replication/falsification collective.

Built on ScienceClaw artifact/need primitives. See README.md and DECISIONS.md.

Public surface:
    from repliclaw import verify          # cross-team verify() interface (AC13)
    from repliclaw import Claim           # structured claim model
    from repliclaw.benchmark import run_benchmark
    from repliclaw.strategies import run_strategy, STRATEGY_RUNNERS
"""

__version__ = "0.1.0"

from .models import Claim, Verdict, VerdictLabel  # noqa: F401
from .verify import VerificationReport, verify  # noqa: F401

__all__ = ["Claim", "Verdict", "VerdictLabel", "verify", "VerificationReport"]
