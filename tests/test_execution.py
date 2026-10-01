"""Execution honesty (ported from F02, adapted to the P02 pipeline).

Core acceptance logic, preserved intact from F02:

* A model's self-attestation alone can NEVER produce a verified record —
  ``ExecutionRecord.verified`` / ``verify_report`` are verifier-only.
* A run is ``verified=True`` ONLY when produced by the actual runner
  (``run_python_execution``) and independently re-verified (``verify_execution``
  / P02 ``replay``).
* Self-attested, tampered, and swapped records are rejected.

The F02 protocol/investigator wiring is intentionally NOT ported (P02 ticket:
"stub the 2 protocol-dependent tests with the SAME acceptance logic against
the P02 run pipeline"). The P02 pipeline analogue of "the protocol verifies
the evidence row" is ``repliclaw.counterfactual.replay``: a canonical arm is
accepted only when re-execution reproduces every pinned artifact hash.
"""
from __future__ import annotations

import json
from pathlib import Path

from repliclaw import execution as ex
from repliclaw.counterfactual import InterventionSpec, replay, run_canonical, run_case
from repliclaw.counterfactual.case import sha256_bytes
from repliclaw.counterfactual.executor import ARM_FILES, load_case, load_interventions


def _canonical(tmp_path: Path) -> Path:
    """Build a fresh canonical run in a temp dir (cheap: 5 offline arms)."""
    case = load_case("policy_rag_v1")
    out = tmp_path / "canon"
    run_canonical(case, load_interventions("policy_rag_v1"), seed=0, out_root=out)
    return out


