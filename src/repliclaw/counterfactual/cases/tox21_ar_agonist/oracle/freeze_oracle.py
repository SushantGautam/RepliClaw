#!/usr/bin/env python3
"""One-shot: freeze the sealed oracle from the measured RDKit constants.

Run ONCE (offline) to compute the expected per-arm mean Crippen-logP shifts on
the frozen 48-molecule subset and write oracle/oracle.json. The oracle is then
the sealed ground truth the judge alone reads.
"""
import json
import statistics
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Descriptors

HERE = Path(__file__).resolve().parent  # the case's oracle/ directory
CASE = HERE.parent                      # the case directory
DATA = CASE / "data" / "molecules.json"
OUT = HERE / "oracle.json"

ARMS = {
    "I0_baseline": ("none", None),
    "I1_OH": ("hydroxylation", "O"),
    "I2_Cl": ("chlorination", "Cl"),
    "I3_Me": ("methylation", "C"),
}


def site_idx(mol):
    for a in mol.GetAtoms():
        if a.GetIsAromatic() and a.GetNumImplicitHs() > 0:
            return a.GetIdx()
    return None


def edit(mol, element):
    if element is None:
        return mol
    idx = site_idx(mol)
    if idx is None:
        return None
    rw = Chem.RWMol(mol)
    rw.GetAtomWithIdx(idx).SetNoImplicit(True)
    new = rw.AddAtom(Chem.Atom(element))
    rw.AddBond(idx, new, Chem.BondType.SINGLE)
    out = rw.GetMol()
    try:
        Chem.SanitizeMol(out, catchErrors=True)
    except Exception:
        return None
    return out if out and out.GetNumAtoms() else None


def mean_shift(smiles_list, element):
    ds = []
    for smi in smiles_list:
        m = Chem.MolFromSmiles(smi)
        if m is None:
            continue
        base = Descriptors.MolLogP(m)
        e = edit(m, element)
        if e is None:
            continue
        ds.append(Descriptors.MolLogP(e) - base)
    return statistics.mean(ds)


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    smiles = [m["smiles"] for m in data["molecules"]]
    outcomes = {}
    for arm, (fn, element) in ARMS.items():
        val = 0.0 if element is None else round(mean_shift(smiles, element), 6)
        outcomes[arm] = {
            "functionalization": fn,
            "mean_delta_logp": val,
        }
    oracle = {
        "schema": "repliclaw.sealed_oracle/v1",
        "case": "tox21_ar_agonist_v1",
        "true_cause": "functionalization_type_drives_logp",
        "hypothesis": "H_FT",
        "hypothesis_statement": (
            "The type of a single directed aromatic functionalization determines "
            "the mean change in Crippen logP of the frozen 48-compound Tox21 "
            "AR-agonist subset: hydroxylation lowers logP, chlorination and "
            "methylation raise it by distinct magnitudes, so the four arms "
            "yield distinct mean_delta_logp outcomes."
        ),
        "seeded_fault": None,
        "tolerance_abs_delta_logp": 0.001,
        "reference_measurement": "rdkit_crippen_logp (RDKit Chem.Descriptors.MolLogP), site=" +
            "first_aromatic_implicit_h_carbon",
        "expected_arm_outcomes": outcomes,
        "expected_ranking_by_mean_delta_logp": (
            "I0_baseline(0) < I1_OH < I3_Me < I2_Cl  (expected direction)"
        ),
        "supports_hypothesis": {
            "H_FT": "distinct, direction-consistent per-arm mean_delta_logp"
        },
        "note": (
            "Frozen from a real offline RDKit run on the 48-compound subset "
            "(rdkit_version recorded in data/molecules.json). The judge alone "
            "reads this file; no arm code path references it."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(oracle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", OUT)
    for arm in ARMS:
        print(f"  {arm:12s} {outcomes[arm]['functionalization']:16s} expected={outcomes[arm]['mean_delta_logp']:+.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
