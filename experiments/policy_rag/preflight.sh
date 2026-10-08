#!/usr/bin/env bash
# P08 pre-flight suite (PREREG-2026-10-v1.1 §9.2/§10.1 step 1).
#
# Runs every pre-flight gate the prereg requires before run 1 and prints a
# PASS/FAIL summary. Exits 0 only if ALL gates pass.
#
#   (S3)  P05 parity suite (tests/test_comparators.py)
#   (S4)  leakage guard + scorer self-test (tests/test_p08_score.py)
#   (P02) canonical replay byte-identical (experiments/policy_rag/replay.sh)
#   (CLI) runner CLI smoke (S0 + eess_offline offline runs, contract
#         artifacts, C1 same-envelope hash, live-arm exit-2 refusal,
#         --assert-frozen) — all offline, fake client, mktemp -d scratch
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

# Gate 5: runner CLI smoke (prereg v1.1 §10.1 step 1). All offline:
# fake client, REPLICLAW_LLM_ALLOW_LIVE cleared, scratch dir cleaned on exit.
gate5_runner_cli_smoke() {
  local tmp rc
  tmp="$(mktemp -d)"
  rc=0
  export REPLICLAW_LLM_ALLOW_LIVE=

  # (a) one offline arm (S0) and one offline EESS arm (eess_offline), exit 0.
  "$PY" -m repliclaw.comparators.runner --arm S0 --case policy_rag \
    --out "$tmp/S0" --client-factory fake || { echo "  S0 offline run: FAIL"; rc=1; }
  "$PY" -m repliclaw.comparators.runner --arm eess_offline --case policy_rag \
    --out "$tmp/eess_offline" --client-factory fake || { echo "  eess_offline offline run: FAIL"; rc=1; }

  # (b) the 4 contract artifacts under <out>/run-01/ for each arm.
  local arm f
  for arm in S0 eess_offline; do
    for f in final_verdict.json budget_ledger.json traces.jsonl run_metadata.json; do
      if [ ! -f "$tmp/$arm/run-01/$f" ]; then
        echo "  $arm/run-01/$f: MISSING"
        rc=1
      fi
    done
  done

  # (c) C1 same-task hash: both run_metadata.json share envelope_sha256.
  local h1 h2
  h1="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["envelope_sha256"])' "$tmp/S0/run-01/run_metadata.json" 2>/dev/null)"
  h2="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["envelope_sha256"])' "$tmp/eess_offline/run-01/run_metadata.json" 2>/dev/null)"
  if [ -z "$h1" ] || [ -z "$h2" ] || [ "$h1" != "$h2" ]; then
    echo "  C1 envelope_sha256 mismatch: S0=$h1 eess_offline=$h2"
    rc=1
  else
    echo "  C1 envelope_sha256: $h1 (shared)"
  fi

  # (d) live-arm refusal on the secondary no-LLM case: exit 2, no run-01 dir.
  local s5rc=0
  "$PY" -m repliclaw.comparators.runner --arm S5 --case tox21_ar_agonist \
    --out "$tmp/s5" --client-factory fake 2>/dev/null || s5rc=$?
  if [ "$s5rc" -ne 2 ]; then
    echo "  S5/tox21 refusal: expected exit 2, got $s5rc"
    rc=1
  fi
  if [ -d "$tmp/s5/run-01" ]; then
    echo "  S5/tox21 refusal: run-01 dir must not be created"
    rc=1
  fi

  # (e) --assert-frozen passes for the S5 fake run on the primary case.
  "$PY" -m repliclaw.comparators.runner --arm S5 --case policy_rag \
    --out "$tmp/s5f" --client-factory fake --assert-frozen || { echo "  S5 --assert-frozen: FAIL"; rc=1; }

  rm -rf "$tmp"
  return "$rc"
}

run_gate "runner CLI smoke (offline S0 + eess_offline, contract artifacts, C1 hash, exit-2 refusal, --assert-frozen)" \
  gate5_runner_cli_smoke

echo ""
if [ "$FAILURES" -eq 0 ]; then
  echo "ALL PRE-FLIGHT GATES PASS — run-branch SHA to pin (S6): $(git rev-parse HEAD)"
  exit 0
else
  echo "$FAILURES gate(s) FAILED — do NOT start the campaign." >&2
  exit 1
fi
