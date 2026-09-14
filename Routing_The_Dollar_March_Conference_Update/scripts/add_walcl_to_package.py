#!/usr/bin/env python3
"""Add WALCL (Fed total assets) to this package, alongside WSHOSHO (the decided series).

WHY. PAPER.md Section IV.A explicitly reports Fed total assets (WALCL) as a NEGATIVE comparison:
"total assets ... does not reject" (trace 61.56 vs conditional cv95 66.78-67.0, p about 0.19-0.22),
with the 2023 emergency-lending jump identified as the cause (excess kurtosis 41.6). WALCL is not
the paper's headline series (that is WSHOSHO, see add_wshosho_to_package.py), but it is needed to
reproduce this explicitly-discussed contrast from committed package data.

SOURCE, WHAT, IDEMPOTENCE, POSITIVE CONTROL: identical in structure to add_wshosho_to_package.py.
data/raw/WALCL_fred_source.csv beside this script (FRED public CSV endpoint, id=WALCL, no key).
Positive control: WALCL exceeds WSHOMCB everywhere on the shared 157-week primary-window
calendar (MBS holdings are a strict subset of total assets).
"""
import os, sys
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
SRC = os.path.join(PKG, "data", "raw", "WALCL_fred_source.csv")
WINDOW = ("2023-02-01", "2026-01-31")

TARGETS = [
    (os.path.join(PKG, "data", "raw", "fred_wide.csv"), "date"),
    (os.path.join(PKG, "data", "processed", "unified_extended_dataset.csv"), "date"),
]


def load_walcl():
    w = pd.read_csv(SRC, parse_dates=["observation_date"]).set_index("observation_date")["WALCL"]
    w = pd.to_numeric(w, errors="coerce").dropna()
    w.index.name = "date"
    return w


def positive_control(walcl):
    fred = pd.read_csv(TARGETS[0][0], index_col=0, parse_dates=True)
    mbs = fred["WSHOMCB"].dropna().loc[WINDOW[0]:WINDOW[1]]
    wal = walcl.loc[WINDOW[0]:WINDOW[1]]
    assert len(mbs) == 157, f"WSHOMCB window n={len(mbs)}, expected 157"
    assert len(wal) == 157, f"WALCL window n={len(wal)}, expected 157"
    assert mbs.index.equals(wal.index), "WALCL and WSHOMCB observation calendars differ"
    assert (wal.values > mbs.values).all(), "WALCL is not everywhere above WSHOMCB; wrong series or units"
    r = float(np.corrcoef(np.log(mbs.values), np.log(wal.values))[0, 1])
    print(f"  positive control PASS: same 157 Wednesdays; WALCL > WSHOMCB everywhere; log corr {r:+.4f}")
    print(f"    WSHOMCB ${mbs.min()/1e6:,.2f}T to ${mbs.max()/1e6:,.2f}T")
    print(f"    WALCL   ${wal.min()/1e6:,.2f}T to ${wal.max()/1e6:,.2f}T")
    return r


def add_column(path, index_name, walcl):
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    existed = "WALCL" in df.columns
    df["WALCL"] = walcl.reindex(df.index)
    df.index.name = index_name
    df.to_csv(path)
    back = pd.read_csv(path, index_col=0, parse_dates=True)
    got = back["WALCL"].dropna()
    want = walcl.reindex(back.index).dropna()
    assert got.index.equals(want.index) and np.allclose(got.values, want.values), f"write-back mismatch in {path}"
    print(f"  {'updated' if existed else 'added  '} WALCL in {os.path.relpath(path, PKG)}: "
          f"{len(got)} non-null of {len(back)} rows")
    return len(got)


def main():
    print("=" * 72)
    print("A1: add WALCL (Fed total assets, negative-comparison series) to the package")
    print("=" * 72)
    walcl = load_walcl()
    print(f"source {os.path.relpath(SRC, PKG)}: n={len(walcl)}, "
          f"{walcl.index.min().date()} to {walcl.index.max().date()}, all Wednesdays="
          f"{set(walcl.index.weekday) == {2}}")
    positive_control(walcl)
    for path, idx in TARGETS:
        add_column(path, idx, walcl)
    d = pd.read_csv(os.path.join(PKG, "data", "processed", "unified_extended_dataset.csv"))
    print()
    print(f"closure check (WALCL in unified_extended_dataset.csv): "
          f"{'PASS' if 'WALCL' in d.columns else 'FAIL'}")
    return 0 if "WALCL" in d.columns else 1


if __name__ == "__main__":
    sys.exit(main())
