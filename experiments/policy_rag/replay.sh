#!/usr/bin/env bash
# P08 pre-flight (PREREG v1.1 §10.1 step 1): P02 canonical replay gate.
#
# Regenerates the policy_rag_v1 hero-case counterfactual arm files
# (offline SimpleAudit, deterministic, no network) and verifies them
# byte-identical against the sha256 pins committed in
# artifacts/science/p02-hero-canonical/manifest.json. Prints per-arm
# sha256. Exits non-zero on any drift.
#
# Usage:  bash experiments/policy_rag/replay.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

if [ -x "$REPO/.venv/bin/python" ]; then
  PY="$REPO/.venv/bin/python"
else
  PY="$(command -v python3)"
fi

echo "[replay] using $PY"
cd "$REPO"

"$PY" - <<'PYEOF'
import filecmp
import hashlib
import json
import shutil
from pathlib import Path

from repliclaw.counterfactual import load_case, load_interventions, replay, run_canonical

CASE_ID = "policy_rag_v1"
CANON = Path("artifacts/science/p02-hero-canonical")

case = load_case(CASE_ID)
interventions = load_interventions(CASE_ID)
manifest = json.loads((CANON / "manifest.json").read_text())
seed = int(manifest["arms"][interventions[0].intervention_id].get("seed", 0))

regen = CANON / ".regen"
if regen.exists():
    shutil.rmtree(regen)
run_canonical(case, interventions, seed=seed, out_root=regen)

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

for arm_dir in sorted((CANON / "interventions").iterdir()):
    for f in sorted(arm_dir.iterdir()):
        if f.is_file():
            h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
            print(f"  {h}  {arm_dir.name}/{f.name}")
PYEOF

echo "[replay] done."
