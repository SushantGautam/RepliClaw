#!/usr/bin/env bash
# P08 pre-flight suite (PREREG-2026-10-v1.1 §9.2/§10.1 step 1).
#
# Runs every pre-flight gate the prereg requires before run 1 and prints a
# PASS/FAIL summary. Exits 0 only if ALL gates pass.
#
#   (S3)  P05 parity suite (tests/test_comparators.py)
#   (S4)  leakage guard + scorer self-test (tests/test_p08_score.py)
#   (P02) canonical replay byte-identical (experiments/policy_rag/replay.sh)
#   (SHA) current run-branch SHA printed for pinning (S6)
#
# Usage:  bash experiments/policy_rag/preflight.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
PY="$REPO/.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "FATAL: $PY not found — activate/install the repo venv first." >&2
  exit 2
fi

cd "$REPO"
FAILURES=0
run_gate() {
  local name="$1"; shift
  echo ""
  echo "=== GATE: $name ==="
  if "$@"; then
    echo "[gate] $name: PASS"
  else
    echo "[gate] $name: FAIL (exit $?)"
    FAILURES=$((FAILURES + 1))
  fi
}

echo "run branch: $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse HEAD)"
echo "tree status: $(git status --porcelain | wc -l | tr -d ' ') modified paths (must be 0 at pin time)"

run_gate "S3 parity suite (tests/test_comparators.py)" \
  "$PY" -m pytest tests/test_comparators.py -q

run_gate "S4 leakage + scorer self-test (tests/test_p08_score.py)" \
  "$PY" -m pytest tests/test_p08_score.py -q

run_gate "P02 canonical replay byte-identical" \
  bash "$REPO/experiments/policy_rag/replay.sh"

run_gate "scorer --self-test entrypoint" \
  "$PY" -m repliclaw.p08.score --self-test

echo ""
if [ "$FAILURES" -eq 0 ]; then
  echo "ALL PRE-FLIGHT GATES PASS — run-branch SHA to pin (S6): $(git rev-parse HEAD)"
  exit 0
else
  echo "$FAILURES gate(s) FAILED — do NOT start the campaign." >&2
  exit 1
fi
