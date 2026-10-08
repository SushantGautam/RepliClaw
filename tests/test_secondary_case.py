"""P06 second scientific case: Tox21 AR-agonist directed functionalization.

Contract tests (ticket P06 "Red tests to write FIRST" + mission acceptance
criteria):

  1. test_arms_discriminate      -- the four arms give DISTINCT observed mean
                                    logP shifts, direction-consistent
                                    (baseline 0, OH < 0 < Me < Cl)
  2. test_determinism            -- same seed -> byte-identical arm artifacts
                                    across two fresh run dirs
  3. test_oracle_not_leaked      -- the arm source never references the sealed
                                    ground-truth file; its literals do not
                                    appear in any canonical artifact; the
                                    oracle file is not importable/visible to
                                    the arm
  4. test_judge_is_sole_reader   -- ``judge.py`` is the only module that opens
                                    the ground-truth file
  5. test_single_factor_at_a_time-- each arm's effective config differs from
                                    baseline in exactly the one intervention
                                    factor (functionalization/element)
  6. test_tamper_detection       -- flipping one byte of a stored artifact
                                    makes ``replay`` reject the run
  7. test_canonical_artifacts    -- the committed canonical run exists, is
                                    replay-genuine, and pins the engine +
                                    per-arm artifact hashes
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from repliclaw.counterfactual.cases import _base
from repliclaw.counterfactual.cases.tox21_ar_agonist import Tox21ArAgonistCase, load_case

pytest.importorskip("rdkit", reason="RDKit is a lazy dependency of the Tox21 P06 case")

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = REPO_ROOT / "artifacts" / "science" / "p06-hero-canonical"
CASE_DIR = REPO_ROOT / "src" / "repliclaw" / "counterfactual" / "cases" / "tox21_ar_agonist"
ORACLE_FILE = CASE_DIR / "oracle" / "oracle.json"
BASELINE = "I0_baseline"
ARMS = [BASELINE, "I1_OH", "I2_Cl", "I3_Me"]


@pytest.fixture(scope="module")
def case() -> Tox21ArAgonistCase:
    return load_case()


@pytest.fixture(scope="module")
def canon(tmp_path_factory) -> Path:
    """One module-scoped canonical run in a temp dir (avoids re-running RDKit)."""
    out = tmp_path_factory.mktemp("p06_canon")
    _base.run_canonical(load_case(), out, seed=0)
    return out


def _arm_files_bytes(root: Path, arm_id: str) -> dict[str, bytes]:
    arm_dir = Path(root) / "interventions" / arm_id
    return {name: (arm_dir / name).read_bytes() for name in _base.ARM_FILES}


def _oracle_literals() -> list[str]:
    """Distinctive string literals unique to the sealed ground truth (to grep
    for leakage). We deliberately use the descriptive strings (not the numeric
    mean deltas) because a PASSING arm's judge artifact legitimately records
    the measured value, which equals the expected value on success.
    """
    oracle = json.loads(ORACLE_FILE.read_text(encoding="utf-8"))
    return [oracle["true_cause"], oracle["hypothesis"], oracle["hypothesis_statement"]]


# 1 --------------------------------------------------------------------------
def test_arms_discriminate(canon: Path) -> None:
    """Observed per-arm mean logP shifts are pairwise distinct AND direction
    consistent (hydroxylation lowers logP; Cl > Me raises it)."""
    case = load_case()
    means = {arm: float(_base.run_case(case, arm, seed=0).target_output["mean_delta_logp"]) for arm in ARMS}
    # Pairwise distinct (the core counterfactual: arms are NOT relabelled copies).
    vals = list(means.values())
    assert len(set(vals)) == len(vals), f"arms did not discriminate: {means}"
    # Direction consistency of the OBSERVED values.
    assert means[BASELINE] == pytest.approx(0.0, abs=1e-9)
    assert means["I1_OH"] < 0.0 < means["I3_Me"] < means["I2_Cl"], f"sign/order wrong: {means}"
    # Each arm was scored within the ground-truth tolerance by the judge.
    for arm in ARMS:
        judgment = json.loads((canon / "interventions" / arm / "judgment.json").read_text())
        assert judgment["within_tolerance"] is True, f"{arm} failed to match its expected shift"
        assert judgment["severity"] == "pass"


# 2 --------------------------------------------------------------------------
def test_determinism(tmp_path: Path) -> None:
    """Same seed -> byte-identical persisted arm artifacts in two fresh dirs."""
    case = load_case()
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    _base.run_canonical(case, out_a, seed=0)
    _base.run_canonical(case, out_b, seed=0)
    for arm in ARMS:
        fa, fb = _arm_files_bytes(out_a, arm), _arm_files_bytes(out_b, arm)
        assert set(fa) == set(fb)
        for name in _base.ARM_FILES:
            assert fa[name] == fb[name], f"{arm}/{name} not byte-identical across runs"
        # hash files agree too
        ha = (out_a / "interventions" / arm / "hashes.json").read_bytes()
        hb = (out_b / "interventions" / arm / "hashes.json").read_bytes()
        assert ha == hb, f"{arm}/hashes.json not byte-identical"


# 3 --------------------------------------------------------------------------
def test_oracle_not_leaked(canon: Path) -> None:
    """Sealed ground-truth literals must not appear in any arm source or any
    canonical artifact; the arm module never references the oracle file."""
    assert ORACLE_FILE.exists(), "sealed ground truth must exist (it is the scoring key)"
    # (a) The arm source file must not reference the oracle file or its literal
    #     values.
    arm_src = (CASE_DIR / "case.py").read_text(encoding="utf-8")
    assert "oracle.json" not in arm_src, "arm case.py references the oracle file"
    for lit in _oracle_literals():
        assert lit not in arm_src, f"oracle literal {lit!r} leaked into arm case.py"
    # (b) No oracle literal appears anywhere in the canonical artifact tree.
    scanned = 0
    for p in canon.rglob("*"):
        if p.is_file():
            scanned += 1
            text = p.read_text(errors="ignore")
            for lit in _oracle_literals():
                assert lit not in text, f"oracle literal {lit!r} leaked into {p}"
    assert scanned > 0, "canonical artifact tree is empty"
    # (c) The arm-side runtime modules (the code measure_arm/run_case execute)
    #     never reference the ground-truth file. Only judge.py (and the
    #     oracle/ ground-truth side) do.
    assert ORACLE_FILE.is_file()
    arm_side = ["__init__.py", "__main__.py", "case.py"]
    for name in arm_side:
        src = (CASE_DIR / name).read_text(encoding="utf-8")
        assert "oracle.json" not in src, f"arm-side module {name} references the oracle file"


# 4 --------------------------------------------------------------------------
def test_judge_is_sole_reader() -> None:
    """Only ``judge.py`` opens the ground-truth file; no arm module does."""
    case_src = (CASE_DIR / "case.py").read_text(encoding="utf-8")
    judge_src = (CASE_DIR / "judge.py").read_text(encoding="utf-8")
    init_src = (CASE_DIR / "__init__.py").read_text(encoding="utf-8")
    # The judge module is the one that names the ground-truth file.
    assert "oracle.json" in judge_src, "judge must be the ground-truth reader"
    # The arm module and the package __init__ never name it.
    assert "oracle.json" not in case_src, "arm case.py names the oracle file"
    assert "oracle.json" not in init_src, "package __init__ names the oracle file"


# 5 --------------------------------------------------------------------------
def test_single_factor_at_a_time() -> None:
    """Each arm differs from baseline in exactly ONE intervention factor."""
    case = load_case()
    base = case.effective_config(BASELINE)
    for arm in ARMS[1:]:
        eff = case.effective_config(arm)
        diff = {k for k in eff if k not in base or eff[k] != base[k]}
        # arm_id labels the arm itself; the only *factor* change is the
        # functionalization/element pair.
        assert diff == {"arm_id", "functionalization", "element"}, f"{arm}: diff={diff}"


# 6 --------------------------------------------------------------------------
def test_tamper_detection(canon: Path) -> None:
    """A genuine canonical run replays True; a single flipped byte fails it."""
    case = load_case()
    assert _base.replay(case, canon) is True, "genuine canonical run must replay"
    target = canon / "interventions" / "I1_OH" / "target_output.json"
    original = target.read_bytes()
    try:
        flipped = original[:-1] + bytes([original[-1] ^ 0x01])
        target.write_bytes(flipped)
        assert _base.replay(case, canon) is False, "tampered artifact must fail replay"
    finally:
        target.write_bytes(original)
    # Restored -> replays again.
    assert _base.replay(case, canon) is True


# 7 --------------------------------------------------------------------------
def test_canonical_artifacts(case: Tox21ArAgonistCase) -> None:
    """The committed canonical run exists, is replay-genuine, and pins the
    engine version + per-arm artifact hashes (machine-provenance contract)."""
    assert CANONICAL.exists(), (
        f"canonical run missing: {CANONICAL} "
        "(generate with: .venv/bin/python -m repliclaw.counterfactual.cases.tox21_ar_agonist "
        "artifacts/science/p06-hero-canonical  -- or run replay.sh)"
    )
    manifest_path = CANONICAL / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    # Case identity is pinned and matches the case.
    assert manifest["case_sha256"] == case.case_sha256()
    # Engine provenance is recorded (RDKit version pinned).
    assert manifest["engine"]["name"] == "rdkit"
    assert manifest["engine"]["version"], "engine version must be pinned"
    # Every arm pins its artifact hashes, and the tree replays genuinely.
    for arm in ARMS:
        entry = manifest["arms"][arm]
        assert set(entry["artifacts"]) == set(_base.ARM_FILES)
        assert all(entry["artifacts"][n] for n in _base.ARM_FILES)
    assert _base.replay(case, CANONICAL) is True
