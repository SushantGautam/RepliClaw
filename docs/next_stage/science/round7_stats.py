#!/usr/bin/env python3
"""Round-7 (V3.5-D) statistical analysis — RepliClaw RCAEval pilot.

Read-only over round-7 artifacts. Every number in
round7_statistical_analysis.md is produced by running this script.

Run:
  /Users/sushantgautam/Documents/ScienceClawHackathon/.venv/bin/python \
    docs/next_stage/science/round7_stats.py
"""
import json
import statistics
from itertools import product
from pathlib import Path

from scipy import stats

ROOT = Path("/Users/sushantgautam/Documents/RepliClaw-stg2-v35/.artifacts/rcaeval/pilot/run_v35/round7/round7")
CASES = [f"RCA-P-{i:02d}" for i in range(1, 9)]
SEEDS = [20261011, 20261012]
ARMS = ["D-E-TELEM", "C-EQ-TELEM"]
BOOT_B = 10_000
BOOT_SEED = 20261011

# ---------------------------------------------------------------- load
runs = {}  # (case, seed, arm) -> dict
mismatches = []
ledger_tokens = {}
for line in (ROOT / "ledger.jsonl").read_text().splitlines():
    rec = json.loads(line)
    p = ROOT.parent.parent / "run_v35" / rec["run_path"]
    runs[(rec["case"], rec["seed"], rec["arm"])] = {
        "case": rec["case"], "seed": rec["seed"], "arm": rec["arm"],
        "status": rec["status"], "hit": rec["hit"],
        "tokens": rec["tokens"], "wall_s": rec["wall_s"],
    }
    ledger_tokens[(rec["case"], rec["seed"], rec["arm"])] = rec["tokens"]

for case, seed, arm in product(CASES, SEEDS, ARMS):
    d = ROOT / case / f"seed{seed}" / arm
    sf = d / "status.json"
    if not sf.exists():
        continue  # never launched
    s = json.loads(sf.read_text())
    key = (case, seed, arm)
    scf = d / "score.json"
    if key in runs:
        rec0 = runs[key]
        for f in ("status", "tokens", "wall_s"):
            if s.get(f) != rec0.get(f):
                mismatches.append(f"{key}: ledger {f}={rec0.get(f)} vs status.json {s.get(f)}")
    rec = runs.setdefault(key, {"case": case, "seed": seed, "arm": arm})
    rec.update(status=s["status"], tokens=s["tokens"], wall_s=s["wall_s"],
               crash_error=s.get("crash_error"))
    if scf.exists():
        rec["hit"] = json.loads(scf.read_text())["hit"]
    elif s["status"] == "completed":
        rec["hit"] = None
        mismatches.append(f"{key}: completed but score.json MISSING")
    else:
        rec["hit"] = None

STOP = json.loads((ROOT / "STOP.json").read_text())
META = json.loads((ROOT / "parallel_meta.json").read_text())

print("== LEDGER/JSON CROSS-CHECK ==")
print("runs present on disk:", len(runs))
print("mismatches:", mismatches if mismatches else "none")
tot = sum(r["tokens"] for r in runs.values())
print("total tokens (24 runs):", tot)
print("STOP snapshot cumulative + post-trip =",
      STOP["checks"]["stop3_tokens"]["cumulative"] + 302152 + 275300)

# ---------------------------------------------------------------- per-run table
print("\n== PER-RUN TABLE (case x seed x arm) ==")
print(f"{'case':9} {'seed':10} {'arm':11} {'status':16} {'hit':6} {'tokens':>8} {'wall_s':>8}")
for case in CASES:
    for seed in SEEDS:
        for arm in ARMS:
            r = runs.get((case, seed, arm))
            if r is None:
                print(f"{case:9} {seed:10} {arm:11} {'NOT LAUNCHED':16} {'-':6} {'-':>8} {'-':>8}")
            else:
                h = "-" if r["hit"] is None else str(r["hit"])
                print(f"{case:9} {seed:10} {arm:11} {r['status']:16} {h:6} {r['tokens']:>8} {r['wall_s']:>8.3f}")

# ---------------------------------------------------------------- case level
print("\n== CASE-LEVEL (rule: case hit = TRUE iff >=1 completed run of that arm's seeds hit; "
      "missing = no completed runs for that arm) ==")
