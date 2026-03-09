"""Sprint 5a: Quadrivariate cointegration robustness — DTWEXBGS and VIX systems.

Extends the trivariate baseline {WSHOMCB, RRPONTSYD, total_supply} with
two additional variables that a discussant might suggest as omitted:

  System A: + DTWEXBGS  (trade-weighted broad dollar index)
  System B: + VIXCLS    (CBOE VIX closing)

For each, runs Johansen trace test and reports whether the original
cointegrating relationship survives (rank >= 1).

Outputs:
  data/processed/quadrivariate_robustness.csv   — trace stats + CV95
  data/processed/quadrivariate_alpha.csv        — VECM alpha coefficients
  data/processed/quadrivariate_unit_roots.csv   — ADF tests on all 5 series

Data:
  data/raw/dtwexbgs_weekly.csv   — FRED DTWEXBGS (weekly)
  data/raw/vixcls_weekly.csv     — FRED VIXCLS  (weekly)
  data/raw/fred_wide.csv         — baseline FRED series
  data/processed/unified_extended_dataset.csv — stablecoin supply
"""
import pandas as pd
import numpy as np
import warnings
import sys
from pathlib import Path

warnings.filterwarnings("ignore")

from statsmodels.tsa.vector_ar.vecm import coint_johansen, VECM
from statsmodels.tsa.vector_ar.var_model import VAR
from statsmodels.tsa.stattools import adfuller

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"


def load_baseline():
    """Replicate the exact data pipeline from 02_cointegration.py."""
    fred = pd.read_csv(DATA_RAW / "fred_wide.csv", index_col=0, parse_dates=True)
    sc = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv",
                     index_col=0, parse_dates=True)
    supply = sc["total_supply"]

    merged = fred[["WSHOMCB", "RRPONTSYD"]].join(
        pd.DataFrame(supply), how="inner"
    ).dropna(subset=["WSHOMCB"])
    merged["RRPONTSYD"] = merged["RRPONTSYD"].ffill()
    weekly = merged.resample("W-WED").last().dropna()
    primary = weekly["2023-02-01":"2026-01-31"]
    return primary


def load_extra_series(filename, col_name):
    """Load a weekly FRED CSV and align to Wednesday resampling."""
    path = DATA_RAW / filename
    if not path.exists():
        print(f"  ERROR: {path} not found")
        return None
    df = pd.read_csv(path, parse_dates=["date"], index_col="date")
    # Resample to Wednesday to match baseline
    weekly = df[col_name].resample("W-WED").last().ffill()
    return weekly


def adf_battery(data, names):
    """Run ADF on levels and first differences for all columns."""
    rows = []
    for col in names:
        s = data[col].dropna()
        lev = adfuller(s, autolag="AIC")
        dif = adfuller(s.diff().dropna(), autolag="AIC")
        rows.append({
            "series": col,
            "level_adf": round(float(lev[0]), 4),
            "level_p": round(float(lev[1]), 4),
            "diff_adf": round(float(dif[0]), 4),
            "diff_p": round(float(dif[1]), 4),
            "I1": "yes" if lev[1] > 0.05 and dif[1] < 0.05 else "check",
        })
    return pd.DataFrame(rows)


def run_johansen(log_data, var_names, max_lag=8):
    """Run Johansen cointegration test, return structured results."""
    var_model = VAR(log_data)
    lag = var_model.select_order(maxlags=max_lag).aic
    lag = max(1, min(lag, max_lag))
    k = max(1, lag - 1)

    joh = coint_johansen(log_data, det_order=0, k_ar_diff=k)
    n_vars = log_data.shape[1]

    trace_rows = []
    rank = 0
    for i in range(n_vars):
        stat = float(joh.lr1[i])
        cv95 = float(joh.cvt[i, 1])
        reject = stat > cv95
        if reject:
            rank += 1
        trace_rows.append({
            "h0_rank_le": i,
            "trace_stat": round(stat, 2),
            "cv_95": round(cv95, 2),
            "reject_95": reject,
        })

    return {
        "lag_aic": lag,
        "k_ar_diff": k,
        "rank": rank,
        "cointegrated": rank > 0,
        "n_obs": len(log_data),
        "trace": trace_rows,
    }


