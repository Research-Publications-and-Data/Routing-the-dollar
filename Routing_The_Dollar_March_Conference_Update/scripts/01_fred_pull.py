"""Task 1: Pull all required FRED series."""
import requests, pandas as pd, time, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "config"))
from settings import FRED_API_KEY, FRED_SERIES, EXTENDED_START, PRIMARY_END
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import DATA_RAW, save_csv

def pull_fred(series_id, api_key, start, end):
    url = (f"https://api.stlouisfed.org/fred/series/observations"
           f"?series_id={series_id}&api_key={api_key}&file_type=json"
           f"&observation_start={start}&observation_end={end}")
    data = requests.get(url).json()
    rows = []
    for obs in data.get("observations", []):
        val = None if obs["value"] == "." else float(obs["value"])
        rows.append({"date": obs["date"], "series_id": series_id, "value": val})
    return pd.DataFrame(rows)

def main():
    if not FRED_API_KEY:
        print("ERROR: Set FRED_API_KEY in config/settings.py")
        sys.exit(1)
    print(f"Pulling {len(FRED_SERIES)} FRED series...")
    frames = []
    for sid, desc in FRED_SERIES.items():
        print(f"  {sid}: {desc}")
        try:
            df = pull_fred(sid, FRED_API_KEY, EXTENDED_START, PRIMARY_END)
            print(f"    -> {len(df)} obs, {df['value'].notna().sum()} non-null")
            frames.append(df)
        except Exception as e:
            print(f"    -> ERROR: {e}")
        time.sleep(0.5)
    combined = pd.concat(frames, ignore_index=True)
    save_csv(combined, "fred_all_series.csv", directory=DATA_RAW)
    wide = combined.pivot(index="date", columns="series_id", values="value")
    wide.index = pd.to_datetime(wide.index)
    save_csv(wide.sort_index(), "fred_wide.csv", directory=DATA_RAW)
    print(f"\nTotal: {len(combined)} rows, {combined['series_id'].nunique()} series")

if __name__ == "__main__":
    main()