case_lvl = {}
for case in CASES:
    row = {"case": case}
    for arm in ARMS:
        hits = [runs[(c, s, a)]["hit"] for (c, s, a) in runs
                if c == case and a == arm and runs[(c, s, a)]["status"] == "completed"]
        row[arm] = hits
        row[arm + "_hit"] = (max(hits) if hits else None)
    case_lvl[case] = row
    de = row["D-E-TELEM_hit"]; ce = row["C-EQ-TELEM_hit"]
    mark = "" if de is not None or ce is not None else " (neither arm completed: uninformative)"
    print(f"{case}: D-E completed-seed hits={row['D-E-TELEM']} -> {de} | "
          f"C-EQ completed-seed hits={row['C-EQ-TELEM']} -> {ce}{mark}")

full8_de = sum(1 for c in case_lvl.values() if c["D-E-TELEM_hit"])
full8_ce = sum(1 for c in case_lvl.values() if c["C-EQ-TELEM_hit"])
informative = [c for c in CASES if case_lvl[c]["D-E-TELEM_hit"] is not None
               or case_lvl[c]["C-EQ-TELEM_hit"] is not None]
inf_de = sum(1 for c in informative if case_lvl[c]["D-E-TELEM_hit"])
inf_ce = sum(1 for c in informative if case_lvl[c]["C-EQ-TELEM_hit"])
print(f"\nFULL-COHORT (primary, pre-specified denominator, n=8): "
      f"D-E {full8_de}/8 = {full8_de/8:.3f}, C-EQ {full8_ce}/8 = {full8_ce/8:.3f}")
print(f"INFORMATIVE (at least one arm >=1 completed run, n={len(informative)}): "
      f"{informative}")
print(f"INFORMATIVE hits: D-E {inf_de}/{len(informative)}, C-EQ {inf_ce}/{len(informative)}")
print(f"  (no-completion counted as NON-hit in both denominators; "
      f"paired-discordant subset where BOTH arms completed: "
      f"{[c for c in CASES if case_lvl[c]['D-E-TELEM_hit'] is not None and case_lvl[c]['C-EQ-TELEM_hit'] is not None]})")

# ---------------------------------------------------------------- paired exact
print("\n== PAIRED EXACT TESTS (case level) ==")
# Full-cohort table (treat no-completion as a non-hit for the paired count;
# ties = both non-hit)
tbl = {"++": 0, "+-": 0, "-+": 0, "--": 0}
for c in case_lvl.values():
    a, b = bool(c["D-E-TELEM_hit"]), bool(c["C-EQ-TELEM_hit"])
    tbl[("+" if a else "-") + ("+" if b else "-")] += 1
print("full-cohort 2x2:", tbl)
n = 8
discordant = tbl["+-"] + tbl["-+"]
# sign test (two-sided exact, ties dropped), full cohort
if discordant:
    sign_p = min(1.0, 2 * sum(stats.binom.pmf(k, discordant, 0.5)
                              for k in range(0, min(tbl["+-"], tbl["-+"]) + 1)))
else:
    sign_p = 1.0
print(f"full-cohort sign test: discordant={discordant}, p={sign_p}")
# McNemar (exact, two-sided), full cohort
b, c_ = tbl["+-"], tbl["-+"]
if b + c_ > 0:
    mcn_p = min(1.0, 2 * sum(stats.binom.pmf(k, b + c_, 0.5)
                             for k in range(0, min(b, c_) + 1)))
    print(f"McNemar exact two-sided: b={b}, c={c_}, p={mcn_p}")
# informative-only pairings (paired per case, n=6)
inf_tbl = {"++": 0, "+-": 0, "-+": 0, "--": 0}
for c in informative:
    row = case_lvl[c]
    a, b2 = bool(row["D-E-TELEM_hit"]), bool(row["C-EQ-TELEM_hit"])
    inf_tbl[("+" if a else "-") + ("+" if b2 else "-")] += 1
print("informative 2x2:", inf_tbl)
bi, ci = inf_tbl["+-"], inf_tbl["-+"]
if bi + ci > 0:
    mcn_p_inf = min(1.0, 2 * sum(stats.binom.pmf(k, bi + ci, 0.5)
                                 for k in range(0, min(bi, ci) + 1)))
else:
    mcn_p_inf = 1.0
print(f"informative McNemar exact two-sided: b={bi}, c={ci}, p={mcn_p_inf}")

