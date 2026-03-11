-- =============================================================================
-- EXHIBIT E: Tokenized Treasury / Safe Asset AUM Tracking
-- =============================================================================
-- Purpose: Track growth of on-chain tokenized Treasury products
-- Output:  Daily AUM for tokenized T-bills, MMFs, and similar products
-- Window:  2023-02-01 to 2026-01-31
-- =============================================================================
-- Note: This query aggregates supply of known tokenized treasury products.
-- Add new products as they launch (BlackRock BUIDL, Franklin Templeton, etc.)
-- =============================================================================

WITH tokenized_products AS (
    SELECT * FROM (VALUES
        -- Ondo Finance OUSG (Short-Term US Government Treasuries)
        (0x1B19C19393e2d034D8Ff31ff34c81252FcBbEE92, 'OUSG', 'Ondo Finance', 18, 'tokenized_tbill'),
        
        -- Ondo USDY (Tokenized Note secured by US Treasuries)
        (0x96F6eF951840721AdBF46Ac996b59E0235CB985C, 'USDY', 'Ondo Finance', 18, 'tokenized_note'),
        
        -- Mountain Protocol USDM (Yield-bearing stablecoin backed by T-bills)
        (0x59D9356E565Ab3A36dD77763Fc0d87fEaf85508C, 'USDM', 'Mountain Protocol', 18, 'yield_stablecoin'),
        
        -- Backed Finance bIB01 (Tokenized iShares Treasury Bond ETF)
        (0xCA30c93B02514f86d5C86a6e375E3A330B435Fb5, 'bIB01', 'Backed Finance', 18, 'tokenized_etf'),
        
        -- Maple Finance USDC Pool Token (if Treasury-backed)
        -- Add more products as they emerge
        
        -- BlackRock BUIDL (when available on Ethereum)
        -- Franklin Templeton BENJI (when available)
        
        -- Placeholder for future products
        (0x0000000000000000000000000000000000000000, 'PLACEHOLDER', 'Future', 18, 'future')
    ) AS t(contract_address, symbol, issuer, decimals, product_type)
    WHERE contract_address != 0x0000000000000000000000000000000000000000
),

-- Get daily total supply for each product
-- Using Transfer events to track mints/burns
daily_supply_changes AS (
    SELECT
        DATE_TRUNC('day', evt_block_time) AS date_utc,
        contract_address,
        SUM(
            CASE 
                WHEN "from" = 0x0000000000000000000000000000000000000000 THEN CAST(value AS DOUBLE)  -- Mint
                WHEN "to" = 0x0000000000000000000000000000000000000000 THEN -CAST(value AS DOUBLE)  -- Burn
                ELSE 0
            END
        ) AS net_supply_change
    FROM erc20_ethereum.evt_Transfer
    WHERE contract_address IN (SELECT contract_address FROM tokenized_products)
      AND evt_block_time >= TIMESTAMP '2023-02-01'
      AND evt_block_time < TIMESTAMP '2026-02-01'
      AND ("from" = 0x0000000000000000000000000000000000000000 
           OR "to" = 0x0000000000000000000000000000000000000000)
    GROUP BY 1, 2
),

-- Calculate cumulative supply
cumulative_supply AS (
    SELECT
        date_utc,
        contract_address,
        SUM(net_supply_change) OVER (
            PARTITION BY contract_address 
            ORDER BY date_utc
        ) AS total_supply_raw
    FROM daily_supply_changes
),

-- Join with product metadata and convert to USD
daily_aum AS (
    SELECT
        c.date_utc,
        p.symbol,
        p.issuer,
        p.product_type,
        c.total_supply_raw / POWER(10, p.decimals) AS total_supply_tokens,
        -- For T-bill tokens, NAV ≈ $1 per token (with small accrual)
        -- Use price feed if available, otherwise assume $1
        (c.total_supply_raw / POWER(10, p.decimals)) 
            * COALESCE(pr.price, 1.0) AS aum_usd
    FROM cumulative_supply c
    INNER JOIN tokenized_products p ON c.contract_address = p.contract_address
    LEFT JOIN prices.usd_daily pr 
        ON pr.contract_address = c.contract_address 
        AND pr.day = c.date_utc
),

-- Aggregate by product type
daily_aum_by_type AS (
    SELECT
        date_utc,
        product_type,
        SUM(aum_usd) AS aum_usd
    FROM daily_aum
    GROUP BY 1, 2
),

-- Create complete date spine
date_spine AS (
    SELECT date_utc
    FROM UNNEST(SEQUENCE(
        DATE '2023-02-01',
        DATE '2026-01-31',
        INTERVAL '1' DAY
    )) AS t(date_utc)
),

-- Final aggregation with date spine
final_aum AS (
    SELECT
        d.date_utc,
        COALESCE(SUM(CASE WHEN a.product_type = 'tokenized_tbill' THEN a.aum_usd END), 0) AS tokenized_tbill_aum_usd,
        COALESCE(SUM(CASE WHEN a.product_type = 'tokenized_note' THEN a.aum_usd END), 0) AS tokenized_note_aum_usd,
        COALESCE(SUM(CASE WHEN a.product_type = 'yield_stablecoin' THEN a.aum_usd END), 0) AS yield_stablecoin_aum_usd,
        COALESCE(SUM(CASE WHEN a.product_type = 'tokenized_etf' THEN a.aum_usd END), 0) AS tokenized_etf_aum_usd,
        COALESCE(SUM(a.aum_usd), 0) AS total_tokenized_safe_asset_aum_usd
    FROM date_spine d
    LEFT JOIN daily_aum_by_type a ON d.date_utc = a.date_utc
    GROUP BY 1
)

SELECT
    date_utc,
    tokenized_tbill_aum_usd,
    tokenized_note_aum_usd,
    yield_stablecoin_aum_usd,
    tokenized_etf_aum_usd,
    total_tokenized_safe_asset_aum_usd,
    -- Forward fill for days with no activity
    COALESCE(
        total_tokenized_safe_asset_aum_usd,
        LAST_VALUE(total_tokenized_safe_asset_aum_usd IGNORE NULLS) OVER (
            ORDER BY date_utc
        )
    ) AS total_aum_ffill
FROM final_aum
ORDER BY date_utc;
