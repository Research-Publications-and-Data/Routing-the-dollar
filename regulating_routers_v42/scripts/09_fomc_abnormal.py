"""B.3: FOMC event study with abnormal returns (baseline-adjusted). Also computes B.4 medians."""
import pandas as pd, numpy as np, json, sys, warnings
from scipy import stats
warnings.filterwarnings("ignore")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_json

# FOMC dates from config/settings.py
FOMC_DATES = [
    ("2023-02-01", 25, "hawkish"),
    ("2023-03-22", 25, "hawkish"),
    ("2023-05-03", 25, "hawkish"),
    ("2023-06-14", 0, "hawkish"),
    ("2023-07-26", 25, "hawkish"),
    ("2023-09-20", 0, "neutral"),
    ("2023-11-01", 0, "neutral"),
    ("2023-12-13", 0, "dovish"),
    ("2024-01-31", 0, "neutral"),
    ("2024-03-20", 0, "neutral"),
    ("2024-05-01", 0, "neutral"),
    ("2024-06-12", 0, "neutral"),
    ("2024-07-31", 0, "dovish"),
    ("2024-09-18", -50, "dovish"),
    ("2024-11-07", -25, "dovish"),
    ("2024-12-18", -25, "dovish"),
    ("2025-01-29", 0, "neutral"),
    ("2025-03-19", 0, "neutral"),
    ("2025-05-07", 0, "neutral"),
]

HORIZONS = [1, 3, 5, 10]
BASELINE_WINDOW = 10  # trailing 10-day average daily growth

