# SIH26182 — Web Research (Step 3)

Compiled 2026-09-26 → 2026-09-27 for the VASP-Trace review. It covers SAHYOG, the Indian VASP landscape, crime patterns, existing tools, technical methods and free data sources.

## How to read this file: evidence labels

| Label | Meaning |
|---|---|
| **[F]** | **Fetched and read this session.** The URL was opened and the claim is taken from the page. |
| **[Q]** | **Confirmed from web-search results this session.** The claim appears in the result titles/snippets of the listed URLs; the page itself was not opened. |
| **[T]** | **From the team's research notes** (`research/*.md`, live-researched 2026-09-14, citing primary sources). Not re-fetched this session. |
| **[L]** | **Measured live on this repo this session.** Running code or a direct API probe; see REVIEW.md §1.1. |
| **[U]** | **Unverified lead.** From memory or a code comment. **Do not cite** until someone opens the source. |
| **[I]** | **Inference or our own design proposal.** Not a fact. |

### Research limitations (be aware before quoting anything)

- The first wave of research agents used up the session's **WebSearch budget (200/200)** and then hit the account's session limit. Their transcripts were empty, so nothing was recovered from them.
- The second wave (six agents, run in parallel on request) hit **auto mode's safety check on their web fetches**:
  - five were blocked outright and verified nothing;
  - the methods agent verified 5 sources before it was blocked;
  - the SAHYOG agent produced a design proposal only.
- Everything marked **[F]** below was therefore fetched directly from the main session. Findings in this file are narrower than intended; the **Could-not-verify** list at the end is the to-do list.
- **How to deepen this research:** re-run the six briefs in the default permission mode (not auto mode), or raise `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`.
- **About `docs/sih-review/notes/`:** these are the agents' own hand-back reports. Most say "blocked, nothing verified"; their "leads" are unverified memory. Everything usable from them — the SAHYOG contract design, the methods agent's verified sources and citation fix — has been merged into this file with labels. **Treat the notes as a log, not as findings.** They are safe to delete.

---

## A. SAHYOG portal

### A.1 What it is, per official sources

