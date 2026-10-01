#!/usr/bin/env bash
# P06 second scientific case (Tox21 AR-agonist) — regenerate the canonical run.
#
# Deterministic: the arms are pure functions of the frozen 48-compound subset
# (Crippen logP via RDKit, a deterministic fragment sum) and the per-arm files
# contain no wall-clock timestamps. So regenerating the arm files is
# byte-identical (sha256-pinned) across runs and machines (given the same
# pinned RDKit version, recorded in manifest.json -> engine.version).
#
# Usage:  bash artifacts/science/p06-hero-canonical/replay.sh
#
# Verifies the regenerated arm files match the sha256 pins in manifest.json
# (two-pass: stored files + a clean re-execution), then prints the per-arm
# sha256 summary.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Here = <worktree>/artifacts/science/p06-hero-canonical -> 3 levels up = worktree.
REPO="$(cd "$HERE/../../.." && pwd)"

# Prefer this worktree's venv (has RDKit + repliclaw installed).
if [ -x "$REPO/.venv/bin/python" ]; then
  PY="$REPO/.venv/bin/python"
else
  PY="$(command -v python3)"
fi

echo "[replay] using $PY"
cd "$REPO"

"$PY" - <<'PYEOF'
import hashlib
import json
import shutil
from pathlib import Path

from repliclaw.counterfactual.cases import _base
from repliclaw.counterfactual.cases.tox21_ar_agonist import load_case

CANON = Path("artifacts/science/p06-hero-canonical")
case = load_case()
manifest = json.loads((CANON / "manifest.json").read_text())
seed = int(manifest["arms"][sorted(manifest["arms"])[0]].get("seed", 0))

# Regenerate arm files in a scratch dir, then copy over the committed ones
# (byte-identical; keeps the committed manifest's original timestamps).
regen = CANON / ".regen"
if regen.exists():
    shutil.rmtree(regen)
_base.run_canonical(case, regen, seed=seed)
for arm_dir in (regen / "interventions").iterdir():
    dst = CANON / "interventions" / arm_dir.name
    dst.mkdir(parents=True, exist_ok=True)
    for f in arm_dir.iterdir():
        if f.is_file():
            (dst / f.name).write_bytes(f.read_bytes())
shutil.rmtree(regen)

ok = _base.replay(case, CANON)
print(f"[replay] byte-identical verification: {ok}")
if not ok:
    raise SystemExit("[replay] FAILED — regenerated artifacts differ from pins")

# Per-arm sha256 summary.
for arm_dir in sorted((CANON / "interventions").iterdir()):
    for f in sorted(arm_dir.iterdir()):
        if f.is_file():
            h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
            print(f"  {h}  {arm_dir.name}/{f.name}")
PYEOF

echo "[replay] done."
