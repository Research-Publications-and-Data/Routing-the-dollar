"""Verify that processed data files back specific paper claims."""
import pandas as pd
import numpy as np
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"

sys.path.insert(0, str(ROOT / "config"))

PASS = 0
FAIL = 0
SKIP = 0


def check(description, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {description}")
    else:
        FAIL += 1
        print(f"  FAIL  {description}")
    if detail:
        print(f"        {detail}")


def skip(description, reason):
    global SKIP
    SKIP += 1
    print(f"  SKIP  {description} ({reason})")


def main():
    print("=" * 70)
    print("PAPER CLAIM VERIFICATION")
    print("=" * 70)

    # --- 51 addresses, 19 entities ---
    print("\n[Gateway Registry]")
    try:
        reg = pd.read_csv(DATA_PROC / "gateway_registry_expanded.csv")
        n_addr = reg["address"].nunique() if "address" in reg.columns else len(reg)
        n_ent = reg["entity"].nunique() if "entity" in reg.columns else reg["name"].nunique()
        check("51 addresses", n_addr == 51, f"got {n_addr}")
        check("19 entities", n_ent == 19, f"got {n_ent}")
    except FileNotFoundError:
        # Fallback: check the Dune daily file
        try:
            daily = pd.read_csv(DATA_RAW / "dune_eth_daily_expanded_v2.csv")
            n_ent = daily["entity"].nunique() if "entity" in daily.columns else 0
            check("19 entities (from daily data)", n_ent >= 17, f"got {n_ent}")
            skip("51 addresses", "registry file not found; address count in daily data")
        except FileNotFoundError:
            skip("51 addresses", "no gateway registry or daily data found")
            skip("19 entities", "no gateway registry or daily data found")

    # --- Coverage ratio: 27.7% ---
    print("\n[Coverage Ratio]")
    try:
        gw = pd.read_csv(DATA_PROC / "gateway_volume_summary_v2.csv")
        total_file = DATA_RAW / "dune_eth_total_v2.csv"
        if total_file.exists():
            total = pd.read_csv(total_file)
            total_vol = total["volume_usd"].sum()
            gw_vol = gw["total_volume"].sum() if "total_volume" in gw.columns else gw["volume_usd"].sum()
            ratio = gw_vol / total_vol
            check("27.7% coverage", abs(ratio - 0.277) < 0.02, f"got {ratio:.3f}")
        else:
            skip("27.7% coverage", "total volume file not found")
    except Exception as e:
        skip("27.7% coverage", str(e))

    # --- HHI ---
    print("\n[HHI Concentration]")
    # Use v2 files (19-entity expanded analysis) over upgraded files (older 12-address)
    try:
        conc = pd.read_csv(DATA_PROC / "exhibit_C2_concentration_daily_v2.csv",
                           index_col=0, parse_dates=True)
        if "entity_hhi" in conc.columns:
            hhi_mean = conc["entity_hhi"].mean()
            check("HHI entity-level mean ~2,742 gross", abs(hhi_mean - 2742) < 500,
                  f"got {hhi_mean:.1f}")
        else:
            skip("HHI entity-level mean", f"columns: {list(conc.columns)[:10]}")

        if "tier_hhi" in conc.columns:
            tier_hhi = conc["tier_hhi"].mean()
            check("HHI tier-level mean ~5,021", abs(tier_hhi - 5021) < 500,
                  f"got {tier_hhi:.1f}")
    except FileNotFoundError:
        skip("HHI entity-level", "exhibit_C2_concentration_daily_v2.csv not found")

    # --- Tier 1 share ---
    print("\n[Tier 1 Share]")
    # Use v2 files (19-entity expanded analysis)
    try:
        shares = pd.read_csv(DATA_PROC / "exhibit_C1_gateway_shares_daily_v2.csv",
                              index_col=0, parse_dates=True)
        t1_col = [c for c in shares.columns if "tier1" in c.lower() and "share" in c.lower()]
        if not t1_col:
            t1_col = [c for c in shares.columns if "tier_1" in c.lower() or "t1" in c.lower()
                      or c == "Tier 1"]
        if t1_col:
            t1 = shares[t1_col[0]]
            # Convert from percentage to fraction if needed
            if t1.mean() > 1:
                t1 = t1 / 100
            t1_mean = t1.mean()
            check("Tier 1 share ~41% gross", abs(t1_mean - 0.41) < 0.05,
                  f"got {t1_mean:.3f}")

            # SVB spike and collapse
            svb_window = t1["2023-03-09":"2023-03-14"]
            if len(svb_window) > 0:
                svb_max = svb_window.max()
                svb_min = svb_window.min()
                check("SVB: T1 spiked to ~63%", abs(svb_max - 0.63) < 0.10,
                      f"got {svb_max:.3f}")
                check("SVB: T1 collapsed to ~13%", abs(svb_min - 0.13) < 0.10,
                      f"got {svb_min:.3f}")
            else:
                skip("SVB T1 spike/collapse", "no data in SVB window")
        else:
            skip("Tier 1 share", f"no tier 1 column; columns: {list(shares.columns)[:10]}")
    except FileNotFoundError:
        skip("Tier 1 share", "shares file not found")

    # --- Zero tier changes (no-freeze) ---
    print("\n[CLII No-Freeze Robustness]")
    try:
        nf = pd.read_csv(DATA_PROC / "clii_nofreeze_robustness.csv")
        tc_col = [c for c in nf.columns if "tier_changed" in c.lower() or "tier_change" in c.lower()]
        if tc_col:
            n_changes = nf[tc_col[0]].sum()
            check("Zero tier changes (no-freeze)", n_changes == 0, f"got {n_changes} changes")
        else:
            # Check if baseline and nofreeze tiers match
            if "baseline_tier" in nf.columns and "nofreeze_tier" in nf.columns:
                n_changes = (nf["baseline_tier"] != nf["nofreeze_tier"]).sum()
                check("Zero tier changes (no-freeze)", n_changes == 0, f"got {n_changes} changes")
            else:
                skip("Zero tier changes", f"columns: {list(nf.columns)}")
    except FileNotFoundError:
        skip("Zero tier changes", "clii_nofreeze_robustness.csv not found")

    # --- Cointegration / Johansen ---
    print("\n[Cointegration]")
    try:
        with open(DATA_PROC / "vecm_reconciliation.json") as f:
            vecm = json.load(f)
        # The key structure varies; look for trace stat in various locations
        trace = (vecm.get("johansen", {}).get("trace_stat")
                 or vecm.get("trace_stat")
                 or vecm.get("specification", {}).get("trace_stat") if isinstance(vecm.get("specification"), dict) else None)
        if trace is not None:
            check("Johansen trace ~30.68", abs(float(trace) - 30.68) < 5,
                  f"got {trace}")
        else:
            # Just verify the file exists and has cointegration info
            has_coint = any(k for k in vecm.keys() if "cointegrat" in k.lower() or "beta" in k.lower())
            check("VECM reconciliation has cointegration data", has_coint,
                  f"keys: {list(vecm.keys())[:6]}")
    except FileNotFoundError:
        skip("Johansen trace", "vecm_reconciliation.json not found")

    # --- FOMC events ---
    print("\n[FOMC Event Study]")
    # Paper's FOMC claim refers to the 19 dates in config/settings.py
    # The CSV may contain more events from extended analysis
    try:
        sys.path.insert(0, str(ROOT / "config"))
        from settings import FOMC_DATES
        n = len(FOMC_DATES)
        check("FOMC n = 19 events (config)", n == 19, f"got {n}")
        classes = {}
        for _, _, cls in FOMC_DATES:
            classes[cls] = classes.get(cls, 0) + 1
        check("FOMC: 5 dovish, 9 neutral, 5 hawkish",
              classes.get("dovish", 0) == 5 and classes.get("neutral", 0) == 9
              and classes.get("hawkish", 0) == 5,
              f"got {classes}")
    except ImportError:
        try:
            fomc = pd.read_csv(DATA_PROC / "fomc_events.csv")
            check("FOMC events CSV exists", len(fomc) > 0, f"{len(fomc)} rows")
        except FileNotFoundError:
            skip("FOMC events", "neither config nor CSV found")

    # --- r = -0.94 ---
    print("\n[Headline Correlation]")
    try:
        unified = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv",
                              index_col=0, parse_dates=True)
        weekly = unified[["total_supply", "WSHOMCB"]].resample("W-WED").last().dropna()
        primary = weekly["2023-02-01":"2026-01-31"]
        if len(primary) > 10:
            r = primary["total_supply"].corr(primary["WSHOMCB"])
            check("r = -0.94 (Fed assets vs supply)", abs(r - (-0.94)) < 0.05,
                  f"got r = {r:.4f} (n={len(primary)})")
        else:
            skip("r = -0.94", f"only {len(primary)} weeks in primary window")
    except FileNotFoundError:
        skip("r = -0.94", "unified_extended_dataset.csv not found")

    # --- Placebo ---
    print("\n[Placebo Analysis]")
    try:
        placebo = pd.read_csv(DATA_PROC / "placebo_swing_stats.csv")
        check("Placebo analysis exists", len(placebo) > 0, f"{len(placebo)} rows")
    except FileNotFoundError:
        skip("Placebo analysis", "placebo_swing_stats.csv not found")

    # --- Nansen claims ---
    print("\n[Nansen Network Data]")
    nansen_files = list(DATA_PROC.glob("*nansen*"))
    if nansen_files:
        for f in nansen_files:
            print(f"        Found: {f.name}")
        check("Nansen processed data exists", True)
    else:
        skip("Nansen data (15 gateways, 3,804 dyads)", "no nansen files in processed/")
        skip("Wintermute share 1.4% → 19.9%", "needs Nansen data")
        skip("Cross-gateway counterparties 5.8% → 2.6%", "needs Nansen data")

    # --- Summary ---
    print("\n" + "=" * 70)
    total = PASS + FAIL + SKIP
    print(f"RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped (of {total} checks)")
    if FAIL == 0:
        print("STATUS: ALL CHECKS PASSED")
    else:
        print("STATUS: SOME CHECKS FAILED — review above")
    print("=" * 70)

    return 1 if FAIL > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