- **[F] Official purpose statement** (https://sahyog.mha.gov.in/, Ministry of Home Affairs): *"To automate the process of sending notices to intermediaries by the Appropriate Government or its agency under IT Act, 2000 to facilitate the removal or disabling of access to any information, data or communication link being used to commit an unlawful act."* The portal brings *"all Authorized Agencies of the country and all the intermediaries on one platform."*
  - The landing page says nothing about crypto, VASPs, data-disclosure requests, or any API.
- **[F] Karnataka High Court, *X Corp v. Union of India*** — judgment dated **24 Sep 2025**, Justice **M. Nagaprasanna** (https://indiankanoon.org/doc/7614885/). Per the fetched text:
  - The legal basis in issue is **IT Act s.79(3)(b)**, **IT Rules 2021 Rule 3(1)(d)**, and **MeitY Office Memorandum dated 31.10.2023 (No. 1(4)/2020-CLES-1)**, which prescribed a *"model format for takedown notice to intermediaries"*.
  - The record lists **28+ authorities** empowered to send such notices: many State/UT police departments plus central ministries, including Defence, Railways, Finance and Health.
  - The judgment concerns **content takedown only**. It does not mention the portal being used for data or information requests.
  - The core dispute was whether s.79(3)(b) permits blocking-type orders outside s.69A and the 2009 Blocking Rules. *Shreya Singhal* (SC, 2015) was invoked.
- **[U] Outcome.** The case is widely reported as a **dismissal of X's petition**, but the fetched text was truncated before the operative order. Confirm from the full judgment before quoting.
- **[F] I4C site** (https://i4c.mha.gov.in/) lists I4C's verticals as NCRP, NCTAU (threat analytics), NCEMU (ecosystem management), JCCT (joint coordination teams), NCFL (forensic lab), NCTC (training) and NCR&IC (research & innovation). The homepage body does not describe SAHYOG.
- **[F] NCRP** (https://cybercrime.gov.in/) has a "Financial Fraud" complaint category, a 1930 banner, and a **"Suspect Repository"** where citizens can search identifiers — *"mobile numbers, e-mail Ids, account numbers, URLs and other identifiers."* **No mention of crypto wallet addresses** on the homepage. [I] That gap is an opening for VASP-Trace: wallet and deposit addresses as first-class suspect identifiers.

### A.2 Are VASPs on SAHYOG? Do disclosure or freeze requests go through it?

- **[F] Nothing official we could open says so.** The official portal text and the High Court record describe a takedown-notice system.
- **[U] Bitget press release (~23 Jun 2025).** A code comment (`app/sahyog/gateway.py:9-15`) cites it as saying 45+ exchanges were onboarded to SAHYOG for BNSS s.94 disclosure requests. It **could not be located** this session. Do not put it on a slide.
- **[I] How to handle this in the pitch.** The PS itself (written by MHA/I4C) states that LEAs "raise lawful information disclosure requests through the SAHYOG Portal to VASPs". Treat that as the **problem owner's own statement of their internal workflow**, since the public documentation doesn't cover it. Say so plainly: *"Public SAHYOG documentation describes takedown notices under s.79(3)(b); per the problem statement, disclosure requests to VASPs also flow through it. We built to a proposed contract that I4C can adopt."*

### A.3 Technical form and API

- **[F]** No public API, schema or integration guide was found at sahyog.mha.gov.in.
- **[T]** `app/api/main.py:1-7` already frames the tool's own OpenAPI as the proposed integration contract.
- **[I]** Therefore any "integration" in the demo must be an **adapter against a mock**, labelled as such.

### A.4 Proposed SAHYOG ↔ VASP-Trace contract [I] (design, not fact)

Drafted from the verified role of SAHYOG as a hub between authorised agencies and intermediaries.

**Actors**
- The **authorised officer** initiates.
- **SAHYOG** is the routing hub.
- The **VASP** responds through its SAHYOG account.
- **VASP-Trace** drafts requests, receives status callbacks and keeps the audit trail. It never auto-submits and never contacts a VASP directly.

**Hub endpoints** (hypothetical)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/intermediaries?category=VASP` | Directory with `intermediary_id`, legal name and supported request types. |
| `POST` | `/v1/vasp-requests` | Submit a request. Idempotency key = `request_id`. Returns `202 {sahyog_ref, status}`. |
| `GET` | `/v1/vasp-requests/{sahyog_ref}` | Status (polling fallback). |

**VASP-Trace endpoints**

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/sahyog/events` | Signed status callbacks. |
| `POST` | `/v1/sahyog/cases` | Complaint intake: SAHYOG/NCRP pushes the wallet list and case metadata. |

**Request types:** `DISCLOSURE`, `FREEZE`, `RELEASE` (points to the freeze via `related_ref`), `PRESERVE`.

**Payload core**
- `case`: internal id, NCRP acknowledgement number, FIR number, police station, district, state.
- `requesting_agency`: agency id + officer id, name, designation.
- `legal_basis`: **the officer picks it** from a hub-maintained list, plus order reference and date.
- `target`: `intermediary_id`.
- `subjects[]`: chain, asset, address, role (deposit address / hot wallet), tx hashes, amounts, time window, and attribution (label, method, hops, confidence).
- `data_requested[]`: KYC, login IP/device, deposit/withdrawal history, linked bank/UPI.
- `evidence`: trace run id, **block height / time cutoff**, tool version, SHA-256 of the s.63 bundle.

**Callback types:** `ACKNOWLEDGED`, `CLARIFICATION_SOUGHT`, `RESPONDED`, `ACTIONED`, `REJECTED`, `OVERDUE`, `WITHDRAWN`.

**Security**
- Mutual TLS, with tokens bound to the client certificate (RFC 8705).
- The officer signs the canonical payload (JWS over RFC 8785 JCS) using a DSC or eSign — a hub policy decision.
- The deployment key signs the evidence bundle.
- Officer identity comes via OIDC from the hub/agency identity provider; the tool stores no officer passwords.
- Replay protection: `iat` within ±5 min, a nonce, and callbacks de-duplicated by `event_id`.
- VASP responses are JWE-encrypted to the requesting agency.

**Audit**
- An append-only, hash-chained log: `{seq, at_utc, actor, action, object, payload_sha256, prev_hash}`, with the head hash signed daily.
- Reads and exports of VASP responses are logged too, not only writes.
- Due-by timers are configurable per provision, because the statutory timelines were not verified.

---

## B. The Indian VASP landscape

### B.1 Legal framework

- **[Q][T] S.O. 1072(E), 7 Mar 2023** (MoF, under PMLA s.2(1)(sa)(vi)). It makes five VDA activities, done "for or on behalf of another person", a "designated business or profession", and hence a **PMLA reporting entity**:
  1. VDA↔fiat exchange;
  2. VDA↔VDA exchange;
  3. transfer of VDAs;
  4. safekeeping or administration of VDAs;
  5. financial services around a VDA issuer's offer.
  - Sources: https://www.legal500.com/developments/thought-leadership/virtual-digital-assets-as-reporting-entity-under-pmla-regulation-and-way-forward/ , https://www.azbpartners.com/bank/notification-under-section-2-of-pmla/ , and gazette https://egazette.gov.in/WriteReadData/2023/244184.pdf [T].
  - Companion PMLR amendment: S.O. 1074(E), same date [T].
- **[T] FIU-IND AML/CFT Guidelines for VDA SPs, 10 Mar 2023** — https://fiuindia.gov.in/pdfs/AML_legislation/AMLCFTguidelines10032023.pdf.
- **[Q][T] Updated guidelines dated 8 Jan 2026** — https://fiuindia.gov.in/pdfs/downloads/VDA08012026.pdf. Secondary summaries: https://tsaaro.com/blogs/india-s-2026-aml-cft-guidelines-for-virtual-digital-assets-what-changed , https://www.zigram.tech/article/fiu-ind-aml-cft-guidelines-2026/.
  - Transfers to or from **unhosted wallets are high-risk**.
  - **Travel Rule** data (originator and beneficiary name, PAN/ID, wallet address) must travel with the transfer.
  - CERT-In-empanelled audits.
  - Per the team's triangulation: 5-year record retention, mixers not to be facilitated, and STRs to carry wallet addresses and tx hashes.
  - [T] Primary PDF text not extracted — spot-check before quoting.
- **[Q] Tax.** 30% tax on VDA income plus 1% TDS (**s.194S**) since Budget 2022. The Esya Centre estimate: **>₹3.5 lakh crore** of Indian VDA trading moved to offshore platforms between Jul 2022 and Oct 2023, **>90% share**.
  - Via https://www.koinx.com/stats/india-tds-on-crypto-statistics and https://www.techtimes.com/articles/317939/20260607/india-crypto-tax-drives-61-billion-offshore-each-year-parliament-demands-answers.htm. The Esya primary report was not opened.
  - [U] The Income-tax Act 2025 may have renumbered s.115BBH / s.194S from 1 Apr 2026 — check before citing section numbers.
  - [I] Offshore concentration means many traces will end at **offshore** VASPs, so jurisdiction-aware routing matters.

### B.2 Who is registered

- **[F] Lok Sabha, 4 Dec 2023** (MoS Finance Pankaj Chaudhary): *"As many as 28 entities providing services related to virtual digital assets (VDAs) have registered with FIU-IND."* Named registrants:
  - Neblio Technologies (**CoinDCX**)
  - Zanmai Labs (**WazirX**)
  - Bitcipher Labs (**CoinSwitch**)
  - Nextgendev Solutions (**CoinSwitchX**)
  - Awlencan Innovations India (**ZebPay**)
  - Source: https://inc42.com/buzz/coindcx-wazirx-28-vda-service-providers-registered-fiu-govt/.
  - **This is the only official name-trail we found for Indian registrants.** It fills the gap the team's note flagged ("no official roster").
- **[F] ~1 Oct 2025, MoF statement:** *"So far, 50 VDA SPs have registered with FIU IND"* (https://coingeek.com/indian-regulator-issues-notices-to-25-offshore-crypto-platforms/, 7 Oct 2025; PIB PRID 2173758 [T]).
- **[T] Other counts.** 49 (45 onshore + 4 offshore; CoinGabbar, Jan 2026, single source). **54** appears only in SEO listicles [Q] (e.g. https://www.cryptowire.in/crypto/fiu-registered-crypto-exchanges-india/). Unreconciled.
- **[T] Registered after penalty** (official order PDFs on fiuindia.gov.in):
  - **Binance** — ₹18.82 cr, 19 Jun 2024. Also [Q] https://www.forbesindia.com/article/cryptocurrency/binance-hit-with-rs1882-crore-fiuind-fine/93438/1.
  - **KuCoin** — ₹34.5 lakh, 2024.
  - **Bybit** — ₹9.27 cr, 31 Jan 2025.
- **[T][U] Coinbase** reportedly registered in ~Mar 2025, with no penalty order.

### B.3 Enforcement against offshore VASPs (named lists)

| Wave | Date | Entities | Source |
|---|---|---|---|
| 1 | 28 Dec 2023 | Binance, KuCoin, Kraken, Huobi, Gate.io, Bittrex, Bitstamp, MEXC Global, Bitfinex | [Q] PIB PRID 1991372 https://www.pib.gov.in/PressReleasePage.aspx?PRID=1991372 ; [T] CoinDesk, The Block |
| 2 | ~1 Oct 2025 | AscendEx, BC.Game, BingX, BitMEX, Bitrue, BTCC, BTSE, CEX.IO, Changelly, CoinCola, CoinEx, CoinW, **Huione**, HitBTC, LBank, LCX, LocalCoinSwap, Paxful, Phemex, Poloniex, PrimeXBT, ProBit Global, Remitano, YouHodler, ZooMex | [F] https://coingeek.com/indian-regulator-issues-notices-to-25-offshore-crypto-platforms/ ; [Q] Business Standard, Charltons Quantum |
| 3 | 9 Sep 2026 | Weex, Blofin, Rezorex, Bitunix, DigiFinex, Toobit, XT.com, Latoken, WOO X, Pionex, **ChangeNOW, SimpleSwap, FixedFloat**, WhiteBIT, **Guardarian** | [Q] https://www.business-standard.com/markets/cryptocurrency/fiu-issues-notice-to-15-crypto-service-providers-asks-to-take-down-urls-126090900585_1.html , https://www.cryptotimes.io/2026/09/09/indias-fiu-orders-takedown-of-15-offshore-crypto-apps-over-aml-non-compliance/ , https://ddindia.co.in/2026/09/fiu-india-issues-notices-to-15-offshore-crypto-platforms-for-non-compliance/ |

- Wave 3 includes **four instant-swap / on-ramp services** (ChangeNOW, SimpleSwap, FixedFloat, Guardarian). These are exactly the "cross-chain swap services" the PS names. The repo's `app/data/fiu_compliance.py` lists only `changenow` of the four, and only 10 of wave 2's 25 names.
- **[Q] Exchange hacks that shaped Indian wallet practice:**
  - **WazirX, 18 Jul 2024** — ~US$235M stolen from a multisig under Liminal custody, attributed to the **Lazarus Group**. The US–Japan–South Korea joint statement is reported by BusinessToday: https://www.businesstoday.in/technology/news/story/north-koreas-lazarus-group-behind-235-million-wazirx-hack-confirms-joint-statement-by-us-south-korea-japan-460804-2025-01-14 ; see also https://en.wikipedia.org/wiki/2024_WazirX_hack.
  - **CoinDCX, 19 Jul 2025** — ~US$44M drained from an internal operational (liquidity) wallet after a server compromise; customer funds reported safe (https://techcrunch.com/2025/07/21/indian-crypto-exchange-coindcx-confirms-44-million-stolen-during-hack).
  - [U] WazirX's operating and registration status after its Singapore restructuring was not verified.

### B.4 How LEAs obtain KYC and freezes today

- **[Q] Exchange law-enforcement portals.** Binance runs a *Government Law Enforcement Request System* via **Kodex**. Requests need *"a valid court order from a competent jurisdiction or police orders/warrants"*; access requests are reviewed in about 3 business days (https://www.binance.com/en/support/law-enforcement , https://www.binance.com/en/support/law-enforcement/guidelines). [Q] Coinbase and Crypto.com also use Kodex portals (https://www.kodexglobal.com/industries/crypto).
- **[U] Indian exchanges' LE channels.** No public law-enforcement request page was found for CoinDCX; WazirX, CoinSwitch, ZebPay, Mudrex, Giottus and Bitbns were not checked. [I] The VASP directory needs a "LE channel" field filled by hand from each exchange's legal/privacy pages or nodal-officer letters.
- **[F] Tether.** Its terms say it may freeze Tether tokens when it "determines or suspects" prohibited use, and may share personal information with law enforcement (https://tether.to/en/legal/). A separate **Law Enforcement Requests Policy** exists (`/en/legal/?tab=law-enforcement-requests`), but its content is script-rendered and was not readable here. [F] USDT's ERC-20 contract carries blacklisting functions (see F.4).
- **[F] Freezing bank or crypto accounts under the BNSS: the High Courts are split in 2026.** This matters for freeze routing:
  - **Andhra Pradesh HC**, *Blue Sea Ventures LLP v. State of AP*, **31 Mar 2026** (https://indiankanoon.org/doc/195992643/): *"Section 106 empowers police only to seize property for evidentiary purposes and does not confer any authority to attach or debit-freeze bank accounts"*; attachment *"can only be effected upon orders of the learned Jurisdictional Magistrate."* Notices under s.106 and **s.94** used to freeze accounts were held *"manifestly without jurisdiction"*, and the freeze was quashed. The case was a commercial dispute, not cyber fraud.
  - **Karnataka HC**, *State of Karnataka v. JAR Gold Retail Pvt Ltd*, **10 Aug 2026**, Nagaprasanna J (https://indiankanoon.org/doc/14622554/): *"debit freezing of a bank account is not an attachment within the meaning of Section 107 of the BNSS at all, but is a species of seizure squarely traceable to the power conferred upon the Police under Section 106"*. The police freeze and must *"forthwith report the seizure to the Magistrate"*. s.107 attachment needs an application and a **14-day** show-cause notice. The court notes s.106 derives from former CrPC s.102.
  - **Bombay HC**, *Smartpaddle Technology Pvt Ltd v. State of Maharashtra*, **30 Jul 2026** (https://indiankanoon.org/doc/22370397/). s.94 (document production) cannot authorise freezing, but *"considering the power of freezing the accounts under Sections 106 and 107 of BNSS"*, the action was upheld even though the notices cited the wrong sections.
  - **Delhi HC**, *Pay 10 Services Pvt Ltd v. Union of India*, **26 Feb 2026**, P K Kaurav J (https://indiankanoon.org/doc/11567432/). The s.106-vs-s.107 question was **left open**. The police relied on **NCRP alerts** and argued a "temporary protective lien" was needed.
  - **Takeaway [I]:**
    - **BNSS s.94 is a disclosure instrument** (KYC and records). Using it to freeze is risky everywhere.
    - A freeze needs **s.106 (police freeze + immediate report to the Magistrate)** in Karnataka and Bombay jurisdictions, but **s.107 (Magistrate order)** in Andhra Pradesh.
    - The tool should draft freeze requests **per state position**, show the officer the split, and never auto-select.
- **[F] s.94 is the production-of-documents power.** The Bombay HC fetch above describes *"Section 94 BNSS (document production)"* as unable to authorise freezing, and the AP HC treated s.94 freeze notices as without jurisdiction. That confirms the disclosure-vs-freeze split the tool needs.
- **[U] Other instruments to verify before use:**
  - BNSS **s.112**: letter of request for investigation abroad (the old CrPC s.166A).
  - PMLA s.5 (provisional attachment), s.17 (search/seizure/freezing), s.50 (summons).
  - IT Rules 2021 Rule 3(1)(j): information to authorised agencies within 72 hours.
  - The **CERT-In Directions of 28 Apr 2022**: VASPs, exchanges and custodian wallet providers to keep KYC and transaction records for 5 years. The PDF at https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf was fetched but not text-extractable.
  - The MHA mutual-legal-assistance / letters-rogatory guidelines: mha.gov.in returned 403.

### B.5 Routing by target type

| Target | Disclosure (KYC/records) | Freeze | Channel | Constraint | Basis |
|---|---|---|---|---|---|
| FIU-registered **Indian** VASP (e.g. CoinDCX, WazirX, CoinSwitch, ZebPay) | BNSS s.94 notice | s.106 (+ report to Magistrate) or s.107 (Magistrate order), **state-dependent** | Exchange nodal officer; SAHYOG per the PS | Reporting entity under PMLA; KYC must exist | [F] Lok Sabha list; [F] HC split |
| FIU-registered **offshore** VASP (Binance, KuCoin, Bybit; Coinbase [U]) | s.94 notice via the exchange's LE portal (Kodex) | Exchange's LE process + court or police order | Kodex LE portal | Exchange reviews case by case | [Q] Binance LERS |
| **Unregistered / flagged** offshore VASP (waves 1–3) | Voluntary LE portal if one exists; otherwise MLAT / letter of request [U] | Same; plus FIU-IND intimation | LE portal or MLAT | Slow; no Indian compliance lever beyond blocking | [Q][F] FIU waves; [I] |
| **Stablecoin issuer** (USDT / USDC) | — | **Contract-level blacklist** by the issuer | Issuer's LE request policy | Issuer's discretion; fastest route while funds sit in USDT | [F] Tether terms; [F] USDT contract functions |
| **DeFi protocol / bridge / unhosted wallet** | None (no custodian) | None directly | Follow to the next custodial hop | Treat as "continue trace" | [I] |

---

## C. Crypto-crime patterns in Indian cybercrime

- **[F] Adoption.** India ranks **#1** in the Chainalysis **2025** Global Crypto Adoption Index (published 2 Sep 2025), ahead of the US, Pakistan, Vietnam and Brazil. It leads in retail and institutional centralised-service value received (https://www.chainalysis.com/blog/2025-global-crypto-adoption-index/).
- **[F] SE-Asia laundering infrastructure (Huione)** — via https://en.wikipedia.org/wiki/Huione_Group, citing FinCEN, Reuters and Elliptic:
  - In **May 2025** FinCEN found Cambodia-based **Huione Group** a financial institution of **primary money-laundering concern**, having laundered *"over US$4 billion … from August 2021 to January 2025"*, including DPRK heist and scam proceeds.
  - Elliptic called Huione Guarantee *"the largest criminal marketplace of all time"* (>US$27B).
  - Huione appears in FIU-IND's wave-2 list (B.3).
  - The Wikipedia text itself does **not** mention USDT on Tron.
- **[L] A real Indian-case wallet from the repo** (TNnrfcBk7…P5, cited in `app/data/chain_native_labels.py:4-13`):
  - **15 distinct funders** paid USDT-TRC20 in, and everything went out to **one** destination, tagged **"Binance-Hot 7"**.
  - The sending wallet scored **0.95** as a Binance **deposit address**.
  - This is the canonical **collection wallet → exchange deposit address** pattern. It is a single case, not a statistic.
- **[Q]** Binance assisted Indian authorities in a **₹226 crore** crypto network investigation linked to alleged terror financing (search summary of Binance LE pages; the primary report was not opened).
- **[U] Leads to verify** before any slide:
  - The UNODC Oct 2024 report on SE-Asian scam compounds and underground banking naming USDT on Tron as a preferred rail (https://www.unodc.org/roseap/uploads/documents/Publications/2024/TOC_Convergence_Report_2024.pdf).
  - The **T3 Financial Crime Unit** (Tether + TRON + TRM Labs, ~Sep 2024) and its freeze totals.
  - CBI **Operation Chakra** rounds (cbi.gov.in).
  - ED cases where cyber-fraud proceeds were converted to USDT. Code comments cite an ED freeze of 160,339 USDT in a ₹303 crore syndicate case, and a ₹226 crore Gujarat case.
  - I4C "digital arrest" advisories and statistics.
  - The **P2P path**: mule bank account → P2P/OTC USDT purchase → Tron wallets → exchange.
- **[I] Implication.** Prioritise **USDT-TRC20 on Tron**, then USDT/ETH on Ethereum and BSC. Demo the collection-wallet → deposit-address → exchange story. Treat the P2P/UPI leg as the unique Indian link, which the repo already models via `upi_hops`.

## D. Existing tools and the gap for an indigenous tool

| Tool | What we could confirm this session | To verify |
|---|---|---|
| Chainalysis (Reactor, KYT, Rapid…) | [F] Its **sanctions oracle** is free and keyless (see F.4). The team notes every other product is licensed. | Pricing (believed quote-based), Indian LEA contracts |
| TRM Labs (Forensics) | [U] Partner in the T3 FCU | Everything |
| Elliptic (Investigator / Navigator / Lens) | [F] Source for the Huione findings (via Wikipedia) | Pricing, India usage |
| Crystal Intelligence | [Q] Published a WazirX hack analysis (https://crystalintelligence.com/investigations/expert-analysis-wazirx-hack/) | Pricing, India usage |
| Merkle Science, Arkham, BlockSec MetaSleuth, SlowMist MistTrack, Breadcrumbs | — | Everything |
| CipherTrace | [U] Mastercard-owned, reportedly wound down (the Wikipedia fetch 404'd) | Status |
| GraphSense / Iknaio | [T][L] TagPacks are MIT-licensed and git-cloned into this repo. Measured **500,115 labels, 96.6% Bitcoin; Tron 30, Solana 5, Polygon 4, BNB 0** | — |
| Exchange LE portals (Kodex) | [Q] Binance, Coinbase and Crypto.com | Indian exchanges |

**Gaps an indigenous tool can fill** (mostly [I], with evidence where we have it):

1. **Indian-VASP attribution.**
   - [T] GraphSense carries 0 addresses for WazirX, CoinDCX, ZebPay, Giottus, Mudrex, Bitbns and BuyUcoin (`app/data/indian_vasps.py:3-8`).
   - [L] Only 30 Tron labels exist in the vendored set, yet Indian fraud proceeds are overwhelmingly USDT on Tron.
2. **Indian legal output.**
   - BSA 2023 s.63 certificate (Part A / Part B + hash report) — the repo already generates it.
   - BNSS disclosure vs freeze routing, aware of the 2026 High Court split [F].
   - NCRP acknowledgement and CCTNS FIR fields.
3. **Fiat leg.** Manual UPI/bank hops tie a complaint's UTRs to the crypto off-ramp; incumbents are chain-only [I].
4. **Data sovereignty and cost.** Self-hostable, open datasets; no case data sent to foreign SaaS [I]. Caveat: address lookups still go to public explorer APIs until self-hosted indexers are used.
5. **Cross-case linking** (differentiator 1, REVIEW.md §4). The shared deposit address across complaints fills the gap left by the NCRP Suspect Repository's lack of crypto identifiers [F].

---

## E. Technical methods

### E.1 Address clustering

- **[T] Common-input ownership** — Meiklejohn et al., *A Fistful of Bitcoins*, IMC 2013, §4.3 Heuristic 1 (https://cseweb.ucsd.edu/~smeiklejohn/files/imc13.pdf).
  - Failure modes: CoinJoin and PayJoin (https://en.bitcoin.it/wiki/Common-input-ownership_heuristic), exchange batching, multisig.
- **[F] Change-address heuristics** — BlockSci documentation (https://citp.github.io/BlockSci/reference/heuristics/change.html):
  - address reuse;
  - address type;
  - **optimal change** ("an output that is smaller than any of the inputs"; meaningless with one input);
  - **power of ten** (round outputs are payments);
  - client behaviour (first-time output address);
  - locktime and peeling-chain dynamic heuristics (these also return unspent outputs, so combine with the "spent" filter).
- **[F] Change prediction and "cluster collapse"** — Möser & Narayanan, *Resurrecting Address Clustering in Bitcoin*, FC 2022 (https://arxiv.org/abs/2107.05749). Ground-truth change outputs, a low-false-positive change predictor, and detection and prevention of cluster collapse. **Citation fix:** this arXiv ID is *not* "How to Peel a Million".
- **[F] Peel chains** — Kappos, Yousaf, Stütz, Rollet, Haslhofer & Meiklejohn, *How to Peel a Million: Validating and Expanding Bitcoin Clusters*, USENIX Security 2022 (https://www.usenix.org/conference/usenixsecurity22/presentation/kappos ; arXiv 2205.13882). It is a peel-chain heuristic used to validate and expand clusters, with ML-based validation on ground truth.
- **[T] Ethereum** — Victor, *Address Clustering Heuristics for Ethereum*, FC 2020 (https://www.ifca.ai/fc20/preproceedings/31.pdf).
  - **Deposit-address reuse** was the dominant heuristic: 17.9% of active addresses were clustered, with parameters tuned at `amax` ≈ 0.01 ETH and `tmax` ≈ 3,200 blocks.
  - The paper also describes airdrop multi-participation and self-authorisation.
- **[F] Tron account activation** (https://developers.tron.network/docs/account, dated 2026-09-16):
  - A new address is activated by *"send[ing] any amount of TRX or a TRC-10 token … or call[ing] `wallet/createaccount`"*; the **sender pays a 1 TRX creation fee** (+0.1 TRX if short of bandwidth).
  - A contract transfer to an unactivated address activates it for an extra **25,000 Energy**.
  - TRC-20 transfers are not listed as activating.
- **[F] Tron resource model** (https://developers.tron.network/docs/resource-model): 600 free bandwidth per 24 h, Energy for contract calls (a TRC-20 transfer is a contract call), and TRX burned when resources are short.
- **[I] Tron "activator / fee-funder" signal** — cheap, and we found no published method.
  - An exchange deposit address that receives USDT must be **activated and supplied with TRX or Energy** before it can sweep.
  - A recurring activator or fee-funder F across many addresses that all sweep USDT to the same hot wallet H is a strong deposit-cluster signal.
  - Validate it on known deposit addresses before it carries weight.

### E.2 Exchange deposit-address and hot-wallet sweep detection

- **[T]** Victor 2020: deposit addresses forward almost the whole balance to a main (hot) address, slightly reduced by fees.
- **[L]** The repo's sweep scorer (`app/graph/sweep.py`) scored the real Tron case 0.95.
- **[I] Signals that add precision:**
  - the sweep target is a labelled hot wallet;
  - forwarding ≥90% within a short window;
  - many distinct funders;
  - on Tron, the activator / fee-funder link above;
  - on EVM, a gas top-up from a known exchange "gas supplier" (the repo's Indian dataset already holds CoinDCX and WazirX *Gas Supplier* addresses).

### E.3 Mixers and tumblers

- **[F] Tornado Cash delisting.** On **21 Mar 2025** US Treasury removed the economic sanctions on Tornado Cash, "as reflected in Treasury's Monday filing in *Van Loon v. Department of the Treasury*" (https://home.treasury.gov/news/press-releases/sb0057). The repo's label *"OFAC-sanctioned Aug 2022"* is now misleading. [L] The live Chainalysis oracle returned **not sanctioned** for the donation address.
- **[F] Deposit→withdrawal linking** — Wang et al., *On How Zero-Knowledge Proof Blockchain Mixers Improve, and Worsen User Privacy* (2022, https://arxiv.org/abs/2201.09035).
  - Their heuristics shrink the claimed anonymity sets by **~27.34% (Ethereum)** and **~46.02% (BSC)**.
  - They also find **205 attackers and 2,595 BEV extractors** use mixers as their funding source.
  - The exact heuristics were not in the abstract [U]. Commonly cited ones: same deposit/withdraw address, unique gas price, linked addresses, multi-denomination.
- **[U]** Van Loon (5th Cir., Nov 2024); the Pertsev and Storm cases; ChipMixer (2023), Sinbad (2023), Samourai (2024) and Wasabi coordinator (2024) actions; CoinJoin equal-output detection (e.g. Stütz et al., AFT 2022). All to verify.
- **[I] Practical rule.** Treat a labelled mixer as a stop condition with HIGH exposure. Only claim a deposit→withdrawal link when a published heuristic fires.

### E.4 Bridges and cross-chain swaps: identifying them and decoding the destination

| Service | Destination encoded in | Free resolver | Evidence |
|---|---|---|---|
| **THORChain** | The **memo**: `SWAP:ASSET:DESTADDR:LIM/INTERVAL/QUANTITY:AFFILIATE:FEE`, short form `=`, e.g. `=:BTC.BTC:bc1q…`. On Bitcoin the memo sits in **OP_RETURN** (80-byte limit); on EVM chains it is passed through the **router deposit function/event**; 250-byte max memo | Midgard / THORNode public endpoints: `https://midgard.thorchain.network/v2/doc`, `https://gateway.liquify.com/chain/thorchain_midgard/v2/doc`, THORNode `https://thornode.thorchain.network/thorchain/doc` | [F] https://dev.thorchain.org/concepts/memos.html ; [F] https://dev.thorchain.org/concepts/connecting-to-thorchain.html |
| **LI.FI** (aggregator over many bridges) | — | `GET https://li.quest/v1/status?txHash=…`. Returns the sending and receiving `txHash` + `chainId`, `status` (NOT_FOUND / INVALID / PENDING / DONE / FAILED), `substatus`, `toAddress`. Needs `x-lifi-api-key` (free via partner portal). Returns 200 even when not found | [F] https://docs.li.fi/api-reference/check-the-status-of-a-cross-chain-transfer |
| **LayerZero** (Stargate etc.) | Message `srcEid` / `dstEid` | `GET https://scan.layerzero-api.com/v1/messages/tx/{tx}` ("Lookup messages using a transaction hash"). Auth and limits not stated | [F] https://docs.layerzero.network/v2/tools/layerzeroscan/api |
| **Across** | Deposit (destination chain, recipient) | `https://app.across.to/api`: `GET /deposit/status`, `/deposit`, `/deposits`. **Requires a Bearer token + `integratorId`** | [F] https://docs.across.to/reference/api-reference |
| **Wormhole** | VAA (target chain / address) | Wormholescan API exists (https://wormholescan.io/#/developers/api-doc); endpoints not extracted | [F] https://wormhole.com/docs/ ; details [U] |
| **Allbridge Core** | — | **Supports Tron** (with EVM chains, Solana, Sui, Stacks) for **USDT, USDC, USDe**. No public status API in the overview — "transfer history" is in-app only | [F] https://docs-core.allbridge.io/ |
| **deBridge (DLN)** | order (take chain, receiver) | Docs moved to https://docs.debridge.com/ ; order-lookup API not located | [F] redirect; details [U] |
| Chainflip, Symbiosis, Relay, Axelar/Squid, Celer, Synapse, Polygon PoS, Arbitrum/OP canonical bridges, BTTC (Tron) | — | — | [U] not checked |

- **[F] Free bridge-contract registry — DefiLlama `bridges-server`** (https://github.com/DefiLlama/bridges-server).
  - Per-bridge adapters live under `src/`.
  - **Contract addresses and per-chain parameters** are in `src/data/bridgeNetworkData.ts`.
  - Adapter output shape: `txHash, blockNumber, from, to, token, isDeposit, amount`.
  - The licence is not shown on the README page [U] — check before redistributing.
- **[F] Swap services now under Indian enforcement:** ChangeNOW, SimpleSwap, FixedFloat and Guardarian (FIU-IND wave 3, B.3). [U] eXch's reported 2025 shutdown was not verified.
- **[I] Mapping with no API:**
  - match the amount (minus fee) within a time window on the destination chain;
  - for EVM→EVM, check the same recipient address on the destination chain.
  - Always label the method ("decoded memo" beats "API lookup" beats "heuristic match") and its confidence.

### E.5 Confidence scoring

- **[U]** The literature and taint models (Möser, Böhme & Breuker 2014 — poison and haircut; FIFO "Clayton's case"; TIHO) and how vendors describe direct and indirect exposure were not verified.
- **[I] Recommended design** — explainable, with no new dependencies:
  - Keep an explicit evidence list per attribution: signal, source, reliability `r`, hop distance `h`, and whether it is independent.
  - Combine independent signals with noisy-OR: `P = 1 − Π(1 − w·r·dʰ)`, with decay `d ≈ 0.75`.
  - Show every term. Show direct (h = 0/1) and indirect exposure separately, as the repo's `exposure.py` already does.

### E.6 Laundering typologies and simple on-chain rules

FATF's *Virtual Assets Red Flag Indicators of ML/TF* (Sept 2020) is the canonical reference [U] — the FATF site returned **403**. The rules below are [I] unless noted.

| Typology | Rule a small team can implement | Status in repo |
|---|---|---|
| Peel chain | ≥3–4 hops each forwarding 70–99% to a fresh address, with a small piece peeled off (BlockSci peeling-chain heuristic [F]; Kappos 2022 [F]) | ✅ `typology.py:174-219` |
| Fan-out / smurfing | ≥8 destinations in near-equal amounts within 7 days | ✅ `typology.py:142-171` |
| Fan-in / collection wallet | ≥5 funders, ≤3 destinations | ✅ `typology.py:86-106` |
| Rapid layering | Median hold ≤1 h, ≥3 sweeps, ≥80% forwarded | ✅ `typology.py:109-139` |
| Round-amount structuring | The same multiple-of-100 amount ≥4 times | ✅ `typology.py:222-247` |
| Chain-hopping | The path reaches a bridge, swap service or instant exchanger | ❌ needs E.4 |
| Mixer, then exchange | A mixer on the path within N hops of an exchange | ❌ (risk reads the primary path only) |
| Address poisoning | An inbound zero-value or fake-token transfer from a look-alike address (same first/last 4–6 characters as a real counterparty) | ❌ |
| Nested service / OTC broker | The payer into a deposit address is itself a high-fan-in service | ❌ |
| Round-tripping | Funds return to the origin cluster within ≤5 hops | ❌ |

---

## F. Free and low-cost data sources

### F.1 Explorer and data APIs

| Chain | Provider | Free-tier facts | Evidence |
|---|---|---|---|
| ETH / Polygon | **Etherscan API V2** | **3 calls/s, 100,000 calls/day, selected chains only**. Paid from Lite (5/s) to Pro Plus (30/s, 1.5M/day) | [F] https://docs.etherscan.io/resources/rate-limits |
| BNB | Etherscan V2 | **Paid-only since 22 Nov 2025** (also Base, OP, Avalanche) | [T] https://docs.etherscan.io/supported-chains |
| BNB | **NodeReal MegaNode** | Free: **10,000,000 CU/month, 150 CUPS**. Whether Enhanced APIs (`nr_getAssetTransfers`) are on Free is not stated [U]. [L] The team's key worked live | [F] https://nodereal.io/pricing |
| Tron | **TronGrid** | Limits vary "by API key, account, IP, endpoint type, and time window". TRC-20 history is at `/v1/accounts/{address}/transactions/trc20` (page dated 2026-09-16) | [F] https://developers.tron.network/docs/trongrid |
| Tron | **Tronscan API** | Unauthenticated: 3 req/s; **no guaranteed QPS without a key since 31 Aug 2025**. `start+limit ≤ 10,000`; the transaction list returns "the latest 2,000 records" per time range | [T] research/01 (Tronscan support announcements) |
| Solana | **Helius** | Free: **1M credits/month, 10 RPC req/s, 2 DAS req/s**, no card. The pricing page lists "Preprocessed Transactions" as not on Free, **yet [L] the team's key returned parsed history** — check which plan the key is on | [F] https://www.helius.dev/pricing |
| BTC | **Blockstream Esplora** | `GET /address/:addr/txs` gives up to 50 mempool + 25 confirmed; `/txs/chain/:last_seen_txid` gives 25 per page. Inputs carry `prevout.scriptpubkey_address` + `value`, which **enables CIOH**. No rate limit documented. [L] Answered **HTTP 200 keyless** from the team's machine | [F] https://github.com/Blockstream/esplora/blob/master/API.md |
| BTC | **Blockchair** | [L] Keyless calls answered **HTTP 430** *"Your IP address is temporary blacklisted due to exceeding usage of API resources"*. Soft limit 30 req/min [T] | [L] live probe ; [T] research/01 |
| BTC | mempool.space | [L] Connection timed out from the team's network | — |
| Prices | **CoinGecko** Demo | **100 calls/min, 10,000 calls/month**, 1 year of daily history | [F] https://www.coingecko.com/en/api/pricing |

### F.2 Open labelled address datasets

| Dataset | Covers | Licence | Evidence |
|---|---|---|---|
| **GraphSense TagPacks** | 500,115 labels (96.6% BTC; ETH 16,449; TRX 30; SOL 5). **81,815 labels have no category** (e.g. Tornado pools, "upbit hack", "defi fraud") | MIT [T] | [L] profiled locally |
| **eth-labels** (dawsbot) | "169k+ labeled addresses and tokens across EVM chains" (ETH, Base, Arbitrum, Optimism, BSC, Gnosis, Celo), copied from Etherscan; web API + MCP server | MIT | [F] https://github.com/dawsbot/eth-labels — [T] Etherscan's ToS restricts dataset reuse of its labels, so check before relying on it |
| **Forta labelled-datasets** | Malicious contracts and phishing EOAs on Ethereum + Optimism (Etherscan `exploit` / `heist` / `phish-hack` labels) | MIT | [F] https://github.com/forta-network/labelled-datasets |
| **Dune Spellbook** (CEX addresses) | Source of the repo's Indian VASP CSV. The team found 158 of 270 upstream rows failed checksum validation | Apache-2.0 per code comment [U] | `app/data/indian_vasps.py:10-27` |
| **DefiLlama bridges-server** | Bridge contract addresses per chain | [U] | [F] E.4 |
| Exchange proof-of-reserves address lists (Binance, OKX, Bybit, KuCoin; any Indian exchange) | First-party hot/cold wallets | — | [U] not checked (JS-heavy pages) |
| ScamSniffer, CryptoScamDB, Chainabuse, MistTrack, Elliptic++ | Scam, phishing and risk labels | — | [U] not checked |

### F.3 Sanctions lists

- **[F] 0xB10C `ofac-sanctioned-digital-currency-addresses`** (https://github.com/0xB10C/ofac-sanctioned-digital-currency-addresses):
  - 18 assets, including XBT, ETH, **USDT**, **TRX**, BSC and SOL;
  - the `lists` branch is regenerated **nightly at 0 UTC** from the SDN list;
  - MIT, no warranty.
  - [L] The repo loads 910 addresses across ETH, XBT, TRX, SOL and BSC.
- **[F] Chainalysis sanctions oracle** (https://go.chainalysis.com/chainalysis-oracle-docs.html):
  - `isSanctioned(address)` at **0x40C57923924B5c5c5455c48D93317139ADDaC8fb** on Ethereum, Polygon, BNB, Avalanche, Optimism, Arbitrum, Fantom and Celo; Base uses **0x3A91A31cB3dC49b4db9Ce721F50a9D076c8D739B**;
  - covers US, EU and UN designations;
  - free, with no customer relationship needed;
  - Chainalysis "cannot guarantee the accuracy, timeliness…". The free Screening API is mentioned without technical detail.

### F.4 Stablecoin freeze signals (free and on-chain)

- **[F] USDT (ERC-20, `0xdac17f…1ec7`) verified source** (https://etherscan.io/address/0xdac17f958d2ee523a2206206994597c13d831ec7#code):
  - functions `addBlackList`, `removeBlackList`, `destroyBlackFunds`, `isBlackListed`, `getBlackListStatus`;
  - events **`AddedBlackList(address)`**, `RemovedBlackList`, `DestroyedBlackFunds`.
  - [I] Reading `isBlackListed` for each USDT address on a trail costs one free call and shows whether the issuer has already frozen it. [U] Confirm that the Tron USDT contract (`TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`) exposes the same.
- [U] USDC's `Blacklisted` event (circlefin/stablecoin-evm) was not checked.

---

## Could not verify (the to-do list)

1. SAHYOG:
   - the operative outcome of *X Corp* (reported dismissal);
   - any official statement that VASPs are onboarded or that disclosure/freeze requests flow through SAHYOG;
   - the Bitget June 2025 release;
   - SAHYOG manuals and FAQs.
2. I4C systems:
   - CFCFRMS launch date;
   - the 10 Sep 2024 launches (Suspect Registry, CFMC, Samanvaya, Cyber Commandos);
   - any I4C / C-DAC crypto tool;
   - IT Rules 2021 Rule 3(1)(j).
3. Law:
   - the BNSS s.94/s.106/s.107/s.112 mapping from the Act's own text (s.106↔CrPC s.102 is confirmed by the Karnataka HC);
   - PMLA s.5/17/50;
   - the CERT-In 2022 VASP record-keeping direction;
   - MHA MLAT guidelines;
   - Tether's LE Requests Policy text;
   - Circle's policy.
4. Registration status:
   - the Indian exchanges' LE contacts;
   - WazirX's 2026 status;
   - Coinbase's registration;
   - the current registered count (50 vs 49 vs 54).
5. Crime patterns:
   - UNODC 2024;
   - the T3 FCU;
   - CBI Operation Chakra;
   - ED USDT cases;
   - digital-arrest statistics;
   - crypto's share of Indian cyber-fraud losses (possibly unpublished).
6. Tools:
   - pricing and Indian LEA usage of every vendor;
   - CipherTrace status;
   - indigenous tools.
7. Methods:
   - FATF 2020 red flags and later targeted updates (403);
   - taint-model papers;
   - Wang et al.'s exact heuristics;
   - Tornado court history beyond the Treasury statement.
8. Bridges:
   - Wormholescan, deBridge, Chainflip, Symbiosis, Relay, Axelar, canonical bridges and BTTC details;
   - the DefiLlama licence;
   - eXch.
9. Data:
   - Tronscan's authenticated limits;
   - NodeReal Enhanced-API availability on Free;
   - Solscan, Blockscout, Alchemy and Bitquery free tiers;
   - proof-of-reserves lists;
   - the Etherscan "1,000 records per call since Jul 2026" claim in `app/api_clients/etherscan.py:15-17`.

## Source index (fetched or search-confirmed this session)

- https://sahyog.mha.gov.in/ · https://indiankanoon.org/doc/7614885/ · https://i4c.mha.gov.in/ · https://cybercrime.gov.in/
- https://indiankanoon.org/doc/195992643/ · https://indiankanoon.org/doc/14622554/ · https://indiankanoon.org/doc/22370397/ · https://indiankanoon.org/doc/11567432/
- https://inc42.com/buzz/coindcx-wazirx-28-vda-service-providers-registered-fiu-govt/ · https://coingeek.com/indian-regulator-issues-notices-to-25-offshore-crypto-platforms/
- https://www.business-standard.com/markets/cryptocurrency/fiu-issues-notice-to-15-crypto-service-providers-asks-to-take-down-urls-126090900585_1.html · https://www.cryptotimes.io/2026/09/09/indias-fiu-orders-takedown-of-15-offshore-crypto-apps-over-aml-non-compliance/ · https://ddindia.co.in/2026/09/fiu-india-issues-notices-to-15-offshore-crypto-platforms-for-non-compliance/
- https://www.pib.gov.in/PressReleasePage.aspx?PRID=1991372 · https://www.forbesindia.com/article/cryptocurrency/binance-hit-with-rs1882-crore-fiuind-fine/93438/1
- https://www.legal500.com/developments/thought-leadership/virtual-digital-assets-as-reporting-entity-under-pmla-regulation-and-way-forward/ · https://www.azbpartners.com/bank/notification-under-section-2-of-pmla/
- https://tsaaro.com/blogs/india-s-2026-aml-cft-guidelines-for-virtual-digital-assets-what-changed · https://www.zigram.tech/article/fiu-ind-aml-cft-guidelines-2026/
- https://www.koinx.com/stats/india-tds-on-crypto-statistics · https://www.techtimes.com/articles/317939/20260607/india-crypto-tax-drives-61-billion-offshore-each-year-parliament-demands-answers.htm
- https://en.wikipedia.org/wiki/2024_WazirX_hack · https://www.businesstoday.in/technology/news/story/north-koreas-lazarus-group-behind-235-million-wazirx-hack-confirms-joint-statement-by-us-south-korea-japan-460804-2025-01-14 · https://techcrunch.com/2025/07/21/indian-crypto-exchange-coindcx-confirms-44-million-stolen-during-hack
- https://www.binance.com/en/support/law-enforcement · https://www.binance.com/en/support/law-enforcement/guidelines · https://www.kodexglobal.com/industries/crypto · https://tether.to/en/legal/
- https://www.chainalysis.com/blog/2025-global-crypto-adoption-index/ · https://en.wikipedia.org/wiki/Huione_Group · https://crystalintelligence.com/investigations/expert-analysis-wazirx-hack/
- https://citp.github.io/BlockSci/reference/heuristics/change.html · https://arxiv.org/abs/2107.05749 · https://www.usenix.org/conference/usenixsecurity22/presentation/kappos · https://arxiv.org/abs/2201.09035 · https://home.treasury.gov/news/press-releases/sb0057
- https://developers.tron.network/docs/account · https://developers.tron.network/docs/resource-model · https://developers.tron.network/docs/trongrid
- https://dev.thorchain.org/concepts/memos.html · https://dev.thorchain.org/concepts/connecting-to-thorchain.html · https://docs.li.fi/api-reference/check-the-status-of-a-cross-chain-transfer · https://docs.layerzero.network/v2/tools/layerzeroscan/api · https://docs.across.to/reference/api-reference · https://wormhole.com/docs/ · https://docs-core.allbridge.io/ · https://github.com/DefiLlama/bridges-server
- https://docs.etherscan.io/resources/rate-limits · https://nodereal.io/pricing · https://www.helius.dev/pricing · https://github.com/Blockstream/esplora/blob/master/API.md · https://www.coingecko.com/en/api/pricing
- https://github.com/0xB10C/ofac-sanctioned-digital-currency-addresses · https://go.chainalysis.com/chainalysis-oracle-docs.html · https://github.com/dawsbot/eth-labels · https://github.com/forta-network/labelled-datasets · https://etherscan.io/address/0xdac17f958d2ee523a2206206994597c13d831ec7#code
- Team notes relied on as [T]: `research/01-block-explorer-apis.md`, `research/05-fiu-vasp-list.md`, `research/06-clustering-heuristics.md`, `research/07-legal-context.md`.
