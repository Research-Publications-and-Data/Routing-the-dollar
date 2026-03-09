# config/settings.py

# ── API Keys ─────────────────────────────────────────────────
FRED_API_KEY = ""  # REQUIRED — get free at https://fred.stlouisfed.org/docs/api/api_key.html
COINGECKO_API_KEY = ""  # OPTIONAL — free tier works
DUNE_API_KEY = ""  # OPTIONAL — queries can run in Dune UI
ARTEMIS_API_KEY = ""  # OPTIONAL — for use-case decomposition

# ── Date Ranges ──────────────────────────────────────────────
PRIMARY_START = "2023-02-01"
PRIMARY_END = "2026-01-31"
EXTENDED_START = "2019-01-01"

# ── FRED Series ──────────────────────────────────────────────
FRED_SERIES = {
    "WSHOMCB": "Fed total assets (weekly)",
    "RRPONTSYD": "ON RRP outstanding (daily)",
    "DFF": "Effective fed funds rate (daily)",
    "SOFR": "SOFR (daily)",
    "DGS10": "10-year Treasury yield (daily)",
    "DPSACBW027SBOG": "Total deposits, commercial banks (weekly SA)",
    "LTDACBW027SBOG": "Large time deposits, all commercial banks (weekly SA)",
    "SAVINGSL": "Savings deposits (monthly SA)",
    "DEMDEPSL": "Demand deposits (monthly SA)",
    "LTDACBQ158SBOG": "Large time deposits, all commercial banks (quarterly)",
}

# ── Token Contracts (Ethereum) ───────────────────────────────
TOKEN_CONTRACTS = {
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "BUSD": "0x4Fabb145d64652a948d72533023f6E7A623C7C53",
}

# ── Gateway Addresses (Ethereum) ─────────────────────────────
GATEWAYS = {
    # Tier 1 (CLII > 0.75)
    "0x55FE002aefF02F77364de339a1292923A15844B8": {"name": "Circle Treasury", "tier": 1, "clii": 0.92},
    "0xE25a329d385f77df5D4eD56265babe2b99A5436e": {"name": "Paxos", "tier": 1, "clii": 0.88},
    "0x503828976D22510aad0201ac7EC88293211D23Da": {"name": "Coinbase", "tier": 1, "clii": 0.85},
    "0xd24400ae8BfEBb18cA49Be86258a3C749cf46853": {"name": "Gemini", "tier": 1, "clii": 0.82},
    "0x0e7EB45C8F8DA3D62627b1B16e107bBf8BcD24e6": {"name": "PayPal", "tier": 1, "clii": 0.88},
    "0x5C985E89DDe482eFE97ea9f1950aD149Eb73829B": {"name": "BitGo", "tier": 1, "clii": 0.80},
    # Tier 2 (CLII 0.30–0.75)
    "0x5754284f345afc66a98fbB0a0Afe71e0F007B949": {"name": "Tether Treasury", "tier": 2, "clii": 0.45},
    "0x28C6c06298d514Db089934071355E5743bf21d60": {"name": "Binance", "tier": 2, "clii": 0.38},
    "0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2": {"name": "Kraken", "tier": 2, "clii": 0.58},
    "0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b": {"name": "OKX", "tier": 2, "clii": 0.40},
    "0xf89d7b9c864f589bbF53a82105107622B35EaA40": {"name": "Bybit", "tier": 2, "clii": 0.40},
    "0x40B38765696e3d5d8d9d834D8AaD4bB6e418E489": {"name": "Robinhood", "tier": 2, "clii": 0.75},
    # Tier 3 (CLII < 0.30)
    "0xE592427A0AEce92De3Edee1F18E0157C05861564": {"name": "Uniswap V3", "tier": 3, "clii": 0.15},
    "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD": {"name": "Uniswap Universal Router", "tier": 3, "clii": 0.15},
    "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7": {"name": "Curve 3pool", "tier": 3, "clii": 0.18},
    "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2": {"name": "Aave V3", "tier": 3, "clii": 0.20},
    "0x1111111254EEB25477B68fb85Ed929f73A960582": {"name": "1inch", "tier": 3, "clii": 0.18},
    "0xc3d688B66703497DAA19211EEdff47f25384cdc3": {"name": "Compound V3", "tier": 3, "clii": 0.18},
    "0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b": {"name": "Tornado Cash", "tier": 3, "clii": 0.02},
}

# ── Stablecoin IDs ───────────────────────────────────────────
STABLECOIN_IDS_COINGECKO = {
    "tether": "USDT", "usd-coin": "USDC", "dai": "DAI",
    "binance-usd": "BUSD", "true-usd": "TUSD", "first-digital-usd": "FDUSD",
    "paypal-usd": "PYUSD", "ethena-usde": "USDe", "usds": "USDS", "usual-usd": "USD0",
}

STABLECOIN_IDS_DEFILLAMA = {1: "USDT", 2: "USDC", 3: "DAI", 4: "BUSD", 5: "TUSD"}

# ── FOMC Dates (2023–2026) ───────────────────────────────────
# Format: (date, decision_bps, classification)
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

# ── Enforcement Actions (for CLII validation) ────────────────
ENFORCEMENT_ACTIONS = [
    {"gateway": "Tether Treasury", "date": "2021-10-15", "agency": "CFTC", "amount_usd": 41_000_000, "description": "Settlement for misrepresenting reserves"},
    {"gateway": "Tether Treasury", "date": "2021-02-23", "agency": "NY AG", "amount_usd": 18_500_000, "description": "Settlement for reserve misrepresentation"},
    {"gateway": "Binance", "date": "2023-11-21", "agency": "DOJ", "amount_usd": 4_300_000_000, "description": "Criminal settlement, BSA/AML violations"},
    {"gateway": "Binance", "date": "2023-06-05", "agency": "SEC", "amount_usd": 0, "description": "Civil suit, securities violations"},
    {"gateway": "Tornado Cash", "date": "2022-08-08", "agency": "OFAC", "amount_usd": 0, "description": "SDN designation"},
    {"gateway": "Kraken", "date": "2023-02-09", "agency": "SEC", "amount_usd": 30_000_000, "description": "Staking settlement"},
    {"gateway": "Kraken", "date": "2023-11-28", "agency": "FinCEN/OFAC", "amount_usd": 362_158, "description": "BSA violations, Iran sanctions"},
    {"gateway": "Coinbase", "date": "2023-06-06", "agency": "SEC", "amount_usd": 0, "description": "Civil suit (dismissed/settled 2025)"},
    {"gateway": "Paxos", "date": "2023-02-13", "agency": "NYDFS", "amount_usd": 0, "description": "BUSD cease-mint order (supervisory, not penalty)"},
]

# ── Chart Style ──────────────────────────────────────────────
CHART_STYLE = {
    "font_body": "Georgia", "font_labels": "Arial", "dpi": 300,
    "figsize_landscape": (8, 5), "figsize_portrait": (6, 8),
    "colors": {
        "primary": "#003366", "secondary": "#4682B4", "tertiary": "#D3D3D3",
        "stress": "#CC3333", "positive": "#339933",
        "tier1": "#003366", "tier2": "#4682B4", "tier3": "#999999",
    },
    "grid_color": "#E0E0E0", "grid_style": "--",
    "title_size": 12, "label_size": 10, "source_size": 8,
}
