#!/usr/bin/env python3
"""
Nansen API Collector v4 — Queries 2–6 for Stablecoin Gateway Paper
===================================================================
Executes all five queries in priority order:
  Q3: Solana Gateway Tier Mapping        (~200 credits)
  Q6: Missing ETH Gateway Coverage       (~200 credits)
  Q4: BUSD Wind-Down Counterparty Net    (~300 credits)
  Q5: Base + Arbitrum L2 Mapping         (~400 credits)
  Q2: Monthly Counterparty Network       (~3000 credits)

Usage:
    export NANSEN_API_KEY="..."
    python nansen_collector_v4.py --query Q3
    python nansen_collector_v4.py --query Q6
    python nansen_collector_v4.py --all
    python nansen_collector_v4.py --consolidate
"""
import os, sys, json, time, csv, argparse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("Run: pip install requests"); sys.exit(1)

# ============================================================
# CONFIGURATION
# ============================================================
API_KEY = os.environ.get("NANSEN_API_KEY", "")
BASE_URL = "https://api.nansen.ai"
V1 = "/api/v1"
BETA = "/api/beta"

OUT_DIR = Path(__file__).resolve().parent.parent / "nansen_v4"
RAW_DIR = OUT_DIR / "raw"
PROCESSED_DIR = OUT_DIR / "processed"
CREDIT_LOG = OUT_DIR / "credit_log.csv"

BUDGET_LIMIT = 10200
BUDGET_HARD_STOP = 10200

# Budget caps per query
QUERY_BUDGETS = {"Q2": 8200, "Q3": 300, "Q4": 700, "Q5": 600, "Q6": 500}

for d in [OUT_DIR, RAW_DIR, PROCESSED_DIR,
          RAW_DIR / "monthly_cpty", RAW_DIR / "solana_cpty",
          RAW_DIR / "solana_related", RAW_DIR / "solana_balance",
          RAW_DIR / "busd_cpty", RAW_DIR / "base_cpty",
          RAW_DIR / "base_related", RAW_DIR / "base_balance",
          RAW_DIR / "arbitrum_cpty", RAW_DIR / "missing_eth_cpty"]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# GATEWAY DEFINITIONS
# ============================================================
ETH_GATEWAYS = {
    "Circle_Treasury":     "0x55fe002aeff02f77364de339a1292923a15844b8",
    "Coinbase_Custody":    "0x503828976d22510aad0201ac7ec88293211d23da",
    "Coinbase_USDC":       "0x28c5b0445d0728bc25f143f8eba5c5539fae151a",
    "Paxos_Treasury":      "0x5338035c008ea8c4b850052bc8dad6a002678f5f",
    "Gemini":              "0x07ee55aa48bb72dcc6e9d78256648910de513eca",
    "Tether_Treasury":     "0x5754284f345afc66a98fbb0a0afe71e0f007b949",
    "Binance_Hot_Wallet":  "0x28c6c06298d514db089934071355e5743bf21d60",
    "Kraken":              "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",
    "Kraken_Hot":          "0xf30ba117ebc41e2c34bf2f23f0116e1c83b90f1e",
    "OKX":                 "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b",
    "Bybit":               "0xf833685f98eba1b99947d418c9512d27c8193b1a",
    "Uniswap_V3_Router":   "0xe592427a0aece92de3edee1f18e0157c05861564",
    "Curve_3pool":         "0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7",
    "Aave_V3_Pool":        "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2",
    "1inch_Router":        "0x1111111254EEB25477B68fb85Ed929f73A960582",
}

SOLANA_GATEWAYS = {
    "Binance_1":         "H8BgJgae6qhMtf7BM2JtKLbyab7bmPATnNnwXp5sCDMR",
    "Circle":            "7VHUFJHWu2CuExkJcJrzhQPJjRXnbN3yAodFJ6v4GmeP",
    "Binance_2":         "5tzFkiKscXHK5ZXCGbXZxdw7aVGthTRSIhJYT8hHZjAp",
    "Jupiter_Perps":     "AVzP2GeRmqGphJsMxWoqHiUfFBB5kMUiR2QrMzzAHrL3",
    "Coinbase_1":        "8Vkgsarud8mSc1gkzayGQuA1FZpCK9iYCDRM21FRpump",
    "Circle_Bridge":     "DBD8hAwLDRQkTsu6EqviN9tCpsAFj1DWGmKSBEgtoCkG",
    "KuCoin":            "FPRFLszBJFHCThF2yWvkQpreMiud4kPqQLQRnXWJFLaC",
    "Coinbase_2":        "HsQwR1swWwGGkg7EJ8A1NXsBkFZpDvPPLF3ZsYWnJ7Yr",
    "OKX_Hot":           "8wM44Ryv9DFCSfkgUnPEdkM7VLJr3pT3L1SLdap6Kvba",
    "OKX_2":             "CBEADkb8TZAXHjVE3zwaZi8nG77DhvPMRCETxrkEibhQ",
    "Gate":              "u6PJ8DtQuPFnfmwHbGFUq5d9BVMgugCJPjkcMfaTJFB",
    "Unknown_1":         "A3znyaRYUvi7GbQv1pp9TD18MBr1HGRo4DxprVgzjsfW",
    "Unknown_2":         "4Dg89gRmz8rUrTRiBP6XFGwGwVJ9nDB3q7PR8UFYTJ82",
    "Unknown_3":         "66GvPQJhqjUoeq8H93QYnUHmfHxGLa5AuqKQJ3t2pump",
    "JLP_Pool":          "7s1da8DduuBFqGra5bJBUmMVhLfphQxWjWP2PBQcCikd",
    "Drift":             "JCNCMFXo5M5qwUPg2Utu4c5K4YH6kJBNiTvPATBY7jQU",
}

