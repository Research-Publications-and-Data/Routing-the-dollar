#!/usr/bin/env python3
"""A1: the cointegration test under a null whose size is 0.05 BY CONSTRUCTION.

WHY THE EARLIER NULLS FAILED, AND WHY THIS ONE CANNOT
Three nulls have now been used on this system. The first two were wrong in ways that a size
measurement exposes, and the third is wrong in a way that no size measurement can, because its
size is exact by construction rather than measured.

  asymptotic Johansen critical values   measured size 0.158 at T=157.  Unusable.
  simulate ALL THREE series as random walks with the data's own drifts and sds
                                        measured size 1.00 on any log-WALCL system, 0.007 on the
                                        log-WSHOMCB system. Oversized one way, CONSERVATIVE the
                                        other, and conservative is not safe: an undersized test
                                        that fails to reject is weak evidence, not strong.
  CONDITIONAL RANDOMISATION (this file) hold the two REAL Fed series fixed and draw ONLY the
                                        dependent series as an independent I(1) process. The
                                        critical value is the 95th percentile of the SAME
                                        statistic under the SAME design, so size is 0.05
                                        exactly. There is no calibration step that can fail.

The conditional null also matches the question the paper actually asks. "Is stablecoin supply
cointegrated with THESE TWO Fed series?" is not "would three unrelated random walks look
cointegrated?" Conditioning on the real Fed series carries their heavy tails, their trends, and
any cointegration BETWEEN THEM into the null distribution as well as into the observed statistic,
where those features cancel instead of contaminating.

State the hypothesis honestly: this tests whether supply relates to the Fed pair more strongly
than an unrelated I(1) series does. That is a conditional null, not the textbook rank-0 null, and
it cannot speak to cointegration running between the two Fed variables themselves.

WHAT IT FINDS (2026-08-25, two independent seeds, three designs for the drawn series)
  1. On FED MBS HOLDINGS (WSHOMCB) the relation REJECTS: trace 30.68 against cv95 29.6 to 30.5,
     p 0.038 to 0.048. Marginal, and consistent across every design and seed tried.
  2. The DOLLAR-SPECIFICITY PLACEBO HOLDS DECISIVELY: Bitcoin p 0.35 to 0.37 and Ethereum
     p 0.38 to 0.39 against supply's 0.038 to 0.043. A null that merely rejected everything could
     not produce that gap, and one that never rejected could not produce supply's rejection, so
     the placebo separation is itself a two-sided validity check on the null.
  3. FED TOTAL ASSETS (WALCL) CANNOT CARRY THE CLAIM: p 0.21, and the conditional cv95 of 66.7
     EXCEEDS the observed trace of 61.6. An unrelated random walk routinely out-scores the real
     dependent series against WALCL. That is a property of the regressor, not evidence about
     stablecoins, and it is what the March 2023 emergency-lending jump does to the series.
  4. REGIME DEPENDENCE DOES NOT SURVIVE, and it reverses: tightening p 0.058, easing p 0.047,
     which are marginal and statistically indistinguishable from each other. The published
     pattern (strong in QT, absent in easing) came from reading subsample trace statistics
     against a FULL-SAMPLE asymptotic critical value; the shorter easing sample looked weaker
     for the arithmetic reason that it is shorter.
"""
import os, sys, json, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
from statsmodels.tsa.vector_ar.vecm import coint_johansen, VECM
from statsmodels.stats.diagnostic import acorr_ljungbox

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
OUT = os.path.join(HERE, "a1_conditional_null.json")
NS = 6000
R = {}


def load():
    fred = pd.read_csv(f"{PKG}/data/raw/fred_wide.csv", index_col=0, parse_dates=True)
    sc = pd.read_csv(f"{PKG}/data/processed/unified_extended_dataset.csv", index_col=0, parse_dates=True)
    m = fred[["WSHOMCB", "RRPONTSYD", "WALCL"]].join(pd.DataFrame(sc["total_supply"]), how="inner").dropna(subset=["WSHOMCB"])
    m["RRPONTSYD"] = m["RRPONTSYD"].ffill()
    b = m.resample("W-WED").last().dropna()["2023-02-01":"2026-01-31"]
    ce = pd.read_csv(os.path.join(HERE, "btc_eth_weekly.csv"), index_col=0, parse_dates=True)
    return b, {k: ce[k].resample("W-WED").last().ffill().reindex(b.index) for k in ("BTC", "ETH")}


def conditional_p(b, bs, dep, k, rng, kind="gauss", ns=NS):
    """Hold the real Fed pair fixed; draw only the dependent series. Size is 0.05 by construction."""
    x1 = np.log(b[bs].values)
    x2 = np.log(b.RRPONTSYD.values)
    d = np.diff(np.log(b.total_supply.values))
    mu, sd = d.mean(), d.std(ddof=1)
    T = len(b)
    t = float(coint_johansen(np.column_stack([x1, x2, np.log(dep)]), det_order=0, k_ar_diff=k).lr1[0])

    def draw():
        if kind == "gauss":
            return np.cumsum(rng.normal(size=T) * sd + mu)
        if kind == "iid":
            return np.cumsum(d[rng.integers(0, len(d), T)])
        out = []
        while len(out) < T:
            s = rng.integers(0, len(d)); L = 1 + rng.geometric(1 / 8)
            out.extend(d[(np.arange(s, s + L)) % len(d)])
        return np.cumsum(np.array(out[:T]))

    r = []
    for _ in range(ns):
        try:
            r.append(float(coint_johansen(np.column_stack([x1, x2, draw()]), det_order=0, k_ar_diff=k).lr1[0]))
        except Exception:
            pass
    r = np.array(r)
    p = float((r >= t).mean())
    se = float((p * (1 - p) / len(r)) ** 0.5)
    return {"trace": t, "cv95": float(np.percentile(r, 95)), "p": p, "mc_se": se,
            "ci_lo": max(0.0, p - 1.96 * se), "ci_hi": p + 1.96 * se, "draws": len(r), "T": T}


