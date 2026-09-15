# FIU-IND Registered VASPs & Non-Compliant Offshore Exchanges (India)

**Research date (accessed):** 2026-09-14
**Purpose:** Ground-truth ledger of (a) entities registered with FIU-IND as PMLA "Reporting Entities" in the Virtual Digital Asset Service Provider (VDA SP / VASP) category, and (b) offshore exchanges FIU-IND has flagged, penalized, or ordered blocked. Used for SIH26182 (nearest-VASP attribution for unknown wallets).

> **Headline finding, stated up front:** FIU-IND does **not** publish a single browsable, named, regularly-updated public list of all registered VDA SP reporting entities on fiuindia.gov.in. The official site (checked directly, see §1) exposes only: (i) registration **circulars/guidelines** (procedural PDFs, no entity names), (ii) **compliance/penalty orders** against individual named entities that were investigated, and (iii) the Ministry of Finance/PIB issues periodic **press releases with an aggregate count** ("N VDA SPs have registered to date") without a name-by-name roster. Every named "registered entity" list in this file is therefore reconstructed from secondary reporting (news outlets, legal/industry blogs) referencing FIU-IND actions or figures — **not** copied from an official roster, because no such public roster was found. This is a material gap for the SIH26182 ground-truth and is elaborated in Notes & Confidence.

---

## 1. Official FIU-IND site structure (verified directly)

Checked `https://fiuindia.gov.in/` and its Downloads page directly on 2026-09-14.

- Main nav: Home / About-FIUIND / Legislation / **Compliance Orders** / Publications / **Downloads** / International / FAQs / Contact Us.
- Downloads page (`fiuindia.gov.in/files/Downloads/Downloads.html`) lists VDA-SP-related documents as **circulars only**, no entity list:
  - "AML & CFT Guidelines for Reporting Entities Providing Services Related to Virtual Digital Assets — updated 8 Jan 2026" — `fiuindia.gov.in/pdfs/downloads/VDA08012026.pdf`
  - "3rd Revision of Circular for Registration of VDA SPs in FIU-IND as Reporting Entity — 15 Sept 2025" — `fiuindia.gov.in/pdfs/downloads/VDASP15092025.pdf`
  - "2nd Revision — 20 Jan 2025" — `fiuindia.gov.in/pdfs/downloads/VDASP20012025.pdf`
  - "Revision — 17 Oct 2023" — `fiuindia.gov.in/pdfs/downloads/VDASP17102023.pdf`
  - "Original circular — 4 July 2023" — `fiuindia.gov.in/pdfs/downloads/VDASP04072023.pdf`
  - Base AML/CFT Guidelines effective 10 March 2023 — `fiuindia.gov.in/pdfs/AML_legislation/AMLCFTguidelines10032023.pdf`
  - Attempted to fetch the 15-Sept-2025 circular directly for a named list: it is a procedural document (registration process/requirements), not a roster.
- "Compliance Orders" page (`fiuindia.gov.in/files/ComplianceOrder/ComplianceOrder.html`) returned an access-denial page to the automated fetch used in this research (not confirmed browsable by a human visitor); individual **named penalty-order PDFs** were, however, reachable directly (see §4), e.g. `fiuindia.gov.in/pdfs/judgements/Binance_Order_10_2024.pdf`.
- **Confidence: confirmed directly** (primary source, accessed 2026-09-14) — no named public registry exists at the paths checked.

---

## 2. Regulatory basis (confirmed, primary source)

- VDA SPs (exchange, transfer, safekeeping/administration of virtual digital assets, VASP financial services) were brought under PMLA AML/CFT obligations effective **10 March 2023** via FIU-IND's AML & CFT Guidelines. All VDA SPs serving India — onshore or offshore — must register with FIU-IND as a Reporting Entity under PMLA §2(1)(wa) and comply with §12(1) recordkeeping/reporting duties.
  Source: fiuindia.gov.in AML/CFT Guidelines PDF (10 March 2023); reiterated in PIB press release on the Sept 2026 enforcement action. **Confidence: confirmed, official primary source.**
