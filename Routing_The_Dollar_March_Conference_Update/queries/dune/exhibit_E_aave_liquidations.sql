-- DUNE TEMPLATE: Exhibit E — Aave liquidations (daily USD; Ethereum v2 example)
-- Export as: data/raw/dune/aave_liquidations.csv (date_utc, liquidations_usd)

WITH liq AS (
  SELECT
    date_trunc('day', evt_block_time) AS date_utc,
    collateralAsset AS collateral_asset,
    liquidatedCollateralAmount AS collateral_amount_raw
  FROM aave_v2_ethereum.LendingPool_evt_LiquidationCall
  WHERE evt_block_time >= TIMESTAMP '2023-02-01'
    AND evt_block_time <  TIMESTAMP '2026-02-01'
),
liq_usd AS (
  SELECT
    date_utc,
    SUM( (collateral_amount_raw / POWER(10, COALESCE(t.decimals,18))) * COALESCE(p.price,0) ) AS liquidations_usd
  FROM liq
  LEFT JOIN tokens.erc20 t ON LOWER(t.contract_address)=LOWER(liq.collateral_asset)
  LEFT JOIN prices.usd p ON p.contract_address=LOWER(liq.collateral_asset) AND p.minute=date_utc
  GROUP BY 1
)
SELECT * FROM liq_usd ORDER BY date_utc;
