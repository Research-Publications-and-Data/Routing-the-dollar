# Routing the Dollar -- Replication Package

**Paper:** Routing the Dollar: Gateway Infrastructure, Monetary Policy Transmission, and the Dollar's International Functions in Digital Markets

**Author:** Zach Zukowski, Tokeneconomics

**Venue:** Prepared for the Fifth Conference on International Roles of the U.S. Dollar, Board of Governors of the Federal Reserve System and Federal Reserve Bank of New York, June 22-23, 2026

**Version:** v42 (conference release, March 2026)

## Repository Structure

```
regulating_routers_v42/
├── config/
│   └── settings.py                      # API keys, gateway registry, chart style
├── scripts/                             # Numbered Python pipeline (70+ scripts)
├── queries/
│   └── dune/                            # 29 Dune Analytics SQL queries
├── data/
│   ├── raw/                             # Source data (FRED, Dune, Artemis, CoinGecko, DefiLlama)
│   ├── processed/                       # Computed intermediates backing paper claims
│   └── exhibits/                        # Generated chart PNGs and PDFs
├── media/                               # 74 exhibit PNGs embedded in paper/supplement
├── MANIFEST.md                          # Data provenance
├── CHANGELOG_v25_to_v42.md              # What changed from v25
├── requirements.txt
└── .gitignore
```

## Data Sources

| Source | Data | Access |
|--------|------|--------|
| FRED | Fed balance sheet, ON RRP, rates, deposits | Free API key ([fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html)) |
| Dune Analytics | On-chain USDC/USDT volumes (Ethereum, Tron, Solana, Base) | Free tier or Pro; SQL in `queries/dune/` |
| DefiLlama | Stablecoin market capitalization time series | Free, no key |
| CoinGecko | Exchange volume shares, depeg price data | Free tier or Pro |
| Artemis | Application-level stablecoin categorization | API key required |
| Nansen | Entity labels and counterparty flows | Commercial license; see `data/raw/NANSEN_NOTICE.md` |
| NY Fed | ON RRP counterparty data | Public API |

## Quick Start

```bash
pip install -r requirements.txt
```

Set API keys in environment or `config/settings.py` as needed:
- `FRED_API_KEY` (required for FRED pulls)
- `DUNE_API_KEY` (required for Dune query execution; alternatively run SQL in Dune UI)
- Nansen API key (commercial; see `data/raw/NANSEN_NOTICE.md`)

## Pipeline

Scripts are numbered for sequential execution. Core pipeline:

```bash
cd scripts

# Sprint 1: Critical path
python 01_fred_pull.py              # Pull FRED data
python 03_extended_sample.py        # Extended stablecoin supply (DefiLlama/CoinGecko)
python 02_cointegration.py          # Johansen cointegration, VECM, IRFs

# Sprint 2: Data expansion
python 04_rolling_corr.py           # Rolling correlations (extended sample)
python 05_fomc_event_study.py       # FOMC event study
python 06_onrrp_decomposition.py    # ON RRP counterparty decomposition
python 07_deposit_displacement.py   # Deposit displacement analysis
python 08a_dune_queries.py          # Execute Dune queries (needs API key)
python 08b_coverage_ratio.py        # Gateway coverage ratio

# Sprint 2b: Expanded gateway analysis
python 29_expanded_gateway_analysis.py  # 51-address, 19-entity analysis
python 32_dune_daily_expanded.py        # Daily expanded volumes
python 33_recompute_metrics_v2.py       # HHI, tier shares, SVB metrics

# Sprint 3: Validation
python 09_depeg_data.py             # Depeg data for CLII validation
python 10_clii_validation.py        # CLII empirical validation
python 10_irf_bootstrap.py          # Bootstrap IRF confidence intervals
python 11_usecase_decomposition.py  # Use-case decomposition

# Sprint 4: Robustness
python 13_placebo_cointegration.py  # Placebo cointegration tests
python 14_cross_stablecoin_cointegration.py  # Cross-stablecoin tests
python 15_weak_exogeneity.py        # Johansen weak exogeneity
python phase2_phase3_compute.py     # CLII robustness (no-freeze, PCA)

# Verification
python verify_claims.py             # Verify paper statistics
python audit_replication_package.py # Structural audit

# Exhibits
python regen_exhibits.py            # Regenerate all paper exhibits
python build_supplement.py          # Build online supplement docx
```

## Dune SQL Queries

All 29 Dune Analytics SQL queries are stored in `queries/dune/`. Key queries:

| Query | Purpose |
|-------|---------|
| `phase1_eth_expanded_gateway.sql` | Main query: 51 addresses, 19 entities, daily volumes |
| `phase1_eth_total_volume.sql` | Total Ethereum USDC+USDT volume (denominator) |
| `phase2_tron_gateway.sql` | Tron USDT gateway volumes |
| `phase3_solana_gateway.sql` | Solana USDC+USDT gateway volumes |
| `phase4_base_gateway.sql` | Base USDC gateway volumes |
| `internal_transfers.sql` | Internal transfer detection (Binance 18.3%) |
| `bilateral_flows.sql` | Bilateral flow double-counting check |

## CLII Scores

The Compliance-Linked Infrastructure Index (CLII) scores use Table 2a as the single source of truth. The 5-dimension architecture is: License (25%), Reserve Transparency (20%), Freeze/Blacklist Capability (20%), Compliance Infrastructure (20%), Geographic/Sanctions Restrictions (15%).

Tier cutoffs: Tier 1 > 0.75 (strict), Tier 2 >= 0.30, Tier 3 < 0.30.

## Changes from v25

See `CHANGELOG_v25_to_v42.md` for a complete list. Key additions: expanded gateway registry (19 entities, 51 addresses), multi-chain analysis (Ethereum + Tron + Solana + Base), yield-spread mechanism confirmation, VECM weak exogeneity, bootstrap IRFs, placebo tests.
