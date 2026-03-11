-- Query D: Tron USDT daily volume
-- Save output as: data/raw/dune_tron_volume.csv
-- Uses tokens_tron.transfers (Dune curated table, not tron.trc20_transfers)
SELECT date_trunc('day', block_time) AS day, COUNT(*) AS n_transfers,
    SUM(amount) AS volume_usd
FROM tokens_tron.transfers
WHERE contract_address_varchar = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
AND block_time >= TIMESTAMP '2023-02-01'
GROUP BY 1 ORDER BY 1
