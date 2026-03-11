# Routing the Dollar: Gateway Infrastructure as Monetary Policy Transmission Channel

Replication package for "The Control Layer of Tokenized Dollar Assets: Gateway Infrastructure as Monetary Policy Transmission Channel," prepared for the Fifth Conference on the International Roles of the U.S. Dollar, Federal Reserve Board & Federal Reserve Bank of New York.

## Repository Structure

```
regulating_routers_v25/
├── Routing_the_Dollar_v41.docx          # Main paper (final)
├── Routing_the_Dollar_Supplement_v42.docx  # Online supplement (final)
├── paper_v25.md                         # Markdown source (supplement builder input)
├── config/
│   └── settings.py                      # Chart style, Dune API key
├── scripts/                             # Numbered Python pipeline (70+ scripts)
├── queries/
│   └── dune/                            # 29 Dune Analytics SQL queries
├── data/
│   ├── raw/                             # Source data (FRED, Dune, Artemis, CoinGecko, DefiLlama)
│   ├── processed/                       # Computed intermediates backing paper claims
│   └── exhibits/                        # Generated chart PNGs and PDFs
├── media/                               # 74 exhibit PNGs embedded in paper/supplement
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

## Key Data Files

| File | Description |
|------|-------------|
| `data/raw/dune_eth_daily_expanded_v2.csv` | Daily USDC+USDT gateway volumes, 51 addresses, 19 entities, Feb 2023–Jan 2026 |
| `data/raw/dune_eth_expanded_gateway_v2.csv` | Monthly gateway volumes by entity and token |
| `data/raw/fred_all_series.csv` | 10 FRED series: Fed assets, ON RRP, SOFR, DFF, DGS10, deposits |
| `data/raw/stablecoin_supply_extended.csv` | Daily stablecoin market caps (2019–2026) |
| `data/processed/unified_extended_dataset.csv` | Merged FRED + stablecoin supply (weekly) |
| `data/processed/exhibit_C1_gateway_shares_daily_upgraded.csv` | Daily tier shares (source for Exhibit C1) |
| `data/processed/exhibit_C2_concentration_daily_upgraded.csv` | Daily HHI by entity and tier |
| `data/processed/gateway_volume_summary_v2.csv` | Aggregate gateway statistics (Table 2 source) |
| `data/processed/clii_nofreeze_robustness.csv` | CLII scores with/without freeze dimension |
| `data/processed/vecm_reconciliation.json` | VECM coefficients and Johansen test results |
| `data/processed/fomc_events.csv` | FOMC event study: supply changes at t+1,3,5,10 |
| `data/processed/placebo_swing_stats.csv` | SVB placebo test (50 windows) |
| `data/raw/dtwexbgs_weekly.csv` | FRED DTWEXBGS trade-weighted dollar index (weekly) |
| `data/raw/vixcls_weekly.csv` | FRED VIXCLS closing VIX (weekly) |
| `data/processed/quadrivariate_robustness.csv` | Johansen trace stats for baseline, +DTWEXBGS, +VIX |
| `data/processed/quadrivariate_alpha.csv` | VECM alpha coefficients for quadrivariate systems |
| `data/processed/quadrivariate_unit_roots.csv` | ADF unit root tests on all 5 series |
| `data/processed/yield_spread_robustness.csv` | Granger F-stats at lags 1–4, both directions |

## Reproduction

### Prerequisites

```bash
pip install -r requirements.txt
```

Set API keys in environment or `config/settings.py` as needed:
- `FRED_API_KEY` (required for FRED pulls)
- `DUNE_API_KEY` (required for Dune query execution; alternatively run SQL in Dune UI)
- Nansen API key (commercial; see `data/raw/NANSEN_NOTICE.md`)

### Pipeline

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

# Sprint 5: Quadrivariate + yield-spread robustness
python 16_quadrivariate_robustness.py      # DTWEXBGS + VIX quadrivariate Johansen
python 17_yield_spread_robustness.py       # Compound yield-spread Granger causality

# Verification
python verify_claims.py             # Verify paper statistics
python audit_replication_package.py # Structural audit

# Exhibits
python regen_exhibits.py            # Regenerate all paper exhibits
python build_supplement.py          # Build online supplement docx
```

### Dune SQL Queries

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

### Nansen Data

Raw Nansen entity labels are not redistributable. See `data/raw/NANSEN_NOTICE.md` for details. The collection script (`scripts/nansen_collector_v4.py`) documents the methodology.

## CLII Scores

The Compliance-Linked Infrastructure Index (CLII) scores in this package use v42 docx Table 2a as the single source of truth. The 5-dimension architecture is: License (25%), Reserve Transparency (20%), Freeze/Blacklist Capability (20%), Compliance Infrastructure (20%), Geographic/Sanctions Restrictions (15%).

Tier cutoffs: Tier 1 > 0.75 (strict), Tier 2 >= 0.30, Tier 3 < 0.30.

## Version History

| Version | Changes |
|---------|---------|
| v24 | Pre-review draft |
| v25 | Hedged overclaims, fixed Johansen rank=3, added CLII no-freeze robustness, recalculated SVB weekend metrics with expanded registry |
| v41 | Full paper revision: 19 entities (51 addresses), multi-chain data, expanded econometrics |
| v42 | Supplement sync: fixed 3 stale CLII values, added Robinhood to Table B2, verified all 11 references resolve |
