-- Query E: Solana USDC+USDT daily volume
-- Save output as: data/raw/dune_solana_volume.csv
-- Uses tokens_solana.transfers (Dune curated table, not solana.token_transfers)
SELECT date_trunc('day', block_time) AS day,
    CASE WHEN token_mint_address = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' THEN 'USDC'
         WHEN token_mint_address = 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB' THEN 'USDT' END AS token,
    COUNT(*) AS n_transfers, SUM(amount_display) AS volume_usd
FROM tokens_solana.transfers
WHERE token_mint_address IN ('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB')
AND block_time >= TIMESTAMP '2023-02-01'
GROUP BY 1, 2 ORDER BY 1
