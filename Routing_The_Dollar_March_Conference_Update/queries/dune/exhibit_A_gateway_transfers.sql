-- DUNE TEMPLATE: Exhibit A — USDC/USDT transfers touching Mexico gateway clusters (Ethereum)
-- Export as: data/raw/dune/gateway_transfers.csv
-- Required columns: date_utc, token, chain, gateway_name, corridor_proxy_variant, direction, amount_usd, tx_hash

WITH tokens AS (
  SELECT * FROM (VALUES
    ('USDC', LOWER('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'), 6),
    ('USDT', LOWER('0xdAC17F958D2ee523a2206206994597C13D831ec7'), 6)
  ) AS t(token, contract_address, decimals)
),
gateways AS (
  -- TODO: Replace with Dune labels or your maintained address lists
  SELECT LOWER(address) AS address, 'Bitso' AS gateway_name, 'A_strict' AS corridor_proxy_variant
  FROM UNNEST(ARRAY[
    -- TODO: Bitso addresses
  ]) AS x(address)
  UNION ALL
  SELECT LOWER(address), 'Bitso', 'B_broader'
  FROM UNNEST(ARRAY[
    -- TODO: Bitso + broader gateways
  ]) AS x(address)
),
xfer AS (
  SELECT
    date_trunc('day', evt_block_time) AS date_utc,
    t.token,
    'ethereum' AS chain,
    LOWER("from") AS sender,
    LOWER("to") AS recipient,
    tx_hash,
    (value / POWER(10, t.decimals)) AS amount_token
  FROM erc20_ethereum.evt_Transfer tr
  JOIN tokens t ON LOWER(tr.contract_address)=t.contract_address
  WHERE evt_block_time >= TIMESTAMP '2023-02-01'
    AND evt_block_time <  TIMESTAMP '2026-02-01'
),
priced AS (
  SELECT
    x.date_utc, x.token, x.chain, g.gateway_name, g.corridor_proxy_variant,
    CASE WHEN x.recipient=g.address THEN 'in' WHEN x.sender=g.address THEN 'out' END AS direction,
    x.tx_hash,
    x.amount_token * COALESCE(p.price, 1) AS amount_usd
  FROM xfer x
  JOIN gateways g ON x.sender=g.address OR x.recipient=g.address
  LEFT JOIN prices.usd p
    ON p.contract_address = CASE WHEN x.token='USDC'
                                 THEN LOWER('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')
                                 ELSE LOWER('0xdAC17F958D2ee523a2206206994597C13D831ec7') END
   AND p.minute = x.date_utc
)
SELECT date_utc, token, chain, gateway_name, corridor_proxy_variant, direction, amount_usd, tx_hash
FROM priced
WHERE direction IS NOT NULL;