# per-seed run-level sign check (context, n=14 D-E completed-pair runs is not
# paired per run; report per-seed completion pairs where BOTH arms completed)
per_seed_pairs = {}
for c in CASES:
    for s in SEEDS:
        de = runs.get((c, s, "D-E-TELEM")); ce = runs.get((c, s, "C-EQ-TELEM"))
        if de and ce and de["status"] == "completed" and ce["status"] == "completed":
            per_seed_pairs[(c, s)] = (de["hit"], ce["hit"])
print(f"\nper-seed pairs where BOTH arms completed: {len(per_seed_pairs)}")
hh = sum(1 for a, b2 in per_seed_pairs.values() if a and b2)
dh = sum(1 for a, b2 in per_seed_pairs.values() if a and not b2)
ch = sum(1 for a, b2 in per_seed_pairs.values() if not a and b2)
print(f"  D-E-hit&CEQ-hit={hh}, D-E-only={dh}, C-EQ-only={ch}")
if dh + ch:
    p_seed = min(1.0, 2 * sum(stats.binom.pmf(k, dh + ch, 0.5)
                              for k in range(0, min(dh, ch) + 1)))
    print(f"  sign test p={p_seed}")

# ---------------------------------------------------------------- bootstrap
print("\n== BOOTSTRAP (B=%d, seed=%d, resample unit = case) ==" % (BOOT_B, BOOT_SEED))
pass  # deterministic LCG defined below (reproducible, no numpy RNG state)


class LCG:
    def __init__(self, seed):
        self.s = seed

    def __call__(self):
        self.s = (1664525 * self.s + 1013904223) % (1 << 32)
        return self.s


def pct(x, lo=2.5, hi=97.5):
    x = sorted(x)
    import math
    n = len(x)
    # linear interpolation (type 7, matches numpy default)
    def idx(p):
        h = (n - 1) * p / 100.0
        lo_i = int(math.floor(h)); hi_i = min(lo_i + 1, n - 1)
        return x[lo_i] + (x[hi_i] - x[lo_i]) * (h - lo_i)
    return idx(lo), idx(hi)


def bootstrap(full_denom=8, subset=None):
    """full_denom: denominator for the rate (8 or 6); subset: case names."""
    cases = subset if subset is not None else CASES
    de_case = {c: case_lvl[c]["D-E-TELEM_hit"] for c in cases}
    ce_case = {c: case_lvl[c]["C-EQ-TELEM_hit"] for c in cases}
    r = LCG(BOOT_SEED)
    de_rates, ce_rates, diffs = [], [], []
    m = len(cases)
    for _ in range(BOOT_B):
        samp = [cases[r() % m] for _ in range(m)]
        de = sum(1 for c in samp if de_case[c]) / full_denom
        ce = sum(1 for c in samp if ce_case[c]) / full_denom
        de_rates.append(de); ce_rates.append(ce); diffs.append(de - ce)
    return de_rates, ce_rates, diffs


for label, denom, subset in [
    ("PRIMARY full-cohort (n=8)", 8, None),
    ("secondary informative (n=6)", 6, informative),
]:
    de_r, ce_r, diff_r = bootstrap(denom, subset)
    print(f"\n[{label}]")
    print("  D-E hit-rate  observed={:.3f}  bootstrap point(mean of B)={:.4f}  "
          "CI2.5-97.5: [{:.3f}, {:.3f}]".format(
              (sum(1 for c in (subset or CASES) if case_lvl[c]['D-E-TELEM_hit']) / denom),
              sum(de_r) / BOOT_B, *pct(de_r)))
    print("  C-EQ hit-rate observed={:.3f}  bootstrap point(mean of B)={:.4f}  "
          "CI2.5-97.5: [{:.3f}, {:.3f}]".format(
              (sum(1 for c in (subset or CASES) if case_lvl[c]['C-EQ-TELEM_hit']) / denom),
              sum(ce_r) / BOOT_B, *pct(ce_r)))
    print("  paired diff (D-E - C-EQ) observed={:.3f}  bootstrap point={:.4f}  "
          "CI2.5-97.5: [{:.3f}, {:.3f}]".format(
              ((sum(1 for c in (subset or CASES) if case_lvl[c]['D-E-TELEM_hit'])
                - sum(1 for c in (subset or CASES) if case_lvl[c]['C-EQ-TELEM_hit'])) / denom),
              sum(diff_r) / BOOT_B, *pct(diff_r)))