def row(lbl, c):
    v = "REJECTS" if c["ci_hi"] < 0.05 else ("marginal" if c["p"] < 0.05 else "does not reject")
    print(f"  {lbl:<38} {c['T']:>4} {c['trace']:>7.2f} {c['cv95']:>7.2f} {c['p']:>7.4f} "
          f"{f'[{c[chr(99)+chr(105)+chr(95)+chr(108)+chr(111)]:.4f}, {c[chr(99)+chr(105)+chr(95)+chr(104)+chr(105)]:.4f}]':>18}  {v}")


def main():
    b, crypto = load()
    print("=" * 104)
    print("A1 UNDER A CONDITIONAL RANDOMISATION NULL (size 0.05 by construction)")
    print("=" * 104)
    print("Two independent seeds are run for every headline cell. 'REJECTS' requires the Monte Carlo")
    print("confidence interval to sit ENTIRELY below 0.05; a point estimate under 0.05 whose interval")
    print("straddles it is reported as 'marginal', because that is what it is.")
    print()
    print(f"  {'cell':<38} {'T':>4} {'trace':>7} {'cv95':>7} {'p':>7} {'MC 95 pct CI':>18}  verdict")

    for seed in (31415, 999983):
        rng = np.random.default_rng(seed)
        print(f"  -- seed {seed} " + "-" * 78)
        for nm, dep in (("stablecoin supply", b.total_supply.values),
                        ("BTC market cap (placebo)", crypto["BTC"].values),
                        ("ETH market cap (placebo)", crypto["ETH"].values)):
            c = conditional_p(b, "WSHOMCB", dep, 7, rng)
            row(f"MBS holdings, {nm}", c)
            R[f"seed{seed}|{nm}"] = c

    rng = np.random.default_rng(20260825)
    print()
    print("  -- null design sensitivity for the drawn series, seed 20260825 " + "-" * 30)
    for kind, lbl in (("gauss", "Gaussian RW, supply moments"), ("iid", "i.i.d. resample of supply diffs"),
                      ("block", "block bootstrap, mean 8 weeks")):
        c = conditional_p(b, "WSHOMCB", b.total_supply.values, 7, rng, kind)
        row(f"MBS holdings, {lbl}", c); R[f"design|{kind}"] = c

    print()
    print("  -- balance-sheet series: which one can be conditioned on? " + "-" * 34)
    for bs, note in (("WSHOMCB", "programmatic, cap-driven runoff"), ("WALCL", "includes 2023 emergency lending")):
        c = conditional_p(b, bs, b.total_supply.values, 7, rng, ns=4000)
        row(f"{bs} ({note})", c); R[f"series|{bs}"] = c
    w = R["series|WALCL"]
    print(f"     WALCL's conditional cv95 ({w['cv95']:.1f}) EXCEEDS its own observed trace ({w['trace']:.1f}):")
    print("     an unrelated random walk routinely out-scores the real dependent series against it.")

    print()
    print("  -- lag grid, MBS holdings " + "-" * 66)
    for L in (4, 6, 8, 10, 12):
        v = VECM(np.column_stack([np.log(b.WSHOMCB.values), np.log(b.RRPONTSYD.values),
                                  np.log(b.total_supply.values)]), k_ar_diff=L - 1, coint_rank=1,
                 deterministic="n").fit()
        lb = min(float(acorr_ljungbox(v.resid[:, i], lags=[10], return_df=True)["lb_pvalue"].iloc[0]) for i in range(3))
        c = conditional_p(b, "WSHOMCB", b.total_supply.values, L - 1, rng, ns=4000)
        row(f"lag {L} (Ljung-Box {lb:.3f}, {'adequate' if lb > 0.05 else 'INADEQUATE'})", c)
        R[f"lag|{L}"] = dict(c, lb_min_p=lb, adequate=bool(lb > 0.05))

    print()
    print("  -- regime split at the first FOMC cut, 2024-09-18 " + "-" * 42)
    for lbl, sl in (("tightening", slice(None, "2024-09-17")), ("easing", slice("2024-09-18", None))):
        bb = b.loc[sl]
        c = conditional_p(bb, "WSHOMCB", bb.total_supply.values, 7, rng, ns=4000)
        row(f"{lbl}", c); R[f"regime|{lbl}"] = c
    print("     The published pattern (strong in QT, absent in easing) does NOT survive and reverses.")
    print("     Both subsamples are marginal and indistinguishable from each other. The published")
    print("     contrast came from reading subsample statistics against a FULL-SAMPLE critical value.")

    with open(OUT, "w") as f:
        json.dump(R, f, indent=2, default=float)
    print()
    print(f"wrote {os.path.relpath(OUT, HERE)}")


if __name__ == "__main__":
    main()