BASE_GATEWAYS = {
    "Morpho_Blue":       "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb",
    "Avantis_Vault":     "0x944766f715b51967e5d7d1a6a84e6f5dfe1b1480",
    "Binance_Hot":       "0xee7ae85f2fe2239e27d9c1e23fffe168d63b4055",
    "Coinbase_Deposit":  "0x0ccc149f4c01a2eada24a2f5aecce2c2f02d39a3",
    "Unknown_Base_1":    "0x8da91a6298ea5d1a8b4297e6f0fbca8b1cbad4de",
    "Unknown_Base_2":    "0xb026ba5501c9fcdb5bcd2c85e1e15fc92eb9e1d2",
    "Unknown_Base_3":    "0xba4c04812275b74241a90a1d478c7b8fdb7c4c19",
    "Unknown_Base_4":    "0x9ca12796619c24eeee70ddaac92b38e78c895e3f",
    "Unknown_Base_5":    "0x7d72f952824c963422cf2dd7e08e1f1db0723222",
}

ARBITRUM_GATEWAYS = {
    "Hyperliquid":       "0x2df1c51e09aecf9cacb7bc98cb1742757f163df7",
    "Binance_Wallet":    "0x9dfb9014e88087fba78cc9309c64031d02be9a33",
    "Binance_Hot":       "0xee7ae85f2fe2239e27d9c1e23fffe168d63b4055",
    "Binance_Reserve":   "0xf977814e90da44bfa03b6295a0616a897441acec",
    "Binance_Hot2":      "0xb38e8c17e38363af6eb332b53c1b4e4636a15bdf",
    "Aave_aUSDC":        "0x724dc807b04555b71ed48a6896b6f41593b8c637",
    "Aave_aUSDT":        "0x6ab707aca953edaefbc4fd23ba73294241490620",
    "Ostium_LP":         "0x20d419a8e12c45f88f68b3c825e3253a0f95e0f0",
    "GMX_WBTC_USDC":     "0x47c031236e19d024b42f8ae6780e44a573170703",
    "Bitget":            "0xffa8db7b38579e6a2d1fd0a28ef5ca29d7fbfa87",
    "Circle":            "0x463f5d63e5a5edb8613caf5ff11d76b6f7cd4d38",
    "Bybit":             "0x9d271a4e9523d74572be60e32daae5a3de7f0bec",
}

# Missing ETH gateways (Q6)
MISSING_ETH_GATEWAYS = {
    "Bybit_1":           "0xf833685f98eba1b99947d418c9512d27c8193b1a",
    "Bybit_2":           "0x25c76fa90e90f5a5a6914da07baed9a9647c3dfd",
    "Compound_cUSDCv3":  "0xc3d688b66703497daa19211eedff47f25384cdc3",
    "Compound_cUSDTv3":  "0x3afdc9bca9213a35503b077a6072f3d0d5ab0840",
    "1inch_Router_v5":   "0x1111111254EEB25477B68fb85Ed929f73A960582",
    "1inch_Router_v6":   "0x111111125421ca6dc452d289314280a0f8842a65",
    "BitGo":             "0x5c985e89dde482efe97ea9f1950ad149eb73829b",
    "PayPal":            "0x0e7eb45c8f8da3d62627b1b16e107bbf8bcd24e6",
    "Robinhood":         "0x40b38765696e3d5d8d9d834d8aad4bb6e418e489",
}

