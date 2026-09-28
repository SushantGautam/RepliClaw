"""LLM client + investigator backends.

Two backends behind one interface:
- `LLMInvestigator` — calls an OpenAI-compatible endpoint (default: the
  verified SimulaChat Open WebUI). Tracks real token usage for AC11.
- `DeterministicInvestigator` — offline, hermetic, per-role "lens" over the
  claim's bundled data. Used by the test suite so it runs with no network.

Config (env or explicit):
- REPLICLAW_LLM_BASE_URL   (default https://simulachat.sushant.pp.ua/api/v1)
- REPLICLAW_LLM_API_KEY    (default $CUSTOM_SIMULACHAT_KEY)
- REPLICLAW_LLM_MODEL      (default "default")
- REPLICLAW_LLM_MAX_CALLS  (per-run budget guard)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import InvestigatorConfig, ResourceUsage

DEFAULT_BASE_URL = "https://simulachat.sushant.pp.ua/api/v1"
DEFAULT_MODEL = "default"


@dataclass
class LLMConfig:
    base_url: str = field(
        default_factory=lambda: os.environ.get("REPLICLAW_LLM_BASE_URL", DEFAULT_BASE_URL)
    )
    api_key: str = field(
        default_factory=lambda: os.environ.get("REPLICLAW_LLM_API_KEY")
        or os.environ.get("CUSTOM_SIMULACHAT_KEY")
        or ""
    )
    model: str = field(default_factory=lambda: os.environ.get("REPLICLAW_LLM_MODEL", DEFAULT_MODEL))
    max_calls: int = field(default_factory=lambda: int(os.environ.get("REPLICLAW_LLM_MAX_CALLS", "64")))
    max_tokens: int = int(os.environ.get("REPLICLAW_LLM_MAX_TOKENS", "1024"))
    temperature: float = float(os.environ.get("REPLICLAW_LLM_TEMPERATURE", "0.2"))
    timeout: float = float(os.environ.get("REPLICLAW_LLM_TIMEOUT", "120"))

    @property
    def available(self) -> bool:
        return bool(self.api_key)


class BudgetExceeded(Exception):
    pass


class LLMClient:
    """Thin OpenAI-compatible client with usage accounting."""

    def __init__(self, cfg: Optional[LLMConfig] = None):
        self.cfg = cfg or LLMConfig()
        self.usage = ResourceUsage()
        self._calls = 0
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.cfg.available:
            raise RuntimeError(
                "No LLM API key configured. Set REPLICLAW_LLM_API_KEY "
                "(or CUSTOM_SIMULACHAT_KEY) or use backend='deterministic'."
            )
        from openai import OpenAI

        self._client = OpenAI(
            base_url=self.cfg.base_url,
            api_key=self.cfg.api_key,
            timeout=self.cfg.timeout,
        )
        return self._client

    def chat(
        self,
        prompt: str,
        system: str = "You are a careful, quantitative scientific investigator.",
        max_tokens: Optional[int] = None,
    ) -> str:
        if self._calls >= self.cfg.max_calls:
            raise BudgetExceeded(f"exceeded LLM budget ({self.cfg.max_calls} calls)")
        client = self._ensure_client()
        self._calls += 1
        resp = client.chat.completions.create(
            model=self.cfg.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            max_tokens=max_tokens or self.cfg.max_tokens,
            temperature=self.cfg.temperature,
        )
        u = getattr(resp, "usage", None)
        if u is not None:
            self.usage.prompt_tokens += int(getattr(u, "prompt_tokens", 0) or 0)
            self.usage.completion_tokens += int(getattr(u, "completion_tokens", 0) or 0)
            self.usage.total_tokens = self.usage.prompt_tokens + self.usage.completion_tokens
        self.usage.llm_calls += 1
        return resp.choices[0].message.content or ""

    def chat_json(self, prompt: str, system: Optional[str] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        raw = self.chat(
            prompt,
            system=system or (
                "You are a careful, quantitative scientific investigator. "
                "Return ONLY a valid JSON object, no markdown, no commentary."
            ),
            max_tokens=max_tokens,
        )
        return _extract_json(raw)


def _extract_json(raw: str) -> Dict[str, Any]:
    """Robustly pull the first JSON object out of a model response."""
    text = (raw or "").strip()
    # Strip code fences.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    # Find first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object in model output: {raw[:200]!r}")
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Try a lenient repair: strip trailing commas.
        import re

        repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
        return json.loads(repaired)


# ---------------------------------------------------------------------------
# Investigators
# ---------------------------------------------------------------------------
FINDING_SCHEMA = {
    "conclusion": "supported | refuted | uncertain",
    "statement": "one-sentence verdict on the claim",
    "plan": "the analysis/experiment you performed or would perform",
    "evidence": "object of quantitative results (test, effect size, p-value, CI, ...)",
    "confidence": "number 0..1",
    "executable": "true if you ran actual computation, else false",
}


class Investigator:
    def __init__(self, config: InvestigatorConfig):
        self.config = config

    def run(self, context) -> Dict[str, Any]:  # pragma: no cover - interface
        raise NotImplementedError

    def name(self) -> str:
        return self.config.agent_id


class LLMInvestigator(Investigator):
    def __init__(self, config: InvestigatorConfig, client: LLMClient):
        super().__init__(config)
        self.client = client

    def run(self, context) -> Dict[str, Any]:
        prompt = context.to_prompt_block(revealed=False)
        prompt += (
            "\n\n# OUTPUT\nInvestigate the claim independently. Do NOT assume any "
            "other investigator's result. Return a JSON object with exactly these keys:\n"
            + json.dumps(FINDING_SCHEMA, indent=2)
            + "\nBe quantitative. If the bundled data is insufficient or misleading, say so."
        )
        finding = self.client.chat_json(prompt)
        # Normalize.
        finding.setdefault("conclusion", "uncertain")
        finding.setdefault("statement", "")
        finding.setdefault("plan", "")
        finding.setdefault("evidence", {})
        try:
            finding["confidence"] = float(finding.get("confidence", 0.5))
        except (TypeError, ValueError):
            finding["confidence"] = 0.5
        finding["executable"] = bool(finding.get("executable", False))
        finding["agent"] = self.config.agent_id
        finding["role"] = self.config.role.value
        finding["model"] = self.client.cfg.model
        return finding


class DeterministicInvestigator(Investigator):
    """Offline, hermetic investigator.

    Applies a per-role statistical "lens" to the claim's bundled data
    (`claim.data`). Different roles use different methods so that, on a
    seeded-fault claim, they can genuinely disagree — enabling the
    disagreement → follow-up → verdict path in tests without a network.
    """

    def run(self, context) -> Dict[str, Any]:
        data = context.claim.data or {}
        role = self.config.role.value
        finding = self._analyze(role, data, context.claim)
        finding["agent"] = self.config.agent_id
        finding["role"] = role
        finding["model"] = "deterministic"
        finding["executable"] = True  # performs real computation on bundled data
        return finding

    def _analyze(self, role: str, data: Dict[str, Any], claim) -> Dict[str, Any]:
        # The canonical controlled fixture shape (see tests/fixtures/):
        #   data = {
        #     "n": int, "mean_treat": float, "mean_ctrl": float,
        #     "sd_treat": float, "sd_ctrl": float, "alpha": float,
        #     "baseline_rr": float,  # published risk ratio to verify
        #     "events_treat": int, "events_ctrl": int,
        #     "tot_treat": int, "tot_ctrl": int,
        #     "fault": {...}  # optional seeded-fault metadata (visible to all)
        #   }
        try:
            return self._two_arm_analysis(role, data, claim)
        except (KeyError, TypeError, ZeroDivisionError, ValueError):
            return {
                "conclusion": "uncertain",
                "statement": "insufficient structured data to compute a test",
                "plan": "recompute primary endpoint from raw events",
                "evidence": {"error": "insufficient data"},
                "confidence": 0.2,
            }

    def _two_arm_analysis(self, role: str, data: Dict[str, Any], claim) -> Dict[str, Any]:
        n = data.get("n")
        alpha = float(data.get("alpha", 0.05))
        if role == "statistician":
            # Independent two-sample t-test on means.
            mt, mc = float(data["mean_treat"]), float(data["mean_ctrl"])
            st, sc = float(data["sd_treat"]), float(data["sd_ctrl"])
            from math import sqrt

            se = sqrt(st * st / n + sc * sc / n)
            t = (mt - mc) / se if se else 0.0
            # two-sided p via normal approx (adequate for large n fixture)
            from math import erf, sqrt

            p = 2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2))))
            sig = p < alpha
            rr = _risk_ratio(data)
            return {
                "conclusion": "supported" if sig else "uncertain",
                "statement": f"two-sample t-test: t={t:.2f}, p={p:.4f} (alpha={alpha})",
                "plan": "independent two-sample t-test on bundled per-arm means",
                "evidence": {"t": round(t, 3), "p": round(p, 5), "significant": sig,
                              "risk_ratio_observed": rr},
                "confidence": min(0.95, 0.5 + 0.4 * abs(sig)),
            }
        if role == "falsifier":
            # Attack: verify the published RR against the raw event counts and
            # check whether the CI excludes 1. A seeded 'wrong_stat_test' or
            # 'leakage' fault will push the naive reading off the raw events.
            rr = _risk_ratio(data)
            baseline = float(data.get("baseline_rr", 0.0)) or None
            has_raw = None not in (
                data.get("events_treat"), data.get("tot_treat"),
                data.get("events_ctrl"), data.get("tot_ctrl"),
            )
            if not has_raw:
                # No raw events to recompute from: this lens cannot adjudicate.
                return {
                    "conclusion": "uncertain",
                    "statement": "no raw event counts bundled; cannot falsify from raw data",
                    "plan": "recompute RR and CI from raw event counts",
                    "evidence": {"error": "no raw events"},
                    "confidence": 0.2,
                }
            lo, hi = _rr_ci(data)
            # Falsifier flags discrepancy if published RR is not within
            # the confidence interval recomputed from raw events.
            mismatch = baseline is not None and not (lo <= baseline <= hi)
            excludes_one = hi < 1.0 or lo > 1.0
            return {
                "conclusion": "refuted" if (mismatch or not excludes_one) else "supported",
                "statement": (
                    f"published RR={baseline} vs raw-event RR={rr:.3f} "
                    f"(95% CI [{lo:.3f},{hi:.3f}]); "
                    + ("CI excludes 1 → effect real" if excludes_one else "CI includes 1 → effect not established")
                ),
                "plan": "recompute RR and CI from raw event counts; compare to published figure",
                "evidence": {"rr_published": baseline, "rr_raw": rr,
                              "ci": [round(lo, 3), round(hi, 3)],
                              "ci_excludes_one": excludes_one, "mismatch": mismatch},
                "confidence": 0.7 if mismatch else 0.8,
            }
        # default analyst: effect size + simple significance on difference
        mt, mc = float(data["mean_treat"]), float(data["mean_ctrl"])
        st, sc = float(data["sd_treat"]), float(data["sd_ctrl"])
        from math import sqrt

        d = (mt - mc) / (sqrt(st * st + sc * sc) / 2 + 1e-9)
        sig = abs(d) >= 0.5  # medium effect threshold
        return {
            "conclusion": "supported" if sig else "uncertain",
            "statement": f"standardized effect size d={d:.2f}",
            "plan": "pooled effect size from bundled per-arm stats",
            "evidence": {"effect_size": round(d, 3), "significant": sig},
            "confidence": 0.6,
        }


def _risk_ratio(data: Dict[str, Any]) -> float:
    et, tt = data.get("events_treat"), data.get("tot_treat")
    ec, tc = data.get("events_ctrl"), data.get("tot_ctrl")
    if None in (et, tt, ec, tc) or tt == 0 or tc == 0:
        return float(data.get("baseline_rr", 0.0) or 0.0)
    return (et / tt) / (ec / tc)


def _rr_ci(data: Dict[str, Any]):
    et, tt = data.get("events_treat", 0), data.get("tot_treat", 1)
    ec, tc = data.get("events_ctrl", 0), data.get("tot_ctrl", 1)
    if tt == 0 or tc == 0 or et == 0 or ec == 0:
        return (0.5, 2.0)
    from math import exp, log, sqrt

    rr = (et / tt) / (ec / tc)
    se = sqrt(1 / et - 1 / tt + 1 / ec - 1 / tc)
    lo = exp(log(rr) - 1.96 * se)
    hi = exp(log(rr) + 1.96 * se)
    return (lo, hi)
