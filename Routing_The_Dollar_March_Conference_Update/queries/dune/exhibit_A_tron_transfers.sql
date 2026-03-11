-- =============================================================================
-- EXHIBIT A: US→Mexico Corridor - TRON USDT Transfers
-- =============================================================================
-- Purpose: Capture Tron-based USDT flows to Mexico gateways
-- Note:    Tron carries significant remittance volume
-- Window:  2023-02-01 to 2026-01-31
-- =============================================================================
-- IMPORTANT: This query requires Dune's Tron tables (tron.transactions or 
-- trc20_tron.evt_Transfer). Verify table names in your Dune environment.
-- =============================================================================

WITH tron_usdt AS (
    -- USDT TRC-20 contract on Tron: TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t
    SELECT
        DATE_TRUNC('day', block_time) AS date_utc,
        'USDT' AS token_symbol,
        'tron' AS chain,
        from_address AS sender,
        to_address AS recipient,
        tx_hash,
        CAST(value AS DOUBLE) / 1e6 AS amount_token  -- USDT has 6 decimals
    FROM trc20_tron.evt_Transfer  -- Verify table name
    WHERE contract_address = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
      AND block_time >= TIMESTAMP '2023-02-01'
      AND block_time < TIMESTAMP '2026-02-01'
      AND value > 0
),

-- Tron gateway addresses (base58 format)
-- Note: Convert to hex if needed for your Dune environment
tron_gateways AS (
    -- ===========================================
    -- BITSO TRON ADDRESSES (Tier 1)
    -- Verify via Tronscan / Dune labels
    -- ===========================================
    SELECT address, 'Bitso' as gateway_name, 'tier1_high_clii' as tier, 'A_strict' as proxy_variant
    FROM (VALUES
        ('TBitsoXXXXXXXXXXXXXXXXXXXXXXXXXXX')  -- Placeholder: replace with actual Bitso Tron addresses
    ) AS t(address)
    WHERE address != 'TBitsoXXXXXXXXXXXXXXXXXXXXXXXXXXX'  -- Filter out placeholder
    
    UNION ALL
    
    SELECT address, 'Bitso', 'tier1_high_clii', 'B_broader'
    FROM (VALUES
        ('TBitsoXXXXXXXXXXXXXXXXXXXXXXXXXXX')
    ) AS t(address)
    WHERE address != 'TBitsoXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    
    UNION ALL
    
    -- ===========================================
    -- BINANCE TRON (Tier 2, B_broader)
    -- ===========================================
    SELECT address, 'Binance', 'tier2_offshore_cefi', 'B_broader'
    FROM (VALUES
        ('TNXoiAJ3dct8Fjg4M9fkLFh9S2v9TXc32G'),  -- Binance Hot Wallet (Tron)
        ('TWd4WrZ9wn84f5x1hZhL4DHvk738ns5jwb'),  -- Binance (verify)
        ('TJDENsfBJs4RFETt1X1W8wMDc8M5XnSdGr')   -- Binance (verify)
    ) AS t(address)
    
    UNION ALL
    
    -- ===========================================
    -- OKX TRON (Tier 2, B_broader)
    -- ===========================================
    SELECT address, 'OKX', 'tier2_offshore_cefi', 'B_broader'
    FROM (VALUES
        ('TQrY8tryqsYVCYS3MFbtffiPp2ccyn4STm'),  -- OKX (verify)
        ('TAzsQ9Gx8eqFNFSKbeXrbi45CuVPHzA8wr')   -- OKX 2 (verify)
    ) AS t(address)
),

-- Join transfers with gateways
gateway_transfers AS (
    SELECT
        t.date_utc,
        t.token_symbol,
        t.chain,
        g.gateway_name,
        g.tier,
        g.proxy_variant,
        t.tx_hash,
        CASE 
            WHEN t.recipient = g.address THEN 'inflow'
            WHEN t.sender = g.address THEN 'outflow'
        END AS direction,
        t.amount_token AS amount_usd  -- USDT assumed at $1.00
    FROM tron_usdt t
    INNER JOIN tron_gateways g 
        ON t.sender = g.address OR t.recipient = g.address
    WHERE (t.recipient = g.address OR t.sender = g.address)
),

-- Aggregate daily
daily_aggregates AS (
    SELECT
        date_utc,
        token_symbol AS token,
        chain,
        gateway_name,
        tier,
        proxy_variant,
        direction,
        COUNT(*) AS tx_count,
        SUM(amount_usd) AS volume_usd,
        APPROX_PERCENTILE(amount_usd, 0.5) AS median_transfer_usd
    FROM gateway_transfers
    GROUP BY 1, 2, 3, 4, 5, 6, 7
)

SELECT *
FROM daily_aggregates
ORDER BY date_utc, proxy_variant, gateway_name, direction;