# ============================================================
# CREDIT TRACKER
# ============================================================
class CreditTracker:
    def __init__(self, budget=BUDGET_LIMIT, log_path=CREDIT_LOG):
        self.budget = budget
        self.total_used = 0
        self.query_used = {}  # per-query tracking
        self.log_path = Path(log_path)
        if self.log_path.exists():
            with open(self.log_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.total_used = int(row.get("cumulative_total", 0))
            print(f"[RESUME] Credits used so far: {self.total_used}")

    def spend(self, credits, endpoint, chain="", token="", note=""):
        self.total_used += credits
        # Track per-query
        q = note.split("_")[0] if "_" in note else note
        self.query_used[q] = self.query_used.get(q, 0) + credits
        entry = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint, "chain": chain, "token": token,
            "credits": credits, "cumulative_total": self.total_used, "note": note,
        }
        file_exists = self.log_path.exists()
        with open(self.log_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=entry.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(entry)

    def check(self, needed, query_id=None):
        if self.total_used + needed > self.budget:
            print(f"  [BUDGET] Would exceed global limit ({self.total_used}+{needed}>{self.budget}). Stopping.")
            return False
        if query_id and query_id in QUERY_BUDGETS:
            q_used = self.query_used.get(query_id, 0)
            if q_used + needed > QUERY_BUDGETS[query_id]:
                print(f"  [BUDGET] Query {query_id} would exceed its cap ({q_used}+{needed}>{QUERY_BUDGETS[query_id]})")
                return False
        return True

    def summary(self):
        return f"Credits: {self.total_used}/{self.budget} ({self.budget - self.total_used} remaining)"


tracker = CreditTracker()

# ============================================================
# API CALLER
# ============================================================
def api_call(endpoint, body, credits, chain="", token="", note="",
             use_beta=False, timeout=90) -> Optional[dict]:
    if not tracker.check(credits, note.split("_")[0] if "_" in note else ""):
        return None
    prefix = BETA if use_beta else V1
    url = f"{BASE_URL}{prefix}/{endpoint}"
    headers = {"apiKey": API_KEY, "Content-Type": "application/json", "Accept": "*/*"}

    for attempt in range(3):
        try:
            time.sleep(1.0)
            resp = requests.post(url, headers=headers, json=body, timeout=timeout)

            if resp.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"  [RATE LIMITED] Waiting {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code == 404 and not use_beta:
                return api_call(endpoint, body, credits, chain, token, note,
                                use_beta=True, timeout=timeout)

            if resp.status_code == 200:
                tracker.spend(credits, endpoint, chain, token, note)
                return resp.json()

            print(f"  [ERROR] {resp.status_code}: {resp.text[:300]}")
            if attempt < 2:
                time.sleep(2 * (attempt + 1))

        except requests.exceptions.RequestException as e:
            print(f"  [NETWORK] {e}")
            if attempt < 2:
                time.sleep(3 * (attempt + 1))

    print(f"  [FAILED] {endpoint} after 3 attempts")
    return None


def save(data, filepath):
    path = RAW_DIR / filepath
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def fetch_counterparties(addr, chain, date_from, date_to, note_prefix,
                         save_dir, save_prefix, max_pages=5):
    """Fetch counterparties with pagination. Returns all items."""
    body = {
        "address": addr, "chain": chain,
        "date": {"from": date_from, "to": date_to},
        "pagination": {"page": 1, "per_page": 100},
    }
    data = api_call("profiler/address/counterparties", body, 5, chain, "",
                    f"{note_prefix}", timeout=90)
    if not data:
        return []
    save(data, f"{save_dir}/{save_prefix}.json")
    items = data.get("data", [])
    if not isinstance(items, list):
        items = []

    # Paginate
    if len(items) == 100:
        for page in range(2, max_pages + 1):
            body["pagination"]["page"] = page
            more = api_call("profiler/address/counterparties", body, 5, chain, "",
                            f"{note_prefix}_p{page}", timeout=90)
            if not more:
                break
            more_items = more.get("data", [])
            if not isinstance(more_items, list) or len(more_items) == 0:
                break
            save(more, f"{save_dir}/{save_prefix}_p{page}.json")
            items.extend(more_items)
            if len(more_items) < 100:
                break

    return items


# ============================================================
# QUERY 3: Solana Gateway Tier Mapping
# ============================================================
def query_3():
    print("\n" + "=" * 70)
    print("QUERY 3: SOLANA GATEWAY TIER MAPPING")
    print("=" * 70)

    # Pass 1: Counterparties
    print("\n--- Pass 1: Counterparties ---")
    for name, addr in SOLANA_GATEWAYS.items():
        if not tracker.check(5, "Q3"):
            break
        print(f"  {name} ({addr[:12]}...)")
        items = fetch_counterparties(
            addr, "solana", "2023-02-01", "2026-02-01",
            f"Q3_sol_cpty_{name}", "solana_cpty", name
        )
        n = len(items) if items else 0
        print(f"    → {n} counterparties")

    # Pass 2: Related wallets for unknowns
    print("\n--- Pass 2: Related wallets (unknowns) ---")
    for name in ["Unknown_1", "Unknown_2", "Unknown_3"]:
        if not tracker.check(1, "Q3"):
            break
        addr = SOLANA_GATEWAYS[name]
        print(f"  {name} ({addr[:12]}...)")
        body = {"address": addr, "chain": "solana"}
        data = api_call("profiler/address/related-wallets", body, 1,
                        "solana", "", f"Q3_sol_related_{name}")
        if data:
            save(data, f"solana_related/{name}.json")

    # Pass 3: Current balances for unknowns
    print("\n--- Pass 3: Current balances (unknowns) ---")
    for name in ["Unknown_1", "Unknown_2", "Unknown_3"]:
        if not tracker.check(1, "Q3"):
            break
        addr = SOLANA_GATEWAYS[name]
        body = {"address": addr, "chain": "solana"}
        data = api_call("profiler/address/current-balance", body, 1,
                        "solana", "", f"Q3_sol_balance_{name}")
        if data:
            save(data, f"solana_balance/{name}.json")

    print(f"\n  Q3 complete. {tracker.summary()}")


# ============================================================
# QUERY 6: Complete Ethereum Gateway Coverage
# ============================================================
def query_6():
    print("\n" + "=" * 70)
    print("QUERY 6: MISSING ETH GATEWAY COVERAGE")
    print("=" * 70)

    svb_windows = [
        ("pre_svb", "2023-01-01", "2023-03-09"),
        ("svb_stress", "2023-03-10", "2023-03-17"),
        ("post_svb", "2023-03-18", "2023-04-30"),
    ]

    for name, addr in MISSING_ETH_GATEWAYS.items():
        if not tracker.check(5, "Q6"):
            break
        print(f"\n  {name} ({addr[:12]}...)")

        # Full sample
        items = fetch_counterparties(
            addr, "ethereum", "2023-02-01", "2026-02-01",
            f"Q6_missing_cpty_{name}", "missing_eth_cpty", name
        )
        n = len(items) if items else 0
        print(f"    Full sample: {n} counterparties")

        # SVB windows
        for window_name, w_start, w_end in svb_windows:
            if not tracker.check(5, "Q6"):
                break
            items_w = fetch_counterparties(
                addr, "ethereum", w_start, w_end,
                f"Q6_missing_{window_name}_{name}", "missing_eth_cpty",
                f"{window_name}_{name}"
            )
            n_w = len(items_w) if items_w else 0
            print(f"    {window_name}: {n_w} counterparties")

    print(f"\n  Q6 complete. {tracker.summary()}")


# ============================================================
# QUERY 4: BUSD Wind-Down Counterparty Network
# ============================================================
def query_4():
    print("\n" + "=" * 70)
    print("QUERY 4: BUSD WIND-DOWN COUNTERPARTY NETWORK")
    print("=" * 70)

    BUSD_WINDOWS = [
        ("pre_busd",    "2022-12-01", "2023-02-09"),
        ("busd_early",  "2023-02-10", "2023-06-30"),
        ("busd_late",   "2023-07-01", "2023-12-31"),
    ]

    for window_name, w_start, w_end in BUSD_WINDOWS:
        print(f"\n--- Window: {window_name} ({w_start} to {w_end}) ---")
        for gw_name, gw_addr in ETH_GATEWAYS.items():
            if not tracker.check(5, "Q4"):
                break
            print(f"  {gw_name}")
            items = fetch_counterparties(
                gw_addr, "ethereum", w_start, w_end,
                f"Q4_busd_{window_name}_{gw_name}", "busd_cpty",
                f"{window_name}_{gw_name}"
            )
            n = len(items) if items else 0
            if n > 0:
                print(f"    → {n} counterparties")
            else:
                print(f"    → empty/failed")

    print(f"\n  Q4 complete. {tracker.summary()}")


# ============================================================
# QUERY 5: Base + Arbitrum Gateway Mapping
# ============================================================
def query_5():
    print("\n" + "=" * 70)
    print("QUERY 5: BASE + ARBITRUM GATEWAY MAPPING")
    print("=" * 70)

    # Base counterparties
    print("\n--- Base ---")
    for name, addr in BASE_GATEWAYS.items():
        if not tracker.check(5, "Q5"):
            break
        print(f"  {name} ({addr[:12]}...)")
        items = fetch_counterparties(
            addr, "base", "2023-08-01", "2026-02-01",
            f"Q5_base_cpty_{name}", "base_cpty", name
        )
        n = len(items) if items else 0
        print(f"    → {n} counterparties")

    # Arbitrum counterparties
    print("\n--- Arbitrum ---")
    for name, addr in ARBITRUM_GATEWAYS.items():
        if not tracker.check(5, "Q5"):
            break
        print(f"  {name} ({addr[:12]}...)")
        items = fetch_counterparties(
            addr, "arbitrum", "2023-02-01", "2026-02-01",
            f"Q5_arb_cpty_{name}", "arbitrum_cpty", name
        )
        n = len(items) if items else 0
        print(f"    → {n} counterparties")

    # Related wallets for Base unknowns
    print("\n--- Base unknowns: related wallets ---")
    for name in [n for n in BASE_GATEWAYS if n.startswith("Unknown")]:
        if not tracker.check(1, "Q5"):
            break
        addr = BASE_GATEWAYS[name]
        body = {"address": addr, "chain": "base"}
        data = api_call("profiler/address/related-wallets", body, 1,
                        "base", "", f"Q5_base_related_{name}")
        if data:
            save(data, f"base_related/{name}.json")

    # Current balances for Base unknowns
    print("\n--- Base unknowns: balances ---")
    for name in [n for n in BASE_GATEWAYS if n.startswith("Unknown")]:
        if not tracker.check(1, "Q5"):
            break
        addr = BASE_GATEWAYS[name]
        body = {"address": addr, "chain": "base"}
        data = api_call("profiler/address/current-balance", body, 1,
                        "base", "", f"Q5_base_balance_{name}")
        if data:
            save(data, f"base_balance/{name}.json")

    print(f"\n  Q5 complete. {tracker.summary()}")


# ============================================================
# QUERY 2: Monthly Time-Varying Counterparty Network
# ============================================================
def build_monthly_windows():
    windows = []
    for year in [2023, 2024, 2025]:
        for month in range(1, 13):
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
            if start >= date(2023, 2, 1) and start <= date(2026, 1, 1):
                windows.append((start.isoformat(), end.isoformat()))
    return windows


# Priority order: high-volume gateways first so we get most value if budget runs out
Q2_PRIORITY_GATEWAYS = [
    "Circle_Treasury", "Coinbase_Custody", "Binance_Hot_Wallet",
    "Tether_Treasury", "OKX", "Kraken", "Bybit", "Coinbase_USDC",
    "Kraken_Hot", "Uniswap_V3_Router", "Curve_3pool", "1inch_Router",
    "Aave_V3_Pool", "Paxos_Treasury", "Gemini",
]

def query_2():
    print("\n" + "=" * 70)
    print("QUERY 2: MONTHLY COUNTERPARTY NETWORK (36 MONTHS)")
    print("=" * 70)

    windows = build_monthly_windows()
    print(f"  {len(windows)} monthly windows: {windows[0][0]} to {windows[-1][1]}")
    print(f"  {len(Q2_PRIORITY_GATEWAYS)} gateways (priority order)")
    total_calls = len(windows) * len(Q2_PRIORITY_GATEWAYS)
    print(f"  Estimated calls: {total_calls} × 5 credits = {total_calls * 5} credits")

    completed = 0
    skipped = 0
    empty = 0

    for gw_name in Q2_PRIORITY_GATEWAYS:
        gw_addr = ETH_GATEWAYS[gw_name]
        print(f"\n  === {gw_name} ===")

        for w_start, w_end in windows:
            month_tag = w_start[:7]
            save_name = f"{gw_name}_{month_tag}"
            save_path = RAW_DIR / "monthly_cpty" / f"{save_name}.json"

            # Skip if already collected
            if save_path.exists():
                skipped += 1
                continue

            if not tracker.check(5, "Q2"):
                print(f"  [BUDGET] Q2 cap reached at {completed} calls.")
                print(f"\n  Q2 partial. Completed: {completed}, Skipped: {skipped}, Empty: {empty}")
                print(f"  {tracker.summary()}")
                return

            items = fetch_counterparties(
                gw_addr, "ethereum", w_start, w_end,
                f"Q2_monthly_{gw_name}_{month_tag}", "monthly_cpty", save_name
            )
            n = len(items) if items else 0
            if n == 0:
                empty += 1
            completed += 1

            if completed % 20 == 0:
                print(f"    [{completed}/{total_calls}] {tracker.summary()}")

    print(f"\n  Q2 complete. Completed: {completed}, Skipped: {skipped}, Empty: {empty}")
    print(f"  {tracker.summary()}")


# ============================================================
# CONSOLIDATION
# ============================================================
def consolidate():
    print("\n" + "=" * 70)
    print("CONSOLIDATION")
    print("=" * 70)

    # Helper to parse counterparty JSON files
    def parse_cpty_file(filepath):
        try:
            with open(filepath) as f:
                data = json.load(f)
            items = data.get("data", [])
            if isinstance(items, dict):
                items = items.get("data", items.get("rows", []))
            if not isinstance(items, list):
                return []
            return items
        except Exception:
            return []

    def _safe_label(val):
        """Normalize label — Nansen sometimes returns list instead of str."""
        if val is None:
            return "Unknown"
        if isinstance(val, list):
            return ", ".join(str(v) for v in val) if val else "Unknown"
        return str(val)

    def extract_row(item, source, chain="ethereum"):
        return {
            "source_gateway": source,
            "counterparty_address": item.get("counterparty_address", item.get("address", "")),
            "counterparty_label": _safe_label(item.get("counterparty_address_label",
                                           item.get("label", item.get("address_label", "Unknown")))),
            "interaction_count": item.get("interaction_count", item.get("count", 0)),
            "total_volume_usd": item.get("total_volume_usd", item.get("volume_usd", 0)),
            "volume_in_usd": item.get("volume_in_usd", 0),
            "volume_out_usd": item.get("volume_out_usd", 0),
            "chain": chain,
        }

    # ---- Q3: Solana ----
    print("\n  --- Solana Gateway Network ---")
    sol_rows = []
    for f in sorted((RAW_DIR / "solana_cpty").glob("*.json")):
        source = f.stem.split("_p")[0]  # strip pagination suffix
        for item in parse_cpty_file(f):
            sol_rows.append(extract_row(item, source, "solana"))

    if sol_rows:
        write_csv(sol_rows, "solana_gateway_network.csv")
        print(f"    {len(sol_rows)} rows")

        # Tier mapping
        SOLANA_TIERS = {
            "Binance_1": 2, "Binance_2": 2, "Circle": 1, "Circle_Bridge": 1,
            "Coinbase_1": 1, "Coinbase_2": 1, "KuCoin": 2, "OKX_Hot": 2, "OKX_2": 2,
            "Gate": 2, "Jupiter_Perps": 3, "JLP_Pool": 3, "Drift": 3,
            "Unknown_1": 0, "Unknown_2": 0, "Unknown_3": 0,
        }
        tier_map = []
        for name in SOLANA_GATEWAYS:
            gw_rows = [r for r in sol_rows if r["source_gateway"] == name]
            vol = sum(float(r.get("total_volume_usd", 0) or 0) for r in gw_rows)
            n_cpty = len(gw_rows)
            top_cpty = max(gw_rows, key=lambda r: float(r.get("total_volume_usd", 0) or 0))["counterparty_label"] if gw_rows else ""
            top_vol = max(float(r.get("total_volume_usd", 0) or 0) for r in gw_rows) if gw_rows else 0
            tier_map.append({
                "gateway": name, "tier": SOLANA_TIERS.get(name, 0),
                "volume_usd": vol, "counterparty_count": n_cpty,
                "top_counterparty": top_cpty, "top_counterparty_volume": top_vol,
            })
        write_csv(tier_map, "solana_tier_mapping.csv")

        # Compute tier shares
        tier_vols = {}
        for r in tier_map:
            t = r["tier"]
            tier_vols[t] = tier_vols.get(t, 0) + r["volume_usd"]
        total = sum(tier_vols.values())
        if total > 0:
            print(f"    Solana tier shares:")
            for t in sorted(tier_vols):
                label = {0: "Unknown", 1: "Tier 1", 2: "Tier 2", 3: "Tier 3"}.get(t, f"Tier {t}")
                pct = tier_vols[t] / total * 100
                print(f"      {label}: {pct:.1f}% (${tier_vols[t]/1e9:.1f}B)")

    # ---- Q4: BUSD ----
    print("\n  --- BUSD Counterparty Network ---")
    busd_rows = []
    busd_summary_rows = []
    for f in sorted((RAW_DIR / "busd_cpty").glob("*.json")):
        # Parse: window_gateway or window_gateway_pN
        stem = f.stem
        parts = stem.split("_", 1)
        if len(parts) < 2:
            continue
        # Find the window prefix
        for w in ["pre_busd", "busd_early", "busd_late"]:
            if stem.startswith(w + "_"):
                window = w
                gw = stem[len(w) + 1:].split("_p")[0]
                break
        else:
            continue

        items = parse_cpty_file(f)
        for item in items:
            row = extract_row(item, gw)
            row["window"] = window
            busd_rows.append(row)

    if busd_rows:
        write_csv(busd_rows, "busd_counterparty_network.csv")
        print(f"    {len(busd_rows)} rows")

        # Summary per window+gateway
        from collections import defaultdict
        busd_agg = defaultdict(lambda: {"total_volume": 0, "n_counterparties": 0,
                                         "wintermute_volume": 0, "paxos_volume": 0})
        for r in busd_rows:
            key = (r["window"], r["source_gateway"])
            busd_agg[key]["total_volume"] += float(r.get("total_volume_usd", 0) or 0)
            busd_agg[key]["n_counterparties"] += 1
            raw_label = r.get("counterparty_label") or ""
            label = (raw_label if isinstance(raw_label, str) else str(raw_label)).lower()
            if "wintermute" in label:
                busd_agg[key]["wintermute_volume"] += float(r.get("total_volume_usd", 0) or 0)
            if "paxos" in label:
                busd_agg[key]["paxos_volume"] += float(r.get("total_volume_usd", 0) or 0)

        busd_summary = [
            {"window": k[0], "gateway": k[1], **v}
            for k, v in sorted(busd_agg.items())
        ]
        write_csv(busd_summary, "busd_network_summary.csv")

    # ---- Q5: L2s ----
    print("\n  --- L2 Gateway Network ---")
    l2_rows = []
    for chain_dir, chain_name in [("base_cpty", "base"), ("arbitrum_cpty", "arbitrum")]:
        for f in sorted((RAW_DIR / chain_dir).glob("*.json")):
            source = f.stem.split("_p")[0]
            for item in parse_cpty_file(f):
                l2_rows.append(extract_row(item, source, chain_name))

    if l2_rows:
        write_csv(l2_rows, "l2_gateway_network.csv")
        print(f"    {len(l2_rows)} rows")

        # Tier mapping for L2s
        L2_TIERS = {
            # Base
            "Morpho_Blue": ("base", 3), "Avantis_Vault": ("base", 3),
            "Binance_Hot": ("base", 2), "Coinbase_Deposit": ("base", 1),
            "Unknown_Base_1": ("base", 0), "Unknown_Base_2": ("base", 0),
            "Unknown_Base_3": ("base", 0), "Unknown_Base_4": ("base", 0),
            "Unknown_Base_5": ("base", 0),
            # Arbitrum
            "Hyperliquid": ("arbitrum", 3), "Binance_Wallet": ("arbitrum", 2),
            "Binance_Hot": ("arbitrum", 2), "Binance_Reserve": ("arbitrum", 2),
            "Binance_Hot2": ("arbitrum", 2),
            "Aave_aUSDC": ("arbitrum", 3), "Aave_aUSDT": ("arbitrum", 3),
            "Ostium_LP": ("arbitrum", 3), "GMX_WBTC_USDC": ("arbitrum", 3),
            "Bitget": ("arbitrum", 2), "Circle": ("arbitrum", 1),
            "Bybit": ("arbitrum", 2),
        }
        l2_tier_map = []
        for name in list(BASE_GATEWAYS) + list(ARBITRUM_GATEWAYS):
            chain, tier = L2_TIERS.get(name, ("unknown", 0))
            gw_rows = [r for r in l2_rows if r["source_gateway"] == name]
            vol = sum(float(r.get("total_volume_usd", 0) or 0) for r in gw_rows)
            n_cpty = len(gw_rows)
            top_cpty = ""
            top_vol = 0
            if gw_rows:
                best = max(gw_rows, key=lambda r: float(r.get("total_volume_usd", 0) or 0))
                top_cpty = best.get("counterparty_label", "")
                top_vol = float(best.get("total_volume_usd", 0) or 0)
            l2_tier_map.append({
                "chain": chain, "gateway": name, "tier": tier,
                "volume_usd": vol, "counterparty_count": n_cpty,
                "top_counterparty": top_cpty, "top_counterparty_volume": top_vol,
            })
        write_csv(l2_tier_map, "l2_tier_mapping.csv")

    # ---- Q6: Complete ETH ----
    print("\n  --- Complete ETH Counterparty Network ---")
    # Merge existing v2 data + new Q6 data
    eth_rows = []
    # Existing from nansen_v2
    v2_dir = Path(__file__).resolve().parent.parent.parent / "nansen_v2" / "raw"
    for f in sorted(v2_dir.glob("eth_counterparties_*.json")):
        source = f.stem.replace("eth_counterparties_", "")
        for item in parse_cpty_file(f):
            eth_rows.append(extract_row(item, source))
    # New Q6 data
    for f in sorted((RAW_DIR / "missing_eth_cpty").glob("*.json")):
        stem = f.stem
        # Skip SVB window files for the main network
        if any(w in stem for w in ["pre_svb", "svb_stress", "post_svb"]):
            continue
        source = stem.split("_p")[0]
        for item in parse_cpty_file(f):
            eth_rows.append(extract_row(item, source))

    if eth_rows:
        write_csv(eth_rows, "complete_eth_counterparty_network.csv")
        print(f"    {len(eth_rows)} rows (existing + new)")

    # ---- Q2: Monthly ----
    print("\n  --- Monthly Counterparty Network ---")
    monthly_rows = []
    monthly_summary = []
    from collections import defaultdict

    monthly_agg = defaultdict(lambda: {
        "n_gateways_active": 0, "n_unique_counterparties": set(),
        "total_volume": 0, "wintermute_volume": 0, "wintermute_gateways": set(),
        "cumberland_volume": 0, "counterparty_volumes": defaultdict(float),
    })

    for f in sorted((RAW_DIR / "monthly_cpty").glob("*.json")):
        stem = f.stem
        # Parse gateway_YYYY-MM or gateway_YYYY-MM_pN
        parts = stem.rsplit("_", 1)
        if len(parts) < 2:
            continue
        # Find month tag (YYYY-MM pattern)
        month_tag = None
        for p in stem.split("_"):
            if len(p) == 7 and p[4] == "-":
                month_tag = p
                break
        if not month_tag:
            continue

        gw_name = stem.split(f"_{month_tag}")[0]
        items = parse_cpty_file(f)

        for item in items:
            row = extract_row(item, gw_name)
            row["month"] = month_tag
            monthly_rows.append(row)

            vol = float(row.get("total_volume_usd", 0) or 0)
            raw_label = row.get("counterparty_label") or ""
            label = (raw_label if isinstance(raw_label, str) else str(raw_label)).lower()
            addr = row.get("counterparty_address", "")

            monthly_agg[month_tag]["total_volume"] += vol
            monthly_agg[month_tag]["n_unique_counterparties"].add(addr)
            monthly_agg[month_tag]["counterparty_volumes"][addr] += vol

            if "wintermute" in label:
                monthly_agg[month_tag]["wintermute_volume"] += vol
                monthly_agg[month_tag]["wintermute_gateways"].add(gw_name)
            if "cumberland" in label:
                monthly_agg[month_tag]["cumberland_volume"] += vol

    if monthly_rows:
        write_csv(monthly_rows, "monthly_counterparty_network.csv")
        print(f"    {len(monthly_rows)} rows")

        # Build summary
        for month in sorted(monthly_agg):
            agg = monthly_agg[month]
            # Count active gateways
            active_gws = set(r["source_gateway"] for r in monthly_rows if r.get("month") == month)
            n_cpty = len(agg["n_unique_counterparties"])
            # Top 3 share
            all_vols = sorted(agg["counterparty_volumes"].values(), reverse=True)
            top3 = sum(all_vols[:3]) / agg["total_volume"] if agg["total_volume"] > 0 else 0
            # Density
            density = len(agg["counterparty_volumes"]) / (len(active_gws) * n_cpty) if n_cpty > 0 and len(active_gws) > 0 else 0

            monthly_summary.append({
                "month": month,
                "n_gateways_active": len(active_gws),
                "n_unique_counterparties": n_cpty,
                "total_volume": agg["total_volume"],
                "wintermute_volume": agg["wintermute_volume"],
                "wintermute_gateways": len(agg["wintermute_gateways"]),
                "cumberland_volume": agg["cumberland_volume"],
                "top3_counterparty_share": round(top3, 4),
                "network_density": round(density, 4),
            })

        write_csv(monthly_summary, "monthly_network_summary.csv")
        print(f"    {len(monthly_summary)} monthly summaries")

    # ---- Collection summary ----
    summary = {
        "timestamp": datetime.now().isoformat(),
        "credits_used": tracker.total_used,
        "files_collected": {
            "solana_cpty": len(list((RAW_DIR / "solana_cpty").glob("*.json"))),
            "busd_cpty": len(list((RAW_DIR / "busd_cpty").glob("*.json"))),
            "base_cpty": len(list((RAW_DIR / "base_cpty").glob("*.json"))),
            "arbitrum_cpty": len(list((RAW_DIR / "arbitrum_cpty").glob("*.json"))),
            "missing_eth_cpty": len(list((RAW_DIR / "missing_eth_cpty").glob("*.json"))),
            "monthly_cpty": len(list((RAW_DIR / "monthly_cpty").glob("*.json"))),
        },
        "processed_files": [f.name for f in sorted(PROCESSED_DIR.glob("*.csv"))],
    }
    with open(OUT_DIR / "collection_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Consolidation complete. {tracker.summary()}")


def write_csv(rows, filename):
    if not rows:
        return
    path = PROCESSED_DIR / filename
    # Normalize: ensure all dicts, convert sets to counts
    clean = []
    for r in rows:
        c = {}
        for k, v in r.items():
            if isinstance(v, set):
                c[k] = len(v)
            else:
                c[k] = v
        clean.append(c)

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=clean[0].keys())
        writer.writeheader()
        writer.writerows(clean)
    print(f"    [SAVED] {path} ({len(clean)} rows)")


