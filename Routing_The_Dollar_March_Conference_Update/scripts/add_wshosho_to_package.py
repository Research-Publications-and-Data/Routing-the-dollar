#!/usr/bin/env python3
"""Add WSHOSHO (Fed securities held outright, the paper's DECIDED balance-sheet series) to this
package.

WHY. handoff/decisions/a1-mbs-runoff-reframe.md in the program's workflow repo was DECIDED
2026-09-14: this paper's long-run claim is reported on FRED WSHOSHO (Securities Held Outright:
All, i.e. Treasuries plus MBS), not on WSHOMCB (MBS alone, already in this package) or WALCL
(total assets, not the decided series). PAPER.md Section IV.A reports the resulting headline
(trace 46.22, conditional-null cv95 43.7, p = 0.030); this package never carried the series that
produced it. This script closes that gap.

WHAT. Adds a WSHOSHO column to:

    data/raw/fred_wide.csv
    data/processed/unified_extended_dataset.csv

stamped exactly the way WSHOMCB already is (Wednesday-dated, NaN on other days, units of
millions of USD). IDEMPOTENT: re-running overwrites the column with the same values. Every write
is verified by re-reading the file from disk, never from the in-memory frame.

SOURCE. data/raw/WSHOSHO_fred_source.csv and data/raw/TREAST_fred_source.csv beside this script's
data directory: the FRED public CSV endpoint, no key required,
    https://fred.stlouisfed.org/graph/fredgraph.csv?id=WSHOSHO
    https://fred.stlouisfed.org/graph/fredgraph.csv?id=TREAST
the same no-key channel scripts/01_fred_pull.py uses. TREAST is read only for the positive
control below and is not itself added to the package: the decided series is the aggregate alone.

POSITIVE CONTROL. Before writing: (1) WSHOSHO and WSHOMCB share an observation calendar over the
primary window (n=157 Wednesdays); (2) WSHOSHO exceeds WSHOMCB everywhere (MBS is a strict subset
of the aggregate); (3) WSHOSHO minus TREAST minus WSHOMCB, the federal-agency-debt residual (the
aggregate's small third component), is small and stable. Measured before writing this assertion:
$2,346M to $2,348M across all 157 weeks (0.029% to 0.038% of WSHOSHO), matching the Fed's
long-held, near-static small agency-debt position. The assertion bounds it at 0% to 1% of
WSHOSHO: generous around the measured range, tight enough to catch a wrong series, wrong units,
or a misaligned join, any of which would produce a residual comparable to WSHOSHO itself.
"""
import os, sys
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
SRC = os.path.join(PKG, "data", "raw", "WSHOSHO_fred_source.csv")
TREAST_SRC = os.path.join(PKG, "data", "raw", "TREAST_fred_source.csv")
WINDOW = ("2023-02-01", "2026-01-31")

TARGETS = [
    (os.path.join(PKG, "data", "raw", "fred_wide.csv"), "date"),
    (os.path.join(PKG, "data", "processed", "unified_extended_dataset.csv"), "date"),
]


def load_series(path, col):
    s = pd.read_csv(path, parse_dates=["observation_date"]).set_index("observation_date")[col]
    s = pd.to_numeric(s, errors="coerce").dropna()
    s.index.name = "date"
    return s


def positive_control(wshosho):
    """A wrong series, wrong units, or transcription error must fail here, not silently propagate."""
    fred = pd.read_csv(TARGETS[0][0], index_col=0, parse_dates=True)
    mbs = fred["WSHOMCB"].dropna().loc[WINDOW[0]:WINDOW[1]]
    sho = wshosho.loc[WINDOW[0]:WINDOW[1]]
    treast = load_series(TREAST_SRC, "TREAST").loc[WINDOW[0]:WINDOW[1]]
    assert len(mbs) == 157, f"WSHOMCB window n={len(mbs)}, expected 157"
    assert len(sho) == 157, f"WSHOSHO window n={len(sho)}, expected 157"
    assert len(treast) == 157, f"TREAST window n={len(treast)}, expected 157"
    assert mbs.index.equals(sho.index), "WSHOSHO and WSHOMCB observation calendars differ"
    assert mbs.index.equals(treast.index), "WSHOSHO and TREAST observation calendars differ"
    assert (sho.values > mbs.values).all(), "WSHOSHO is not everywhere above WSHOMCB; wrong series or units"
    resid = sho.values - treast.values - mbs.values
    resid_pct = resid / sho.values * 100
    assert (resid_pct >= 0.0).all() and (resid_pct <= 1.0).all(), (
        f"WSHOSHO - TREAST - WSHOMCB residual out of [0%, 1%] of WSHOSHO: "
        f"min {resid_pct.min():.4f}%, max {resid_pct.max():.4f}%; wrong series, wrong units, "
        f"or a misaligned join"
    )
    r = float(np.corrcoef(np.log(mbs.values), np.log(sho.values))[0, 1])
    print(f"  positive control PASS: same 157 Wednesdays; WSHOSHO > WSHOMCB everywhere; log corr {r:+.4f}")
    print(f"    WSHOMCB  ${mbs.min()/1e6:,.2f}T to ${mbs.max()/1e6:,.2f}T")
    print(f"    TREAST   ${treast.min()/1e6:,.2f}T to ${treast.max()/1e6:,.2f}T")
    print(f"    WSHOSHO  ${sho.min()/1e6:,.2f}T to ${sho.max()/1e6:,.2f}T")
    print(f"    residual (federal agency debt) ${resid.min():,.0f}M to ${resid.max():,.0f}M "
          f"({resid_pct.min():.4f}% to {resid_pct.max():.4f}% of WSHOSHO)")
    return r


def add_column(path, index_name, wshosho):
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    existed = "WSHOSHO" in df.columns
    df["WSHOSHO"] = wshosho.reindex(df.index)
    df.index.name = index_name
    df.to_csv(path)
    back = pd.read_csv(path, index_col=0, parse_dates=True)
    got = back["WSHOSHO"].dropna()
    want = wshosho.reindex(back.index).dropna()
    assert got.index.equals(want.index) and np.allclose(got.values, want.values), f"write-back mismatch in {path}"
    print(f"  {'updated' if existed else 'added  '} WSHOSHO in {os.path.relpath(path, PKG)}: "
          f"{len(got)} non-null of {len(back)} rows")
    return len(got)


def main():
    print("=" * 72)
    print("A1: add WSHOSHO (Fed securities held outright, DECIDED series) to the package")
    print("=" * 72)
    wshosho = load_series(SRC, "WSHOSHO")
    print(f"source {os.path.relpath(SRC, PKG)}: n={len(wshosho)}, "
          f"{wshosho.index.min().date()} to {wshosho.index.max().date()}, all Wednesdays="
          f"{set(wshosho.index.weekday) == {2}}")
    positive_control(wshosho)
    for path, idx in TARGETS:
        add_column(path, idx, wshosho)
    d = pd.read_csv(os.path.join(PKG, "data", "processed", "unified_extended_dataset.csv"))
    print()
    print(f"closure check (WSHOSHO in unified_extended_dataset.csv): "
          f"{'PASS' if 'WSHOSHO' in d.columns else 'FAIL'}")
    return 0 if "WSHOSHO" in d.columns else 1


if __name__ == "__main__":
    sys.exit(main())
