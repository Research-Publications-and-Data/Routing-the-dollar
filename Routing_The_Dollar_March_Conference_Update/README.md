# Routing the Dollar -- Replication Package

**Paper:** Routing the Dollar: Gateway Infrastructure, Monetary Policy Transmission, and the Dollar's International Functions in Digital Markets

**Author:** Zach Zukowski, Tokeneconomics

**Venue:** Fifth Conference on the International Roles of the U.S. Dollar, Board of Governors of the Federal Reserve System and Federal Reserve Bank of New York, June 2026

**Version:** v42 (conference release, March 2026)

## Repository Structure

```
Routing_The_Dollar_March_Conference_Update/
├── Routing_the_Dollar_March_Conference_Update.docx    # Conference paper (DOCX)
├── Routing_the_Dollar_March_Conference_Update.pdf     # Conference paper (PDF)
├── Routing_the_Dollar_Supplement_March_Conference_Update.docx   # Online supplement
├── paper_v25.md                            # Markdown source (supplement builder input)
├── config/
│   └── settings.py                         # API keys, gateway registry, chart style
├── scripts/                                # Numbered Python pipeline (70+ scripts)
├── queries/
│   └── dune/                               # 29 Dune Analytics SQL queries
├── data/
│   ├── raw/                                # Source data (FRED, Dune, Artemis, CoinGecko, DefiLlama)
│   ├── processed/                          # Computed intermediates backing paper claims
│   └── exhibits/                           # Generated chart PNGs and PDFs
├── media/                                  # 74 exhibit PNGs embedded in paper/supplement
├── MANIFEST.md                             # Data provenance and licensing
├── CHANGELOG_v25_to_v42.md                 # What changed from v25
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
| `data/raw/dune_eth_daily_expanded_v2.csv` | Daily USDC+USDT gateway volumes, 51 addresses, 19 entities, Feb 2023 -- Jan 2026 |
| `data/raw/dune_eth_expanded_gateway_v2.csv` | Monthly gateway volumes by entity and token |
| `data/raw/fred_all_series.csv` | 10 FRED series: Fed assets, ON RRP, SOFR, DFF, DGS10, deposits |
| `data/raw/stablecoin_supply_extended.csv` | Daily stablecoin market caps (2019 -- 2026) |
| `data/processed/unified_extended_dataset.csv` | Merged FRED + stablecoin supply (weekly) |
| `data/processed/gateway_volume_summary_v2.csv` | Aggregate gateway statistics (Table 2 source) |
| `data/processed/vecm_reconciliation.json` | VECM coefficients and Johansen test results |
| `data/processed/fomc_events.csv` | FOMC event study: supply changes at t+1, 3, 5, 10 |
| `data/processed/placebo_swing_stats.csv` | SVB placebo test (50 windows) |
| `data/processed/quadrivariate_robustness.csv` | Johansen trace stats for baseline, +DTWEXBGS, +VIX |

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

## Nansen Data

Raw Nansen entity labels are not redistributable. See `data/raw/NANSEN_NOTICE.md` for details. The collection script (`scripts/nansen_collector_v4.py`) documents the methodology.

## CLII Scores

The Compliance-Linked Infrastructure Index (CLII) scores use v42 DOCX Table 2a as the single source of truth. The 5-dimension architecture is: License (25%), Reserve Transparency (20%), Freeze/Blacklist Capability (20%), Compliance Infrastructure (20%), Geographic/Sanctions Restrictions (15%).

Tier cutoffs: Tier 1 > 0.75, Tier 2 >= 0.30, Tier 3 < 0.30.

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v24 | Feb 2026 | Pre-review draft |
| v25 | Feb 2026 | Hedged overclaims, fixed Johansen rank=3, added CLII no-freeze robustness, recalculated SVB weekend metrics with expanded registry |
| v41 | Mar 2026 | Full paper revision: 19 entities (51 addresses), multi-chain data, expanded econometrics |
| v42 | Mar 2026 | Supplement sync, exhibit renumbering, sign-error fixes, conference submission |

See `CHANGELOG_v25_to_v42.md` for a complete list of changes from v25.
