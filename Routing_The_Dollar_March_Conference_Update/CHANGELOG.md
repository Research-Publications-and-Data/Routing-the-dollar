# CHANGELOG: Gateway Registry and Paper Revisions

## Gateway Registry

- Expanded from 12 addresses / 12 entities to 51 addresses / 19 entities
- Added: PayPal (Tier 1, CLII 0.88), BitGo (Tier 1, CLII 0.80), Robinhood (Tier 2, CLII 0.75), Bybit (Tier 2, CLII 0.40), Uniswap Universal Router (Tier 3, CLII 0.15), 1inch (Tier 3, CLII 0.18), Compound V3 (Tier 3, CLII 0.18)
- Replaced Tornado Cash primary address with 1inch AggregationRouterV5 in final analysis (OFAC sanctions predate sample)
- Multi-address mapping: Coinbase (8 addresses), Binance (7), Kraken (4), etc.

## Econometrics

- Johansen cointegration confirmed at rank = 1 (trace = 30.68, cv95 = 29.80)
- Fixed stale Johansen rank = 3 claim from v24 (was an AIC-selected lag issue)
- Added VECM weak exogeneity tests: rejected for all three variables
- Added yield spread mechanism: T-bill vs. Aave V3 USDC rate (Granger F = 11.30, p = 0.001)
- Added placebo tests: 0 of 5 lag specifications significant for Bitcoin or Ethereum
- Added cross-stablecoin cointegration (USDT vs USDC vs DAI)
- Added FEVD decomposition
- Added bootstrap IRF confidence intervals (1,000 replications)

## Multi-Chain

- Added Tron analysis: 27.9% of global volume, zero Tier 1 presence
- Added Solana analysis: USDC-dominant, exchange-heavy routing
- Added Base analysis: Coinbase dominance in L2 gateway
- 4-chain coverage: Ethereum, Tron, Solana, Base

## CLII

- 5-dimension architecture: License (25%), Reserve Transparency (20%), Freeze/Blacklist (20%), Compliance Infrastructure (20%), Geographic/Sanctions (15%)
- No-freeze robustness: zero tier changes when freeze dimension removed
- PCA validation: first principal component explains 68% of variance
- Continuous CLII robustness: results hold with continuous scores (no tier cutoffs)

## SVB Analysis

- Recalculated with expanded 19-entity registry
- Weekend-adjusted metrics (SVB crisis spanned a weekend)
- Added placebo analysis: 50 random windows, SVB response 4.2 sigma outlier

## Data Quality

- Internal transfer detection: Binance 18.3% internal (adjusted in net metrics)
- Selection bias analysis: top-500 unlabeled addresses, size distribution checks
- Jackknife LOO stability: all 19 entities individually removable without sign change

## Paper Text

- Title updated: "Routing the Dollar: Gateway Infrastructure, Monetary Policy Transmission, and the Dollar's International Functions in Digital Markets"
- Abstract rewritten to reflect three-contribution structure
- Section IV.A compressed to focus on yield-spread mechanism
- Hedged overclaims throughout (Johansen rank, coverage framing, causal language)
- Added Appendix J: eurodollar analogy development
- 32 exhibit caption edits for accuracy
- 27 exhibit images replaced with v2 versions
