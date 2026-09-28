# C: Crypto crime patterns in India, and existing tools (research notes)

**Status (2026-09-27): blocked. Nothing verified.** The auto-mode safety check refused all five web fetches in the first batch. The refusal said it was set off by earlier conversation content, not by the pages requested, and that it would keep firing for the rest of this session. I did not try to get around it (no curl, no browser tools, no search engines). Since nothing was fetched, every item below is either a gap or an **unverified lead from model memory (training cutoff June 2026)**. Use them as a checklist for a re-run. Do not cite them.

Refused fetches (0 of 5 succeeded, about 30 left in the budget):
- https://www.chainalysis.com/blog/2025-global-adoption-index/
- https://www.chainalysis.com/blog/2024-global-crypto-adoption-index/
- https://en.wikipedia.org/wiki/Huione_Group
- https://en.wikipedia.org/wiki/Pig_butchering_scam
- https://tether.io/news/

**To unblock:** re-run this brief in the default permission mode (not auto mode) or in a fresh session, following the fetch plan under "Could not verify".

## Crypto crime patterns in India

Verified: **nothing.**

Unverified leads to check. Each needs a fetched URL and an (a)/(b)/(c) label before use.
1. **Chainalysis Global Crypto Adoption Index.** I recall India ranked #1 in the 2023 and 2024 editions and #1 again in 2025. Check both Chainalysis seed pages.
2. **USDT on Tron as the main laundering rail.** I recall the UNODC 2024 convergence report calls USDT on Tron a preferred instrument of Southeast Asian scam and underground-banking networks. For India specifically, find ED or CBI press releases that name "USDT" or "TRC-20".
3. **Laundering path** (mule accounts, then P2P/OTC USDT purchase, then Tron wallets, then an offshore exchange). I recall many ED money-laundering (PMLA) press releases on cyber fraud describing proceeds converted to USDT and sent to foreign wallets. Specific releases, dates and amounts are not recalled.
4. **Huione.** I recall FinCEN proposed a Section 311 "primary money laundering concern" rule against Huione Group (Cambodia) in May 2025, citing about $4bn in illicit proceeds between Aug 2021 and Jan 2025. I recall a final rule later in 2025 but not its date. I also recall Elliptic reporting that Huione Guarantee/Haowang moved tens of billions of dollars, mostly USDT on Tron. Check Wikipedia and fincen.gov.
5. **Prince Group / Chen Zhi.** I recall US DOJ and OFAC action in Oct 2025, including a forfeiture action over about 127k BTC (about $15bn). Check.
6. **CBI Operation Chakra.** I recall Chakra-I (2022), Chakra-II (Dec 2023, tech-support and crypto fraud), and later rounds in 2024–25 against digital-arrest and mule-account networks. I don't reliably recall amounts or dates. Check cbi.gov.in.
7. **"Digital arrest" scams.** I recall MHA/I4C advisories and account blocking in 2024, but no reliable figures.
8. **FIU-IND and offshore exchanges.** I recall Dec 2023 notices to nine offshore exchanges (including Binance and KuCoin), then penalties on Binance (about Rs 18.82 cr, 2024) and Bybit (about Rs 9.27 cr, 2025). Check fiuindia.gov.in or PIB.
9. **Tether and the T3 FCU.** I recall the T3 Financial Crime Unit (Tether + TRON + TRM Labs) launched around Sept 2024 and announced cumulative freezes in the hundreds of millions of USD during 2025. Tether says it works with hundreds of agencies in dozens of countries. I recall no specific Indian cooperation.
10. **Crypto's share of Indian cyber-fraud losses.** I recall no figure. If none turns up, record it as a published-data gap.

## Existing tools

Verified: **nothing.** This table is a scaffold. Every cell except the URL still needs a fetch.

| Tool | What it does (unverified recall) | Chains | Pricing | Indian LEA usage (sourced) | URL (not fetched) |
|---|---|---|---|---|---|
| Chainalysis Reactor / KYT | Reactor: investigation graphing. KYT: transaction monitoring for exchanges | not verified | not verified (believed quote-based) | none sourced | https://www.chainalysis.com/reactor/ |
| TRM Labs Forensics | Multi-chain tracing and investigations. Partner in T3 FCU | not verified | not verified | none sourced | https://www.trmlabs.com/products/forensics |
| Elliptic Investigator / Navigator / Lens | Investigations / transaction monitoring / wallet screening | not verified | not verified | none sourced | https://www.elliptic.co/ |
| Crystal Intelligence | Blockchain analytics (formerly Crystal Blockchain) | not verified | not verified | none sourced | https://crystalintelligence.com/ |
| Merkle Science | Investigation and monitoring products. Singapore HQ, India links recalled but unverified | not verified | not verified | none sourced | https://www.merklescience.com/ |
| CipherTrace | Mastercard-owned. Recalled as wound down around 2024 (unverified) | n/a | n/a | none sourced | https://en.wikipedia.org/wiki/CipherTrace |
| Arkham | Explorer and intelligence platform with entity labels, free web tier | not verified | not verified | none sourced | https://www.arkhamintelligence.com/ |
| BlockSec MetaSleuth | Fund-flow tracing and visualisation | not verified | not verified (free and paid tiers recalled) | none sourced | https://blocksec.com/metasleuth |
| SlowMist MistTrack | Anti-money-laundering tracing and address risk scores | not verified | not verified | none sourced | https://misttrack.io/ |
| Breadcrumbs | Visual investigation tool | not verified | not verified (free tier recalled) | none sourced | https://www.breadcrumbs.app/ |
| GraphSense / Iknaio | Open-source analytics platform (from AIT, Austria). Iknaio is the commercial spin-off | not verified | GraphSense open source and self-hosted; Iknaio commercial | none sourced | https://github.com/graphsense , https://www.iknaio.com/ |

