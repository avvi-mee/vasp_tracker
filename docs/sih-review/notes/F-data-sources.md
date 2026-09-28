# F: Data sources for VASP-Trace (research status)

_Date: 2026-09-27 · Status: **blocked, nothing verified**_
_Notes file: D:\VASP-Trace\docs\sih-review\notes\F-data-sources.md (same content as the hand-back report)_

## What happened
- Claude Code's auto-mode safety check refused my first four WebFetch calls: Tronscan docs, TronGrid docs, Etherscan rate-limits and Etherscan supported-chains. The message said: "Auto mode could not evaluate this action… a safety check separate from auto mode blocked this request because of earlier conversation content… it will keep firing for the rest of this conversation."
- The block applies to the whole session and has nothing to do with these URLs. It also says not to rework the action to get around it, so I did not try curl, the browser tool or any other workaround. WebSearch was already off-limits.
- Result: no facts verified. All 4 fetches I tried were refused, so none of the ~40-fetch budget went to real research. I could not fill any of the requested tables without breaking the "quote and link" rule, so I did not fill them from memory.

## How to unblock
Re-run this brief in a fresh session, or outside auto mode (default permission mode) so WebFetch calls can be approved. The resume plan below puts the Tron-first answers at the front in case the budget runs short.

## Explorer APIs by chain
Not verified (blocked). Every provider in question 1 is on the Could not verify list.

## Labelled datasets
Not verified (blocked).

## Sanctions & stablecoin blacklists
Not verified (blocked).

## Prices
Not verified (blocked).

## Could not verify
Everything in questions 1 to 4:
1. Explorer APIs: Blockstream Esplora, mempool.space, Blockchair, BlockCypher, WalletExplorer; Etherscan V2 (including any July 2026 change to max records per call), Blockscout, Alchemy, Moralis, Covalent/GoldRush, Ankr, publicnode; NodeReal MegaNode (including whether nr_getAssetTransfers covers BEP-20 in both directions); TronGrid, Tronscan; Helius, Solana public RPC, Solscan; Bitquery, Dune, Arkham.
2. Labelled datasets: GraphSense TagPacks, the Dune Spellbook CEX models and their licence, dawsbot/eth-labels, brianleect/etherscan-labels, Forta labelled-datasets, ScamSniffer, CryptoScamDB, Chainabuse, MistTrack, Elliptic/Elliptic++, DefiLlama bridges-server. Also the proof-of-reserves wallet lists for Binance, OKX, Bybit, KuCoin, CoinDCX, ZebPay, WazirX and Mudrex.
3. Sanctions: OFAC SDN address fields and downloads, the 0xB10C list, how access works for the Chainalysis oracle and Screening API, USDT (AddedBlackList / isBlackListed) and USDC (Blacklisted) checked against the verified contract source, free ways to query those on Tron and Ethereum, the UN/EU/UK lists, and any Indian list.
4. Prices: CoinGecko Demo vs keyless limits; a free source of historical INR prices.

## Resume plan (fetch order for the next session)
Seeds come from the brief. URLs marked (candidate) are my guesses at the right page and may have moved.
1. Tron: https://docs.tronscan.org/ then https://developers.tron.network/docs/trongrid
2. EVM: https://docs.etherscan.io/resources/rate-limits then https://docs.etherscan.io/supported-chains
3. BNB: https://nodereal.io/pricing then https://docs.nodereal.io/reference/nr_getassettransfers
4. Bitcoin: https://github.com/Blockstream/esplora/blob/master/API.md, then https://mempool.space/docs/api/rest (Angular page, may come back empty), then https://blockchair.com/api/plans
5. Prices: https://www.coingecko.com/en/api/pricing then https://docs.coingecko.com/docs/common-errors-rate-limit (candidate)
6. Sanctions: https://github.com/0xB10C/ofac-sanctioned-digital-currency-addresses, https://go.chainalysis.com/chainalysis-oracle-docs.html, https://etherscan.io/address/0xdac17f958d2ee523a2206206994597c13d831ec7#code (may block bots), https://github.com/circlefin/stablecoin-evm (candidate, USDC blacklist source), https://ofac.treasury.gov/
7. Labels: GraphSense TagPacks, Spellbook (find the cex addresses models and the LICENSE), eth-labels, etherscan-labels, Forta, ScamSniffer, Elliptic++, DefiLlama bridges-server
8. Proof of reserves: Binance and OKX first (both pages are JS-heavy, so look for downloadable address files), then Bybit, KuCoin and the Indian exchanges
9. Everything else: Helius pricing, https://solana.com/docs/references/clusters (candidate), Solscan, Blockscout, Alchemy, Dune, Moralis, GoldRush, Ankr, Bitquery, Arkham, BlockCypher, WalletExplorer, Chainabuse, MistTrack, CryptoScamDB, UN/EU/UK lists

## Implications for the team's tool
These rest only on the team's own observations from the brief. I researched nothing new.
- Bitcoin: from the team's machine, keyless Blockchair returns HTTP 430 while Blockstream Esplora returns 200. Make Esplora the default Bitcoin source and keep Blockchair as an optional fallback that needs a key. Confirm Esplora's current limits before the demo.
- BNB: the team's notes say Etherscan V2 has needed a paid tier for BNB since Nov 2025, so NodeReal stays the BNB path. It is still open whether nr_getAssetTransfers returns BEP-20 transfers in both directions.
- Everything else, including the best free Tron stack and the top 3 label sources, has to wait for the research to be re-run.