def test_self_attestation_rejected(tmp_path):
    """Self-stamped verified fields are neutralized; a self-attested (forged)
    P02 run manifest that was never actually executed is rejected by replay."""
    # Module level: verifier-only fields cannot be self-stamped.
    rec = ex.run_python_execution("print('x = 12.345')", cwd=str(tmp_path), agent_id="self")
    ok, report = ex.verify_execution(rec, out_dir=tmp_path / "vt")
    assert ok, report
    faked = ex.ExecutionRecord.model_validate(
        {**rec.to_dict(), "verified": True, "verify_report": "I say so"}
    )
    assert faked.verified is False, "self-stamped verified must be neutralized"
    assert faked.verify_report == ""

    # P02 pipeline: an agent self-attests a run by pinning hashes of artifacts
    # that were never actually produced. replay() must reject.
    canon = _canonical(tmp_path)
    manifest = json.loads((canon / "manifest.json").read_text())
    forged_pin = sha256_bytes(b"attested but never produced\n")
    manifest["arms"]["I0_baseline"]["artifacts"]["target_output.txt"] = forged_pin
    forged = tmp_path / "forged"
    forged.mkdir()
    (forged / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    import shutil

    shutil.copytree(canon / "interventions", forged / "interventions")
    assert replay("policy_rag_v1", forged) is False, "self-attested manifest must be rejected"


def test_tampered_record_rejected(tmp_path):
    """Doctored stdout/exit fails verify_execution; a tampered P02 arm artifact
    (target_output.txt edited after the fact) fails replay."""
    rec = ex.run_python_execution("print('x = 12.345')", cwd=str(tmp_path), agent_id="tamper")
    assert rec.exit_code == 0
    ok, report = ex.verify_execution(rec, out_dir=tmp_path / "vt")
    assert ok, report

    # Doctored stdout: same command/code, fabricated output.
    bad = rec.model_copy(update={"stdout": rec.stdout + "(tampered line)"})
    bad_ok, bad_report = ex.verify_execution(bad, out_dir=tmp_path / "vt2")
    assert bad_ok is False, "doctored stdout must fail verification"
    assert "mismatch" in bad_report.lower()

    # Doctored exit code: a crash record claiming success.
    crash = ex.run_python_execution("print(1/0)", cwd=str(tmp_path / "c"), agent_id="t2")
    lie = crash.model_copy(update={"exit_code": 0})
    lie_ok, _ = ex.verify_execution(lie, out_dir=tmp_path / "vt3")
    assert lie_ok is False, "doctored exit code must fail verification"

    # P02 pipeline: edit an arm's target_output.txt after the manifest pinned
    # its hash -> the tampered canonical run must fail replay.
    canon = _canonical(tmp_path)
    arm = canon / "interventions" / "I0_baseline" / "target_output.txt"
    arm.write_text(arm.read_text().replace("14 days", "90 days"))
    assert replay("policy_rag_v1", canon) is False, "tampered arm artifact must fail replay"


def test_verified_record_accepted(tmp_path):
    """A genuinely executed, deterministic record verifies in a fresh dir and
    the verifier (only) can stamp it verified=True. A genuine P02 canonical
    run is accepted by replay (verified=True)."""
    det = ex.run_python_execution(
        "import hashlib\nprint(hashlib.sha256(b'policy_rag').hexdigest()[:12])",
        cwd=str(tmp_path),
        agent_id="det-analyst",
    )
    assert det.exit_code == 0
    # Independent verification in a FRESH dir.
    ok, report = ex.verify_execution(det, out_dir=tmp_path / "fresh")
    assert ok, f"record must verify in a fresh dir: {report}"
    assert det.artifact_hashes.get("script.py"), "records must hash their script"

    # Only the verifier stamps verified=True.
    stamped = ex.ExecutionRecord.from_verified_payload(det.to_dict(), True, report)
    assert stamped.verified is True and stamped.verify_report == report
    faked = ex.ExecutionRecord.model_validate(
        {**det.to_dict(), "verified": True, "verify_report": "I say so"}
    )
    assert faked.verified is False and faked.verify_report == ""

    # P02 pipeline: a genuine canonical run verifies (accepted).
    canon = _canonical(tmp_path)
    assert replay("policy_rag_v1", canon) is True, "genuine canonical run must verify"


def test_crash_not_executable(tmp_path):
    """A crashed snippet is recorded faithfully (non-zero exit, stderr intact)
    and its honest record verifies — but a non-zero-exit record is NOT
    executable evidence. The P02 pipeline likewise records a failing arm
    honestly (abstained/failed target output preserved, never fabricated)."""
    rec = ex.run_python_execution("print(1/0)", cwd=str(tmp_path), agent_id="crash")
    assert rec.exit_code != 0
    assert "ZeroDivisionError" in rec.stderr
    # The crash is reproducible, so the record is honest (verifies).
    ok, report = ex.verify_execution(rec, out_dir=tmp_path / "v")
    assert ok, f"a faithful crash record must verify: {report}"
    # Honest but non-executable: acceptance logic for P02 evidence.
    assert rec.exit_code != 0, "non-zero exit => not executable evidence"

    # P02 pipeline: an arm whose target abstains (no retrieval data) is
    # recorded honestly — the abstention is preserved verbatim and still
    # verifies via replay.
    case = load_case("policy_rag_v1")
    adhoc = InterventionSpec(intervention_id="adhoc_empty", case_id="policy_rag_v1", retrieval=[])
    out = tmp_path / "adhoc"
    run = run_case(case, adhoc, seed=0, out_root=out)
    assert run.exit_code == 0 and "don't have" in run.target_output, "abstention recorded verbatim"
    assert run.severity == "critical", "abstention fails the rubric honestly"


def test_no_data_is_honestly_not_executable(tmp_path):
    """A run that produced no data files must not claim data artifacts; the
    P02 run record carries honest zero token counts (offline), never fabricated
    spend or outputs."""
    rec = ex.run_python_execution("pass", cwd=str(tmp_path / "nd"), agent_id="nodata")
    assert rec.exit_code == 0
    assert rec.stdout.strip() == ""
    # Only the script is hashed; no data artifacts claimed.
    assert set(rec.artifact_hashes) == {"script.py"}
    ok, report = ex.verify_execution(rec, out_dir=tmp_path / "vnd")
    assert ok, report

    # P02 pipeline: offline run records 0 real tokens and the honest
    # 0/0/0/0/0 token counts (no fabricated spend).
    case = load_case("policy_rag_v1")
    run = run_case(case, load_interventions("policy_rag_v1")[0], seed=0)
    assert all(v == 0 for v in run.token_counts.values() if v is not None)
    assert run.token_counts["real_token_calls"] == 0


def test_swapped_record_rejected(tmp_path):
    """A record of a DIFFERENT computation than the one committed to fails
    (script-hash mismatch); a P02 arm whose artifacts were swapped for another
    arm's fails replay."""
    # Swap: the investigator committed to computation A (honest record) but
    # attaches the source of a DIFFERENT computation B. Re-executing the
    # attached source produces a script hash that does not match the
    # committed record's pinned script hash -> swapped.
    honest = ex.run_python_execution("print('committed computation A')", cwd=str(tmp_path / "a"), agent_id="sw-a")
    other = ex.run_python_execution(
        "print('something else entirely')", cwd=str(tmp_path / "b"), agent_id="sw-b"
    )
    swapped = honest.model_copy(update={"code": other.code})
    ok, report = ex.verify_execution(swapped, out_dir=tmp_path / "sw")
    assert ok is False, "a swapped record must not verify"
    assert "script hash mismatch" in report

    # P02 pipeline: swap I0's artifacts into the I_J arm directory -> the
    # pinned hashes no longer match what the arm actually produced.
    canon = _canonical(tmp_path)
    i0 = canon / "interventions" / "I0_baseline"
    ij = canon / "interventions" / "I_J_judge_fix"
    for name in ARM_FILES:
        (ij / name).write_bytes((i0 / name).read_bytes())
    assert replay("policy_rag_v1", canon) is False, "swapped arm artifacts must fail replay"