**Indigenous Indian efforts (C-DAC, I4C, NCB, state police): nothing found, because nothing could be fetched.** I have no confident memory of a named, public Indian-built tracing tool. Don't say one exists, or that none exists, until cdac.in, i4c.mha.gov.in and pib.gov.in have been checked.

## Gaps an indigenous tool can fill

All of these are (c) inference, with no source this session.
- **Cost and licensing.** Incumbents sell enterprise or per-seat subscriptions (recall, unverified). District cyber cells may not have the budget.
- **Data sovereignty.** Suspect addresses and victim details go to foreign SaaS platforms. An on-premises Indian tool keeps case data in India.
- **Indian exchange labels.** Attribution of deposit clusters at Indian exchanges and of P2P merchants named in complaints. How well incumbents cover these is unknown.
- **Integration with Indian systems.** NCRP/1930/CFCFRMS complaint IDs, SAHYOG, and evidence packs aligned with the Bharatiya Sakshya Adhiniyam s.63 certificate. I recall that s.63 replaced Evidence Act s.65B and that its Schedule certificate has a Part A (party) and a Part B (expert). Verify on indiacode.nic.in.
- **INR/UPI linkage.** Joining the bank/UPI leg (mule accounts, UTRs) to the on-chain leg. Incumbents appear to be chain-only (inference).
- **Languages.** Reports in Hindi and regional languages for investigating officers and courts (inference).

## Could not verify

**Everything in this document.** That covers all 10 crime-pattern leads, every tools-table cell, indigenous efforts, the BSA s.63 certificate format, SAHYOG/CFCFRMS details, and any Indian law-enforcement use of any vendor.

Fetch plan for the re-run, in priority order (about 30 fetches):
1. Chainalysis 2025 and 2024 adoption-index posts (the two seeds): India's rank.
2. UNODC TOC_Convergence_Report_2024.pdf: USDT on Tron, Huione, underground banking.
3. Wikipedia Huione_Group, then the FinCEN news room for the Huione 311 proposed and final rules.
4. Wikipedia Pig_butchering_scam: India mentions, Prince Group.
5. tether.io/news, then the T3 FCU launch and milestone posts, plus any India mention.
6. cbi.gov.in/press-releases: the Operation Chakra rounds.
7. enforcementdirectorate.gov.in/press-release: cyber-fraud cases that mention USDT or Tron.
8. PIB/MHA: I4C digital-arrest statistics. FIU-IND: penalties on offshore exchanges.
9. The 11 tool seed pages (Chainalysis Reactor, TRM, Elliptic, Crystal, Merkle Science, Wikipedia CipherTrace, Arkham, MetaSleuth, MistTrack, Breadcrumbs, Iknaio/GitHub GraphSense).
10. cdac.in and i4c.mha.gov.in: indigenous tools.
11. BSA 2023 text on indiacode.nic.in: s.63 and the Schedule certificate.

## Implications for the team's tool (provisional)

All (c) inference. They depend on the leads above checking out, so don't present them to judges as sourced.
- **Chains:** prioritise USDT (TRC-20) on Tron, then BTC and USDT on Ethereum/BSC. Confirm the order by counting tokens named in ED/CBI press releases.
- **Headline demo:** digital arrest → mule bank account → P2P USDT seller → Tron hop wallets → offshore exchange deposit address. Keep investment/task scams and pig-butchering as a second demo.
- **Evidence pack:** make BSA s.63-ready output the differentiator. That means Part A and Part B fields, hashes of exported data, tool version, data sources and timestamps. Check the Schedule wording first.
- **Fiat leg:** start from what an NCRP complaint actually holds (UPI IDs, UTRs, mule accounts). Incumbents appear not to cover this.
- **Freeze requests:** when a trail reaches USDT or an exchange, generate a freeze or preservation request pack (for Tether, T3 FCU or the exchange) for the investigating officer.
- **Positioning:** present the tool as the Indian layer alongside Chainalysis/TRM (local labels, INR/UPI linkage, on-premises data, cost, Indian languages), not as a replacement for their global attribution.
