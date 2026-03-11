"""B.1: Johansen lag sensitivity robustness table."""
import pandas as pd, numpy as np, json, sys, warnings
warnings.filterwarnings("ignore")
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

def load_weekly_log_data():
    """Load the same 3-variable weekly dataset used in the paper."""
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    try:
        sc = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", index_col=0, parse_dates=True)
        supply = sc["total_supply"]
    except FileNotFoundError:
        import requests
        resp = requests.get("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=1", timeout=30)
        usdt = [(pd.to_datetime(d["date"], unit="s"), d.get("totalCirculating", {}).get("peggedUSD", 0)) for d in resp.json()]
        resp2 = requests.get("https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2", timeout=30)
        usdc = [(pd.to_datetime(d["date"], unit="s"), d.get("totalCirculating", {}).get("peggedUSD", 0)) for d in resp2.json()]
        supply = pd.Series(dict(usdt)) + pd.Series(dict(usdc)).reindex(pd.Series(dict(usdt)).index, fill_value=0)
        supply.name = "total_supply"

    merged = fred[["WSHOMCB", "RRPONTSYD"]].join(pd.DataFrame(supply), how="inner").dropna(subset=["WSHOMCB"])
    merged["RRPONTSYD"] = merged["RRPONTSYD"].ffill()
    weekly = merged.resample("W-WED").last().dropna()
    primary = weekly["2023-02-01":"2026-01-31"]
    log_df = np.log(primary.replace(0, np.nan).dropna())
    print(f"Sample: {len(log_df)} weeks, {log_df.index[0].date()} to {log_df.index[-1].date()}")
    return log_df

def run_johansen_at_lag(log_df, lag):
    """Run Johansen test at specified lag (k_ar_diff = lag - 1)."""
    k = max(1, lag - 1)
    try:
        joh = coint_johansen(log_df, det_order=0, k_ar_diff=k)
        return {
            "lag": lag,
            "k_ar_diff": k,
            "trace_stat": round(float(joh.lr1[0]), 2),
            "trace_cv90": round(float(joh.cvt[0, 0]), 2),
            "trace_cv95": round(float(joh.cvt[0, 1]), 2),
            "trace_cv99": round(float(joh.cvt[0, 2]), 2),
            "trace_pass_90": bool(joh.lr1[0] > joh.cvt[0, 0]),
            "trace_pass_95": bool(joh.lr1[0] > joh.cvt[0, 1]),
            "trace_pass_99": bool(joh.lr1[0] > joh.cvt[0, 2]),
            "maxeig_stat": round(float(joh.lr2[0]), 2),
            "maxeig_cv90": round(float(joh.cvm[0, 0]), 2),
            "maxeig_cv95": round(float(joh.cvm[0, 1]), 2),
            "maxeig_cv99": round(float(joh.cvm[0, 2]), 2),
            "maxeig_pass_90": bool(joh.lr2[0] > joh.cvm[0, 0]),
            "maxeig_pass_95": bool(joh.lr2[0] > joh.cvm[0, 1]),
            "maxeig_pass_99": bool(joh.lr2[0] > joh.cvm[0, 2]),
        }
    except Exception as e:
        return {"lag": lag, "error": str(e)}

def main():
    print("=" * 70)
    print("B.1: JOHANSEN LAG SENSITIVITY")
    print("=" * 70)
    log_df = load_weekly_log_data()

    lags = [4, 6, 8, 10, 12]
    results = []

    print(f"\n{'Lag':<6}{'Trace':<10}{'cv90':<10}{'cv95':<10}{'cv99':<10}{'90%':<6}{'95%':<6}{'99%':<6}{'λ-max':<10}{'cv95':<10}{'95%':<6}")
    print("-" * 90)

    for lag in lags:
        r = run_johansen_at_lag(log_df, lag)
        results.append(r)
        if "error" not in r:
            t90 = "✓" if r["trace_pass_90"] else "✗"
            t95 = "✓" if r["trace_pass_95"] else "✗"
            t99 = "✓" if r["trace_pass_99"] else "✗"
            m95 = "✓" if r["maxeig_pass_95"] else "✗"
            print(f"{lag:<6}{r['trace_stat']:<10}{r['trace_cv90']:<10}{r['trace_cv95']:<10}{r['trace_cv99']:<10}{t90:<6}{t95:<6}{t99:<6}{r['maxeig_stat']:<10}{r['maxeig_cv95']:<10}{m95:<6}")
        else:
            print(f"{lag:<6} ERROR: {r['error']}")

    # Summary
    pass_90 = sum(1 for r in results if r.get("trace_pass_90", False))
    pass_95 = sum(1 for r in results if r.get("trace_pass_95", False))
    pass_99 = sum(1 for r in results if r.get("trace_pass_99", False))
    maxeig_95 = sum(1 for r in results if r.get("maxeig_pass_95", False))

    print(f"\nTrace passes at 90%: {pass_90}/{len(lags)}")
    print(f"Trace passes at 95%: {pass_95}/{len(lags)}")
    print(f"Trace passes at 99%: {pass_99}/{len(lags)}")
    print(f"Max-eigen passes at 95%: {maxeig_95}/{len(lags)}")

    if pass_95 >= 4:
        verdict = "robust"
        print("\nVERDICT: Cointegration is ROBUST to lag specification.")
    elif pass_95 >= 3:
        verdict = "robust"
        print("\nVERDICT: Cointegration is ROBUST — passes at majority of lags.")
    elif pass_95 >= 2:
        verdict = "moderate"
        print("\nVERDICT: Cointegration is MODERATELY ROBUST.")
    elif pass_90 >= 3:
        verdict = "moderate_at_90"
        print("\nVERDICT: Cointegration is MODERATE — passes at 10% level for most lags.")
    else:
        verdict = "fragile"
        print("\nVERDICT: Cointegration is FRAGILE — passes only at AIC-optimal lag.")

    output = {
        "lags_tested": lags,
        "results": results,
        "summary": {
            "trace_pass_90_count": pass_90,
            "trace_pass_95_count": pass_95,
            "trace_pass_99_count": pass_99,
            "maxeig_pass_95_count": maxeig_95,
            "total_tested": len(lags),
        },
        "verdict": verdict,
    }
    save_json(output, "lag_sensitivity.json")
    print(f"\nSaved to data/processed/lag_sensitivity.json")

if __name__ == "__main__":
    main()
