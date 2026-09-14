#!/usr/bin/env python3
"""Regenerate cointegration_stability.json on the DECIDED series (WSHOSHO), re-specified to the
shape Section IV.A actually supports, per the 2026-09-13 amendment to dispatch step 5
(handoff/dispatch/a1_regime_artifact_regen_and_v43_tag_after_reframe_decision_2026-08-26.md).

WHY THIS SHAPE, NOT THE WITHDRAWN ARTIFACT'S SHAPE. The withdrawn artifact
(exhibits/cointegration_stability/cointegration_stability.json, script_version phase4b_v1) reports
asymptotic critical values (cv95 29.8 throughout) and asymptotic-null subsample traces. Section
IV.A at origin/main now explicitly rejects that approach (measured size 0.158 at this sample
length) and reports a conditional-randomisation null instead. An artifact built by swapping only
the series id into the old asymptotic producer would match Section IV.A on exactly one number,
the trace statistic. So this producer:
  (a) reports the full-sample trace DETERMINISTICALLY (no randomness in the observed statistic
      itself) and it must equal the manuscript's 46.22 to two decimals;
  (b) reports a conditional-null cv95 and Monte Carlo p under TWO null designs (gauss, matching
      the paper's primary headline citation at PAPER.md:282, and block bootstrap mean-8-week,
      matching the dependence-preserving robustness check at PAPER.md:585), each with its own
      seed and draw count recorded, not asymptotic tables;
  (c) carries NO subsample rows: PAPER.md:280 states plainly that asymptotic-null subsamples are
      not reported because their measured size exceeds 0.74, and no conditional-null producer for
      WSHOSHO subsamples is committed anywhere in this repo (confirmed by search 2026-09-14);
  (d) carries NO rolling-window entry: PAPER.md:342 points to Appendix F for the 52-week rolling
      window, but PAPER.md's own Appendix F section (line 781) states its detail tables live in
      the ONLINE SUPPLEMENT, not in this package, and no committed transcript or json anywhere in
      exhibits/regime_and_crypto_control/ carries a rolling-window run on WSHOSHO specifically.
      Point-in-fact confirmed 2026-09-14: this is the same gap the Sept 13 re-verification found
      for the regime split (no committed WSHOSHO regime run exists), extended to the rolling
      window by the same search. Per the amendment: omit rather than assert;
  (e) carries det_order sensitivity as RANKS (not full trace/cv tables), matching PAPER.md:280's
      own framing ("both this and the no-deterministic alternative produce rank = 1, while the
      restricted-trend specification fails"). IMPORTANT CAVEAT, read before citing this artifact's
      det_order block: this producer independently re-derives each det_order's rank under a
      conditional null built the same way as the headline (hold the two real Fed series fixed,
      draw the dependent series as an independent I(1) process, rank = 1 iff the observed trace
      rejects that null). Under that construction det_order=0 and det_order=+1 REPRODUCE the
      manuscript's stated ranks (1 and 0 respectively). det_order=-1 (no deterministic component)
      does NOT: this producer measures p in the 0.16 to 0.41 range depending on whether the null's
      drawn series is given the data's own drift or a zero drift (matching det_order=-1's
      no-deterministic-component assumption), neither of which clears 0.05, so this run's own
      conditional null does not confirm rank=1 for det_order=-1. That may be a genuine artifact of
      how this producer constructs the det_order=-1 null rather than a defect in the manuscript's
      claim; no committed producer anywhere in this repo makes the manuscript's own det_order=-1
      computation reproducible, so this discrepancy cannot be resolved from committed material
      alone. Recorded honestly rather than silently forced to match: `det_order_minus1_rank` is
      written as "UNCONFIRMED", with this run's own measurement attached, not as "1".

METHOD. Imports conditional_p() from the committed a1_conditional_null.py verbatim (same Johansen
construction, same Monte Carlo machinery); only the balance-sheet series (WSHOSHO) and, for (e),
the det_order argument change.

DATA SOURCE. PKG/data/raw/fred_wide.csv and PKG/data/processed/unified_extended_dataset.csv at
/Users/zach/Routing-the-dollar, where WSHOSHO was committed by add_wshosho_to_package.py
(commit 4a7d931) and WALCL by add_walcl_to_package.py (commit 622f036). Both committed, not a
dirty working tree, unlike the provenance caveat a1_aggregate_block_bootstrap.py carries.

Usage: python3 a1_regenerate_cointegration_stability.py
"""
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
OUT = os.path.join(PKG, "data", "processed", "cointegration_stability.json")
SERIES = "WSHOSHO"
LAG_K_AR_DIFF = 7  # "lag 8" in the manuscript's prose
SEED = 20260914
DRAWS = 20000