def main():
    print("=" * 70)
    print("B.3: FOMC EVENT STUDY — ABNORMAL RETURNS (+ B.4 MEDIANS)")
    print("=" * 70)

    # Load daily supply data
    try:
        sc = pd.read_csv(DATA_PROC / "unified_extended_dataset.csv", index_col=0, parse_dates=True)
        supply = sc["total_supply"].dropna()
    except:
        sc = pd.read_csv(DATA_RAW / "stablecoin_supply_extended.csv", index_col=0, parse_dates=True)
        supply = sc["total_supply"].dropna()

    daily_return = supply.pct_change()
    print(f"Supply data: {len(supply)} days, {supply.index[0].date()} to {supply.index[-1].date()}")

    results = {"raw": {}, "abnormal": {}, "events": [], "baseline_window_days": BASELINE_WINDOW}

    for cls in ["dovish", "neutral", "hawkish"]:
        dates = [(d, b) for d, b, c in FOMC_DATES if c == cls]
        raw_by_h = {h: [] for h in HORIZONS}
        abn_by_h = {h: [] for h in HORIZONS}

        for date_str, bps in dates:
            event_date = pd.to_datetime(date_str)
            # Find nearest available date
            if event_date not in supply.index:
                mask = supply.index >= event_date
                if mask.any():
                    event_date = supply.index[mask][0]
                else:
                    continue

            idx = supply.index.get_loc(event_date)

            # Pre-event baseline: trailing BASELINE_WINDOW-day average daily return
            if idx < BASELINE_WINDOW + 1:
                continue
            baseline_daily = daily_return.iloc[idx - BASELINE_WINDOW:idx].mean()

            event_data = {
                "date": date_str, "decision_bps": bps, "classification": cls,
                "supply_at_event": round(float(supply.iloc[idx]), 0),
                "baseline_daily_pct": round(float(baseline_daily * 100), 6),
            }

            for h in HORIZONS:
                if idx + h >= len(supply):
                    continue
                # Raw cumulative return
                raw_cum = (supply.iloc[idx + h] / supply.iloc[idx] - 1) * 100
                # Expected (baseline x horizon)
                expected = baseline_daily * h * 100
                # Abnormal
                abnormal = raw_cum - expected

                raw_by_h[h].append(float(raw_cum))
                abn_by_h[h].append(float(abnormal))
                event_data[f"raw_t{h}"] = round(float(raw_cum), 4)
                event_data[f"expected_t{h}"] = round(float(expected), 4)
                event_data[f"abn_t{h}"] = round(float(abnormal), 4)

            results["events"].append(event_data)

        # Compute means, medians, and t-tests for each horizon
        results["raw"][cls] = {"n": len(dates)}
        results["abnormal"][cls] = {"n": len(dates)}

        for h in HORIZONS:
            # Raw
            if len(raw_by_h[h]) >= 2:
                arr = np.array(raw_by_h[h])
                t_raw, p_raw = stats.ttest_1samp(arr, 0)
                results["raw"][cls][f"t{h}"] = {
                    "mean": round(float(arr.mean()), 4),
                    "median": round(float(np.median(arr)), 4),
                    "std": round(float(arr.std(ddof=1)), 4),
                    "min": round(float(arr.min()), 4),
                    "max": round(float(arr.max()), 4),
                    "n": len(arr),
                    "t_stat": round(float(t_raw), 3),
                    "p_value": round(float(p_raw), 4),
                }

            # Abnormal
            if len(abn_by_h[h]) >= 2:
                arr = np.array(abn_by_h[h])
                t_abn, p_abn = stats.ttest_1samp(arr, 0)
                # Also Wilcoxon signed-rank (non-parametric)
                try:
                    w_stat, w_p = stats.wilcoxon(arr)
                except:
                    w_stat, w_p = np.nan, np.nan
                results["abnormal"][cls][f"t{h}"] = {
                    "mean": round(float(arr.mean()), 4),
                    "median": round(float(np.median(arr)), 4),
                    "std": round(float(arr.std(ddof=1)), 4),
                    "min": round(float(arr.min()), 4),
                    "max": round(float(arr.max()), 4),
                    "n": len(arr),
                    "t_stat": round(float(t_abn), 3),
                    "p_value": round(float(p_abn), 4),
                    "wilcoxon_stat": round(float(w_stat), 3) if not np.isnan(w_stat) else None,
                    "wilcoxon_p": round(float(w_p), 4) if not np.isnan(w_p) else None,
                }

    # Print comparison table
    print(f"\n{'':15} {'-------- RAW --------':>30}  {'------ ABNORMAL ------':>30}")
    print(f"{'Category':<12} {'t+5 mean':>8} {'t+5 p':>7} {'t+10 mean':>10} {'t+10 p':>7}  {'t+5 mean':>8} {'t+5 p':>7} {'t+10 mean':>10} {'t+10 p':>7}")
    print("-" * 95)
    for cls in ["dovish", "neutral", "hawkish"]:
        raw5 = results["raw"].get(cls, {}).get("t5", {})
        raw10 = results["raw"].get(cls, {}).get("t10", {})
        abn5 = results["abnormal"].get(cls, {}).get("t5", {})
        abn10 = results["abnormal"].get(cls, {}).get("t10", {})

        def fmt(d, key):
            v = d.get(key, None)
            if v is None: return "N/A"
            return f"{v:>7.4f}" if isinstance(v, float) else str(v)

        print(f"{cls:<12} "
              f"{fmt(raw5,'mean'):>8} {fmt(raw5,'p_value'):>7} {fmt(raw10,'mean'):>10} {fmt(raw10,'p_value'):>7}  "
              f"{fmt(abn5,'mean'):>8} {fmt(abn5,'p_value'):>7} {fmt(abn10,'mean'):>10} {fmt(abn10,'p_value'):>7}")

    # Medians table (B.4)
    print(f"\n{'':12} {'--- RAW MEDIAN ---':>25}  {'--- ABNORMAL MEDIAN ---':>25}")
    print(f"{'Category':<12} {'t+5':>8} {'t+10':>8}  {'t+5':>8} {'t+10':>8}")
    print("-" * 60)
    for cls in ["dovish", "neutral", "hawkish"]:
        raw5 = results["raw"].get(cls, {}).get("t5", {})
        raw10 = results["raw"].get(cls, {}).get("t10", {})
        abn5 = results["abnormal"].get(cls, {}).get("t5", {})
        abn10 = results["abnormal"].get(cls, {}).get("t10", {})

        def fmtm(d):
            v = d.get("median", None)
            return f"{v:>8.4f}" if v is not None else "     N/A"

        print(f"{cls:<12} {fmtm(raw5)} {fmtm(raw10)}  {fmtm(abn5)} {fmtm(abn10)}")

    # Key significance check
    print("\n" + "=" * 70)
    print("KEY RESULTS:")
    for cls in ["dovish", "neutral", "hawkish"]:
        for h in [5, 10]:
            abn = results["abnormal"].get(cls, {}).get(f"t{h}", {})
            if abn:
                p = abn.get("p_value", 1)
                mean = abn.get("mean", 0)
                median = abn.get("median", 0)
                sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
                print(f"  {cls} t+{h}: abnormal mean={mean:+.4f}%, median={median:+.4f}%, p={p:.4f}{sig}")

    # Check if neutral t+5 survives
    neutral_abn_t5 = results["abnormal"].get("neutral", {}).get("t5", {})
    if neutral_abn_t5:
        p = neutral_abn_t5.get("p_value", 1)
        if p < 0.05:
            print(f"\n✓ CRITICAL: Neutral t+5 ABNORMAL result SURVIVES (p={p:.4f})")
        elif p < 0.10:
            print(f"\n⚠ Neutral t+5 abnormal result is MARGINAL (p={p:.4f})")
        else:
            print(f"\n✗ Neutral t+5 abnormal result does NOT survive baseline adjustment (p={p:.4f})")

    save_json(results, "fomc_abnormal_results.json")
    print(f"\nSaved to data/processed/fomc_abnormal_results.json")

if __name__ == "__main__":
    main()
