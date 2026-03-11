# Nansen Data Licensing Notice

This replication package uses entity-level blockchain labels from [Nansen](https://www.nansen.ai/) under a commercial API license.

## What is included

- **Aggregated gateway-level statistics** in `data/processed/` (e.g., monthly counterparty counts, dyad-level flow summaries, network topology metrics). These are derived outputs permissible under the license.

## What is NOT included

- **Raw Nansen entity labels** (address → entity mappings) are not redistributable under the Nansen API Terms of Service.
- **Raw counterparty flow data** at the address level is not included.

## How to reproduce

1. Obtain a Nansen API key at https://www.nansen.ai/
2. Run `scripts/nansen_collector_v4.py` with your API key to collect raw entity labels
3. The pipeline scripts aggregate raw labels into the processed statistics used in the paper

## Specific paper claims backed by Nansen data

- 15 gateways, 35 months, 3,804 dyads (Section 4.3)
- Wintermute market-maker share: 1.4% → 19.9% (Table 5)
- Cross-gateway counterparty decline: 5.8% → 2.6% (Table 5)
- Network topology exhibits (Exhibits 14–16)

## Citation

Nansen. "Blockchain Analytics Platform." https://www.nansen.ai/. Accessed 2023–2026.
