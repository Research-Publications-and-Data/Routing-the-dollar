"""B.2: KPSS test on differenced Fed assets to resolve I(1) vs I(2)."""
import pandas as pd, numpy as np, json, sys, warnings
warnings.filterwarnings("ignore")
from statsmodels.tsa.stattools import kpss, adfuller
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

def main():
    print("=" * 60)
    print("B.2: KPSS TEST ON DIFFERENCED FED ASSETS")
    print("=" * 60)

    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    wshomcb = fred["WSHOMCB"].dropna()
    weekly = wshomcb.resample("W-WED").last().dropna()
    primary = weekly["2023-02-01":"2026-01-31"]
    log_series = np.log(primary)

    # Differenced series
    diff = log_series.diff().dropna()

    # ADF on differenced (confirming the known result)
    adf_result = adfuller(diff, autolag="AIC")
    print(f"\nADF on Δlog(WSHOMCB):")
    print(f"  Test stat: {adf_result[0]:.4f}")
    print(f"  p-value:   {adf_result[1]:.4f}")
    print(f"  Lags used: {adf_result[2]}")
    print(f"  Critical values: {adf_result[4]}")

    # KPSS on differenced — this is the key test
    # H₀: stationary. If we FAIL to reject → series IS stationary → confirms I(1)
    kpss_stat, kpss_p, kpss_lags, kpss_cvs = kpss(diff, regression='c', nlags='auto')
    print(f"\nKPSS on Δlog(WSHOMCB):")
    print(f"  Test stat:  {kpss_stat:.4f}")
    print(f"  p-value:    {kpss_p:.4f}")
    print(f"  Lags used:  {kpss_lags}")
    print(f"  Critical values: {kpss_cvs}")

    # Also run on levels for completeness
    kpss_lev_stat, kpss_lev_p, kpss_lev_lags, kpss_lev_cvs = kpss(log_series, regression='c', nlags='auto')
    print(f"\nKPSS on log(WSHOMCB) levels:")
    print(f"  Test stat:  {kpss_lev_stat:.4f}")
    print(f"  p-value:    {kpss_lev_p:.4f}")
    print(f"  Critical values: {kpss_lev_cvs}")

    # Verdict
    i1_confirmed = kpss_p > 0.05  # fail to reject stationarity in differences
    verdict = "I(1) CONFIRMED" if i1_confirmed else "I(2) CONCERN REMAINS"
    print(f"\nVERDICT: {verdict}")
    if i1_confirmed:
        print("  KPSS fails to reject stationarity in differences → Δlog(WSHOMCB) is stationary → I(1)")
        print("  This resolves the borderline ADF p=0.19 concern.")
    else:
        print("  KPSS rejects stationarity in differences → I(2) concern is real")

    # Also run KPSS on the other two variables for completeness
    try:
        sc = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", index_col=0, parse_dates=True)
        supply = sc["total_supply"]
    except:
        supply = None

    other_results = {}
    for name, series_key in [("RRPONTSYD", "RRPONTSYD"), ("total_supply", None)]:
        try:
            if name == "total_supply" and supply is not None:
                s = supply.dropna()
            else:
                s = fred[series_key].dropna()
            s_weekly = s.resample("W-WED").last().dropna()
            s_primary = s_weekly["2023-02-01":"2026-01-31"]
            s_log = np.log(s_primary.replace(0, np.nan).dropna())
            s_diff = s_log.diff().dropna()
            if len(s_diff) > 10:
                # ADF
                adf_d = adfuller(s_diff, autolag="AIC")
                # KPSS
                k_stat, k_p, k_lags, k_cvs = kpss(s_diff, regression='c', nlags='auto')
                # KPSS on levels
                k_lev_stat, k_lev_p, _, _ = kpss(s_log, regression='c', nlags='auto')
                other_results[name] = {
                    "adf_diff_stat": round(adf_d[0], 4),
                    "adf_diff_p": round(adf_d[1], 4),
                    "kpss_diff_stat": round(k_stat, 4),
                    "kpss_diff_p": round(k_p, 4),
                    "kpss_level_stat": round(k_lev_stat, 4),
                    "kpss_level_p": round(k_lev_p, 4),
                    "i1_confirmed": bool(k_p > 0.05),
                }
                status = "I(1) ✓" if k_p > 0.05 else "I(2)?"
                print(f"\n  {name}: ADF diff p={adf_d[1]:.4f}, KPSS diff stat={k_stat:.4f} p={k_p:.4f} → {status}")
        except Exception as e:
            print(f"\n  {name}: error ({e})")

    output = {
        "wshomcb_diff": {
            "adf_stat": round(adf_result[0], 4),
            "adf_p": round(adf_result[1], 4),
            "adf_lags": adf_result[2],
            "adf_cv": {k: round(v, 4) for k, v in adf_result[4].items()},
            "kpss_stat": round(kpss_stat, 4),
            "kpss_p": round(kpss_p, 4),
            "kpss_lags": kpss_lags,
            "kpss_cv": {k: round(v, 4) for k, v in kpss_cvs.items()},
        },
        "wshomcb_levels": {
            "kpss_stat": round(kpss_lev_stat, 4),
            "kpss_p": round(kpss_lev_p, 4),
        },
        "other_variables": other_results,
        "i1_confirmed": i1_confirmed,
        "verdict": verdict,
    }
    save_json(output, "kpss_results.json")
    print(f"\nSaved to data/processed/kpss_results.json")

if __name__ == "__main__":
    main()
