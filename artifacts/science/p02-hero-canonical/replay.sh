#!/usr/bin/env bash
# P02 hero case — regenerate the canonical counterfactual run.
#
# Deterministic: the target and judge are pure functions of the frozen case
# config, SimpleAudit runs OFFLINE (no network, no real tokens), and the
# per-arm files contain no wall-clock timestamps. So regenerating the arm
# files is byte-identical (sha256-pinned) across runs and machines.
#
# Usage:  bash artifacts/science/p02-hero-canonical/replay.sh
#
# Verifies the regenerated arm files match the sha256 pins in manifest.json,
# then prints the per-arm sha256 summary.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Here = <worktree>/artifacts/science/p02-hero-canonical -> 4 levels up = worktree.
REPO="$(cd "$HERE/../../.." && pwd)"

# Prefer this worktree's venv (has SimpleAudit installed editable).
if [ -x "$REPO/.venv/bin/python" ]; then
  PY="$REPO/.venv/bin/python"
else
  PY="$(command -v python3)"
fi

echo "[replay] using $PY"
cd "$REPO"

"$PY" - <<'PYEOF'
import json
import shutil
from pathlib import Path

from repliclaw.counterfactual import load_case, load_interventions, replay, run_canonical

CASE_ID = "policy_rag_v1"
CANON = Path("artifacts/science/p02-hero-canonical")

# Regenerate arm files in place (keeps manifest's original timestamps).
case = load_case(CASE_ID)
interventions = load_interventions(CASE_ID)
manifest = json.loads((CANON / "manifest.json").read_text())
seed = int(manifest["arms"][interventions[0].intervention_id].get("seed", 0))

regen = CANON / ".regen"
if regen.exists():
    shutil.rmtree(regen)
run_canonical(case, interventions, seed=seed, out_root=regen)

# Move regenerated arm files over the committed ones (byte-identical).
import filecmp

for arm_dir in (regen / "interventions").iterdir():
    dst = CANON / "interventions" / arm_dir.name
    for f in arm_dir.iterdir():
        if f.is_file():
            (dst / f.name).write_bytes(f.read_bytes())
shutil.rmtree(regen)

ok = replay(CASE_ID, CANON)
print(f"[replay] byte-identical verification: {ok}")
if not ok:
    raise SystemExit("replay verification FAILED — regenerated artifacts differ")

# Per-arm sha256 summary.
import hashlib

for arm_dir in sorted((CANON / "interventions").iterdir()):
    for f in sorted(arm_dir.iterdir()):
        if f.is_file():
            h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
            print(f"  {h}  {arm_dir.name}/{f.name}")
PYEOF

echo "[replay] done."
