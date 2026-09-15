# Indian Legal/Compliance Context for VASP Attribution (PMLA + FIU-IND)

**Research question:** What is the Indian legal/compliance framework that makes
"attributing an unknown crypto wallet to the nearest VASP" a compliance-relevant
exercise — specifically the PMLA notification that pulled Virtual Digital Asset
(VDA) service providers into the anti-money-laundering regime, and the current
FIU-IND AML/CFT guidance those providers must follow?

**Short answer (as of September 2026):** Since 7 March 2023, entities that
exchange, transfer, safe-keep, or facilitate VDAs "for or on behalf of another
person in the course of business" are legally "reporting entities" under the
Prevention of Money Laundering Act, 2002 (PMLA) — the same status banks and
stockbrokers have. This is what makes VASP identity (which VASP controls a
wallet) matter for compliance: reporting entities must KYC their customers,
keep records, and file Suspicious Transaction Reports (STRs) with FIU-IND.
**The "2026 guidelines" premise checks out** — it is not a false lead. FIU-IND
issued a new, consolidated **"AML & CFT Guidelines for Reporting Entities
Providing Services Related to Virtual Digital Assets," dated 8 January 2026**,
which supersedes the original 10 March 2023 guidelines and folds in several
2024–2025 circulars. Both the 2023 and 2026 documents are hosted directly on
FIU-IND's own domain (`fiuindia.gov.in`), confirmed below.

---

## 1. PMLA and the March 2023 notification bringing VDA service providers under it

### 1a. The core notification: S.O. 1072(E), dated 7 March 2023

The Department of Revenue, Ministry of Finance, issued a gazette notification
under **Section 2(1)(sa)(vi) of the PMLA** — the clause defining "person
carrying on designated business or profession" — adding VDA-related activities
to that list. Because "reporting entity" is defined in **Section 2(1)(wa) of
the PMLA** to include a "person carrying on designated business or
profession," this single notification is what makes a VDA business a PMLA
reporting entity.

The notification specifies five categories of activity, when carried out "for
or on behalf of another natural or legal person in the course of business":

1. exchange between virtual digital assets and fiat currencies;
2. exchange between one or more forms of virtual digital assets;
3. transfer of virtual digital assets;
4. safekeeping or administration of virtual digital assets or instruments
   enabling control over virtual digital assets; and
5. participation in and provision of financial services related to an
   issuer's offer and sale of a virtual digital asset.

"Virtual digital asset" is not separately defined in the notification — it is
tied to **clause (47A) of Section 2 of the Income-tax Act, 1961**, i.e. the
same definition used for crypto taxation purposes.

**Companion notification, same date:** S.O. 1074(E), dated 7 March 2023,
amended the **Prevention of Money-Laundering (Maintenance of Records) Rules,
2005 (PMLR)** to require VDA reporting entities to verify client and
beneficial-owner identity (i.e., KYC) consistent with the rest of the PMLA
regime.

