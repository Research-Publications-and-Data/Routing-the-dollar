"""Task 8b: Compute gateway coverage ratio from Dune exports."""
import pandas as pd, sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from utils import DATA_RAW, save_json

def main():
    try:
        total = pd.read_csv(DATA_RAW / "dune_total_volume.csv")
        gateway = pd.read_csv(DATA_RAW / "dune_gateway_volume.csv")
    except FileNotFoundError as e:
        print(f"Missing Dune CSV: {e}")
        print("Run queries A and B in Dune Analytics UI and save CSVs to data/raw/")
        return

    coverage = gateway["volume_usd"].sum() / total["volume_usd"].sum()
    print(f"Gateway coverage ratio: {coverage:.1%}")
    print(f"(12 addresses capture {coverage:.1%} of total Ethereum USDC+USDT volume)")
    save_json({"coverage_ratio": round(coverage, 4), "gateway_volume": float(gateway["volume_usd"].sum()),
               "total_volume": float(total["volume_usd"].sum())}, "gateway_coverage.json")

if __name__ == "__main__":
    main()
