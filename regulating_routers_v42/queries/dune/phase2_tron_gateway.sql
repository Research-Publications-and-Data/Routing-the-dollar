
SELECT
    date_trunc('day', block_time) AS day,
    COALESCE(
        CASE WHEN "from" = 'TKHuVq1oKVruCGLvqVexFs6dawKv6fQgFs' THEN 'Tether'
        WHEN "from" = 'TNXoiAJ3dct8Fjg4M9fkLFh9S2v9TXc32G' THEN 'Tether'
        WHEN "from" = 'TJDENsfBJs4RFETt1X1W8wMDc8M5XnKhCF' THEN 'Binance'
        WHEN "from" = 'TV6MuMXfmLbBqPZvBHdwFsDnQeVfnmiuEM' THEN 'Binance'
        WHEN "from" = 'TJN6WeqBjghRHCeiE3jnb7TSAB3Rmcoy7o' THEN 'OKX'
        WHEN "from" = 'TRD5yAQVd5DRSBGTsBjqzMtW777ZZsjHJk' THEN 'HTX'
        WHEN "from" = 'TLPh66vQ2QMb64rG3WEBV5qnAhefh2kcdw' THEN 'Bybit'
        WHEN "from" = 'TBAo7PNyKo94YWUq1Cs2LBFxkhTgUmLzvR' THEN 'Kraken'
        WHEN "from" = 'TKcEU8ekq2ZoFzLSGFYCUY6aocePBpCsRS' THEN 'SunSwap'
        WHEN "from" = 'TX7kybeP6UwTBRHLNPYmswFESHfyjm9bAS' THEN 'JustLend' ELSE NULL END,
        CASE WHEN "to" = 'TKHuVq1oKVruCGLvqVexFs6dawKv6fQgFs' THEN 'Tether'
        WHEN "to" = 'TNXoiAJ3dct8Fjg4M9fkLFh9S2v9TXc32G' THEN 'Tether'
        WHEN "to" = 'TJDENsfBJs4RFETt1X1W8wMDc8M5XnKhCF' THEN 'Binance'
        WHEN "to" = 'TV6MuMXfmLbBqPZvBHdwFsDnQeVfnmiuEM' THEN 'Binance'
        WHEN "to" = 'TJN6WeqBjghRHCeiE3jnb7TSAB3Rmcoy7o' THEN 'OKX'
        WHEN "to" = 'TRD5yAQVd5DRSBGTsBjqzMtW777ZZsjHJk' THEN 'HTX'
        WHEN "to" = 'TLPh66vQ2QMb64rG3WEBV5qnAhefh2kcdw' THEN 'Bybit'
        WHEN "to" = 'TBAo7PNyKo94YWUq1Cs2LBFxkhTgUmLzvR' THEN 'Kraken'
        WHEN "to" = 'TKcEU8ekq2ZoFzLSGFYCUY6aocePBpCsRS' THEN 'SunSwap'
        WHEN "to" = 'TX7kybeP6UwTBRHLNPYmswFESHfyjm9bAS' THEN 'JustLend' ELSE NULL END
    ) AS entity,
    CASE COALESCE(
        CASE WHEN "from" = 'TKHuVq1oKVruCGLvqVexFs6dawKv6fQgFs' THEN 'Tether'
        WHEN "from" = 'TNXoiAJ3dct8Fjg4M9fkLFh9S2v9TXc32G' THEN 'Tether'
        WHEN "from" = 'TJDENsfBJs4RFETt1X1W8wMDc8M5XnKhCF' THEN 'Binance'
        WHEN "from" = 'TV6MuMXfmLbBqPZvBHdwFsDnQeVfnmiuEM' THEN 'Binance'
        WHEN "from" = 'TJN6WeqBjghRHCeiE3jnb7TSAB3Rmcoy7o' THEN 'OKX'
        WHEN "from" = 'TRD5yAQVd5DRSBGTsBjqzMtW777ZZsjHJk' THEN 'HTX'
        WHEN "from" = 'TLPh66vQ2QMb64rG3WEBV5qnAhefh2kcdw' THEN 'Bybit'
        WHEN "from" = 'TBAo7PNyKo94YWUq1Cs2LBFxkhTgUmLzvR' THEN 'Kraken'
        WHEN "from" = 'TKcEU8ekq2ZoFzLSGFYCUY6aocePBpCsRS' THEN 'SunSwap'
        WHEN "from" = 'TX7kybeP6UwTBRHLNPYmswFESHfyjm9bAS' THEN 'JustLend' ELSE NULL END,
        CASE WHEN "to" = 'TKHuVq1oKVruCGLvqVexFs6dawKv6fQgFs' THEN 'Tether'
        WHEN "to" = 'TNXoiAJ3dct8Fjg4M9fkLFh9S2v9TXc32G' THEN 'Tether'
        WHEN "to" = 'TJDENsfBJs4RFETt1X1W8wMDc8M5XnKhCF' THEN 'Binance'
        WHEN "to" = 'TV6MuMXfmLbBqPZvBHdwFsDnQeVfnmiuEM' THEN 'Binance'
        WHEN "to" = 'TJN6WeqBjghRHCeiE3jnb7TSAB3Rmcoy7o' THEN 'OKX'
        WHEN "to" = 'TRD5yAQVd5DRSBGTsBjqzMtW777ZZsjHJk' THEN 'HTX'
        WHEN "to" = 'TLPh66vQ2QMb64rG3WEBV5qnAhefh2kcdw' THEN 'Bybit'
        WHEN "to" = 'TBAo7PNyKo94YWUq1Cs2LBFxkhTgUmLzvR' THEN 'Kraken'
        WHEN "to" = 'TKcEU8ekq2ZoFzLSGFYCUY6aocePBpCsRS' THEN 'SunSwap'
        WHEN "to" = 'TX7kybeP6UwTBRHLNPYmswFESHfyjm9bAS' THEN 'JustLend' ELSE NULL END
    )
        WHEN 'Tether' THEN 2
        WHEN 'Tether' THEN 2
        WHEN 'Binance' THEN 2
        WHEN 'Binance' THEN 2
        WHEN 'OKX' THEN 2
        WHEN 'HTX' THEN 2
        WHEN 'Bybit' THEN 2
        WHEN 'Kraken' THEN 2
        WHEN 'SunSwap' THEN 3
        WHEN 'JustLend' THEN 3
    END AS tier,
    COUNT(*) AS n_transfers,
    SUM(amount) AS volume_usd
