
SELECT DISTINCT
    address, name, label_type
FROM labels.addresses
WHERE name ILIKE ANY(ARRAY[
    '%circle%', '%coinbase%', '%binance%',
    '%tether%', '%kraken%', '%okx%',
    '%gemini%', '%paxos%', '%bybit%',
    '%paypal%', '%bitgo%', '%robinhood%',
    '%htx%', '%huobi%', '%mexc%'
])
AND label_type IN ('exchange', 'fund', 'institution', 'contract')
AND blockchain = 'ethereum'
ORDER BY name