- **Primary/official source (gazette, gov.in domain):**
  [Gazette of India, e-Gazette (Extraordinary), 7 March 2023 — egazette.gov.in/WriteReadData/2023/244184.pdf](https://egazette.gov.in/WriteReadData/2023/244184.pdf)
  (Registered as "1512 GI/2023," Regd. No. D.L.-33004/99, the standard Gazette
  of India registration header.) **Caveat:** my fetch tool could not retrieve
  this PDF's text directly (TLS certificate verification error on
  `egazette.gov.in`), so I was not able to quote its operative text verbatim
  myself. The URL and filing details were confirmed via web search result
  metadata (the document's own title line appeared in search snippets), and
  the notification number (S.O. 1072(E)), date, and text are independently and
  consistently reported — including verbatim-quoted extracts — by multiple
  law-firm publications (next bullet). A human should open the gazette PDF
  directly to do a final verbatim check before citing it in any formal
  submission.
- **Corroborating secondary sources (law firm legal updates, all dated
  March–May 2023, all quoting the same S.O. 1072(E) text):**
  - [AZB & Partners — "Notification under Section 2 of PMLA"](https://www.azbpartners.com/bank/notification-under-section-2-of-pmla/)
  - [AZB & Partners — "The Indian Anti-Money Laundering Regime: New Compliance Obligations Around Virtual Digital Assets"](https://www.azbpartners.com/bank/the-indian-anti-money-laundering-regime-new-compliance-obligations-around-virtual-digital-assets-2/)
  - [Legal500 — "Virtual Digital Assets as Reporting Entity under PMLA: Regulation and Way Forward"](https://www.legal500.com/developments/thought-leadership/virtual-digital-assets-as-reporting-entity-under-pmla-regulation-and-way-forward/)
  - [Saikrishna & Associates — "Department of Revenue brings Virtual Digital Assets within the Ambit of the PMLA"](https://www.saikrishnaassociates.com/department-of-revenue-brings-virtual-digital-assets-within-the-ambit-of-the-prevention-of-money-laundering-act-2002/)
  - [Lexology (JSA/other) — "Notification under the PMLA, 2002, regulating virtual digital assets"](https://www.lexology.com/library/detail.aspx?g=501a0854-f447-4a6c-8299-43c4efde9511)
  - [Oxford Law Blogs — "Digital Assets & the Indian Anti-Money Laundering Regime" (July 2023)](https://blogs.law.ox.ac.uk/oblb/blog-post/2023/07/digital-assets-indian-anti-money-laundering-regime)

### 1b. What obligations this creates in plain language

Once a business falls into one of the five VDA activity categories above, it
is treated like a bank or broker under PMLA Chapter IV and must:

- **Register with FIU-IND** (Financial Intelligence Unit – India, under the
  Ministry of Finance) as a reporting entity, via FIU-IND's online portal
  ("FINgate"). Registration produces a "FIU Reporting Entity Identification
  Number" (FIU RE-ID). The framework is **activity-based, not
  location-based** — offshore VDA platforms servicing Indian users are
  expected to register too, and non-compliant offshore platforms have in
  practice been the subject of FIU-IND compliance notices / website-blocking
  requests routed through MeitY.
- **Do KYC / Customer Due Diligence (CDD)** on clients and beneficial owners
  before onboarding, per the amended PMLR (S.O. 1074(E)).
- **Keep records** of client identity and transactions for a specified
  retention period (multiple secondary sources — see §2 — state five years,
  consistent with PMLA Section 12's general record-keeping requirement for
  reporting entities).
- **Monitor transactions and file Suspicious Transaction Reports (STRs)**
  with FIU-IND when activity looks like money laundering, terror financing,
  or proceeds of crime — this is the core PMLA Section 12 obligation for all
  reporting entities, now extended to VDA businesses.
- **Face enforcement under PMLA Section 13** for non-compliance (the
  Director, FIU-IND, can inquire into a reporting entity's records and impose
  monetary penalties or other enforcement action for failing to register,
  failing to maintain records, or failing to report).

This is the compliance hook for the SIH project: because a VASP is a legally
identifiable "reporting entity" with KYC'd customers, **attributing an
unknown wallet to the nearest/controlling VASP** is what lets an investigator
or that VASP itself connect an on-chain address to a legally-obtained
identity and, ultimately, to an STR filing or law-enforcement request.

- Additional secondary-sourced detail on registration timeline (not
  independently verified against a primary notification by me — flagged
  medium confidence): several sources state a further **notification dated 4
  July 2024** made FIU-IND registration explicitly mandatory as a
  pre-condition of operating, and a **November 2023** notification/clarification
  also touched on reporting-entity classification. See
  [Enterslice — "FIU-IND AML & CFT Guidelines 2026"](https://enterslice.com/learning/fiu-ind-aml-and-cft-guidelines/) and
  [CryptoLegal.in — "FIU Registration in India: Guide for VDA Service Providers"](https://cryptolegal.in/fiu-registration-of-vda-service-providers/).
  I could not locate the primary gazette text for the July 2024 notification
  in the time available — treat that specific date as unconfirmed pending a
  primary-source check.

---

## 2. FIU-IND AML/CFT Guidelines: 2023 original vs. 2026 update

### 2a. Both versions are officially published on fiuindia.gov.in

Direct site search on `fiuindia.gov.in` turned up both documents hosted on
FIU-IND's own domain:

- **2023 (original):**
  [AML & CFT Guidelines For Reporting Entities Providing Services Related To Virtual Digital Assets — dated 10 March 2023](https://fiuindia.gov.in/pdfs/AML_legislation/AMLCFTguidelines10032023.pdf)
  (official FIU-IND PDF; I fetched and summarized this directly). It sets out
  the baseline framework: KYC before onboarding, ongoing/enhanced CDD for
  higher-risk customers and beneficial ownership verification, STR filing
  obligations, a registration requirement, and record-keeping duties — i.e.
  it operationalizes the March 2023 gazette notification described in §1
  into guidance FIU-IND expects reporting entities to follow.
- **2026 (current, supersedes 2023):**
  [AML & CFT Guidelines — dated 8 January 2026, file "VDA08012026.pdf"](https://fiuindia.gov.in/pdfs/downloads/VDA08012026.pdf)
  (official FIU-IND PDF; confirmed to exist and be hosted on FIU-IND's own
  domain via direct site search, and via download — the file downloaded
  successfully as a genuine ~14 MB PDF). **I was not able to get a clean
  text extraction of this specific PDF** (WebFetch's model-based summarizer
  rejected it twice — once for exceeding a 10 MB content-processing limit,
  once reporting it looked like undecoded binary/compressed data on a
  smaller companion PDF). So the detailed "what changed" content below is
  triangulated from **three independent secondary sources**, not read
  verbatim by me from the primary PDF — flagged accordingly.

Also confirmed via the same site search: FIU-IND published two of the
interim documents the 2026 guidelines are reported to consolidate —
[VDA SP registration circular, dated 15 September 2025 ("VDASP15092025.pdf")](https://fiuindia.gov.in/pdfs/downloads/VDASP15092025.pdf)
and a Principal Officer guidance document referenced as dated 20 January
2025 / 25 February 2025 in secondary sources
([VDASP20012025.pdf](https://fiuindia.gov.in/pdfs/downloads/VDASP20012025.pdf)).
This is consistent with the "consolidation" story below.

### 2b. What the 2026 guidelines reportedly changed, vs. 2023

Three independent law-firm/industry secondary sources — cross-checked against
each other and broadly consistent — describe the 8 January 2026 guidelines as
**consolidating** the March 2023 guidelines plus the September 2025
registration circular and February 2025 Principal Officer guidance into one
document, with materially tightened requirements:

| Area | 2023 baseline | 2026 update (per secondary sources) |
|---|---|---|
| Registration | Reporting-entity status + basic registration requirement established | Full end-to-end process formalized in one document: FINgate-based initiation, temporary reference IDs, document submission, **mandatory in-person meeting with a live walkthrough demo of the entity's AML/CFT systems**, CERT-In-empanelled cybersecurity audit certificate; non-registration is treated as a PMLA Section 13 violation with enforcement consequences (incl. offshore platforms serving Indian users) |
| KYC/CDD | Standard verification; PAN not consistently mandatory | PAN mandatory for individuals; live-selfie liveness detection (eye-blink/head movement); geolocation + IP + device-ID capture at onboarding; penny-drop bank account verification; beneficial-owner ID at ≥10% ownership threshold (PMLR Rule 9(3)) |
| Risk classification | Not prescribed in detail | Mandatory client risk buckets (at least High/Medium), board-approved framework, re-KYC every 6 months for high-risk clients / annually for others |
| Principal Officer | Role existed, less prescriptive | Must be full-time, exclusive (no concurrent roles), India-based, ≥3 years AML/financial-crime experience, permanent invitee to board risk committee, quarterly Board reporting on STR summaries/effectiveness |
| Travel Rule | Not prominently addressed | Explicit requirement: originator + beneficiary data (verified name, ID number, wallet address, etc.) must travel with the transfer **before or at the time of transfer**, not after |
| High-risk products | Not addressed | Anonymity-enhancing cryptocurrencies: deposits/withdrawals prohibited; mixers/tumblers must not be facilitated; enhanced CDD for unhosted wallets |
| Record-keeping | Not detailed with same granularity | 5 years' retention after account closure, tamper-proof audit trails, extended retention while an investigation is open |
| STR reporting | Standard STR obligation | Expected to include full KYC, wallet addresses, transaction hashes/counterparty data; **attempted** (not just completed) suspicious transactions must also be reported; monthly activity reports to FIU-IND |

- **Sources for the above table (all secondary; all dated January 2026,
  reporting on the same 8 January 2026 FIU-IND document):**
  - [AZB & Partners client update PDF, 14 January 2026](https://www.azbpartners.com/wp-content/uploads/2026/01/Client-Update-FIU-Guidelines-2026-AZB-January-14-2026.pdf) — also indexed as [azbpartners.com/bank/fiu-ind-aml-cft-guidelines-2026](https://www.azbpartners.com/bank/fiu-ind-aml-cft-guidelines-2026/)
  - [Zigram — "FIU-IND AML & CFT Guidelines 2026 For VDA SPs"](https://www.zigram.tech/article/fiu-ind-aml-cft-guidelines-2026/)
  - [Tsaaro — "India's 2026 AML/CFT Guidelines for Virtual Digital Assets: What Changed"](https://tsaaro.com/blogs/india-s-2026-aml-cft-guidelines-for-virtual-digital-assets-what-changed)
  - Also consistent with: [Mondaq — "Update – AML & CFT Guidelines For Reporting Entities Providing Services Related To Virtual Digital Assets, 2026"](https://www.mondaq.com/india/financial-services/1734190/update-aml-cft-guidelines-for-reporting-entities-providing-services-related-to-virtual-digital-assets-2026), [CryptoSlate — "India FIU-IND AML/CFT Guidelines for VDA Service Providers"](https://cryptoslate.com/crypto-laws/india-fiu-ind-aml-cft-guidelines-vda-service-providers/), [Enterslice — "FIU-IND AML & CFT Guidelines 2026: What Every Crypto..."](https://enterslice.com/learning/fiu-ind-aml-and-cft-guidelines/)

### 2c. Why this matters for the SIH project specifically

The Travel Rule expectation (originator/beneficiary identity must travel with
a VDA transfer) and the wallet-address/transaction-hash detail expected in
STRs are the clearest textual link between this legal framework and a
"wallet-to-nearest-VASP attribution" tool: FIU-IND's own guidance now expects
reporting entities to be able to identify counterparty VASPs on both sides of
a transfer, which is exactly the clustering/attribution problem this project
is trying to solve in an automated way.

---

## Notes & confidence

- **High confidence, official-source-backed:** VDA-related businesses became
  PMLA reporting entities via gazette notification **S.O. 1072(E), dated 7
  March 2023**, under PMLA Section 2(1)(sa)(vi)/2(1)(wa), with a companion
  PMLR amendment S.O. 1074(E) the same day. I could not personally extract
  verbatim text from the primary gazette PDF (TLS fetch error on
  `egazette.gov.in`), but the notification number, date, and operative text
  are corroborated consistently across six-plus independent, contemporaneous
  law-firm sources, several of which quote it directly. A human should
  open `https://egazette.gov.in/WriteReadData/2023/244184.pdf` directly (a
  browser will likely succeed where my fetch tool's cert validation did not)
  before citing this in a formal report.
- **High confidence, directly confirmed on an official gov.in domain:** the
  original FIU-IND guidelines exist at
  `fiuindia.gov.in/pdfs/AML_legislation/AMLCFTguidelines10032023.pdf` (dated
  10 March 2023) — I fetched and read this one directly.
- **The "2026 guidelines" premise is CONFIRMED, not a false lead.** A new
  FIU-IND document exists at
  `fiuindia.gov.in/pdfs/downloads/VDA08012026.pdf`, dated **8 January 2026**,
  confirmed to be hosted on FIU-IND's own domain via direct site search and
  via a successful raw download (genuine ~14 MB PDF, not a 404/placeholder).
  However, **I could not get a clean automated text extraction of this exact
  PDF** — my fetch tool failed on it twice (size limit; then what looked like
  a binary/compression parsing failure on a related smaller PDF). So while I
  am confident the 2026 guidelines **exist** and are officially published,
  the **specific "what changed" bullet list in §2b is sourced from three
  independent secondary (law-firm/industry) write-ups published in January
  2026**, not verified by me word-for-word against the primary PDF. Before
  this goes into any formal SIH submission, a team member should open
  `https://fiuindia.gov.in/pdfs/downloads/VDA08012026.pdf` in a browser (or
  re-attempt extraction with a PDF-capable tool — my environment lacked
  `poppler-utils`/`pdftoppm` for page-level OCR) and spot-check the table in
  §2b, particularly the Travel Rule, record-retention period, and Principal
  Officer requirements, since those are the most operationally relevant to
  this project.
- **Medium confidence:** the July 2024 mandatory-registration notification
  and November 2023 clarification mentioned in §1b — reported consistently
  by secondary sources but I did not locate/verify a primary gazette
  citation for either within the scope of this task.
- **Not verified / out of scope here:** whether FIU-IND has issued anything
  *after* 8 January 2026 (i.e., between January and today, 14 September
  2026) that would further update this picture — my searches turned up
  nothing newer than the 8 January 2026 guidelines, but a live check of
  [fiuindia.gov.in/files/Downloads/Downloads.html](https://fiuindia.gov.in/files/Downloads/Downloads.html)
  and [fiuindia.gov.in/files/Publication/Publication.html](https://fiuindia.gov.in/files/Publication/Publication.html)
  closer to the SIH submission date is worth doing given how recently this
  area has been moving.
