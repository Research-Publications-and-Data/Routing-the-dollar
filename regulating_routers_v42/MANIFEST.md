# Data Manifest -- Routing the Dollar Replication Package

## Public data (fully reproducible)

| Source | Series | Frequency | Access |
|--------|--------|-----------|--------|
| FRED | Fed total assets (WALCL), ON RRP (RRPONTSYD), T-bill (DTB3), SOFR, DFF, 10Y, deposits | Daily/Weekly | Public API, no key required |
| DefiLlama | Stablecoin supply, Aave V3 USDC rate, Compound V3 USDC rate | Daily | Public API |
| Dune Analytics | Gateway transfer volumes, address labels | Daily | Community plan (queries in `queries/dune/`) |
| Artemis | Use-case decomposition, Solana/Tron categories | Aggregated | Via published report |
| CoinGecko | Exchange volume shares, depeg price data | Daily | Free tier or Pro |
| NY Fed | ON RRP counterparty data | Daily | Public API |

## Proprietary data (processed aggregates included)

| Source | Content | Included as |
|--------|---------|-------------|
| Nansen | Counterparty networks, entity attribution | Processed aggregates in `data/processed/` |
| Nansen | Raw address-level exports | NOT included (commercial license) |

See `data/raw/NANSEN_NOTICE.md` for licensing details.

## Regenerated outputs

All exhibits are regenerable from `scripts/` + `data/processed/`. Run `python scripts/verify_claims.py` to confirm numerical consistency. Run `python scripts/audit_replication_package.py` for structural checks.

## What is NOT reproducible from this package alone

- Nansen counterparty network raw data (requires subscription)
- Dune queries that exceed community plan limits (processed outputs included)
- Exhibit images use matplotlib with specific font/style settings; visual appearance may vary
