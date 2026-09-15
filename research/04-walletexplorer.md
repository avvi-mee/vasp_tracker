# WalletExplorer.com — Research Notes

Research date: 2026-09-14. All claims below were checked live against the site on this date (site itself reports it is "Updated to block 966865 (2026-09-13 19:51:30)"), unless marked otherwise.

## 1. Is the site operational?

Yes — live and responding normally as of 2026-09-14. Homepage, `/api`, `/info`, and `/privacy` all return HTTP 200; the blockchain index is current (block 966865, Sept 13 2026). Live API calls made during this research succeeded (see §3).

Source: [https://www.walletexplorer.com/](https://www.walletexplorer.com/), [https://www.walletexplorer.com/api](https://www.walletexplorer.com/api)

**Important caveat — the site being "up" is not the same as its data being current:**
- **The wallet/service *name* database has NOT been updated since 2016** (site's own words: *"Name database is NOT updated (except some very rare cases) since 2016"*). Any exchange/VASP that started operating after ~2016, or any exchange that rotated its hot-wallet clusters since then, will **not** be labeled. This is the single most important limitation for an attribution project — WalletExplorer's labels are a historical/legacy snapshot, not a live VASP directory.
- **Blockchain data itself lags 1–2 days** behind the chain tip (site's words: *"It takes 1-2 days for a transaction to be shown on WalletExplorer"*), so it is not real-time.
- Reason given by the site's creator, Aleš Janda: he built WalletExplorer as a hobby project, then joined Chainalysis (2015) where he is paid to discover wallet names professionally, and can no longer disclose new names on the free public site — he explicitly points users to Chainalysis.com for anything newer.

Source (verbatim, fetched from page): [https://www.walletexplorer.com/info](https://www.walletexplorer.com/info)

**Ownership note (relevant to trustworthiness/ToS):** WalletExplorer.com is described in its own Privacy Notice as *"a Chainalysis website"*, and the footer explicitly directs visitors to Chainalysis.com ("the author of WalletExplorer.com now works there"). A 2021 investigative report (The Block, based on leaked Italian law-enforcement training materials) alleges Chainalysis has used WalletExplorer to collect visitor IP addresses tied to Bitcoin address lookups for law-enforcement leads, and that this affiliation was not disclosed on the site itself. This doesn't change the technical facts below, but it's worth knowing that queries made to the site (and likely the API) may be logged and associated with the requester's IP per the site's own Privacy Notice (see §4).

Source: [The Block, "Chainalysis used an IP-scraping block explorer to aid law enforcement, leaked docs say" (Sept 21, 2021)](https://www.theblock.co/linked/118223/chainalysis-used-an-ip-scraping-block-explorer-to-aid-law-enforcement-leaked-docs-say)

Historically WalletExplorer has had a reputation in the OSINT/research community for occasional downtime and being a fragile, unmaintained-feeling hobby project (it runs on "bash scripts and small C++ programs," in the author's own words, with no real database) — but as of this check it was reachable and serving current blockchain data.

## 2. Free lookups on the site today

Confirmed free and working, no login/paywall:
- Search box accepts: a Bitcoin **address**, **txid**, **firstbits** (address prefix), **XPUB/YPUB/ZPUB**, an internal **wallet ID**, or a **service/wallet name**.
- Results page shows the wallet's transactions, and — where WalletExplorer has a name for that cluster — the **owning service label** (e.g. "Bitstamp.net", "Binance.com", "BTC-e.com").
- A recently added feature (since July 2025, per the FAQ): **"Possibility to download CSV with the whole wallet (all pages at once)"** directly from the website, replacing an older manual bash-script workaround.

No paywall, no CAPTCHA encountered, no rate-limit errors encountered during this research (a handful of manual requests).

Source: [https://www.walletexplorer.com/](https://www.walletexplorer.com/), [https://www.walletexplorer.com/info](https://www.walletexplorer.com/info)

## 3. Official API

Yes — WalletExplorer has a documented, free, **no-API-key** JSON API. Documentation page: [https://www.walletexplorer.com/api](https://www.walletexplorer.com/api)

Quoted directly from the page: *"WalletExplorer has a JSON API. You can use it without any API key."*

**Endpoints (all under `https://www.walletexplorer.com/api/1/`):**
| Purpose | Endpoint |
|---|---|
| Transaction info | `tx?txid=TXID` |
| Address's transactions | `address?address=ADDRESS&from=FROM&count=COUNT` |
| Address lookup by prefix ("firstbits") | `firstbits?prefix=ADDRESS_PREFIX` |
| **Wallet/owner lookup for a single address** | `address-lookup?address=ADDRESS` |
| **Wallet/owner lookup for multiple addresses (batch)** | `addresses-lookup?addresses=ADDR1,ADDR2` |
| Addresses belonging to a wallet | `wallet-addresses?wallet=WALLET_ID&from=FROM&count=COUNT` |
| Transactions of a wallet | `wallet?wallet=WALLET_ID&from=0&count=COUNT` |
| Alternative names for a service | `alternatives?service=SERVICE_NAME` |
| Addresses derived from an XPUB | `xpub-addresses?pub=XPUB&gap_limit=GAP_LIMIT` |
| Transactions from an XPUB's addresses | `xpub-txs?pub=XPUB&gap_limit=GAP_LIMIT` |

The `address-lookup` and `addresses-lookup` endpoints are the directly relevant ones for this project's "attribute an unknown address to a VASP/cluster" use case.

**Notes/constraints, quoted from the docs page:**
- *"All parameters are mandatory."*
- *"The result always has the key 'found' (boolean) or 'error' (string) if bad input is provided."*
- *"Parameter FROM starts from 0. It needs to be divisible by 100 (there are fixed indexes in data files, so it's most efficient)."*
- *"Parameter COUNT can be a number from 0 to 1000, inclusively."*
- *"Parameter WALLET_ID could be searched by hexadecimal ID, or a label, or by some variant of the label (e.g. 'bitstamp' instead of 'Bitstamp.net')."*
- *"Parameter GAP_LIMIT can be in range from 1 up to 200 (the usual gap limit implemented in wallets is 20)."*

**Rate limits, quoted verbatim:** *"Currently, there are no limits. The limits can be eventually applied. However, if they are applied, it will return HTTP 429 and ban you for a moment. The thumb of the rule is just to put a bigger delay when the server returns an error :-)"* — i.e. no enforced limits today, but the service reserves the right to add them, and the informal guidance if you ever hit HTTP 429 is to back off.

**Live verification performed during this research (2026-09-14):**
```
GET https://www.walletexplorer.com/api/1/address-lookup?address=16SbwNa22nBwhLtg6HzWVYFQiUxtNzAUpt
→ HTTP 200
→ {"found":true,"label":"BTC-e.com","wallet_id":"000003a2f31608c0","updated_to_block":966865}

GET https://www.walletexplorer.com/api/1/tx?txid=99fd988bf60ff67847488ceeb76d08a8fcca7bde80bb0b06be2ef4a0055c3ba7
→ HTTP 200 (returned full tx JSON with per-address wallet_id/labels on inputs/outputs)
```
Both confirm the API is live, unauthenticated, and returns clean JSON right now.

## 4. robots.txt and Terms of Use — is scraping the only option beyond the API?

Since an official free API exists (§3), scraping is **not** the only option for programmatic access — the JSON API covers the exact use case this project needs (address → owning wallet/service label). Scraping would only be relevant as a fallback if the API were ever disabled, or to get HTML-only features not exposed via API.

Checked directly (2026-09-14):
- `https://www.walletexplorer.com/robots.txt` → **HTTP 404** (no robots.txt file exists at all — nothing is being declared off-limits or explicitly permitted to crawlers via robots.txt).
- Probed common Terms-of-Use paths: `/terms-of-use`, `/terms`, `/tos`, `/legal`, `/legal-notice`, `/disclaimer`, `/copyright`, `/faq` → **all HTTP 404**. No dedicated Terms of Use / Terms of Service page could be found anywhere on the site.
- The only legal/policy document that exists is the **Privacy Notice** (`https://www.walletexplorer.com/privacy`, HTTP 200, last updated October 14, 2021). It governs data collection, not scraping/automated-access rules per se, but it does confirm: *"Our servers automatically log Visitor Information, including the Internet Protocol (IP) address making the request, the website URL requested..., the Visitor's browser type and version, and other technical details..."* — so both scraping and API use are logged by IP. The notice also references *"our agreements, policies, and terms of use"* in one clause about legal enforcement, implying a ToU may exist in principle, but no such page is published or discoverable on the live site.

**Conclusion on legal terms:** There is no published robots.txt and no discoverable Terms of Use/Service prohibiting or permitting scraping. In the absence of any stated restriction, and given that WalletExplorer itself publishes and documents a free JSON API for "more technical Visitors... through their own computer processing programs" (their own words, from the Privacy Notice), the officially sanctioned path for this project is clearly **the documented API (§3)**, not scraping — use the API, not HTML scraping, and be a good citizen by keeping request rates modest since there's no rate limit enforced today (per the docs' own etiquette note above) but that could change.

## 5. Alternatives if WalletExplorer is unreliable or its data is too stale

Not deep-dived (per task scope), noted briefly for later evaluation:
- **Chainalysis** (commercial) — the sanctioned/actively-maintained successor product; WalletExplorer's own footer explicitly recommends it for anything newer than 2016 labels. Paid/enterprise.
- **OXT.me** — community mentions rate it as having better/more current clustering heuristics than WalletExplorer for some use cases.
- **GraphSense** (open-source blockchain analytics platform, iknaio/graphsense) — self-hostable clustering/graph analytics, no vendor lock-in.
- **BlockSci** (academic open-source blockchain analysis framework) — useful for building custom clustering heuristics rather than consuming pre-made labels.
- **Arkham Intelligence** — commercial entity-attribution/analytics platform with its own labeled address database.
- General block explorers with some labeling (Blockchair, walletexplorer-style label sets bundled in open datasets like `EntityAddressBitcoin` on GitHub, which is a static scrape of WalletExplorer circa 2018) can supplement but are not live services.

These are not verified in depth here — just names surfaced by search for a future, separate research pass if WalletExplorer proves insufficient.

Sources: [Medium — Free Bitcoin Forensics](https://medium.com/coinmonks/free-bitcoin-analytics-part-1-6d3452df0b19), [GitHub — Maru92/EntityAddressBitcoin](https://github.com/Maru92/EntityAddressBitcoin)

## Notes & confidence

- **Site operational status, API endpoints, API responses, robots.txt absence, and absence of a Terms of Use page**: HIGH confidence — verified live via direct HTTP requests (`curl`) and WebFetch against `walletexplorer.com` on 2026-09-14, not just via search-engine summaries. Raw HTML/JSON was inspected directly for exact quotes.
- **"Name database frozen since 2016" and "1-2 day blockchain lag"**: HIGH confidence — quoted verbatim from the site's own `/info` (FAQ) page, fetched live.
- **Chainalysis ownership and the IP-logging/law-enforcement angle**: MEDIUM confidence — the Chainalysis-ownership fact is confirmed directly by WalletExplorer's own Privacy Notice ("a Chainalysis website"). The specific law-enforcement/leaked-documents claims come from a single 2021 investigative report (The Block) that Chainalysis declined to confirm or deny; treat that detail as reported-but-unconfirmed, included here only as risk/ethics context, not as an operational fact about the API.
- **Historical uptime-issue reputation**: LOW-to-MEDIUM confidence — this is a commonly repeated characterization in the OSINT/research community and consistent with the site's own admission of a fragile, database-less, script-based architecture, but I could not find a citable uptime-tracking log or incident history to quantify past downtime. Do not treat "it has had uptime issues historically" as independently verified beyond what the site currently is/was up for; it was simply reachable and current at time of this check.
- **Alternatives list (§5)**: LOW confidence / not verified — these are names surfaced by web search only, not individually checked for current API availability, pricing, or data freshness. Treat as leads for a follow-up research task, not as vetted recommendations.
- **Rate limits**: the site currently enforces none (per its own docs, quoted above), but this is explicitly stated as subject to change without notice — do not hardcode an assumption of unlimited access into any production design; add basic backoff-on-429 handling regardless.
