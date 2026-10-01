"""P06 SECOND scientific case -- Tox21 AR-agonist directed functionalization.

FALSIFIABLE QUESTION
--------------------
Does the *type* of a single directed aromatic functionalization determine the
change in computed lipophilicity (Crippen logP, RDKit ``MolLogP``) of a frozen
set of real screened compounds, such that distinct interventions
(hydroxylation, chlorination, methylation) yield DISTINCT per-arm mean logP
shifts -- i.e. the case's counterfactual arms genuinely discriminate, rather
than being relabelled copies of one arm?

Reference chemistry (the sealed ground truth encodes the expected result):
hydroxylation is a Phase-I oxidation that adds a polar group and is expected
to LOWER logP; chlorination/methylation add hydrophobic substituents and are
expected to RAISE logP, by different magnitudes. If every arm reproduced the
baseline shift (or two arms coincided), the hypothesis is refuted and must be
reported honestly.

DATA (a small frozen SUBSET -- NOT "toxicity prediction on the full data")
--------------------------------------------------------------------------
* 48 real compounds, a deterministic subset of the Tox21 androgen-receptor
  (AR) agonist screen (PubChem BioAssay AID 743053, Tox21 10K library).
* Provenance: Zenodo record 20269909 (DOI 10.5281/zenodo.20269909), CC-BY-4.0,
  access date 2026-10-08; the frozen extract is
  ``experiments/tox21_ar_agonist/data/tox21_ar_7069.tsv`` (F05), sha256
  ``a1056c72bad00c0205662f05be791d1c9e92a238f77811520a9ce896a2b13f22``
  (7,069 unique compounds, 220 active / 3.1% prevalence).
* This is a *computational structural* experiment on a 48-compound subset.
  It is NOT an activity/toxicity prediction model on the full 7,069 extract;
  the assay ``label`` column is carried through for provenance only and is not
  used by any arm or the judge.

ARMS (each perturbs exactly ONE factor = the directed functionalization)
------------------------------------------------------------------------
* ``I0_baseline`` : no functionalization (the base case).
* ``I1_OH``       : single aromatic -> phenol (C -> C-OH).
* ``I2_Cl``       : single aromatic -> aryl chloride (C -> C-Cl).
* ``I3_Me``       : single aromatic -> tolyl methyl (C -> C-CH3).

The intervention site is deterministic (first aromatic carbon bearing an
implicit H, lowest atom index), so every arm is a pure function of the frozen
data + the single-factor intervention + seed.

OFFLINE + DETERMINISTIC
-----------------------
RDKit ``MolLogP`` is a deterministic Crippen fragment sum; there is no LLM, no
network, and no real token spend. The same (case_sha256, config_sha256, seed)
reproduces byte-identical artifacts (see ``_base.replay``).

RDKit is a *lazy* dependency (imported only in :func:`_require_rdkit`). It is
not declared in ``pyproject.toml`` (that file is not in P06's owned paths);
the venv used for the canonical run has RDKit pinned (version recorded in the
manifest ``engine`` block). If RDKit is absent, the arms raise a clear error.

SEALED GROUND TRUTH (contract section 6)
----------------------------------------
The ground truth for scoring lives in a sealed file inside this case directory
and is read ONLY by :mod:`.judge` (i.e. by :meth:`Tox21ArAgonistCase.judge_arm`).
This arm module contains no reference to that file; a test greps the arm source
and the canonical artifact tree to prove the ground-truth literals do not leak
into any arm code path, and asserts :mod:`.judge` is the sole reader.

NOTE: the concrete P02 ``counterfactual`` package (CaseSpec /
InterventionSpec / SimpleAuditExecutor) is not in this worktree base; this
case implements the case-agnostic :mod:`repliclaw.counterfactual.cases._base`
runner. Real P02 wiring happens at P07 integration.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from repliclaw.counterfactual.cases._base import (
    Case,
    engine_metadata,
    sha256_bytes,
)

_HERE = Path(__file__).resolve().parent
_DATA_FILE = _HERE / "data" / "molecules.json"

_BASELINE = "I0_baseline"
_ARMS: Dict[str, Dict[str, Any]] = {
    _BASELINE: {"functionalization": None, "element": None, "label": "none"},
    "I1_OH": {"functionalization": "hydroxylation", "element": "O", "label": "aromatic -> phenol"},
    "I2_Cl": {"functionalization": "chlorination", "element": "Cl", "label": "aromatic -> aryl chloride"},
    "I3_Me": {"functionalization": "methylation", "element": "C", "label": "aromatic -> tolyl methyl"},
}

_MEASUREMENT = "rdkit_crippen_logp (RDKit Chem.Descriptors.MolLogP)"
_SITE = "first_aromatic_implicit_h_carbon (lowest atom index)"

_RDKIT_CACHE: Optional[Tuple[Any, Any]] = None


def _require_rdkit():
    """Lazily import and cache the RDKit Chem/Descriptors modules.

    RDKit is an optional, not-declared dependency (see module docstring); the
    error message below is the single actionable failure mode when it is
    absent from the run environment.
    """
    global _RDKIT_CACHE
    if _RDKIT_CACHE is None:
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors
        except Exception as exc:  # noqa: BLE001 - surface one actionable error
            raise RuntimeError(
                "RDKit is required for the Tox21 P06 case and is not installed "
                f"in this environment ({exc!r}). Install it in the run venv, "
                "e.g. `pip install rdkit`. RDKit is a lazy dependency of this "
                "case; it is not declared in pyproject.toml."
            ) from exc
        _RDKIT_CACHE = (Chem, Descriptors)
    return _RDKIT_CACHE


def _site_idx(mol) -> Optional[int]:
    """Deterministic intervention site: first aromatic C with an implicit H."""
    for a in mol.GetAtoms():
        if a.GetIsAromatic() and a.GetNumImplicitHs() > 0:
            return a.GetIdx()
    return None


def _edit(mol, element: Optional[str]):
    """Return a copy of ``mol`` with ``element`` attached at the site, or the
    original mol when ``element is None`` (baseline)."""
    if element is None:
        return mol
    Chem, _ = _require_rdkit()
    idx = _site_idx(mol)
    if idx is None:
        return None
    rw = Chem.RWMol(mol)
    rw.GetAtomWithIdx(idx).SetNoImplicit(True)
    new = rw.AddAtom(Chem.Atom(element))
    rw.AddBond(idx, new, Chem.BondType.SINGLE)
    out = rw.GetMol()
    try:
        Chem.SanitizeMol(out, catchErrors=True)
    except Exception:  # noqa: BLE001 - treat any sanitization failure as a no-edit
        return None
    return out if (out is not None and out.GetNumAtoms() > 0) else None


class Tox21ArAgonistCase(Case):
    """Frozen Tox21 AR-agonist directed-functionalization counterfactual case.

    The arm path (data, :meth:`measure_arm`, :meth:`effective_config`) is
    structurally independent of the sealed ground truth; only
    :meth:`judge_arm` (delegated to :mod:`.judge`) reads it.
    """

    case_id = "tox21_ar_agonist_v1"
    case_version = "v1"
    target_measurement_id = "rdkit_crippen_logp/v1"

    def __init__(self) -> None:
        self._data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
        self._molecules: List[Dict[str, Any]] = list(self._data["molecules"])
        self._n = int(self._data["n_molecules"])

    # -- identity ----------------------------------------------------------
    def case_sha256(self) -> str:
        """sha256 of the frozen molecules.json bytes (the immutable input)."""
        return sha256_bytes(_DATA_FILE.read_bytes())

    def arm_ids(self) -> List[str]:
        return list(_ARMS.keys())

    def effective_config(self, arm_id: str) -> Dict[str, Any]:
        if arm_id not in _ARMS:
            raise KeyError(arm_id)
        spec = _ARMS[arm_id]
        return {
            "arm_id": arm_id,
            "intervention": "directed_aromatic_functionalization",
            "functionalization": spec["functionalization"],
            "element": spec["element"],
            "site": _SITE,
            "measurement": _MEASUREMENT,
            "n_molecules": self._n,
            "case_sha256": self.case_sha256(),
        }

    # -- ARM (structurally independent of the ground truth) ---------------
    def measure_arm(self, arm_id: str, seed: int) -> Dict[str, Any]:
        """Measure the mean Crippen-logP shift of the intervention across the
        frozen molecules. Pure function of frozen data + single-factor arm."""
        del seed  # recorded for parity with live targets; deterministic here
        Chem, Descriptors = _require_rdkit()
        spec = _ARMS[arm_id]
        element = spec["element"]
        per_mol: List[Dict[str, Any]] = []
        deltas: List[float] = []
        for m in self._molecules:
            mol = Chem.MolFromSmiles(m["smiles"])
            if mol is None:
                continue
            base = Descriptors.MolLogP(mol)
            edited = _edit(mol, element)
            if edited is None:
                continue
            dlogp = Descriptors.MolLogP(edited) - base
            deltas.append(dlogp)
            per_mol.append(
                {
                    "inchikey": m["inchikey"],
                    "base_logp": round(base, 6),
                    "edited_logp": round(base + dlogp, 6),
                    "delta_logp": round(dlogp, 6),
                }
            )
        if not deltas:
            raise RuntimeError(f"arm {arm_id}: no molecule was editable")
        mean = sum(deltas) / len(deltas)
        return {
            "arm_id": arm_id,
            "functionalization": spec["functionalization"],
            "measurement": _MEASUREMENT,
            "n_molecules": self._n,
            "n_edited": len(deltas),
            "mean_delta_logp": round(mean, 6),
            "per_molecule": per_mol,
        }

    # -- JUDGE (delegated; the ONLY reader of the ground truth) -----------
    def judge_arm(self, arm_id: str, target_output: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Score the measured mean shift against the sealed ground truth.

        Delegates to :func:`repliclaw.counterfactual.cases.tox21_ar_agonist.judge
        .judge_arm` so that this arm module carries no ground-truth reference.
        """
        from repliclaw.counterfactual.cases.tox21_ar_agonist.judge import judge_arm

        return judge_arm(self, arm_id, target_output)

    def engine_metadata(self) -> Dict[str, str]:
        try:
            from rdkit import rdBase

            version = rdBase.rdkitVersion
        except Exception:  # noqa: BLE001 - engine version is best-effort
            version = ""
        return engine_metadata("rdkit", version, "")


def load_case() -> Tox21ArAgonistCase:
    """Load the frozen Tox21 AR-agonist case."""
    return Tox21ArAgonistCase()