# ---------------------------------------------------------------- cost
print("\n== COST ==")
de_hits = [r for r in runs.values() if r["arm"] == "D-E-TELEM" and r["hit"] is True]
ce_hits = [r for r in runs.values() if r["arm"] == "C-EQ-TELEM" and r["hit"] is True]
print("tokens per completed hit — D-E:", sorted(r["tokens"] for r in de_hits),
      "median", statistics.median(r["tokens"] for r in de_hits))
print("tokens per completed hit — C-EQ:", sorted(r["tokens"] for r in ce_hits),
      "median", statistics.median(r["tokens"] for r in ce_hits))
print("median ratio D-E/C-EQ:",
      statistics.median(r["tokens"] for r in de_hits) / statistics.median(r["tokens"] for r in ce_hits))

de_done_cases = sorted(c for c in CASES if case_lvl[c]["D-E-TELEM_hit"] is not None)
ce_done_cases = sorted(c for c in CASES if case_lvl[c]["C-EQ-TELEM_hit"] is not None)
de_all_tok = {c: sum(r["tokens"] for r in runs.values()
                     if r["case"] == c and r["arm"] == "D-E-TELEM") for c in de_done_cases}
ce_all_tok = {c: sum(r["tokens"] for r in runs.values()
                     if r["case"] == c and r["arm"] == "C-EQ-TELEM") for c in ce_done_cases}
de_hit_tok = {c: sum(r["tokens"] for r in runs.values()
                     if r["case"] == c and r["arm"] == "D-E-TELEM" and r["hit"])
              for c in de_done_cases}
ce_hit_tok = {c: sum(r["tokens"] for r in runs.values()
                     if r["case"] == c and r["arm"] == "C-EQ-TELEM" and r["hit"])
              for c in ce_done_cases}
print("\ncost per case (all runs of that case; incl. sunk aborted tokens) D-E:")
for c in de_done_cases:
    print(f"  {c}: all={de_all_tok[c]}, hit-only={de_hit_tok[c]}, sunk={de_all_tok[c]-de_hit_tok[c]}")
print("cost per case (all runs of that case; incl. sunk aborted tokens) C-EQ:")
for c in ce_done_cases:
    print(f"  {c}: all={ce_all_tok[c]}, hit-only={ce_hit_tok[c]}, sunk={ce_all_tok[c]-ce_hit_tok[c]}")
de_sunk_total = sum(r["tokens"] for r in runs.values()
                    if r["arm"] == "D-E-TELEM" and r["status"] != "completed")
print("D-E total sunk (aborted) tokens:", de_sunk_total)
print("sum incl-sunk D-E:", sum(de_all_tok.values()),
      "| excl-sunk D-E:", sum(de_hit_tok.values()),
      "| C-EQ (no aborts):", sum(ce_hit_tok.values()))

# ---------------------------------------------------------------- power
print("\n== POWER / MINIMUM-N COMPUTATIONS ==")


def mcnemar_exact_two_sided_p(k, n_disc):
    """Exact two-sided McNemar/sign p-value: P(X <= k) * 2 capped at 1,
    X ~ Binom(n_disc, 0.5), where k = min(b, c)."""
    return min(1.0, 2 * sum(stats.binom.pmf(j, n_disc, 0.5) for j in range(0, k + 1)))


# 1) minimum n to distinguish 50% vs 100% (per-case hit prob 0.5 vs 1.0)
# model: per-case paired hit; null p_D = 0.5; alternative p_D = 1.0 (100%).
# sign/McNemar-style: reject when # D-E hits among discordant pairs is
# "all" (two-sided exact sign test).
print("\n(min n: 50% vs 100% per-case hit, two-sided exact sign test, alpha=0.05)")
for n in range(1, 12):
    # under p=0.5, all-hits prob:
    p0_all = 0.5 ** n            # p-value if we observe all-hits under H0
    # power under p=1.0: probability of all-hits = 1.0
    alpha_ok = p0_all <= 0.05
    print(f"  n={n}: p0(P=all hits)={p0_all:.6f} (reject region if <=0.05: {alpha_ok}), "
          f"power under p=1.0 = 1.0")