# ============================================================
# MAIN
# ============================================================
QUERIES = {
    "Q3": ("Solana Gateway Tier Mapping", query_3),
    "Q6": ("Missing ETH Gateway Coverage", query_6),
    "Q4": ("BUSD Wind-Down Network", query_4),
    "Q5": ("Base + Arbitrum L2 Mapping", query_5),
    "Q2": ("Monthly Counterparty Network", query_2),
}

def main():
    if not API_KEY:
        print("ERROR: Set NANSEN_API_KEY: export NANSEN_API_KEY='your_key'")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Nansen Collector v4 — Queries 2-6")
    parser.add_argument("--query", type=str, help="Run specific query (Q2/Q3/Q4/Q5/Q6)")
    parser.add_argument("--all", action="store_true", help="Run all queries in priority order")
    parser.add_argument("--consolidate", action="store_true", help="Build summary CSVs")
    parser.add_argument("--status", action="store_true", help="Show credit status")
    args = parser.parse_args()

    if args.status:
        print(tracker.summary())
        return

    if args.consolidate:
        consolidate()
        return

    if args.query:
        key = args.query.upper()
        if key in QUERIES:
            name, func = QUERIES[key]
            print(f"\nRunning {key}: {name}")
            func()
        else:
            print(f"Invalid query '{args.query}'. Choose Q2/Q3/Q4/Q5/Q6.")
        return

    if args.all:
        for key in ["Q3", "Q6", "Q4", "Q5", "Q2"]:
            name, func = QUERIES[key]
            print(f"\n{'#' * 70}")
            print(f"  {key}: {name}")
            print(f"{'#' * 70}")
            func()
            if tracker.total_used >= BUDGET_HARD_STOP:
                print(f"\n  Global budget stop at {tracker.total_used}.")
                break
        consolidate()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