- Registration circular has been revised three times: 4 Jul 2023 (original), 17 Oct 2023 (1st revision), 20 Jan 2025 (2nd revision), 15 Sept 2025 (3rd revision), guidelines updated again 8 Jan 2026. **Confidence: confirmed, primary source (fiuindia.gov.in Downloads page, accessed 2026-09-14).**

---

## 3. Aggregate registration counts over time (no name-level roster — counts only)

| As-of date | Count reported | Breakdown | Source | Confidence |
|---|---|---|---|---|
| ~Jan 2024 | "over 30" domestic VDA SPs registered; KuCoin first/only offshore registrant at that point | domestic-only figure | Legal500 thought-leadership article, published 4 Apr 2024 (https://www.legal500.com/developments/thought-leadership/the-requirement-of-fiu-ind-registration-and-its-ramifications-for-the-virtual-digital-asset-industry/) | Single source, industry legal commentary — not independently corroborated for this exact figure |
| 1 Oct 2025 | **50** VDA SPs registered to date | not broken down by onshore/offshore in this release | PIB press release PRID=2173758, 1 Oct 2025, "FIU IND issues notices for non-compliance to 25 offshore VDA SPs" (title/snippet confirmed via search; direct fetch blocked 403, see Notes) + corroborated by TechCrunch (2 Oct 2025, https://techcrunch.com/2025/10/02/india-cracks-down-on-25-crypto-exchanges-including-bingx-lbank-coinw-over-compliance-failures/, "at least 50 crypto exchanges have so far registered") and its Yahoo Finance syndication | **Confirmed by 2 independent sources** (PIB primary via search snippet + TechCrunch), both dated ~1–2 Oct 2025 |
| 6 Jan 2026 (article date) | **49** total — 45 India-based, 4 offshore | onshore/offshore split given | CoinGabbar, published 6 Jan 2026, citing "FIU-IND's annual report" and Economic Times reporting, no direct link to the primary report (https://www.coingabbar.com/en/crypto-currency-news/india-crypto-compliance-tightens-fiu-cracks-down-exchanges) | **Single source only** (no second outlet found repeating this exact 45/4 split); also numerically inconsistent with the 50-registered figure from 3 months earlier (50 → 49 despite ongoing registrations — could reflect a deregistration, a reporting-period cutoff, or simply imprecise secondary reporting) |
| mid-2026 (exact date unclear) | **54** VDASPs | not broken down | Low-quality SEO/aggregator content (Medium "Coinmonks" listicle, AnalyticsInsight, Bizzbuzz, Cryptowire — all near-identical "2026 list" articles) | **Unverified / low confidence** — these are affiliate-style listicles, no citation of an official source, and largely reproduce each other's wording |

**Takeaway:** the aggregate count is directionally consistent (30s in early 2024 → ~49–50 by late 2025/early 2026) but the exact current number cannot be pinned down to a single authoritative figure as of this research date, and no source provides a full name-by-name roster to go with any of these counts.

---

## 4. Named entities confirmed as registered / penalized-then-registered (primary-source penalty orders)

These are the only entities in this file backed by an **official FIU-IND document reachable at fiuindia.gov.in** (penalty/compliance orders), each independently corroborated by press coverage:

| Entity | Action | Official order | Date | Independent corroboration | Confidence |
|---|---|---|---|---|---|
| Binance (Nest Services Ltd) | Penalized ₹18.82 crore (~US$2.25M) under PMLA §13 for prior non-registration; then registered/resumed India operations | Order No. 10/DIR/FIU-IND/2024 — `fiuindia.gov.in/pdfs/judgements/Binance_Order_10_2024.pdf` | Order dated **19 June 2024** | Gulf News (19 Jun 2024 report of the $2.25M penalty), CoinDesk (10 May 2024, "Binance, KuCoin win registration...") | **Confirmed, 2+ sources incl. official order PDF** |
| KuCoin (Peken Global Ltd) | Penalized ₹34.5 lakh (~US$41,000); first offshore VASP to register, ~March 2024 | Order "PGL_Order_08_2024" — `fiuindia.gov.in/pdfs/judgements/PGL_Order_08_2024.pdf` | Order dated **22 March 2024** (per secondary reporting; filename suggests order series "08/2024") | CoinDesk (10 May 2024), general industry reporting repeating the $41K figure | **Confirmed, 2+ sources incl. official order PDF** |
| Bybit (Bybit Fintech Ltd) | Penalized ₹9.27 crore (~US$1M) under PMLA §13; registered/resumed India operations after payment | Order — `fiuindia.gov.in/pdfs/judgements/Bybit_Order_15_2024.pdf` (note: filename says "2024" but order/coverage date is Jan 2025 — unresolved minor discrepancy, see Notes) | Order dated **31 January 2025** per PIB (PRID=2098153) and press coverage | PIB press release (title confirmed via search), Inc42, CoinDesk (6 Feb 2025, "Bybit receives India clearance after settling $1M fine"), Yahoo Finance | **Confirmed, 2+ sources incl. official order PDF** |
| Coinbase | Reported to have registered with FIU-IND proactively (no penalty order located) — March 2025 | Not located: no penalty-order PDF found (consistent with "no prior enforcement action" framing) | ~March 2025 (secondary reporting only) | TechCrunch/Yahoo (2 Oct 2025) list Coinbase as registered/re-entered "early 2025"; multiple listicle sources repeat this | **Single-source-type only** (news mentions, no official order or registry confirmation found) |

Other domestic platforms **commonly named** in industry/legal commentary as FIU-IND-registered — **not verified against any official roster**, appearing only in secondary blog/listicle sources that substantially repeat each other's wording (CoinDCX, WazirX, ZebPay, Giottus, CoinSwitch, Mudrex, Bitbns): **Confidence: unverified / single-source-type (repeated listicle content, not independent corroboration).** Treat as plausible but NOT ground truth without direct FIU-IND confirmation.

---

## 5. Non-compliant offshore VDA SPs — three enforcement waves (official PIB press releases)

FIU-IND has issued three rounds of Section-13-PMLA non-compliance/show-cause notices to offshore VASPs, each followed by a request to MeitY (or, later, action under IT Act §79(3)(b)) to block app/URL access in India. All three PIB releases were located via search (titles/snippets confirmed); direct WebFetch of pib.gov.in pages returned HTTP 403 in this session (bot-blocking), so figures below rely on the PIB title/snippet plus independent news corroboration.

### Wave 1 — 28 December 2023 (show-cause notices, 9 entities)
PIB PRID=1991372, title: "Financial Intelligence Unit India (FIU IND) issues compliance Show Cause Notices to nine offshore Virtual Digital Assets Service Providers (VDA SPs)."

Entities: **Binance, KuCoin, Kraken, Huobi, Gate.io, Bittrex, Bitstamp, MEXC Global, Bitfinex.**

Corroboration: PIB (official, title/snippet), CoinDesk (28 Dec 2023, "India to Block URLs of 9 Offshore Exchanges..."), The Block (28 Dec 2023), Zeebiz (28 Dec 2023, names all 9 in headline), PYMNTS (28 Dec 2023). **Confidence: confirmed by 4+ independent sources + official PIB title.** (Note: an earlier low-quality secondary source surfaced during this research incorrectly substituted "Bybit" for "Bitstamp" in this list — that version was rejected after cross-checking 4 independent outlets that all agree on Bitstamp, not Bybit, for the Dec 2023 wave. Bybit was penalized separately in Jan 2025, see §4.)

Outcome: Binance and KuCoin subsequently registered (with penalties, §4). Others' current status not confirmed in this research (see Notes).

### Wave 2 — 1–2 October 2025 (non-compliance notices + blocking order, 25 entities)
PIB PRID=2173758, title: "FIU IND issues notices for non-compliance to 25 offshore Virtual Digital Assets Service providers (VDA SPs) under Section 13 of the PML Act, 2002." Ministry of Finance statement reported by TechCrunch/Yahoo as issued "Wednesday" (1 Oct 2025), articles published 2 Oct 2025.

Full 25-name list, as reported by two blog/industry sources (CryptoTimes-linked Charltons Quantum summary and a second aggregator) that both produced the **identical 25-name list**:
AscendEx, BC.Game, BingX, BitMEX, Bitrue, BTCC, BTSE, CEX.IO, Changelly, CoinCola, CoinEx, CoinW, Huione, HitBTC, LBank, LCX, LocalCoinSwap, Paxful, Phemex, Poloniex, PrimeXBT, ProBit Global, Remitano, YouHodler, ZooMex.

Corroboration for a **subset** (9 of the 25 names) from a tier-1 outlet: TechCrunch/Yahoo Finance (2 Oct 2025) explicitly name BingX, LBank, CoinW, ProBit Global, BTCC, AscendEX, ZooMex, CEX.IO, Poloniex — all 9 match the fuller 25-name list above. CoinGabbar (2 Oct 2025) independently names a further 7: Paxful, CEX.IO, LBank, BingX, CoinEx, AscendEX, CoinW (overlapping set).

**Confidence: the total count (25) and the enforcement action itself are confirmed by the official PIB title plus tier-1 press (TechCrunch/Yahoo, CoinGabbar). The full 25-name roster is corroborated for 9–16 of the 25 names by tier-1 outlets; the remaining names come only from secondary/blog aggregation (Charltons Quantum, CryptoTimes) that agree with each other but were not independently verified against the primary PIB order text (blocked by 403 in this session).** Treat the full 25-name list as **single-source-type, moderate confidence**, not fully confirmed.

Also reported alongside this wave (same Charltons Quantum article): a claim that only **5** platforms were "active and registered" — Binance, Mudrex, Coinbase, CoinSwitch, ZebPay. **This conflicts with the official PIB figure of 50 total registered VDA SPs as of the same date** (§3) and with the multi-source list of ~8 domestic platforms in §4. This "5 platforms" claim is judged to be an incomplete/cherry-picked example set by that blog, **not a reliable total** — flagged explicitly as a conflict, not resolved.

### Wave 3 — 9 September 2026 (non-compliance notices, 15 entities)
PIB PRID=2308131 / PRID=2307952 (two IDs surfaced for what appears to be the same release; not resolved which is canonical — both titled "FIU-IND issues notices for non-compliance to 15 Virtual Digital Assets Service providers (VDA SPs) under Section 13 of the PML Act, 2002," dated 9 Sept 2026), action taken under PMLA §13 plus IT Act §79(3)(b) takedown directions.

Entities: **WEEX (Weex International Exchange Ltd), BloFin (BLF Global Ltd), Rezorex, Bitunix (Bitunix LLC), DigiFinex (DigiFinex Ltd), Toobit (Hopeful Technology Co. Ltd), XT.com (Fibtc Ltd / XT Technical Pte Ltd), LATOKEN (LAtrade Ltd), WOO X (Wootech Ltd), Pionex (Marketa Trading Inc), ChangeNOW (CHN Group LLC), SimpleSwap (SimpleSwap Ltd), FixedFloat (FFGX Group LLC), WhiteBIT (UAB Clear White Technologies), Guardarian (FinSeven CZ).**

Corroboration: **Confirmed by 2+ independent tier-1/trade sources with an identical 15-name list** — CoinDesk (9 Sept 2026, "India's financial intelligence unit flags 15 crypto platforms for AML lapses") and TaxGuru (legal/tax trade press, republishing the PIB text) both give this exact list; CryptoTimes and Business Standard (9 Sept 2026) also cover the same action (names not independently re-extracted from Business Standard due to a fetch error, but headline/topic matches). **Confidence: confirmed by 2+ independent sources**, this is the highest-confidence enforcement list in this file.

---

## 6. Notes & confidence (read this before using any list above as ground truth)

**This is the most important section of this file. Be honest about what was and wasn't found.**

1. **No official named public registry was found.** Despite direct navigation of fiuindia.gov.in (Downloads page, homepage nav, attempted Compliance Orders listing), no page enumerates all currently-registered VDA SP reporting entities by name. The site publishes procedural circulars and, separately, individual penalty-order PDFs only for entities that were investigated/penalized. This means: **entities that registered without ever being penalized (the likely majority of the ~45 domestic registrants) have no official-source name trail at all in this research** — their names, where given in §4, come entirely from secondary listicle/blog content that could not be cross-verified against a primary source.
2. **Aggregate counts conflict and cannot be reconciled from open sources**: 50 (PIB, 1 Oct 2025) vs. 49 with a 45/4 split (CoinGabbar, 6 Jan 2026, citing an unlinked "FIU-IND annual report") vs. 54 (undated 2026 SEO listicles, not citing any primary source). These are treated in this file as **three separate, non-reconciled data points**, not updates superseding one another — do not average or pick one as "the" current number without further primary-source verification.
3. **A direct conflict was found and is flagged, not resolved**: one industry blog (Charltons Quantum, covering the Oct 2025 enforcement wave) states only 5 platforms are "active and registered" with FIU-IND (Binance, Mudrex, Coinbase, CoinSwitch, ZebPay), which is inconsistent with the official 50-registered figure from the same period and with other sources naming CoinDCX, WazirX, Giottus, Bitbns, etc. as also registered. This looks like the blog listing only the subset of exchanges that had a prior enforcement/registration news story, not a complete list. **Do not treat the "5 platforms" figure as the total registered count.**
4. **pib.gov.in blocked direct automated fetches (HTTP 403)** for all three press releases in this session. All PIB content in this file is reconstructed from search-engine snippets of the PIB page (title + short excerpt) plus independent news-outlet corroboration, not a full read of the primary release text. If a fully authoritative reading is needed, the PIB pages should be retrieved by a human browser session or an alternative fetch method: PRID=1991372 (Dec 2023), PRID=2173758 (Oct 2025), PRID=2308131 / PRID=2307952 (Sept 2026).
5. **One PDF (VDASP15092025.pdf) fetched successfully but returned corrupted/binary content** through the fetch tool used, preventing text extraction; based on its filename and position among other circulars, it is almost certainly a procedural registration circular, not a named list, but this was not confirmed by reading its actual text.
6. **A factual error was caught and corrected during this research**: an initial web-search synthesis (not a primary source) claimed the Dec 2023 nine-entity show-cause wave included "Bybit." Direct cross-checking against 4 independent outlets (CoinDesk, The Block, Zeebiz, PYMNTS) plus the PIB title all agree the ninth entity was **Bitstamp**, not Bybit. Bybit's own FIU-IND enforcement action was separate and later (order dated 31 Jan 2025). This is noted here as a caution: **single-source or synthesized web-search answers on this topic were found to contain at least one verifiable error during this research and should not be trusted without cross-checking.**
7. **The Bybit order filename says "2024"** (`Bybit_Order_15_2024.pdf`) while every press account of the actual order date says **31 January 2025**. This discrepancy (fiscal-year-style filename vs. calendar order date) was not resolved — flagged, not guessed at.
8. **Domestic "commonly registered" platform names (CoinDCX, WazirX, ZebPay, Giottus, CoinSwitch, Mudrex, Bitbns)** appear consistently across several industry/legal blog sources, but these sources substantially reuse each other's wording (likely derivative content), so they count here as effectively **one source type**, not independent corroboration, despite appearing on multiple URLs. WazirX in particular underwent a major 2024 security breach and offshore restructuring; its current FIU-IND registration status as of Sept 2026 was **not specifically re-verified** in this research and should not be assumed current without a fresh check.
9. **Overall confidence assessment for this file**: HIGH for the existence, dates, and regulatory basis of FIU-IND's VDA SP registration requirement and for the three enforcement-wave dates/entity counts (each backed by an official PIB title plus 2+ independent tier-1 sources). MEDIUM for the exact 25-name roster in the Oct 2025 wave (partially corroborated). LOW for any specific "currently registered" name list and for the exact current aggregate count — **no single figure or roster in §3/§4 should be treated as authoritative without direct verification against a fresh, human-browsed fiuindia.gov.in session or a formal RTI/FIU-IND inquiry**, which was outside the scope of this research pass.

---

## Source list (all URLs cited above, with access/publish dates)

- fiuindia.gov.in homepage and Downloads page — accessed 2026-09-14
- https://fiuindia.gov.in/pdfs/downloads/VDASP15092025.pdf — dated 15 Sept 2025 (fetch corrupted, not fully readable)
- https://fiuindia.gov.in/pdfs/downloads/VDA08012026.pdf — dated 8 Jan 2026 (not fetched, listed only)
- https://fiuindia.gov.in/pdfs/AML_legislation/AMLCFTguidelines10032023.pdf — dated 10 Mar 2023
- https://fiuindia.gov.in/pdfs/judgements/Binance_Order_10_2024.pdf — order dated 19 Jun 2024
- https://fiuindia.gov.in/pdfs/judgements/PGL_Order_08_2024.pdf — order dated ~22 Mar 2024 (KuCoin/Peken Global)
- https://fiuindia.gov.in/pdfs/judgements/Bybit_Order_15_2024.pdf — order dated 31 Jan 2025 per press coverage
- PIB PRID=1991372 — 28 Dec 2023 (9 offshore VDA SPs show-cause)
- PIB PRID=2173758 — ~1 Oct 2025 (25 offshore VDA SPs non-compliance)
- PIB PRID=2308131 / PRID=2307952 — 9 Sept 2026 (15 VDA SPs non-compliance)
- https://www.legal500.com/developments/thought-leadership/the-requirement-of-fiu-ind-registration-and-its-ramifications-for-the-virtual-digital-asset-industry/ — published 4 Apr 2024
- https://www.coingabbar.com/en/crypto-currency-news/india-crypto-compliance-tightens-fiu-cracks-down-exchanges — published 6 Jan 2026
- https://www.coingabbar.com/en/crypto-currency-news/fiu-india-crypto-exchange-ban-25-offshore-platforms-blocked — published 2 Oct 2025
- https://techcrunch.com/2025/10/02/india-cracks-down-on-25-crypto-exchanges-including-bingx-lbank-coinw-over-compliance-failures/ — published 2 Oct 2025
- https://finance.yahoo.com/news/india-cracks-down-25-crypto-131335174.html — published 2 Oct 2025 (syndicated TechCrunch)
- https://charltonsquantum.com/india-crypto-crackdown-2025-fiu-blocks-exchanges/ — undated blog, covers Oct 2025 wave
- https://www.cryptotimes.io/2026/09/09/indias-fiu-orders-takedown-of-15-offshore-crypto-apps-over-aml-non-compliance/ — published 9 Sept 2026
- https://www.coindesk.com/policy/2026/09/09/india-s-financial-intelligence-unit-flags-15-crypto-platforms-for-aml-lapses — published 9 Sept 2026
- https://taxguru.in/finance/fiu-ind-issues-non-compliance-notices-15-vda-service-providers-pmla.html — published ~9 Sept 2026
- https://www.businesstoday.in/technology/news/story/india-blocks-access-to-overseas-crypto-exchanges-binance-kucoin-and-more-after-show-cause-notice-413117-2024-01-13 — published 13 Jan 2024
- https://www.coindesk.com/policy/2023/12/28/india-issues-compliance-show-cause-notices-to-9-offshore-exchanges-including-binance-and-kucoin — published 28 Dec 2023
- https://www.theblock.co/post/269551/indias-financial-intelligence-unit-issues-compliance-notices-to-offshore-crypto-exchanges-including-binance-kraken — published 28 Dec 2023
- https://www.zeebiz.com/india/news-financial-intelligence-unit-issues-notice-looks-to-block-urls-of-9-offshore-crypto-platforms-for-non-compliance-with-anti-money-laundering-law-binance-kucoin-huobi-kraken-gateio-bittrex-bitstamp-mexc-global-bitfenex-crypto-270322 — 28 Dec 2023 (fetch returned 402, title/URL slug used as corroboration only)
- https://www.pymnts.com/cryptocurrency/2023/india-to-block-9-offshore-virtual-digital-asset-service-providers/ — published 28 Dec 2023
- https://www.coindesk.com/policy/2024/05/10/binance-kucoin-win-registration-with-indias-financial-intelligence-unit — published 10 May 2024
- https://www.coindesk.com/policy/2025/02/06/crypto-exchange-bybit-receives-india-clearance-after-settling-usd1m-fine — published 6 Feb 2025
- https://gulfnews.com/business/markets/india-financial-watchdog-imposes-225-million-penalty-on-crypto-exchange-binance-1.1718881007051 — published 19 Jun 2024
- https://inc42.com/buzz/fiu-slaps-inr-9-3-cr-penalty-on-crypto-platform-bybit/ — reporting the 31 Jan 2025 order
