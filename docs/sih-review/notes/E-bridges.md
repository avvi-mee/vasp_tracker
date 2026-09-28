# E: Bridges and cross-chain swaps (BLOCKED, nothing verified)

**Status (2026-09-27):** No research got done. Every web fetch was refused, so this track has **zero verified facts**. The brief requires a citation for every technical claim and forbids inventing addresses, events or endpoints, so nothing here is stated as fact.

## What happened
- WebSearch was already unavailable, as the brief said, so WebFetch was the only way to reach the web.
- I sent the first 5 WebFetch calls in parallel: THORChain memos, Midgard v2 doc, Across docs, deBridge docs and Allbridge Core docs. **All 5 were refused.** The error said auto mode's safety check "blocked this request because of earlier conversation content — it isn't about the action itself". It also said a retry "will hit the same refusal" and that "it will keep firing for the rest of this conversation".
- I did not retry. I also did not route around the block (curl in Bash, Chrome automation, or a Context7 docs lookup), because the refusal message says not to.
- Fetch budget used: 5 of about 40, and all 5 failed.

## Status of the requested sections
- Bridge-by-bridge reference: not written, because there are no verified sources.
- Instant swap services: not written.
- Free sources of bridge contract lists: not written.
- Cross-chain mapping when no API exists: not written. I opened no arXiv pages, so no papers are cited.
- Minimum-viable design: not written. Without verified contracts, events and endpoints, it would only be guesswork.

## Could not verify
Everything in questions 1 to 5. That includes the reported 2025 shutdown of eXch and the 2023 collapse of Multichain.

## How to unblock
Re-run this track in a **fresh session**, or with auto mode off (the default permission mode), so WebFetch works normally. The same brief and seed URLs can be reused unchanged. This fetch order (my suggestion) covers the most useful items first within the budget of about 40:
1. Services with a free API that maps a source tx to its destination tx: THORChain/Midgard, Across, deBridge DLN, LayerZero Scan, Wormholescan, Axelarscan, LI.FI, Bungee, Relay and Chainflip.
2. Bridges that matter for Tron: Allbridge Core and BTTC.
3. Contract lists: DefiLlama bridges-server `src/adapters`, Dune Spellbook, L2BEAT and GraphSense TagPacks. Check the licence of each.
4. Canonical bridges: Polygon PoS, Arbitrum, and OP/Base.
5. Instant-swap services, then the arXiv searches.