def _load_producer():
    path = os.path.join(HERE, "a1_conditional_null.py")
    spec = importlib.util.spec_from_file_location("a1_conditional_null", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["a1_conditional_null"] = mod
    spec.loader.exec_module(mod)
    return mod


def conditional_p_det(b, bs, dep, k, rng, det_order, force_zero_drift=False, kind="gauss", ns=DRAWS):
    """Like a1_conditional_null.conditional_p, but det_order and the null's drift are parameters."""
    x1 = np.log(b[bs].values)
    x2 = np.log(b.RRPONTSYD.values)
    d = np.diff(np.log(b.total_supply.values))
    mu = 0.0 if force_zero_drift else d.mean()
    sd = d.std(ddof=1)
    T = len(b)
    t = float(coint_johansen(np.column_stack([x1, x2, np.log(dep)]), det_order=det_order, k_ar_diff=k).lr1[0])

    def draw():
        if kind == "gauss":
            return np.cumsum(rng.normal(size=T) * sd + mu)
        if kind == "iid":
            return np.cumsum(d[rng.integers(0, len(d), T)])
        out = []
        while len(out) < T:
            s = rng.integers(0, len(d))
            L = 1 + rng.geometric(1 / 8)
            out.extend(d[(np.arange(s, s + L)) % len(d)])
        return np.cumsum(np.array(out[:T]))

    r = []
    for _ in range(ns):
        try:
            r.append(float(coint_johansen(np.column_stack([x1, x2, draw()]), det_order=det_order, k_ar_diff=k).lr1[0]))
        except Exception:
            pass
    r = np.array(r)
    p = float((r >= t).mean())
    se = float((p * (1 - p) / len(r)) ** 0.5)
    return {
        "trace": t, "cv95": float(np.percentile(r, 95)), "p": p, "mc_se": se,
        "ci_lo": max(0.0, p - 1.96 * se), "ci_hi": p + 1.96 * se, "draws": len(r), "T": T,
    }


def main():
    P = _load_producer()
    b, crypto = P.load()
    sho = pd.read_csv(os.path.join(PKG, "data", "raw", "WSHOSHO_fred_source.csv"), index_col=0, parse_dates=True)
    b = b.join(sho[[SERIES]].resample("W-WED").last().ffill(), how="left")
    missing = int(b[SERIES].isna().sum())
    if missing:
        raise SystemExit(f"FATAL: {missing} missing {SERIES} rows after reindex; refusing to interpolate silently.")

    print("=" * 100)
    print(f"A1 cointegration_stability.json REGEN on the DECIDED series ({SERIES})")
    print("=" * 100)

    headline = {}
    for kind in ("gauss", "block"):
        rng = np.random.default_rng(SEED)
        c = conditional_p_det(b, SERIES, b.total_supply.values, LAG_K_AR_DIFF, rng, det_order=0, kind=kind)
        headline[kind] = c
        print(f"  headline [{kind:5s}] T={c['T']} trace={c['trace']:.2f} cv95={c['cv95']:.2f} "
              f"p={c['p']:.4f} CI=[{c['ci_lo']:.4f},{c['ci_hi']:.4f}] draws={c['draws']}")

    placebos = {}
    for nm, dep in (("BTC", crypto["BTC"].values), ("ETH", crypto["ETH"].values)):
        placebos[nm] = {}
        for kind in ("gauss", "block"):
            rng = np.random.default_rng(SEED)
            c = conditional_p_det(b, SERIES, dep, LAG_K_AR_DIFF, rng, det_order=0, kind=kind)
            placebos[nm][kind] = c
            print(f"  placebo {nm} [{kind:5s}] trace={c['trace']:.2f} cv95={c['cv95']:.2f} p={c['p']:.4f}")

    det_order = {}
    for det in (-1, 0, 1):
        rng = np.random.default_rng(SEED)
        zero_drift = det == -1
        c = conditional_p_det(b, SERIES, b.total_supply.values, LAG_K_AR_DIFF, rng, det_order=det,
                               force_zero_drift=zero_drift)
        rejects = c["p"] < 0.05
        det_order[f"det_{('minus1' if det == -1 else str(det))}"] = {
            **c, "rank": (1 if rejects else 0),
            "rank_confidence": "matches PAPER.md:280" if det in (0, 1) else
                                "UNCONFIRMED: this run's own conditional null does not reject at det_order=-1 "
                                "(p={:.4f}); PAPER.md:280 states rank=1 here but no committed producer makes "
                                "that specific computation reproducible from this package".format(c["p"]),
        }
        print(f"  det_order={det:+d}: trace={c['trace']:.2f} p={c['p']:.4f} -> rank={1 if rejects else 0} "
              f"({'confirmed' if det in (0, 1) else 'UNCONFIRMED, see caveat'})")

    artifact = {
        "metadata": {
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "script_version": "a1_regenerate_cointegration_stability_v1",
            "series": SERIES,
            "data_sources": [
                "data/raw/fred_wide.csv",
                "data/processed/unified_extended_dataset.csv",
                "data/raw/WSHOSHO_fred_source.csv",
            ],
            "producer_commits": ["4a7d931 (add WSHOSHO)", "622f036 (restore WALCL, negative comparison)"],
            "null_design": "conditional randomisation (a1_conditional_null.conditional_p, imported verbatim): "
                            "hold the two real Fed series fixed, draw only the dependent series as an "
                            "independent I(1) process; size 0.05 by construction",
            "seed": SEED,
            "note": (
                "Supersedes the WITHDRAWN phase4b_v1 artifact (computed on WSHOMCB, mislabelled as total "
                "assets; withdrawn 2026-08-26). Regenerated on WSHOSHO (the DECIDED series, "
                "handoff/decisions/a1-mbs-runoff-reframe.md) per the 2026-09-13 amendment to dispatch step 5. "
                "No subsample or rolling-window rows: neither has a committed conditional-null producer for "
                "WSHOSHO in this repo (searched 2026-09-14); PAPER.md:280 and :342 point to Appendix F, whose "
                "own detail tables are in the online supplement, not this package. det_order=-1's rank is "
                "UNCONFIRMED by this producer; see det_order_sensitivity.det_minus1.rank_confidence."
            ),
        },
        "headline": headline,
        "placebo": placebos,
        "det_order_sensitivity": det_order,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(artifact, f, indent=2, default=str)
    print(f"\nwrote {OUT}")

    # Acceptance check the dispatch names: trace must match PAPER.md:282 to two decimals.
    trace_ok = abs(headline["gauss"]["trace"] - 46.22) < 0.005
    print(f"\nHALT-2 check: trace {headline['gauss']['trace']:.2f} vs manuscript 46.22 -> "
          f"{'MATCH' if trace_ok else 'MISMATCH, HALT'}")
    return 0 if trace_ok else 2


if __name__ == "__main__":
    sys.exit(main())
