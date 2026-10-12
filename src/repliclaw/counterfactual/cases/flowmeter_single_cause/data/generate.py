#!/usr/bin/env python3
"""One-shot, deterministic generator for the frozen meter telemetry window.

Run ONCE to produce ``meter_window.json`` (the frozen case input). The output
is a pure function of the LCG seed below, so regenerating reproduces the
frozen file byte-for-byte. The file is then committed and its sha256 pinned
in the case manifest; the pipeline never reads anything else.

Window: 14 daily pulse totals from an inline flow meter (meter FT-7731).
``dropped_events`` is the meter's own lost-pulse counter logged per day. It
is 0 for every day in this frozen window (the meter logged the counter and it
was zero) -- that is what makes the "account for dropped events"
intervention a genuine no-op on THIS data, i.e. a valid non-cause control.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

_HERE = Path(__file__).resolve().parent
OUT = _HERE / "meter_window.json"

M = 2**64
A = 6364136223846793005
C = 1442695040888963407
SEED = 20261012  # frozen generation seed (provenance; NOT the run seed)


def lcg(seed: int):
    state = [seed % M]

    def next_int() -> int:
        state[0] = (state[0] * A + C) % M
        return state[0]

    def next_range(lo: int, hi: int) -> int:
        """Uniform integer in [lo, hi)."""
        return lo + next_int() % (hi - lo)

    return next_range


def main() -> int:
    rnd = lcg(SEED)
    start = date(2026, 6, 1)
    days = []
    for i in range(14):
        d = start + timedelta(days=i)
        pulses = rnd(110_000, 180_000)  # ~110k-180k pulses/day on this line
        days.append(
            {
                "day": d.isoformat(),
                "pulse_counts": pulses,
                "dropped_events": 0,  # meter lost-pulse counter: zero all window
                "log_lines": [
                    f"INFO day={d.isoformat()} pulses={pulses} window_close=ok",
                    f"INFO day={d.isoformat()} dropped_events=0 meter=FT-7731",
                ],
            }
        )
    doc = {
        "schema": "repliclaw.frozen_meter_window/v1",
        "case": "flowmeter_single_cause_v1",
        "meter_id": "FT-7731",
        "line": "distribution-loop-7",
        "window_days": 14,
        "pulse_unit": "count",
        "days": days,
        "generator": "data/generate.py (deterministic 64-bit LCG, seed 20261012)",
    }
    OUT.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    total = sum(d["pulse_counts"] for d in days)
    print("wrote", OUT)
    print("total pulses:", total)
    print("expected total @ 0.050 L/count:", total * 0.05)
    print("shipped total  @ 0.0472 L/count:", total * 0.0472)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