def run_vecm_alpha(log_data, var_names, rank, k):
    """Fit VECM and extract alpha coefficients."""
    if rank < 1:
        return None
    try:
        vecm = VECM(log_data, k_ar_diff=k, coint_rank=rank).fit()
        rows = []
        for i, name in enumerate(var_names):
            rows.append({
                "variable": name,
                "alpha": round(float(vecm.alpha[i, 0]), 6),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"    VECM failed: {e}")
        return None


def main():
    print("=" * 60)
    print("QUADRIVARIATE COINTEGRATION ROBUSTNESS")
    print("=" * 60)

    # Load baseline
    baseline = load_baseline()
    print(f"  Baseline: {len(baseline)} weeks, "
          f"{baseline.index[0].date()} to {baseline.index[-1].date()}")

    # Load extra series
    dtwexbgs = load_extra_series("dtwexbgs_weekly.csv", "DTWEXBGS")
    vixcls = load_extra_series("vixcls_weekly.csv", "VIXCLS")

    if dtwexbgs is None or vixcls is None:
        print("  FATAL: Missing raw data files. Cannot proceed.")
        sys.exit(1)

    # Join extra series
    ext = baseline.copy()
    ext = ext.join(dtwexbgs.rename("DTWEXBGS"), how="left")
    ext = ext.join(vixcls.rename("VIXCLS"), how="left")
    ext = ext.ffill().dropna()
    print(f"  Extended sample: {len(ext)} weeks with all 5 series")

    # ── ADF unit root tests ──────────────────────────────────
    print("\nADF Unit Root Tests:")
    all_names = ["WSHOMCB", "RRPONTSYD", "total_supply", "DTWEXBGS", "VIXCLS"]
    log_ext = np.log(ext[all_names].replace(0, np.nan).dropna())
    adf_df = adf_battery(log_ext, all_names)
    for _, row in adf_df.iterrows():
        print(f"  {row['series']:15s}: level p={row['level_p']:.4f}, "
              f"diff p={row['diff_p']:.4f}  [{row['I1']}]")
    adf_df.to_csv(DATA_PROC / "quadrivariate_unit_roots.csv", index=False)
    print(f"  Saved: {DATA_PROC / 'quadrivariate_unit_roots.csv'}")

    # ── Baseline trivariate ──────────────────────────────────
    base_names = ["WSHOMCB", "RRPONTSYD", "total_supply"]
    log_base = np.log(ext[base_names].replace(0, np.nan).dropna())
    print(f"\nBaseline trivariate (n={len(log_base)}):")
    base_result = run_johansen(log_base, base_names)
    print(f"  Lag={base_result['lag_aic']}, Rank={base_result['rank']}, "
          f"Trace(r=0)={base_result['trace'][0]['trace_stat']}")

    # ── System A: + DTWEXBGS ─────────────────────────────────
    sys_a_names = ["WSHOMCB", "RRPONTSYD", "total_supply", "DTWEXBGS"]
    log_a = np.log(ext[sys_a_names].replace(0, np.nan).dropna())
    print(f"\nSystem A: + DTWEXBGS (n={len(log_a)}):")
    result_a = run_johansen(log_a, sys_a_names)
    survives_a = result_a["rank"] >= 1
    print(f"  Lag={result_a['lag_aic']}, Rank={result_a['rank']}, "
          f"Trace(r=0)={result_a['trace'][0]['trace_stat']}, "
          f"CV95={result_a['trace'][0]['cv_95']}, "
          f"Survives={survives_a}")
    alpha_a = run_vecm_alpha(log_a, sys_a_names, result_a["rank"],
                             result_a["k_ar_diff"])

    # ── System B: + VIXCLS ───────────────────────────────────
    sys_b_names = ["WSHOMCB", "RRPONTSYD", "total_supply", "VIXCLS"]
    log_b = np.log(ext[sys_b_names].replace(0, np.nan).dropna())
    print(f"\nSystem B: + VIXCLS (n={len(log_b)}):")
    result_b = run_johansen(log_b, sys_b_names)
    survives_b = result_b["rank"] >= 1
    print(f"  Lag={result_b['lag_aic']}, Rank={result_b['rank']}, "
          f"Trace(r=0)={result_b['trace'][0]['trace_stat']}, "
          f"CV95={result_b['trace'][0]['cv_95']}, "
          f"Survives={survives_b}")
    alpha_b = run_vecm_alpha(log_b, sys_b_names, result_b["rank"],
                             result_b["k_ar_diff"])

    # ── Save results ─────────────────────────────────────────
    # 1. Robustness summary
    robustness_rows = []
    for name, res, survives in [
        ("baseline", base_result, True),
        ("+ DTWEXBGS", result_a, survives_a),
        ("+ VIXCLS", result_b, survives_b),
    ]:
        row = {
            "system": name,
            "n_obs": res["n_obs"],
            "lag_aic": res["lag_aic"],
            "rank": res["rank"],
            "cointegrated": res["cointegrated"],
            "survives": survives,
        }
        for t in res["trace"]:
            row[f"trace_r{t['h0_rank_le']}"] = t["trace_stat"]
            row[f"cv95_r{t['h0_rank_le']}"] = t["cv_95"]
        robustness_rows.append(row)

    rob_df = pd.DataFrame(robustness_rows)
    rob_df.to_csv(DATA_PROC / "quadrivariate_robustness.csv", index=False)
    print(f"\n  Saved: {DATA_PROC / 'quadrivariate_robustness.csv'}")

    # 2. Alpha coefficients
    alpha_rows = []
    if alpha_a is not None:
        for _, r in alpha_a.iterrows():
            alpha_rows.append({"system": "+ DTWEXBGS", **r.to_dict()})
    if alpha_b is not None:
        for _, r in alpha_b.iterrows():
            alpha_rows.append({"system": "+ VIXCLS", **r.to_dict()})
    if alpha_rows:
        alpha_df = pd.DataFrame(alpha_rows)
        alpha_df.to_csv(DATA_PROC / "quadrivariate_alpha.csv", index=False)
        print(f"  Saved: {DATA_PROC / 'quadrivariate_alpha.csv'}")

    # ── Summary ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Baseline rank: {base_result['rank']}")
    print(f"  + DTWEXBGS:    rank={result_a['rank']}, "
          f"trace={result_a['trace'][0]['trace_stat']}, "
          f"survives={survives_a}")
    print(f"  + VIXCLS:      rank={result_b['rank']}, "
          f"trace={result_b['trace'][0]['trace_stat']}, "
          f"survives={survives_b}")
    if survives_a and survives_b:
        print("\n  RESULT: Cointegration survives both quadrivariate extensions.")
    else:
        failed = []
        if not survives_a:
            failed.append("DTWEXBGS")
        if not survives_b:
            failed.append("VIXCLS")
        print(f"\n  RESULT: Cointegration does NOT survive: {', '.join(failed)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
