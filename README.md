# Routing the Dollar

**Gateway Infrastructure, Monetary Policy Transmission, and the Dollar's International Functions in Digital Markets**

Zach Zukowski, [Tokeneconomics](https://tokeneconomics.substack.com)

Prepared for the [Fifth Conference on the International Roles of the U.S. Dollar](https://www.newyorkfed.org/research/conference/2026/international-roles-us-dollar), Board of Governors of the Federal Reserve System and Federal Reserve Bank of New York, June 2026.

---

## Paper (March 2026)

- [Conference paper (PDF)](paper/Routing_the_Dollar_March_Conference_Update.pdf)
- [Conference paper (DOCX)](paper/Routing_the_Dollar_March_Conference_Update.docx)
- [Online supplement (DOCX)](paper/Routing_the_Dollar_Supplement_March_Conference_Update.docx)

## Replication Package

Code, queries, data, and reproduction instructions are in [`Routing_The_Dollar_March_Conference_Update/`](Routing_The_Dollar_March_Conference_Update/).

Data covers four chains (Ethereum, Tron, Solana, Base), 19 gateway entities (51 addresses), February 2023 through January 2026. Sources: FRED, Dune Analytics, DefiLlama, CoinGecko, Artemis, Nansen, NY Fed.

## Abstract

The dollar's international functions -- as a medium of exchange, store of value, and funding instrument -- now operate partly through stablecoin infrastructure the Federal Reserve does not monitor. We argue that the policy-relevant unit of analysis is not the stablecoin token but the *gateway*: the institutional infrastructure through which stablecoin value is routed. The same dollar token produces opposite regulatory, monetary, and safe-haven outcomes depending primarily on which gateway processes it.

Three empirical findings support this argument using daily gateway transfer data for 19 Ethereum entities, monthly counterparty network panels across 15 gateways (35 months, 110,000 counterparty relationships), and stress-episode windows for the SVB crisis and BUSD regulatory action.

1. Stablecoin supply is cointegrated with Fed balance sheet variables, with the yield spread between Treasury bills and on-chain lending rates consistent with the hypothesized transmission mechanism -- a relationship that is dollar-specific, absent for Bitcoin or Ethereum, and strongest during active monetary tightening.

2. The long-run equilibrium distributes unevenly across the gateway layer: institutional gateways (both regulated and offshore) trend with Fed assets while permissionless protocols trend in the opposite direction, and the routing infrastructure is hollowing out -- volume doubled over three years while unique counterparties declined 25 percent and cross-gateway bridges halved.

3. The dollar's safe-haven function in tokenized markets is gateway-contingent, not currency-inherent: stress events route capital across gateways rather than across currencies, with the FDIC's deposit guarantee (designed for bank depositors) serving as the instrument that stabilized stablecoin routing infrastructure.

## Citation

> Zukowski, Zach. 2026. "Routing the Dollar: Gateway Infrastructure, Monetary Policy Transmission, and the Dollar's International Functions in Digital Markets." Working paper, Tokeneconomics.

## License

Paper and text: All rights reserved.
Code and queries: [MIT License](Routing_The_Dollar_March_Conference_Update/LICENSE).
Data: See [`MANIFEST.md`](Routing_The_Dollar_March_Conference_Update/MANIFEST.md) for source-specific terms.
