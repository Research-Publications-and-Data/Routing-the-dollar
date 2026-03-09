"""Task 6: ON RRP counterparty decomposition from NY Fed API."""
import requests, pandas as pd, matplotlib.pyplot as plt, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "config"))
from settings import EXTENDED_START, PRIMARY_END
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import DATA_RAW, DATA_PROC, save_csv, save_json, save_exhibit, setup_plot_style, color

def classify(name):
    nl = name.lower()
    for kw in ["money market", "fund", "fidelity", "vanguard", "blackrock", "jpmorgan", "schwab",
               "goldman sachs", "morgan stanley", "dreyfus", "northern trust", "invesco", "state street"]:
        if kw in nl: return "MMF"
    for kw in ["federal home", "fhlb", "fannie", "freddie"]:
        if kw in nl: return "GSE"
    return "Other"

def main():
    print("ON RRP Counterparty Decomposition\n")
    # Try propositions endpoint
    url = "https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json"
    params = {"startDate": EXTENDED_START.replace("-", ""), "endDate": PRIMARY_END.replace("-", "")}
    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        ops = data.get("repo", {}).get("operations", [])
        rows = []
        for op in ops:
            for prop in op.get("propositions", []):
                rows.append({"date": op["operationDate"], "counterparty": prop.get("parName", ""),
                             "amount_B": float(prop.get("submitted", 0)) / 1e9})
        if rows:
            raw = pd.DataFrame(rows)
            raw["type"] = raw["counterparty"].apply(classify)
            daily = raw.groupby(["date", "type"])["amount_B"].sum().unstack(fill_value=0)
            daily.index = pd.to_datetime(daily.index)
            save_csv(daily.sort_index(), "onrrp_by_counterparty.csv")
            print(f"  Got {len(rows)} propositions across {len(ops)} days")
            for t in daily.columns:
                print(f"    {t}: {daily[t].sum() / daily.sum(axis=1).sum() * 100:.1f}%")
            # Plot
            setup_plot_style()
            fig, ax = plt.subplots(figsize=(8, 5))
            plot_data = daily["2021-03-01":]
            ax.stackplot(plot_data.index, *[plot_data[c] for c in plot_data.columns],
                         labels=plot_data.columns, colors=[color("primary"), color("secondary"), "#E0E0E0"])
            ax.set_ylabel("ON RRP ($B)"); ax.set_title("Overnight Reverse Repo by Counterparty Type")
            ax.legend(loc="upper left")
            save_exhibit(fig, "exhibit13_onrrp_decomposition.png", "Source: NY Fed.")
            print("Done")
            return
    except Exception as e:
        print(f"  Propositions endpoint failed: {e}")

    # Fallback: summary endpoint
    print("  Falling back to summary endpoint...")
    url2 = "https://markets.newyorkfed.org/api/rp/reverserepo/search.json"
    try:
        resp = requests.get(url2, params=params, timeout=60)
        ops = resp.json().get("repo", {}).get("operations", [])
        rows = [{"date": op["operationDate"], "total_B": float(op.get("totalAmtAccepted", 0)) / 1e9,
                 "n_counterparties": int(op.get("totalCounterpartiesAccepted", 0))} for op in ops]
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        save_csv(df.set_index("date"), "onrrp_by_counterparty.csv")
        print(f"  Got {len(df)} daily aggregates (no counterparty breakdown)")
        # Plot total ON RRP
        setup_plot_style()
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.fill_between(df["date"], df["total_B"], color=color("primary"), alpha=0.7)
        ax.set_ylabel("ON RRP ($B)"); ax.set_title("Overnight Reverse Repo Facility Usage")
        save_exhibit(fig, "exhibit13_onrrp_decomposition.png", "Source: NY Fed.")
        print("Done (summary only)")
    except Exception as e:
        print(f"  Both endpoints failed: {e}")
        print("  Manual download: https://www.newyorkfed.org/markets/desk-operations/reverse-repo")

if __name__ == "__main__":
    main()
