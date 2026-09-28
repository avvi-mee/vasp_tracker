# VASP-Trace — SIH 2026 Idea Presentation: slide-by-slide content

Built for the official template `SIH2026-IDEA-Presentation-Format.pptx`. The section order follows the standard SIH idea format: Title → Idea → Technical Approach → Feasibility & Viability → Impact & Benefits → Research & References. The style follows the SIH 2024 winning deck you shared (Saarthi): `❖` section heads with underlines, bold "Label :" lines, dense but ordered points, a diagram on the right, a comparison table, and linked references.

## Rules this content follows

- **Every number is either measured on our running prototype or taken from a named source.** Nothing is invented. There are no "30–50% improvement" style claims.
- **Status is honest.** "✅ Working" means shown working in a live run on 27 Sep 2026. "🛠 In build" means planned before the finale, with the design ready. Keep these two labels on the slides; judges trust a team that separates them.
- **Diagrams are placeholders** marked `[DIAGRAM D1…D5]`, with the exact boxes and arrows to draw, so you can replace them with your own.
- **`[FILL]`** = something only you know (team ID, name, theme).
- **Slide count:** the SIH idea template has historically capped decks at **6 slides**. If the 2026 template allows more, use the optional slide 3B (architecture). Otherwise put diagram D2 on slide 3 and drop 3B.

## Design notes (so it looks human-made, not generated)

- Keep the template's own fonts, colours, SIH logo and title-page layout. Don't restyle it.
- Black text on white; one accent colour for the `❖` heads and the table header, taken from the template.
- **Use real screenshots of your running app** in place of stock icons wherever possible: the verdict card for the Tron trace, the investigation graph, the evidence-pack PDFs. A real screenshot is the strongest "we built this" signal a judge sees.
- Tech-stack logos go in a row under the stack text, as on Saarthi's slide.
- Section head ≈ 20 pt bold underlined; body 11–12 pt (SIH decks are dense); diagram labels ≥ 9 pt.

---

## SLIDE 1 — Title page (template fields)

| Field | Value |
|---|---|
| Problem Statement ID | **SIH26182** |
| Problem Statement Title | **Automated Blockchain Intelligence & VASP Attribution Engine integrated with the SAHYOG Portal** |
| Organisation | Ministry of Home Affairs (MHA) / Indian Cyber Crime Coordination Centre (I4C) |
| Theme | [FILL — copy the exact theme from the SIH portal] |
| PS Category | Software |
| Team ID | [FILL] |
| Team Name | [FILL] |

**Idea name / tagline** (if the template has a slot):
> **VASP-Trace** — from a suspect wallet to the exchange deposit account behind it, with the evidence and the right legal notice ready.

---

## SLIDE 2 — IDEA TITLE: "VASP-Trace — Automated VASP Attribution & SAHYOG Request Engine"

### ❖ Proposed Solution

**What it is :** An India-first blockchain-intelligence engine for cyber cells and I4C. An officer pastes a suspect wallet from an NCRP complaint (or SAHYOG pushes it). VASP-Trace follows the money on-chain, names the **nearest exchange / custodial VASP** and the specific **deposit address** that maps to one KYC'd account, and drafts the **legal request** to that VASP.

