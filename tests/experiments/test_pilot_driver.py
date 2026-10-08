"""Offline tests for the G3 pilot driver (``scripts/pilot_run.py``).

Everything runs without LLM network: the driver's scripted
``FakeLLMClient`` drives both arms; the scorer path is checked both
end-to-end (``run --fake``) and by direct unit calls to
``service_level_success`` with known truth.

Cases that need the real frozen pilot data (``.artifacts/rcaeval/pilot``)
are skipped when that directory is absent — the mapping/plan tests still
require the registry's frozen roster (which is itself the contract).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pilot_run as pr  # noqa: E402

from repliclaw.experiments.v3.telemetry import (  # noqa: E402
    FROZEN_PILOT_IDS,
    service_level_success,
)

REAL_DATA = REPO_ROOT / ".artifacts" / "rcaeval" / "pilot"
DATA_PRESENT = REAL_DATA.is_dir() and any(REAL_DATA.iterdir())
needs_data = pytest.mark.skipif(not DATA_PRESENT, reason="pilot case data not on disk")


def _mk_index(tmp_path: Path, cases: list[tuple[str, str]]) -> Path:
    """Synthetic cases index (scorer side): (upstream_id, root_cause_service)."""
    df = pd.DataFrame(
        {"case": [c[0] for c in cases], "root_cause_service": [c[1] for c in cases]}
    )
    path = tmp_path / "cases_index.parquet"
    df.to_parquet(path, index=False)
    return path


def _run_main(tmp_path: Path, index_path: Path, *extra: str) -> int:
    out = tmp_path / "run"
    return pr.main([
        "run", "--round", "1", "--out", str(out), "--fake", "--max-cases", "1",
        "--cases-index", str(index_path), *extra,
    ])


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def test_plan_40_rows_deterministic_order_and_mapping() -> None:
    rows = pr.build_plan()
    assert len(rows) == 40
    # Deterministic order: case asc, seed asc, arm D-ET then C-EQ (the arm
    # order is mandated, not lexicographic: 'C-EQ-TELEM' < 'D-E-TELEM' as
    # strings).
    arm_rank = {"D-E-TELEM": 0, "C-EQ-TELEM": 1}
    order = [(r["case"], r["seed"], r["arm"]) for r in rows]
    assert order == sorted(order, key=lambda t: (t[0], t[1], arm_rank[t[2]]))
    cases = [r["case"] for r in rows]
    assert cases[0] == "RCA-P-01" and cases[-1] == "RCA-P-10"
    assert len(set(cases)) == 10
    # Opaque mapping derived from the registry contract (NOT hardcoded):
    # RCA-P-NN = the NNth id of the sorted frozen roster.
    expected_mapping = {f"RCA-P-{i:02d}": uid for i, uid in enumerate(sorted(FROZEN_PILOT_IDS), start=1)}
    for row in rows:
        assert set(row) == {"case", "seed", "arm", "round"}
        assert row["round"] == 1
        assert row["seed"] in (20261011, 20261012)
        assert row["arm"] in ("D-E-TELEM", "C-EQ-TELEM")
    for i, opaque in enumerate(sorted(expected_mapping), start=1):
        assert expected_mapping[opaque] == sorted(FROZEN_PILOT_IDS)[i - 1]
    # Per case block: seeds asc, arm D-ET then C-EQ.
    for case in expected_mapping:
        block = [
            (r["seed"], r["arm"]) for r in rows if r["case"] == case
        ]
        assert block == [
            (20261011, "D-E-TELEM"), (20261011, "C-EQ-TELEM"),
            (20261012, "D-E-TELEM"), (20261012, "C-EQ-TELEM"),
        ]


# ---------------------------------------------------------------------------
# canary (end-to-end offline, both arms, all 10 cases)
# ---------------------------------------------------------------------------


@needs_data
def test_canary_end_to_end_offline(tmp_path: Path) -> None:
    out = tmp_path / "canary"
    code = pr.main(["canary", "--data-root", str(REAL_DATA), "--out", str(out)])
    assert code == 0
    report = json.loads((out / "canary_report.json").read_text(encoding="utf-8"))
    checks = report["checks"]
    assert checks["both_arms_complete"]["pass"] is True
    assert checks["both_arms_complete"]["failures"] == {}
    assert checks["payload_parity"]["pass"] is True
    assert checks["scorer_path"]["pass"] is True
    assert checks["scorer_path"]["hit"] is True
    assert checks["scorer_path"]["miss"] is False
    assert checks["label_gate"]["pass"] is True
    assert checks["reset"]["pass"] is True
    assert checks["all_pass"] is True  # all_pass is recorded inside the checks map
    assert report["no_llm_network"] is True


# ---------------------------------------------------------------------------
# run --fake on 1 case: artifacts + scorer correctness
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """run --fake --max-cases 1 with a synthetic cases index; shared by the
    artifact and resume tests. True service for RCA-P-01: 'adservice'."""
    upstream0 = sorted(FROZEN_PILOT_IDS)[0]
    index = _mk_index(tmp_path, [(upstream0, "adservice")])
    monkeypatch.setattr(pr, "CASES_PARQUET_SHA256", hashlib.sha256(index.read_bytes()).hexdigest())
    out = tmp_path / "run"
    code = _run_main(tmp_path, index)
    # Deterministic outcome on the pinned data: the anomaly-suggested
    # ranking lands the true service in top-5, so all 4 runs are
    # all-seeds successes. Under the spec-verbatim denominators (I4.6:
    # sat over the full 10-case cohort, crash over 20 runs per arm),
    # 1/10 = 0.10 < 0.25 and 0/20 = 0.0 — NO stop may trip on a
    # single saturated case; the driver pauses (exit 0) for review.
    assert code == 0
    return out


def _one_case_run_dirs(out: Path) -> list[Path]:
    case = "RCA-P-01"
    return [
        out / "round1" / case / f"seed{s}" / arm
        for s in (20261011, 20261012)
        for arm in ("D-E-TELEM", "C-EQ-TELEM")
    ]


@needs_data
def test_run_fake_artifacts_and_score_schema(fake_run: Path) -> None:
    run_dirs = _one_case_run_dirs(fake_run)
    assert len(run_dirs) == 4
    for d in run_dirs:
        assert d.is_dir(), f"missing run dir {d}"
        status = json.loads((d / "status.json").read_text(encoding="utf-8"))
        assert status["status"] == "completed"
        for key in (
            "tokens", "wall_s", "tool_calls", "llm_calls", "submitted_ranking",
            "submitted_at", "model", "label", "arm", "case_id", "seed", "round",
            "started", "finished", "envelope", "case_sha256", "interface",
        ):
            assert key in status, f"status.json missing {key}"
        assert status["case_id"] == "RCA-P-01"
        assert len(status["submitted_ranking"]) == 5
        score = json.loads((d / "score.json").read_text(encoding="utf-8"))
        assert set(score) == {"hit", "true_service", "method", "scorer_sha"}
        assert isinstance(score["hit"], bool)
        assert score["true_service"] == "adservice"
        assert score["method"] == "rcaeval-official-service-acc5"
        assert len(score["scorer_sha"]) == 64
        # The scripted fake commits the top_anomalies-suggested ranking
        # (it cannot know the truth); the recorded hit is a real scorer
        # bool. On the pinned frozen data RCA-P-01's top anomaly is the
        # adservice metric, so a hit is expected — but the contract
        # under test is the bool + schema, verified hit/miss semantics
        # are covered by the direct scorer unit test below.
        assert score["hit"] is True  # pinned data: deterministic
        # Audit persistence.
        audit = json.loads((d / "audit_llm.json").read_text(encoding="utf-8"))
        assert any(s["agent_id"] in ("inv-a", "inv-b", "inv-c", "manager", "committee") for s in audit)
    # Ledger: exactly one line per run.
    ledger_lines = [
        json.loads(line) for line in (fake_run / "round1" / "ledger.jsonl").read_text().splitlines() if line.strip()
    ]
    assert len(ledger_lines) == 4
    for line in ledger_lines:
        assert set(line) >= {"run_path", "case", "seed", "arm", "status", "tokens", "wall_s", "hit"}
    # Case check written with the four stop-rule sections. On the pinned
    # data all 4 runs hit (1 case saturated) — but the denominators are
    # the FULL cohort (I4.6): sat = 1/10 = 0.10 < 0.25 and crash = 0/20,
    # so nothing trips after a single case. This regression pins the
    # live pilot #3 defect (stop-1/stop-2 firing at 1/1 and 2/2).
    case_check = json.loads((fake_run / "round1" / "RCA-P-01" / "case_check.json").read_text())
    for key in ("stop1_ssat", "stop2_crash", "stop3_tokens", "stop4_floor", "any_tripped"):
        assert key in case_check
    assert case_check["stop1_ssat"]["sat"]["D-E-TELEM"] == pytest.approx(0.10)
    assert case_check["stop1_ssat"]["sat"]["C-EQ-TELEM"] == pytest.approx(0.10)
    assert case_check["stop1_ssat"]["tripped"] is False
    assert case_check["stop2_crash"]["tripped"] is False
    assert case_check["any_tripped"] is False


def test_scorer_unit_hit_miss_and_boundary() -> None:
    # Direct scorer semantics with known truth (no driver involved).
    ranking = ["adservice", "cartservice", "checkoutservice", "currencyservice", "emailservice"]
    assert service_level_success(ranking, "adservice", k=5) is True
    assert service_level_success(ranking, "frontendsvc", k=5) is False
    # k=5 boundary: 6th-place true service is a miss.
    assert service_level_success(ranking + ["frontendsvc"], "frontendsvc", k=5) is False
    # Normalization: dashes/case are ignored.
    assert service_level_success(ranking, "Ad-Service", k=5) is True


def test_resolve_truth_scorer_section(tmp_path: Path) -> None:
    upstream0 = sorted(FROZEN_PILOT_IDS)[0]
    index = _mk_index(tmp_path, [(upstream0, "adservice")])
    df = pd.read_parquet(index)
    true_service, sha = pr.resolve_truth("RCA-P-01", df, "index-sha-x")
    assert true_service == "adservice"
    assert sha == "index-sha-x"


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


@needs_data
def test_resume_skips_completed_no_double_ledger(fake_run: Path, tmp_path: Path) -> None:
    # Same synthetic index as the fixture (same path/content -> same sha).
    index = _mk_index(tmp_path, [(sorted(FROZEN_PILOT_IDS)[0], "adservice")])
    before = (fake_run / "round1" / "ledger.jsonl").read_text().splitlines()
    code = _run_main(tmp_path, index, "--continue")
    assert code == pr.EXIT_ALL_DONE  # all planned cases complete
    after = (fake_run / "round1" / "ledger.jsonl").read_text().splitlines()
    assert after == before  # no double ledger line


# ---------------------------------------------------------------------------
# stop-rule math (synthetic ledger states)
# ---------------------------------------------------------------------------


def _rec(case: str, seed: int, arm: str, status: str = "completed",
         tokens: int = 10_000, hit: bool | None = None) -> pr.RunRecord:
    return pr.RunRecord(
        run_path=f"round1/{case}/seed{seed}/{arm}", case=case, seed=seed, arm=arm,
        status=status, tokens=tokens, wall_s=1.0, hit=hit,
    )


def test_stop_denominators_full_cohort_after_case_1() -> None:
    """I4.6 regression: after ONLY case 1 completes (all-seeds success on
    C-EQ; 2 aborted_budget on D-E), the live pilot #3 harness fired
    stop-1 at 1/1 and stop-2 at 2/2. The spec-verbatim denominators are
    the full cohort: sat = 1/10 = 0.10 (< 0.25, no trip) and
    crash = 2/20 = 0.10 (< 0.25, no trip).
    """
    runs = [
        _rec("RCA-P-01", 20261011, "D-E-TELEM", status="aborted_budget"),
        _rec("RCA-P-01", 20261012, "D-E-TELEM", status="aborted_budget"),
        _rec("RCA-P-01", 20261011, "C-EQ-TELEM", hit=True),
        _rec("RCA-P-01", 20261012, "C-EQ-TELEM", hit=True),
    ]
    checks = pr.evaluate_stop_rules(runs, cases_completed=1)
    assert checks["stop1_ssat"]["sat"]["C-EQ-TELEM"] == pytest.approx(0.10)
    assert checks["stop1_ssat"]["sat"]["D-E-TELEM"] == pytest.approx(0.0)
    assert checks["stop1_ssat"]["tripped"] is False
    assert checks["stop2_crash"]["rate"]["D-E-TELEM"] == pytest.approx(0.10)
    assert checks["stop2_crash"]["tripped"] is False
    assert checks["any_tripped"] is False


def test_stop1_ssat_trip_at_3_of_10() -> None:
    runs: list[pr.RunRecord] = []
    for case_no in range(1, 11):
        case = f"RCA-P-{case_no:02d}"
        for seed in (20261011, 20261012):
            runs += [_rec(case, seed, "D-E-TELEM", hit=case_no <= 3),
                     _rec(case, seed, "C-EQ-TELEM")]
    checks = pr.evaluate_stop_rules(runs, cases_completed=10)
    assert checks["stop1_ssat"]["sat"]["D-E-TELEM"] == pytest.approx(0.30)
    assert checks["stop1_ssat"]["sat"]["C-EQ-TELEM"] == pytest.approx(0.0)
    assert checks["stop1_ssat"]["tripped"] is True
    assert checks["any_tripped"] is True


def test_stop4_floor_trip_at_9_allzero_cases() -> None:
    runs = [
        _rec(f"RCA-P-{n:02d}", seed, arm) for n in range(1, 10)
        for seed in (20261011, 20261012) for arm in ("D-E-TELEM", "C-EQ-TELEM")
    ]  # 9 complete allzero cases + case 10 absent
    checks = pr.evaluate_stop_rules(runs, cases_completed=9)
    assert checks["stop4_floor"]["allzero_case_count"] == 9
    assert checks["stop4_floor"]["allzero_floor"] is True
    # Per-arm 2/20 conjunct not yet evaluable (only 18/20 recorded).
    assert checks["stop4_floor"]["run_success_floor"] == {"D-E-TELEM": False, "C-EQ-TELEM": False}
    assert checks["stop4_floor"]["tripped"] is True
    assert checks["any_tripped"] is True
    # 8 allzero cases is below the >= 9 trip (run-success floor not evaluable).
    short = runs[:-4]
    short_checks = pr.evaluate_stop_rules(short, cases_completed=8)
    assert short_checks["stop4_floor"]["allzero_case_count"] == 8
    assert short_checks["stop4_floor"]["tripped"] is False


def test_v32_amended_constants() -> None:
    # AMEND_V3_2 (approved D-V3-017): B1 150K shared envelope, B4 7.2M ceiling.
    assert pr.ROUND_TOKEN_CEILING == 7_200_000
    assert pr.MAX_TOKENS_PER_RUN == 150_000


def test_stop3_ceiling_preemptive() -> None:
    # V3.2: 150,000/run envelope (B1), 7,200,000 round ceiling (B4).
    # 46 runs x 150,000 = 6,900,000: next run still fits.
    def state(n: int) -> list[pr.RunRecord]:
        return [
            _rec(f"RCA-P-{(i % 10) + 1:02d}",
                 20261011 if i % 2 == 0 else 20261012,
                 "D-E-TELEM" if i % 2 == 0 else "C-EQ-TELEM", tokens=150_000)
            for i in range(n)
        ]

    runs = state(46)
    assert pr.cumulative_tokens(runs) == 6_900_000
    assert pr.ceiling_would_breach(runs) is False  # 6,900,000 + 150,000 <= 7,200,000
    runs = state(47)
    assert pr.cumulative_tokens(runs) == 7_050_000
    assert pr.ceiling_would_breach(runs) is False  # 7,050,000 + 150,000 == ceiling: not strictly over
    runs = state(48)
    assert pr.cumulative_tokens(runs) == 7_200_000
    assert pr.ceiling_would_breach(runs) is True  # 7,200,000 + 150,000 > 7,200,000
    checks = pr.evaluate_stop_rules(runs, cases_completed=0)
    assert checks["stop3_tokens"]["next_run_would_breach"] is True
    assert checks["stop3_tokens"]["tripped"] is False  # cumulative itself is under


def test_stop2_crash_trip_at_6_of_20() -> None:
    runs = []
    for seed in (20261011, 20261012):
        for n in range(1, 11):
            case = f"RCA-P-{n:02d}"
            status = "crashed" if n <= 3 else "completed"  # 6 crashes in 20 runs
            runs.append(_rec(case, seed, "D-E-TELEM", status=status))
            runs.append(_rec(case, seed, "C-EQ-TELEM", hit=True))
    checks = pr.evaluate_stop_rules(runs, cases_completed=10)
    assert checks["stop2_crash"]["rate"]["D-E-TELEM"] == pytest.approx(0.30)
    assert checks["stop2_crash"]["tripped"] is True
    # aborted_budget counts as a crash: flip one *completed* D-E run.
    completed_de = next(r for r in runs if r.arm == "D-E-TELEM" and r.status == "completed")
    completed_de.status = "aborted_budget"
    crashes = pr.crash_rate_per_arm(runs)["D-E-TELEM"]
    assert crashes == pytest.approx(7 / 20)
    assert crashes > pr.CRASH_RATIO_MAX


def test_refusals_manifest_and_roster(tmp_path: Path) -> None:
    assert pr.check_frozen_ids_and_manifest(tmp_path / "missing.json") == pr.EXIT_MANIFEST_MISSING
    bad = tmp_path / "manifest.json"
    bad.write_text(json.dumps({"sorted_ids_sha256": "0" * 64}), encoding="utf-8")
    assert pr.check_frozen_ids_and_manifest(bad) == pr.EXIT_ROSTER_MISMATCH
    good = tmp_path / "manifest2.json"
    good.write_text(json.dumps({"sorted_ids_sha256": pr.FROZEN_PILOT_SHA256}), encoding="utf-8")
    assert pr.check_frozen_ids_and_manifest(good) == pr.EXIT_OK_PAUSE


# ---------------------------------------------------------------------------
# env refusal: no --fake and SIMULACHAT env incomplete -> nonzero, no network
# ---------------------------------------------------------------------------


@needs_data
def test_run_refuses_without_fake_and_env(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    for var in ("SIMULACHAT_BASE_URL", "SIMULACHAT_API_KEY", "CUSTOM_SIMULACHAT_KEY", "SIMULACHAT_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert pr.provider_env_complete() is False
    code = pr.main(["run", "--round", "1", "--out", str(Path.cwd() / "artifacts" / "dev" / "never"),
                    "--max-cases", "1"])
    err = capsys.readouterr().err
    assert code != 0
    assert "provider env incomplete" in err


def test_report_backend_echo_provenance(tmp_path, monkeypatch, capsys):
    """Science-judge N3: the report must surface per-run backend_model echoes
    with a within-run cross-agent consistency check."""
    from scripts import pilot_report

    round_dir = tmp_path / "round3"
    round_dir.mkdir()
    # Minimal ledger so load_runs() is non-empty.
    record = {
        "run_path": "round3/RCA-P-01/seed20261011/D-E-TELEM", "case": "RCA-P-01",
        "seed": 20261011, "arm": "D-E-TELEM", "status": "completed",
        "tokens": 100, "wall_s": 1.0, "hit": None,
    }
    (round_dir / "ledger.jsonl").write_text(json.dumps(record) + "\n")
    (round_dir / "case_check.json").write_text("{}")

    def _status(case, seed, arm, echoes):
        d = round_dir / case / f"seed{seed}" / arm
        d.mkdir(parents=True)
        (d / "status.json").write_text(json.dumps({
            "status": "completed", "tokens": 100, "model": "default",
            "label": "L", "arm": arm, "case_id": case, "seed": seed,
            "backend_model": echoes,
        }))

    # Consistent echoes (incl. a None for a never-scheduled agent).
    _status("RCA-P-01", 20261011, "D-E-TELEM", ["Qwen3.8-27B", "Qwen3.8-27B", None])
    # Inconsistent echoes across agents -> must be flagged.
    _status("RCA-P-01", 20261012, "C-EQ-TELEM", ["Qwen3.8-27B", "OtherModel", None])

    monkeypatch.setattr(
        "sys.argv", ["pilot_report.py", "--round-dir", str(round_dir),
                     "--out", str(tmp_path / "rep.json")]
    )
    pilot_report.main()
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["backend_echo_inconsistent_runs"] == [
        "C-EQ-TELEM/seed20261012/RCA-P-01"
    ]
    de = rep["backend_model_echoes"]["D-E-TELEM/seed20261011/RCA-P-01"]
    assert de["echo_consistent"] is True
    assert de["n_agents_echoed"] == 2
    assert de["n_agents_total"] == 3


def test_simula_client_adapter_chat_create_surface(monkeypatch):
    """build_simula_client must expose client.chat.create (session surface)."""
    import sys
    import types

    from scripts import pilot_run

    class _FakeCompletions:
        def create(self, **kw):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="{}", role="assistant"))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            )

    class _FakeChat:
        def __init__(self):
            self.completions = _FakeCompletions()

    class _FakeSimulaChatClient:
        def __init__(self, config=None, timeout=60.0):
            self.chat = _FakeChat()

    fake_mod = types.ModuleType("repliclaw.benchmarks.agentrx.simula")
    fake_mod.DEFAULT_MODEL = "default"
    fake_mod.ENV_BASE_URL = "SIMULACHAT_BASE_URL"
    fake_mod.SimulaChatClient = _FakeSimulaChatClient
    fake_mod.SimulaChatConfig = lambda **kw: types.SimpleNamespace(**kw)
    monkeypatch.setitem(sys.modules, "repliclaw.benchmarks.agentrx.simula", fake_mod)
    monkeypatch.setenv("SIMULACHAT_BASE_URL", "https://example.invalid/api/v1")
    monkeypatch.setenv("SIMULACHAT_API_KEY", "k" * 30)

    client = pilot_run.build_simula_client()
    resp = client.chat.create(model="default", messages=[{"role": "user", "content": "x"}])
    assert resp.usage.total_tokens == 2
    assert not hasattr(client.chat, "completions")  # adapter surface, not raw client


# ---------------------------------------------------------------------------
# pilot_parallel (AMEND_V3_2) — offline
# ---------------------------------------------------------------------------


def _mk_parallel_index(tmp_path: Path) -> Path:
    """Synthetic cases index covering all 10 frozen pilot ids (truth
    'adservice' for the first id; arbitrary service names elsewhere —
    the scorer only needs the column to exist)."""
    rows = [
        (upstream, "adservice" if i == 0 else f"svc{i:02d}")
        for i, upstream in enumerate(sorted(FROZEN_PILOT_IDS))
    ]
    return _mk_index(tmp_path, rows)


@needs_data
def test_parallel_fake_bounded_round_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """pilot_parallel.py run --fake --max-cases 2: 8 runs recorded, V3.2
    provenance stamped, no stop trip (sat 2/10 = 0.2 < 0.25)."""
    import pilot_parallel as pp

    index = _mk_parallel_index(tmp_path)
    monkeypatch.setattr(pr, "CASES_PARQUET_SHA256",
                        hashlib.sha256(index.read_bytes()).hexdigest())
    out = tmp_path / "par"
    code = pp.main([
        "run", "--round", "1", "--out", str(out), "--fake", "--concurrency", "4",
        "--max-cases", "2", "--cases-index", str(index),
    ])
    assert code == 0

    round_dir = out / "round1"
    meta = json.loads((round_dir / "parallel_meta.json").read_text(encoding="utf-8"))
    assert meta["v32_constants"] == {
        "max_tokens_per_run": 150_000,
        "max_tool_calls": 48,
        "round_token_ceiling": 7_200_000,
        "prompt_volume_band": [0.6, 1.40],
    }
    assert meta["concurrency"] == 4
    assert meta["max_cases"] == 2
    assert meta["driver_sha256"] == pp._driver_sha256()

    ledger_lines = [
        json.loads(line) for line in
        (round_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert len(ledger_lines) == 8
    assert all(line["status"] == "completed" for line in ledger_lines)
    assert {(line["case"], line["seed"], line["arm"]) for line in ledger_lines} == {
        (case, seed, arm) for case in ("RCA-P-01", "RCA-P-02")
        for seed in (20261011, 20261012)
        for arm in ("D-E-TELEM", "C-EQ-TELEM")
    }

    # Every status.json carries the parallel provenance stamp.
    status_paths = sorted(round_dir.glob("*/*/*/status.json"))
    assert len(status_paths) == 8
    for sp in status_paths:
        obj = json.loads(sp.read_text(encoding="utf-8"))
        assert obj["parallel"]["driver_sha256"] == meta["driver_sha256"]
        assert obj["parallel"]["concurrency"] == 4
        assert obj["envelope"]["max_tokens"] == 150_000  # V3.2 B1 in per-run status

    # Per-case checks written for both cases; no trip at 2/10 saturation.
    case_checks = sorted(round_dir.glob("*/case_check.json"))
    assert len(case_checks) == 2
    for cc in case_checks:
        obj = json.loads(cc.read_text(encoding="utf-8"))
        assert obj["any_tripped"] is False


@needs_data
def test_parallel_fake_full_round_trips_stop1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Full 10-case fake round: the scripted fake saturates D-E on
    adservice-truth cases, so stop-1 (sat >= 0.25) trips mid-round on
    those synthetic indices; with other truth mixes stop-4 (C-EQ
    run-success floor) can trip first. The load-bearing invariants are
    the parallel driver's TRIP PATH itself: workers stop claiming,
    STOP.json is written, exit 10, and every recorded run is 'completed'
    (no crashes from the concurrency itself)."""
    import pilot_parallel as pp

    index = _mk_parallel_index(tmp_path)
    monkeypatch.setattr(pr, "CASES_PARQUET_SHA256",
                        hashlib.sha256(index.read_bytes()).hexdigest())
    out = tmp_path / "par"
    code = pp.main([
        "run", "--round", "1", "--out", str(out), "--fake", "--concurrency", "4",
        "--cases-index", str(index),
    ])
    assert code == 10  # EXIT_STOP_TRIP

    round_dir = out / "round1"
    stop = json.loads((round_dir / "STOP.json").read_text(encoding="utf-8"))
    # With the synthetic truth, either stop-1 (fake saturation on
    # adservice-truth cases) or stop-4 (C-EQ run-success floor under the
    # non-adservice synthetic truths) legitimately trips first; the
    # invariants pinned here are the TRIP PATH (STOP.json + exit 10) and
    # that the concurrency itself introduces no run-level failures.
    assert stop["tripped"]
    for name in stop["tripped"]:
        assert stop["checks"][name]["tripped"] is True

    ledger_lines = [
        json.loads(line) for line in
        (round_dir / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    # The 4 concurrently-claimed cases finish (16 runs), the trip halts
    # further claims; in-flight cases may finish, so >= 16, all completed.
    assert len(ledger_lines) >= 16
    assert all(line["status"] == "completed" for line in ledger_lines)


@needs_data
def test_parallel_refuses_partial_round_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A round dir containing a crash-without-ledger (or ledger-without-
    status) state is refused, not resumed: operator clears and relaunches."""
    import pilot_parallel as pp

    index = _mk_parallel_index(tmp_path)
    monkeypatch.setattr(pr, "CASES_PARQUET_SHA256",
                        hashlib.sha256(index.read_bytes()).hexdigest())
    out = tmp_path / "par"
    round_dir = out / "round1"
    # Fabricate a ledger line whose status.json is absent.
    round_dir.mkdir(parents=True)
    with open(round_dir / "ledger.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "run_path": "round1/RCA-P-01/seed20261011/D-E-TELEM",
            "case": "RCA-P-01", "seed": 20261011, "arm": "D-E-TELEM",
            "status": "completed", "tokens": 1000, "wall_s": 1.0, "hit": True,
        }) + "\n")
    code = pp.main([
        "run", "--round", "1", "--out", str(out), "--fake", "--concurrency", "2",
        "--cases-index", str(index),
    ])
    assert code == 1  # EXIT_REFUSED


# ---------------------------------------------------------------------------
# Post-round-4 defect regressions (science-judge-r4 Q1; code-judge-r4)
# ---------------------------------------------------------------------------
def test_stop1_one_seed_success_not_saturated() -> None:
    """Round-4 regression: a case where the arm succeeded on only 1 of 2
    seeds (other seed not yet ledgered, e.g. a stop-tripped round) must NOT
    count as saturated. Pre-fix, 3 such one-seed C-EQ successes gave sat
    3/10 = 0.30 and a false stop-1 co-trip (spec-correct sat = 0.0)."""
    runs: list[pr.RunRecord] = []
    # 3 cases: C-EQ hit on seed 20261011 only (seed 20261012 absent),
    # D-E aborted on that seed too.
    for case_no in range(1, 4):
        case = f"RCA-P-{case_no:02d}"
        runs += [_rec(case, 20261011, "C-EQ-TELEM", hit=True),
                 _rec(case, 20261011, "D-E-TELEM", status="aborted_budget")]
    checks = pr.evaluate_stop_rules(runs, cases_completed=3)
    assert checks["stop1_ssat"]["sat"]["C-EQ-TELEM"] == pytest.approx(0.0)
    assert checks["stop1_ssat"]["sat"]["D-E-TELEM"] == pytest.approx(0.0)
    assert checks["stop1_ssat"]["tripped"] is False


def test_stop1_two_seed_success_still_saturated() -> None:
    """Control: full 2-seed success still saturates (3/10 trips stop-1)."""
    runs = [
        _rec(f"RCA-P-{n:02d}", seed, "C-EQ-TELEM", hit=True)
        for n in range(1, 4) for seed in (20261011, 20261012)
    ]
    checks = pr.evaluate_stop_rules(runs, cases_completed=3)
    assert checks["stop1_ssat"]["sat"]["C-EQ-TELEM"] == pytest.approx(0.30)
    assert checks["stop1_ssat"]["tripped"] is True


def test_seq_driver_refuses_stop_tripped_round(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Code-judge-r4 SHOULD-FIX: a round dir containing STOP.json is closed
    and must be refused by the sequential driver (no relaunch / --continue)."""
    import argparse

    out = tmp_path / "run"
    round_dir = out / "round7"
    round_dir.mkdir(parents=True)
    (round_dir / "STOP.json").write_text('{"tripped": ["stop2_crash"]}', encoding="utf-8")
    args = argparse.Namespace(
        round_no=7, out=str(out), max_cases=None, label="t",
        autonomous=True, continue_=True, cases_index=pr.DEFAULT_CASES_INDEX,
    )
    monkeypatch.setattr(pr, "provider_env_complete", lambda: True)
    monkeypatch.setattr(pr, "build_simula_client", pr.build_fake_client)
    assert pr.cmd_run(args) == pr.EXIT_STOP_TRIP


def test_parallel_driver_refuses_stop_tripped_round(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Code-judge-r4 SHOULD-FIX (parallel surface): STOP.json closes the
    round dir for the parallel driver as well (pre-fix the refusal was
    incidental, via non-completed status.json files)."""
    import argparse

    out = tmp_path / "run"
    round_dir = out / "round8"
    round_dir.mkdir(parents=True)
    (round_dir / "STOP.json").write_text('{"tripped": ["stop2_crash"]}', encoding="utf-8")
    args = argparse.Namespace(
        round_no=8, out=str(out), concurrency=2, fake=True, max_cases=None,
        no_index=True, cases_index=None, label="t",
    )
    import pilot_parallel as pp
    monkeypatch.setattr(pp.pr, "check_frozen_ids_and_manifest", lambda _p: 0)
    assert pp.cmd_run(args) == pp.EXIT_STOP_TRIP
