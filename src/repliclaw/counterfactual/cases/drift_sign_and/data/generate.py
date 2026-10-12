#!/usr/bin/env python3
"""One-shot, deterministic generator for the frozen batch-assay data.

Run ONCE to produce ``batch_assay.json`` (the frozen case input). Pure
function of the LCG seed below; regenerating reproduces the frozen file
byte-for-byte. The file is committed and its sha256 pinned in the manifest.

32 samples from QC batch B-2026-094. Each sample carries:
* ``raw_counts``  -- the uncalibrated instrument's raw readout. The readout
  model is ``raw = k * c_true + b`` (bias ``b`` = instrument drift), so
  ``raw - drift`` is exactly the bias-free readout.
* ``reference_drift_counts`` -- the bias ``b`` measured on an interleaved
  blank (zero-concentration) reference. Visible telemetry: the instrument
  logs it per sample. It is NONZERO on this batch (uncalibrated state).

The two latent causes live in how the pipeline CONSUMES these visible
numbers (correction sign x drift state); no per-sample truth is stored here.
"""
from __future__ import annotations

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
OUT = _HERE / "batch_assay.json"

M = 2**64
A = 6364136223846793005
C = 1442695040888963407
SEED = 20261013  # frozen generation seed (provenance; NOT the run seed)


def lcg(seed: int):
    state = [seed % M]

    def next_int() -> int:
        state[0] = (state[0] * A + C) % M
        return state[0]

    def next_range(lo: int, hi: int) -> int:
        return lo + next_int() % (hi - lo)

    return next_range


def main() -> int:
    rnd = lcg(SEED)
    samples = []
    for i in range(32):
        raw = rnd(42_000, 52_000)  # uncalibrated readout counts
        drift = rnd(90, 421)  # nonzero bias from the blank reference
        samples.append(
            {
                "sample_id": f"S{i + 1:02d}",
                "raw_counts": raw,
                "reference_drift_counts": drift,
                "log_lines": [
                    f"INFO sample=S{i + 1:02d} raw={raw} blank_ref_drift={drift} state=uncalibrated"
                ],
            }
        )
    doc = {
        "schema": "repliclaw.frozen_batch_assay/v1",
        "case": "drift_sign_and_v1",
        "batch_id": "B-2026-094",
        "instrument": {"model": "AX-550", "gain_state": "factory", "state_at_run": "uncalibrated"},
        "n_samples": 32,
        "samples": samples,
        "generator": "data/generate.py (deterministic 64-bit LCG, seed 20261013)",
    }
    OUT.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mean_raw = sum(s["raw_counts"] for s in samples) / 32
    mean_drift = sum(s["reference_drift_counts"] for s in samples) / 32
    print("wrote", OUT)
    print(f"mean raw={mean_raw:.1f}  mean drift={mean_drift:.1f}")
    print(f"true mean conc = (mean_raw - mean_drift)/96 = {(mean_raw - mean_drift) / 96.0:.4f} umg/mL")
    print(f"buggy mean conc = (mean_raw + mean_drift)/96 = {(mean_raw + mean_drift) / 96.0:.4f} umg/mL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