# 2) exact power of the two-sided exact sign test under a binomial model for
# n paired cases: under H1, b~Binom(n, p1), c ~ 0 (D-E always wins discordant)
#    i.e., sign test on D-E-vs-tie structure. Compute exact size at p1=0.5 and
#    power at alternative p1 for the rejection region R = {observed k:
#    mcnemar_exact_two_sided_p(k, n) <= 0.05}, where k = #D-E-only wins among
#    n discordant... For paired 0/1 case-level data with p_ceq fixed, the
#    clean statement is: paired difference D-E - C-EQ with both at p vs p+d.
# We use the simple, conservative model required by the task: n independent
# cases, per-case D-E hit ~ Bernoulli(p), C-EQ hit ~ Bernoulli(q), pairs
# observed; test = exact sign test on discordant pairs, ties dropped.
# MDE table at base q = 0.5 (p0 both arms), detect p - q = d.
print("\n(n vs MDE: exact two-sided sign test on paired case-level hits, "
      "base 50% vs 50%+d, alpha 0.05, power 0.8 target)")
for n in range(4, 21):
    # size: enumerate pairs (D-E hit, C-EQ hit) at p=q=0.5
    # sign test statistic = #D-E-only - #CEQ-only among discordant; exact p-value
    # via distribution. Compute rejection region at p=q=0.5.
    from math import comb
    def pair_prob(dh, ch, t, n, q1=0.5):
        # P(dh D-E-only, ch C-EQ-only, t ties), independent Bernoulli pairs
        p11 = q1 * q1; p00 = (1 - q1) * (1 - q1); p10 = q1 * (1 - q1); p01 = (1 - q1) * q1
        rest = n - dh - ch - t
        # choose cells
        import math
        multinom = math.factorial(n) // (math.factorial(dh) * math.factorial(ch)
                                         * math.factorial(t) * math.factorial(rest))
        return multinom * (p10 ** dh) * (p01 ** ch) * (p11 ** t) * (p00 ** rest)

    def sign_pvalue(dh, ch):
        nd = dh + ch
        if nd == 0:
            return 1.0
        k = min(dh, ch)
        return min(1.0, 2 * sum(stats.binom.pmf(j, nd, 0.5) for j in range(0, k + 1)))

    rej = set()
    size = 0.0
    for dh in range(n + 1):
        for ch in range(n + 1 - dh):
            for t in range(n + 1 - dh - ch):
                pr = pair_prob(dh, ch, t, n, 0.5)
                if sign_pvalue(dh, ch) <= 0.05:
                    rej.add((dh, ch, t))
                if True:
                    size += pr
    # power at alternative p = 0.5 + d for D-E, q = 0.5 for C-EQ
    def power_at(d):
        q1 = 0.5 + d; q = 0.5
        p11 = q1 * q; p00 = (1 - q1) * (1 - q); p10 = q1 * (1 - q); p01 = (1 - q1) * q
        import math
        pw = 0.0
        for dh in range(n + 1):
            for ch in range(n + 1 - dh):
                for t in range(n + 1 - dh - ch):
                    if (dh, ch, t) not in rej:
                        continue
                    rest = n - dh - ch - t
                    multinom = math.factorial(n) // (math.factorial(dh)
                                                     * math.factorial(ch)
                                                     * math.factorial(t)
                                                     * math.factorial(rest))
                    pw += multinom * (p10 ** dh) * (p01 ** ch) * (p11 ** t) * (p00 ** rest)
        return pw
    mdes = [d for d in [0.05 * i for i in range(1, 21)] if power_at(d) >= 0.8]
    mde = mdes[0] if mdes else "> 1.00 (not reachable)"
    print(f"  n={n:2d}: size@50/50={size:.4f}  MDE(alpha.05,power.8)={mde}")

# specific required number: detect +25pp (50% -> 75%), exact two-sided binomial
# on D-E case-level hit count vs 50% reference (one-armed exact binomial, the
# conservative paired-equivalent when C-EQ is treated at its null 50%).
print("\n(+25pp: exact two-sided binomial test, H0 p=0.5, Ha p=0.75, "
      "alpha 0.05 two-sided)")
for n in range(4, 41):
    # rejection region from null distribution
    rej = []
    for k in range(n + 1):
        two_sided = sum(stats.binom.pmf(k2, n, 0.5) for k2 in range(n + 1)
                        if stats.binom.pmf(k2, n, 0.5) <= stats.binom.pmf(k, n, 0.5))
        if two_sided <= 0.05:
            rej.append(k)
    pw = sum(stats.binom.pmf(k, n, 0.75) for k in rej)
    mark = "  <-- first n reaching power 0.8" if pw >= 0.8 else ""
    if n >= 4 and (n <= 25 or pw < 0.8):
        print(f"  n={n:2d}: rej={rej} power={pw:.4f}{mark}")
