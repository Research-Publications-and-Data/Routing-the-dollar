-- =============================================================================
-- EXHIBIT E: Aave DeFi Collateral Composition & Borrow Rates
-- =============================================================================
-- Purpose: Track dollar-denominated collateral share and funding conditions
-- Output:  Daily collateral breakdown + stablecoin borrow rates
-- Window:  2023-02-01 to 2026-01-31
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PART 1: COLLATERAL COMPOSITION (Aave V2 + V3 Ethereum)
-- -----------------------------------------------------------------------------

WITH stablecoin_tokens AS (
    SELECT * FROM (VALUES
        (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 'USDC', 6, 'stablecoin'),
        (0xdAC17F958D2ee523a2206206994597C13D831ec7, 'USDT', 6, 'stablecoin'),
        (0x6B175474E89094C44Da98b954EescdeCB5BE3380, 'DAI', 18, 'stablecoin'),
        (0x853d955aCEf822Db058eb8505911ED77F175b99e, 'FRAX', 18, 'stablecoin')
    ) AS t(contract_address, symbol, decimals, asset_type)
),

-- Tokenized treasury products (add as they become Aave-listed)
tokenized_treasury_tokens AS (
    SELECT * FROM (VALUES
        -- Ondo OUSG (if listed on Aave)
        (0x1B19C19393e2d034D8Ff31ff34c81252FcBbEE92, 'OUSG', 18, 'tokenized_treasury'),
        -- Add more as they get listed
        (0x0000000000000000000000000000000000000000, 'PLACEHOLDER', 18, 'tokenized_treasury')
    ) AS t(contract_address, symbol, decimals, asset_type)
    WHERE contract_address != 0x0000000000000000000000000000000000000000
),

-- Aave V3 daily reserve snapshots
-- Note: Use aave_v3_ethereum.Pool_evt_ReserveDataUpdated or similar
aave_v3_reserves AS (
    SELECT
        DATE_TRUNC('day', evt_block_time) AS date_utc,
        reserve AS asset_address,
        -- Get latest values per day
        LAST_VALUE(liquidityIndex) OVER (
            PARTITION BY DATE_TRUNC('day', evt_block_time), reserve 
            ORDER BY evt_block_time
        ) AS liquidity_index,
        LAST_VALUE(variableBorrowIndex) OVER (
            PARTITION BY DATE_TRUNC('day', evt_block_time), reserve 
            ORDER BY evt_block_time
        ) AS variable_borrow_index
    FROM aave_v3_ethereum.Pool_evt_ReserveDataUpdated
    WHERE evt_block_time >= TIMESTAMP '2023-02-01'
      AND evt_block_time < TIMESTAMP '2026-02-01'
),

-- Alternative: Use Aave subgraph data or pre-aggregated tables
-- This is a simplified approach using supply/borrow events
aave_daily_supply AS (
    SELECT
        DATE_TRUNC('day', evt_block_time) AS date_utc,
        reserve AS asset_address,
        SUM(CASE WHEN action = 'supply' THEN amount ELSE -amount END) AS net_supply_change
    FROM (
        -- Supplies
        SELECT evt_block_time, reserve, CAST(amount AS DOUBLE) AS amount, 'supply' AS action
        FROM aave_v3_ethereum.Pool_evt_Supply
        WHERE evt_block_time >= TIMESTAMP '2023-02-01'
          AND evt_block_time < TIMESTAMP '2026-02-01'
        
        UNION ALL
        
        -- Withdrawals
        SELECT evt_block_time, reserve, CAST(amount AS DOUBLE) AS amount, 'withdraw' AS action
        FROM aave_v3_ethereum.Pool_evt_Withdraw
        WHERE evt_block_time >= TIMESTAMP '2023-02-01'
          AND evt_block_time < TIMESTAMP '2026-02-01'
    ) combined
    GROUP BY 1, 2
),

-- Classify assets and compute daily totals
daily_collateral AS (
    SELECT
        s.date_utc,
        s.asset_address,
        COALESCE(st.symbol, tt.symbol, 'OTHER') AS asset_symbol,
        COALESCE(st.asset_type, tt.asset_type, 'other') AS asset_type,
        s.net_supply_change / POWER(10, COALESCE(st.decimals, tt.decimals, 18)) AS supply_tokens,
        -- Price in USD
        (s.net_supply_change / POWER(10, COALESCE(st.decimals, tt.decimals, 18))) 
            * COALESCE(p.price, 1.0) AS supply_usd
    FROM aave_daily_supply s
    LEFT JOIN stablecoin_tokens st ON s.asset_address = st.contract_address
    LEFT JOIN tokenized_treasury_tokens tt ON s.asset_address = tt.contract_address
    LEFT JOIN prices.usd_daily p ON p.contract_address = s.asset_address AND p.day = s.date_utc
),

-- Aggregate by asset type
daily_collateral_by_type AS (
    SELECT
        date_utc,
        asset_type,
        SUM(supply_usd) AS collateral_usd
    FROM daily_collateral
    GROUP BY 1, 2
),

-- Pivot to get columns
collateral_summary AS (
    SELECT
        date_utc,
        SUM(CASE WHEN asset_type = 'stablecoin' THEN collateral_usd ELSE 0 END) AS stablecoin_collateral_usd,
        SUM(CASE WHEN asset_type = 'tokenized_treasury' THEN collateral_usd ELSE 0 END) AS tokenized_treasury_collateral_usd,
        SUM(CASE WHEN asset_type = 'other' THEN collateral_usd ELSE 0 END) AS other_collateral_usd,
        SUM(collateral_usd) AS total_collateral_usd
    FROM daily_collateral_by_type
    GROUP BY 1
)

SELECT
    date_utc,
    stablecoin_collateral_usd,
    tokenized_treasury_collateral_usd,
    stablecoin_collateral_usd + tokenized_treasury_collateral_usd AS dollar_collateral_usd,
    other_collateral_usd,
    total_collateral_usd,
    (stablecoin_collateral_usd + tokenized_treasury_collateral_usd) 
        / NULLIF(total_collateral_usd, 0) AS dollar_collateral_share
FROM collateral_summary
ORDER BY date_utc;


-- -----------------------------------------------------------------------------
-- PART 2: STABLECOIN BORROW RATES (Separate Query)
-- -----------------------------------------------------------------------------
-- Query Aave interest rate data for USDC/USDT variable borrow APR

/*
SELECT
    DATE_TRUNC('day', evt_block_time) AS date_utc,
    reserve AS asset_address,
    CASE 
        WHEN reserve = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 THEN 'USDC'
        WHEN reserve = 0xdAC17F958D2ee523a2206206994597C13D831ec7 THEN 'USDT'
    END AS asset_symbol,
    -- Convert ray (1e27) to percentage
    AVG(CAST(variableBorrowRate AS DOUBLE) / 1e27 * 100) AS avg_variable_borrow_apr
FROM aave_v3_ethereum.Pool_evt_ReserveDataUpdated
WHERE reserve IN (
    0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48,  -- USDC
    0xdAC17F958D2ee523a2206206994597C13D831ec7   -- USDT
)
AND evt_block_time >= TIMESTAMP '2023-02-01'
AND evt_block_time < TIMESTAMP '2026-02-01'
GROUP BY 1, 2
ORDER BY 1, 2;
*/