FROM tokens_tron.transfers
WHERE contract_address_varchar = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
AND block_time >= TIMESTAMP '2023-02-01'
AND ("from" IN ('TKHuVq1oKVruCGLvqVexFs6dawKv6fQgFs', 'TNXoiAJ3dct8Fjg4M9fkLFh9S2v9TXc32G', 'TJDENsfBJs4RFETt1X1W8wMDc8M5XnKhCF', 'TV6MuMXfmLbBqPZvBHdwFsDnQeVfnmiuEM', 'TJN6WeqBjghRHCeiE3jnb7TSAB3Rmcoy7o', 'TRD5yAQVd5DRSBGTsBjqzMtW777ZZsjHJk', 'TLPh66vQ2QMb64rG3WEBV5qnAhefh2kcdw', 'TBAo7PNyKo94YWUq1Cs2LBFxkhTgUmLzvR', 'TKcEU8ekq2ZoFzLSGFYCUY6aocePBpCsRS', 'TX7kybeP6UwTBRHLNPYmswFESHfyjm9bAS') OR "to" IN ('TKHuVq1oKVruCGLvqVexFs6dawKv6fQgFs', 'TNXoiAJ3dct8Fjg4M9fkLFh9S2v9TXc32G', 'TJDENsfBJs4RFETt1X1W8wMDc8M5XnKhCF', 'TV6MuMXfmLbBqPZvBHdwFsDnQeVfnmiuEM', 'TJN6WeqBjghRHCeiE3jnb7TSAB3Rmcoy7o', 'TRD5yAQVd5DRSBGTsBjqzMtW777ZZsjHJk', 'TLPh66vQ2QMb64rG3WEBV5qnAhefh2kcdw', 'TBAo7PNyKo94YWUq1Cs2LBFxkhTgUmLzvR', 'TKcEU8ekq2ZoFzLSGFYCUY6aocePBpCsRS', 'TX7kybeP6UwTBRHLNPYmswFESHfyjm9bAS'))
GROUP BY 1, 2, 3
ORDER BY 1
