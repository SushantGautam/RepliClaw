"""One-shot stronger-model probe for the D-V3-015 re-pilot decision.

Sends each candidate model a 2-message sequence that mimics the D-E
investigator JSON action protocol (the exact surface on which Qwen3.8-27B
produced `AgentProtocolError: malformed action outputs` in pilot #4).
Checks: reachability, usage reporting, strict-JSON action compliance, and
whether the model understands the tool_call/commit discriminator.

Read-only: no experiment artifacts, no ground truth, tiny token cost.
Output: docs/next_stage/data/model_probe_<ts>.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from repliclaw.benchmarks.agentrx.simula import (  # noqa: E402
    SimulaChatClient,
    SimulaChatConfig,
)

CANDIDATES = ["glm-5-2-fp8", "Borealis2-preview", "autoroute"]

SYSTEM = (
    "You are an SRE root-cause investigator for opaque distributed-system "
    "cases. You communicate ONLY via a single JSON object per turn. "
    "Two valid actions: "
    '{"action": "tool_call", "tool": "service_metrics", "args": {"service": "<name>"}} '
    'to fetch one service\'s metrics, or '
    '{"action": "commit", "ranking": ["<svc1>", "<svc2>", "<svc3>", "<svc4>", "<svc5>"], '
    '"confidence": <0-1>} '
    'to commit your final top-5 root-cause ranking. Output ONLY the JSON object, '
    "no prose, no markdown."
)

USER = (
    "Case: checkout latency spike detected at 09:00 UTC across zone us-east-1. "
    "Candidate services: adservice, cartservice, checkoutservice, "
    "currencyservice, emailservice, paymentservice. "
    "First action: fetch metrics for the most suspicious single service."
)


def probe(model: str, base_url: str, api_key: str) -> dict:
    client = SimulaChatClient(
        config=SimulaChatConfig(base_url=base_url, api_key=api_key, model=model),
        timeout=90.0,
    )
    t0 = time.monotonic()
    out: dict = {"model": model, "ok": False}
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": USER}],
            max_tokens=300,
            temperature=0.0,
        )
        content = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        out["ok"] = True
        out["wall_s"] = round(time.monotonic() - t0, 2)
        out["raw"] = content[:800]
        out["usage"] = {
            "prompt": getattr(usage, "prompt_tokens", None),
            "completion": getattr(usage, "completion_tokens", None),
            "total": getattr(usage, "total_tokens", None),
        }
        # protocol compliance
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            obj = json.loads(text)
            out["json_valid"] = True
            out["action"] = obj.get("action")
            out["protocol_ok"] = (
                obj.get("action") == "tool_call"
                and obj.get("tool") == "service_metrics"
                and isinstance(obj.get("args"), dict)
            )
        except json.JSONDecodeError as e:
            out["json_valid"] = False
            out["json_error"] = str(e)[:120]
            out["protocol_ok"] = False
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
        out["wall_s"] = round(time.monotonic() - t0, 2)
    return out


def main() -> int:
    base = os.environ.get("SIMULACHAT_BASE_URL", "").strip()
    key = os.environ.get("SIMULACHAT_API_KEY", "").strip()
    if not base or not key:
        print("provider env incomplete", file=sys.stderr)
        return 1
    results = [probe(m, base, key) for m in CANDIDATES]
    out_dir = Path(__file__).resolve().parents[1] / "docs" / "next_stage" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir / f"model_probe_{ts}.json"
    out.write_text(json.dumps({"probed_at": ts, "results": results}, indent=2))
    for r in results:
        print(json.dumps({k: r.get(k) for k in
                          ("model", "ok", "protocol_ok", "json_valid",
                           "action", "usage", "error", "wall_s")}))
    print(f"probe: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