**How it works (one line each):**
1. **Detect chain** from the address format — Tron, Ethereum, Polygon, BNB Chain, Solana, Bitcoin.
2. **Trace** — ranked multi-hop search: follows every branch carrying ≥10% of the value, up to 12 hops, one asset at a time (so USDT isn't lost behind dust).
3. **Attribute** — matches every hop against: a curated Indian-VASP dataset (112 checksum-validated addresses: CoinDCX, WazirX, CoinSwitch) → GraphSense TagPacks (500,115 labels) → the explorer's own tags (e.g. Tronscan "Binance-Hot 7").
4. **Pin the deposit address** — sweep test (Victor, FC 2020): forwards ≥90% onward, to one hot wallet, from many funders, within minutes → "this is a customer deposit address".
5. **Judge risk** on two questions:
   - *where did the money go* — sanctions (OFAC list + Chainalysis on-chain oracle), mixers, darknet markets, FIU-IND status;
   - *how does the wallet behave* — 5 laundering typologies with published thresholds: funnel, rapid layering, fan-out smurfing, peel chain, round-amount structuring.
6. **Act** — recommends the legal instrument, drafts the SAHYOG-shaped request, and generates a **BSA 2023 s.63 evidence certificate** (Part A + Part B + SHA-256 hash report).
7. **Track** — case file with NCRP acknowledgement number, CCTNS FIR, UPI/bank money-trail, request status and a watchlist for alerts.

### ❖ How it addresses the problem

| Pain point in the PS | What VASP-Trace does |
|---|---|
| Suspect wallet is unhosted / VASP unknown | Traces to the **nearest named VASP** and the **deposit address** (the address the VASP can answer about) |
| Funds pass through many intermediate wallets | Ranked multi-hop search keeps every material branch and reports what it dropped |
| Manual tracing needs rare expertise and takes days | One paste → a verdict in **~3 s** on live data (measured, Tron case) + a plain-language summary any officer can read |
| Requests go to the wrong party or wrong instrument | Routes by the VASP's FIU-IND status and the request type (disclosure vs freeze) |
| Evidence must stand in court | BSA s.63 certificate pack with a reproducible SHA-256 |

### ❖ Innovation & uniqueness

1. **Deposit-address-level output**, not just "reached Binance". One deposit address = one KYC'd account = one answerable notice.
2. **Cross-case linking** 🛠: the same deposit address across NCRP complaints from different states means the same beneficiary. One notice then resolves many FIRs and exposes mule networks. NCRP's Suspect Repository covers phones, emails, accounts and URLs, but not wallets.
3. **India-native legal layer** ✅/🛠:
   - BSA s.63 certificate ✅;
   - BNSS routing: s.94 for disclosure; freeze per the state's High Court position (s.106 vs s.107 — the Courts split in 2026) 🛠;
   - NCRP / CCTNS / UPI fields ✅.
4. **Honest by design** ✅: "unattributed" is never shown as "clean"; a sanctions source that wasn't consulted is never shown as "clear"; every label carries its source.
5. **Bridges & swap services as their own entity type** 🛠: the destination is decoded where the protocol publishes it (THORChain memo; LI.FI / LayerZero status APIs), then the trace continues on the other chain.

**Proof it works** (live run, 27 Sep 2026):
- A real Indian-case Tron wallet was traced to **Binance-Hot 7** in **3.0 s**.
- The deposit-address score was **0.95**, with **15** funders feeding one destination.
- Behaviour risk came out **HIGH** even though Binance is a compliant exchange.
- **257** automated tests pass.
- The evidence pack generates in **1.7 s**.

`[DIAGRAM D1 — right side]` **Solution flow**, left → right:
Complaint (NCRP / SAHYOG) → Wallet → Trace (multi-hop) → Attribute (VASP + deposit address + confidence) → Risk (trail + behaviour + sanctions) → Act (BNSS notice + s.63 certificate) → Track (case, status, watchlist).
Put a small "screenshot of the verdict card" under it.

**Speaker notes:** Open with the one-case story: a complaint lists one Tron wallet, and today an officer clicks through explorers for days. Show that the output is a deposit address plus a notice, not just a graph. Say clearly which items are working and which are in build.

---

## SLIDE 3 — TECHNICAL APPROACH

### ❖ Technology Stack

- **Frontend :** Next.js 16, React 19, TypeScript, Tailwind CSS 4, Cytoscape.js + dagre (investigation graph).
- **Backend :** Python 3.13, FastAPI (19 REST endpoints, OpenAPI), NetworkX, psycopg2, PyJWT, fpdf2 (PDF certificates).
- **Database :** PostgreSQL (Supabase): cases, officers, audit log, case events, UPI hops, watchlist.
- **Blockchain data APIs** (free tiers, no nodes):
  - Tronscan — Tron TRX + TRC-20 USDT;
  - Etherscan API V2 — Ethereum, Polygon;
  - NodeReal MegaNode — BNB Chain;
  - Helius — Solana;
  - Blockstream Esplora — Bitcoin (replacing Blockchair 🛠).
- **Intelligence datasets :** curated Indian-VASP dataset, GraphSense TagPacks (MIT), OFAC SDN crypto addresses (0xB10C, nightly), Chainalysis sanctions oracle (on-chain, free), CoinGecko (₹ values).
- **Security :** PBKDF2-SHA256 passwords, JWT sessions, officer audit log; supervisor approval before a request is submitted 🛠.
- **Testing :** pytest, 257 tests, all network mocked.
- **Planned for scale :** Redis, worker queue, self-hosted chain indexers at I4C/NCFL.

`[LOGO ROW]` Next.js · React · TypeScript · Tailwind · Python · FastAPI · PostgreSQL · Supabase · Tron · Ethereum · Polygon · BNB Chain · Solana · Bitcoin

### ❖ Methodology & process for implementation

1. **Input** — wallet from NCRP/SAHYOG intake 🛠 or pasted by the officer ✅.
2. **Fetch** — native + token + internal transfers per address, cached 60 s.
3. **Search** — BFS over branches: ≥10% materiality, ≤3 branches per hop, ≤8 active, 12-hop default, 60-lookup budget; every dropped branch is reported.
4. **Label** — precedence: curated Indian VASP → GraphSense → explorer tags; the source is recorded on every hit.
5. **Deposit test** — weighted sweep score (forwarding 0.35 · single destination 0.30 · many funders 0.20 · prompt sweep 0.15), threshold 0.60.
6. **Risk** — 6 ordered trail rules + 5 behaviour typologies; the worse of the two wins, and the basis is named.
7. **Evidence** — canonical JSON record (no clock) → SHA-256 → BSA s.63 Part A / Part B / hash-report PDFs.
8. **Route & request** — instrument by FIU-IND status and request type → SAHYOG-shaped request → status tracking.
9. **Monitor** — watchlist re-trace; an alert opens when risk rises or the attributed entity changes.

`[DIAGRAM D2 — right side, or on optional slide 3B]` **System architecture** (Saarthi style: client top-left, server centre, services column right):

- **Client :** officer on laptop or phone → **Next.js console** (Investigate · Cases · Alerts · Dashboard · Coverage).
- **Server :** **FastAPI** — Auth (JWT) · Trace · Cases · Evidence · Watchlist · **SAHYOG adapter** 🛠.
- **Engine :** ranked multi-hop trace · deposit-address detector · risk + typologies · plain-language summary · **bridge/swap decoder** 🛠 · **cross-case linker** 🛠.
- **Data :** PostgreSQL · label store (Indian VASP, GraphSense, explorer tags) · sanctions (OFAC, Chainalysis oracle) · **VASP directory** (FIU-IND status + LE channel) 🛠.
- **External APIs column :** Tronscan · Etherscan V2 · NodeReal · Helius · Esplora · Chainalysis oracle · CoinGecko · LI.FI / LayerZero Scan / THORChain 🛠.
- **Outbound :** request → **SAHYOG** → **VASP** (exchange / custodian); s.63 certificate → court.

Draw 🛠 components with dashed borders.

**Speaker notes:** Stress "no blockchain nodes, free public APIs, works today". Point out that every threshold is published on the tool's Coverage page, so a defence lawyer can argue with a number, not a black box.

---

## SLIDE 3B (optional — only if the template allows more than 6 slides) — SYSTEM ARCHITECTURE

Full-slide version of `[DIAGRAM D2]` above, plus a legend: solid = working, dashed = in build.

---

## SLIDE 4 — FEASIBILITY AND VIABILITY

### ❖ Feasibility

1. **Technical :**
   - The working prototype traces live data on 6 chains using free hosted APIs, with no nodes.
   - Measured: Tron trace 3.0 s; Ethereum 3-hop trace 34.3 s; 257 tests pass.
2. **Legal :**
   - VDA service providers have been **PMLA reporting entities since 7 Mar 2023** (S.O. 1072(E)), so they must keep KYC and answer lawful requests.
   - FIU-IND's updated **AML/CFT guidelines of 8 Jan 2026** treat unhosted-wallet transfers as high-risk.
3. **Operational :** fits the existing flow — NCRP complaint → case → request to VASP → status — without changing it. It adds NCRP acknowledgement and CCTNS FIR fields.
4. **Economic :** open datasets and free API tiers. Production cost is mainly hosting plus self-hosted indexers; there are no per-seat licences.

### ❖ Potential challenges & risks (stated plainly)

1. **Heuristics are probabilistic** — a sweep pattern suggests a deposit address; it doesn't prove who owns it (only the VASP knows).
2. **Label coverage** — open datasets barely cover India: GraphSense has **30** Tron labels in 500,115, and none for WazirX, CoinDCX or ZebPay.
3. **Offshore / unregistered VASPs** — FIU-IND issued non-compliance notices to **49** offshore entities in 3 waves (Dec 2023: 9 · Oct 2025: 25 · Sep 2026: 15).
4. **Freezing law is unsettled** — in 2026 the Andhra Pradesh HC held that freezing needs a Magistrate's order (BNSS s.107), while the Karnataka and Bombay HCs allowed police freezing under s.106.
5. **Cross-chain hops & mixers** — a trail can leave the chain through a bridge or swap service.
6. **Free-tier limits** — e.g. Etherscan 3 calls/s; Bitcoin's keyless Blockchair access was blocked (HTTP 430) in our tests.
7. **SAHYOG has no public API** — its published role is automated notices to intermediaries under the IT Act.

### ❖ Strategies to overcome them

1. **Evidence-graded confidence**: each score shows its terms (label source, hops, deposit signals); "unattributed" is never "clean".
2. **Grow Indian labels**: persist explorer tags with provenance; build a VASP directory from the Lok Sabha registrant list (Dec 2023: CoinDCX, WazirX, CoinSwitch, ZebPay …), FIU-IND penalty orders and the 3 notice waves.
3. **Registration-aware routing**:
   - registered Indian VASP → BNSS s.94 notice;
   - registered offshore VASP → its law-enforcement portal;
   - unregistered → letter of request / MLAT + FIU-IND intimation;
   - USDT still on-chain → issuer freeze request.
4. **State-aware freeze drafts** (s.106 and s.107 variants); the **officer chooses**, and nothing is auto-filed.
5. **Bridge decoders** 🛠: THORChain memo (deterministic), LI.FI and LayerZero status APIs; otherwise "trail continues on chain X".
6. **Rate limiter + persistent cache now; self-hosted indexers at NCFL** for production. This also stops suspect addresses leaking to third-party explorers.
7. **SAHYOG adapter + mock service + published OpenAPI contract** 🛠, ready for I4C to connect.

### ❖ Use cases

1. District cyber cell: NCRP complaint wallet → deposit address + BNSS s.94 notice in one sitting.
2. I4C analyst: many complaints across states converge on one deposit address → one consolidated notice 🛠.
3. Freeze while funds are still at an exchange or still in USDT → exchange request or issuer-freeze request 🛠.
4. FIU-IND / ED: spot flows reaching the offshore platforms named in the non-compliance waves.
5. Court: BSA s.63 certificate whose hash a defence expert can re-derive.

### ❖ Supporting facts for feasibility & viability (sourced)

- India ranks **#1** in the Chainalysis **2025** Global Crypto Adoption Index (Chainalysis, 2 Sep 2025).
- **50** VDA service providers were registered with FIU-IND as of ~1 Oct 2025 (Ministry of Finance statement, via CoinGeek).
- The Esya Centre estimates **>₹3.5 lakh crore** of Indian VDA trading moved to offshore platforms between Jul 2022 and Oct 2023, a **>90%** share after the 1% TDS (via KoinX).
- FinCEN (May 2025): Cambodia-based Huione Group laundered **>US$4 billion** (Aug 2021–Jan 2025), including scam proceeds. Huione is also in FIU-IND's Oct 2025 notice list.

`[VISUAL]` A shield/check icon, as on Saarthi's slide, or a small table "Risk → Mitigation" (items 1–7 above side by side).

**Speaker notes:** Admit the limits before a judge raises them. The honest list (label coverage, freeze-law split, offshore VASPs) is the most credible slide in the deck.

---

## SLIDE 5 — IMPACT AND BENEFITS

### ❖ Potential impact on the target audience

- **Investigating officers (state cyber cells):** a named VASP and deposit address in seconds instead of manual explorer work, plus a readable summary and a ready notice.
- **I4C:** complaints linked across states through shared deposit addresses 🛠, so fewer, stronger notices and mule networks surfaced.
- **VASPs / exchanges:** precise requests naming the deposit address and tx hashes, so less back-and-forth and faster KYC answers.
- **Courts / prosecution:** a BSA s.63 certificate with a reproducible SHA-256 and published method thresholds.
- **Victims:** faster freezes while funds are still at the exchange or still in USDT, so a better chance of restitution.

### ❖ Benefits of the solution

- **Social :**
  - exposes collection wallets used in investment, task and "digital arrest" scams (our live case: 15 payers → 1 wallet → an exchange);
  - improves recovery odds for victims;
  - deters mule networks.
- **Economic :**
  - no per-seat licence cost, so it can reach every district cyber cell;
  - keeps investigation capability in India;
  - recovered proceeds return to victims.
- **Legal & governance :**
  - native BNSS / BSA outputs;
  - FIU-IND registration status visible at the point of action;
  - a full officer audit log.
- **Technological :**
  - an indigenous, API-first engine built on open datasets;
  - data sovereignty (self-hostable; production indexers at I4C);
  - integrates with SAHYOG / NCRP through a published contract.
- **Environmental :** runs on hosted APIs; no energy-heavy node infrastructure; paperless evidence packs.

`[DIAGRAM D3 — left side]` **Benefits tree** (Saarthi style): top box "Benefits of the solution" → five boxes: Social · Economic · Legal & Governance · Technological · Environmental, each with 1 icon.

**Speaker notes:** Don't quote percentage improvements. Say: "Measured today: 3 seconds from wallet to named exchange on a real case. The manual path the PS describes takes days."

---

## SLIDE 6 — RESEARCH AND REFERENCES

### ❖ Comparison with existing systems

| Feature | **VASP-Trace** | Chainalysis Reactor | TRM Forensics | GraphSense (open source) | Manual explorers (Tronscan / Etherscan) |
|---|---|---|---|---|---|
| Multi-chain tracing | ✅ 6 chains | ✅ | ✅ | ✅ (BTC-focused data) | ❌ one chain at a time |
| Tron USDT focus | ✅ | ✅ | ✅ | ❌ (30 Tron labels) | ✅ view only |
| Deposit-address identification | ✅ | ✅ | ✅ | ❌ | ❌ |
| Indian VASP labels (CoinDCX, WazirX …) | ✅ curated | ? | ? | ❌ | partial tags |
| FIU-IND registration-aware routing | 🛠 | ❌ | ❌ | ❌ | ❌ |
| BNSS notice + BSA s.63 certificate | ✅ s.63 · 🛠 routing | ❌ | ❌ | ❌ | ❌ |
| SAHYOG-shaped request / NCRP + UPI fields | 🛠 / ✅ | ❌ | ❌ | ❌ | ❌ |
| Cross-case linking via deposit addresses | 🛠 | ? | ? | ❌ | ❌ |
| Bridge / cross-chain decoding | 🛠 | ✅ | ✅ | ❌ | ❌ |
| Published thresholds (no black box) | ✅ | ❌ | ❌ | ✅ | — |
| Self-hosted, data in India | ✅ | ❌ SaaS | ❌ SaaS | ✅ | — |
| Licence cost | Free / open data | Commercial | Commercial | Free | Free |

Put this footnote on the slide: *"Competitor columns are from public product descriptions and were not independently tested. '?' = not publicly documented."*

### ❖ References

**Government & legal**
- SAHYOG portal (MHA): https://sahyog.mha.gov.in/
- Karnataka HC, *X Corp v. Union of India*, 24 Sep 2025: https://indiankanoon.org/doc/7614885/
- FIU-IND AML/CFT guidelines for VDA SPs (8 Jan 2026): https://fiuindia.gov.in/pdfs/downloads/VDA08012026.pdf
- Lok Sabha reply, 28 registered VDA SPs (4 Dec 2023): https://inc42.com/buzz/coindcx-wazirx-28-vda-service-providers-registered-fiu-govt/
- 50 VDA SPs registered; 25 offshore notices (Oct 2025): https://coingeek.com/indian-regulator-issues-notices-to-25-offshore-crypto-platforms/
- 15 offshore notices (9 Sep 2026): https://www.business-standard.com/markets/cryptocurrency/fiu-issues-notice-to-15-crypto-service-providers-asks-to-take-down-urls-126090900585_1.html
- Freezing under BNSS:
  - AP HC, 31 Mar 2026: https://indiankanoon.org/doc/195992643/
  - Karnataka HC, 10 Aug 2026: https://indiankanoon.org/doc/14622554/
  - Bombay HC, 30 Jul 2026: https://indiankanoon.org/doc/22370397/

**Research papers & methods**
- Meiklejohn et al., *A Fistful of Bitcoins* (IMC 2013): https://cseweb.ucsd.edu/~smeiklejohn/files/imc13.pdf
- Victor, *Address Clustering Heuristics for Ethereum* (FC 2020): https://www.ifca.ai/fc20/preproceedings/31.pdf
- Kappos et al., *How to Peel a Million* (USENIX Security 2022): https://www.usenix.org/conference/usenixsecurity22/presentation/kappos
- Möser & Narayanan, *Resurrecting Address Clustering in Bitcoin* (FC 2022): https://arxiv.org/abs/2107.05749
- Wang et al., *ZKP mixers and user privacy* (2022): https://arxiv.org/abs/2201.09035

**Data & ecosystem**
- Chainalysis 2025 Global Crypto Adoption Index: https://www.chainalysis.com/blog/2025-global-crypto-adoption-index/
- Chainalysis sanctions oracle: https://go.chainalysis.com/chainalysis-oracle-docs.html
- GraphSense TagPacks: https://github.com/graphsense/graphsense-tagpacks
- OFAC crypto address lists: https://github.com/0xB10C/ofac-sanctioned-digital-currency-addresses
- THORChain memo format: https://dev.thorchain.org/concepts/memos.html
- US Treasury, Tornado Cash delisting (21 Mar 2025): https://home.treasury.gov/news/press-releases/sb0057

`[DIAGRAM D4 — bottom-left]` **Research workflow** (Saarthi style, boxes with ✓):
PS analysis → Legal review (PMLA, FIU-IND, BNSS, BSA) → Literature (clustering & deposit heuristics) → Data-source survey (free APIs, open labels) → Prototype build → Live tests on real case data → Gap review → Roadmap to finale.

**Speaker notes:** The table is honest. We show where incumbents are ahead (bridge decoding) and where we're ahead (Indian labels, Indian legal outputs, self-hosted).

---

## Appendix — likely jury questions (keep for the Q&A, not on the slides)

1. **"SAHYOG has no public API. What did you integrate?"** Its published role is automated notices under IT Act s.79(3)(b). We built a SAHYOG-shaped request pack, an adapter and a mock with a proposed OpenAPI contract, all labelled MOCK. Going live is configuration once I4C exposes an endpoint.
2. **"False-positive rate?"** Not yet measured. Next step: evaluate against known exchange deposit addresses. Every attribution shows its evidence, and unattributed ≠ clean.
3. **"Can you freeze USDT on Tron?"**
   - Exchange route: s.94 for KYC, and a freeze per the state HC's position.
   - Issuer route: USDT has a contract-level blacklist (`addBlackList` / `isBlackListed`).
4. **"Which BNSS section?"** s.94 for disclosure. For freezing, the 2026 High Courts split (AP: s.107 with a Magistrate's order; Karnataka and Bombay: s.106 allowed). The tool drafts both and the officer chooses.
5. **"Why not buy Chainalysis?"** We're complementary: Indian labels, Indian legal outputs, NCRP/UPI linkage, self-hosting, and a cost that reaches every district.

---

## Prompt to build the .pptx (paste into a fresh Claude Code session with auto mode off)

> Build my SIH idea deck. Fill the official template `C:\Users\Avvi\Downloads\SIH2026-IDEA-Presentation-Format.pptx` with the content in `D:\VASP-Trace\docs\sih-review\SIH-PPT-CONTENT.md`, using the pptx skill:
> - Keep the template's layout, fonts, logo and slide count. Use slide 3B only if the template allows more than 6 slides.
> - Put clearly labelled placeholder boxes where it says `[DIAGRAM …]` or `[LOGO ROW]`; I'll replace them with my own diagrams.
> - Keep the ✅ / 🛠 status labels.
> - Put the speaker notes into each slide's notes.
> - Save as `VASP-Trace-SIH2026-Idea.pptx` next to the template, then run the skill's validation and visual QA and fix any overflow.
