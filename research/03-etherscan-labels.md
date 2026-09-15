# Etherscan Address Labels/Tags: API Availability, Workarounds, and ToS Risk

**Research question:** Does Etherscan's public API expose address name tags/labels
(e.g. "Binance: Hot Wallet", "Uniswap: Router") in JSON responses, or are they
only visible on the website UI?

**Short answer (as of September 2026):** Both, in a sense. Etherscan **now has a
documented API endpoint that returns name tags/labels** — but it is a **paid,
Pro Plus-tier-only endpoint** (currently $899/month). The **free tier** (and all
the standard endpoints most integrations actually use — `balance`, `txlist`,
`txlistinternal`, `tokentx`, etc.) still returns **no tag/label field at all**.
So for a free/low-cost SIH-style project, the practical situation is unchanged
from the historically "commonly discussed gap": labels are a UI-only feature
unless you pay for Pro Plus, use the legacy Enterprise export endpoint, or use
a third-party pre-scraped dataset.

---

## 1. What the current Etherscan API actually returns

### 1a. Standard/free-tier endpoints: no label field

The bread-and-butter Etherscan API endpoints that most projects use for
address/transaction data (`account` module — `balance`, `txlist`,
`txlistinternal`, `tokentx`, etc.) do **not** include any tag, label, or name
field. Their documented response fields are purely transactional:
`blockNumber, timeStamp, hash, nonce, blockHash, transactionIndex, from, to,
value, gas, gasPrice, isError, txreceipt_status, input, contractAddress,
cumulativeGasUsed, gasUsed, confirmations`. No `label`, `tag`, or `nametag`
key appears anywhere in this response shape.
Source: [Accounts – Etherscan API docs](https://docs.etherscan.io/sepolia-etherscan/api-endpoints/accounts), [Get Native Balance for an Address](https://docs.etherscan.io/api-reference/endpoint/balance)

This confirms the long-standing community complaint: the labels visible on
`etherscan.io/address/0x...` (e.g. "Binance: Hot Wallet 20") come from a
separate internal tagging system that was, until recently, not exposed to API
consumers at any price.

### 1b. New (2026): the paid "Nametags" API — `getaddresstag`

Etherscan has since introduced a dedicated **Nametags API** as part of its
multichain v2 API, announced on X/Twitter as an evolution of a previous
"Metadata API": *"API Endpoint: Address Nametags — An upgrade from our
previous Metadata API — now fully Multichain. Perfect for security teams to
flag phishing addresses and for wallet teams to enrich UX with meaningful
labels."*
Source: [@etherscan on X](https://x.com/etherscan/status/1935666941571846242)

Documented endpoint details (fetched directly from docs.etherscan.io):

- **Docs pages:** [Nametags – Etherscan API](https://docs.etherscan.io/etherscan-v2/api-endpoints/nametags), [Get Metadata for an Address](https://docs.etherscan.io/api-reference/endpoint/getaddresstag)
- **URL:** `https://api.etherscan.io/v2/api?chainid=1&module=nametag&action=getaddresstag&address=0x...&apikey=YourApiKeyToken`
- **Required tier:** **Pro Plus only** — explicitly stated as "an exclusive
  endpoint for Pro Plus subscribers only."
- **Rate limit:** throttled to 2 calls/second regardless of which Pro tier
  you're on; accepts up to 100 addresses per call.
- **Parameters:** `chainid` (1=Ethereum mainnet, 42161=Arbitrum, 8453=Base,
  etc. — it's multichain), `module=nametag`, `action=getaddresstag`,
  `address` (single or comma-joined, up to 100), `apikey`.

Example JSON response (as documented):

```json
{
  "status": "1",
  "message": "OK",
  "result": [
    {
      "address": "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43",
      "nametag": "Coinbase 10",
      "internal_nametag": "",
      "url": "https://coinbase.com",
      "shortdescription": "",
      "notes_1": "",
      "notes_2": "",
      "labels": ["Coinbase", "Exchange"],
      "labels_slug": ["coinbase", "exchange"],
      "reputation": 0,
      "other_attributes": [],
      "lastupdatedtimestamp": 1721899658
    }
  ]
}
```

This is exactly the "Binance: Hot Wallet" / "Uniswap: Router"-style data the
task is asking about — `nametag` is the display name, `labels`/`labels_slug`
are the category tags (e.g. `exchange`, `nft`, `phish-hack`). But it sits
behind the **Pro Plus** subscription (see §4 pricing).

### 1c. Legacy bulk-export endpoints (also paywalled)

Two older "Metadata API" endpoints still documented under `docs.etherscan.io`
export tag data in bulk, but both are gated to the **Enterprise** tier:

- **`exportaddresstags`** — CSV export of tagged addresses filtered by
  category. `https://api-metadata.etherscan.io/v1/api.ashx?module=nametag&action=exportaddresstags&label=ofac-sanctioned&format=csv&apikey=...`
  Rate limit: 2 calls/sec, **100 calls/day max**. Columns: `address;
  nametag; internal_nametag; url; shortdescription; notes_1; notes_2; labels;
  labels_slug; reputation; other_attributes; lastupdatedtimestamp`.
  Source: [Export Address Tags (Legacy)](https://docs.etherscan.io/api-reference/endpoint/exportaddresstags) — mirrors the label taxonomy shown in the public [Label Word Cloud](https://etherscan.io/labelcloud) UI tool (also on sibling explorers: [OP Mainnet](https://optimistic.etherscan.io/labelcloud), [BscScan](https://bscscan.com/labelcloud), [BaseScan](https://basescan.org/labelcloud)).
- **`getlabelmasterlist`** — returns the taxonomy of label categories
  themselves (`labelname`, `labelslug`, `shortdescription`, `notes`,
  `lastupdatedtimestamp`), not address-to-label mappings. Also Enterprise
  tier. Source: [Get Label Master List (Legacy)](https://docs.etherscan.io/api-reference/endpoint/getlabelmasterlist)

Both are explicitly marked "Legacy" in favor of the v2 `nametag` module
described in §1b, and both require a paid/contact-for-pricing tier.

### 1d. The Label Word Cloud UI page itself

`etherscan.io/labelcloud` ("More > Tools > Label Word Cloud" in the site nav)
is a public, human-browsable page listing label categories and letting you
click through to addresses under each label. It is a website feature, not an
API — there is no documented JSON/CSV endpoint for it outside the paid
`exportaddresstags`/`getlabelmasterlist` calls above.
Source: [Public Name Tags, Labels & Public Notes – Etherscan Information Center](https://info.etherscan.com/public-name-tags-labels/) (confirms labels are curated and "the provided content does not mention API access or bulk export capabilities for public name tags and labels" in the general user-facing help docs — bulk access is only in the separate paid API docs above)

---

## 2. Practical workarounds people actually use (free tier)

Since the free API tier has no label field, the community has consistently
worked around this by either scraping the website or consuming pre-scraped
datasets:

1. **Scraping the address page's label `<div>`.** Etherscan renders the name
   tag/label directly in the HTML of `etherscan.io/address/0x...` (the
   badge/pill near the address header). Tools like
   [`Beasta/etherscan-label-scraper`](https://github.com/Beasta/etherscan-label-scraper)
   and [`octal-crypto/etherscan-labels`](https://github.com/octal-crypto/etherscan-labels)
   parse this HTML directly. Note: because Etherscan increasingly requires a
   logged-in session and bot-detection (Cloudflare) to render some pages,
   more recent scrapers such as
   [`dawsbot/eth-labels`](https://github.com/dawsbot/eth-labels) run a real
   authenticated browser session (log in with an account, then scrape), and
   [`brianleect/etherscan-labels`](https://github.com/brianleect/etherscan-labels)
   uses Selenium + `undetected-chromedriver` to avoid bot detection — its
   README candidly documents that this approach breaks whenever Etherscan
   changes its anti-bot measures (at time of check, that repo's automation
   was reported broken for this exact reason).

2. **Pre-scraped/community-maintained datasets** — these avoid you personally
   scraping, but the data still originated from scraping:
   - [`brianleect/etherscan-labels`](https://github.com/brianleect/etherscan-labels) — "Full label data dump of top EVM chains in JSON/CSV," covering Ethereum, BSC, Polygon.
   - [`dawsbot/eth-labels`](https://github.com/dawsbot/eth-labels) — public dataset, ~115k+ accounts / 54k+ tokens / 170k+ total labeled entries, with an automated login-based scraper.
   - [`dappcenter/etherscan-labels`](https://github.com/dappcenter/etherscan-labels) — CSV/JSON dataset with categories like `exchange`, `phish-hack`.
   - [`xm3van/blockchain_address_label_repository`](https://github.com/xm3van/blockchain_address_label_repository) — aggregates multiple label datasets/APIs with sample queries and utility scripts (broader than just Etherscan).
   - [`function03-labs/WalletLabels`](https://github.com/function03-labs/WalletLabels) — another open wallet-labeling project surfaced in search results.

3. **The paid Etherscan API tiers** (see §1b/1c above) — the only
   *sanctioned* programmatic route today: Pro Plus ($899/mo) for
   per-address `getaddresstag` lookups, or Enterprise (contact for pricing)
   for bulk CSV export via `exportaddresstags`/`getlabelmasterlist`.

4. **Third-party attribution vendors** outside Etherscan entirely — Nansen,
   Arkham Intelligence, Chainalysis, TRM Labs, Dune Analytics'
   community-maintained label spellbook/tables. These aren't Etherscan data
   per se but are the standard alternative when Etherscan's own labels are
   unaffordable/inaccessible. (Not deep-dived here since the task is
   specifically about Etherscan; flagging for a separate research note if
   the SIH project wants a survey of these.)

---

## 3. Terms of Service: scraping and even API-data reuse are both restricted

This matters a lot for an SIH project, because **both scraping the website
and reusing the paid API's label data for a dataset/ML project are
explicitly prohibited without Etherscan's written permission.**

### 3a. Website Terms of Service (`etherscan.io/terms`)

Quoted directly from the page:

> "Use any robot, spider, crawler, scraper or other automated means or
> interface not provided by us to access our Services or to extract data"

> "Engage in Automated Data Collection (scraping) unless such Automated Data
> Collection is confined solely to search indexing for display on the
> Internet"

> "[prohibits] reproduction of any content posted (such as public labels or
> name tags) or extracted from our APIs, CSV exports or our website ...
> without our prior consent or authorization"

> "You may not use Etherscan data whether accessed directly or indirectly
> for any AI, machine learning, automated data collection, or dataset
> creation purposes, including model training, testing, distribution, or
> commercial use, unless you have prior written permission from Etherscan."

That last clause is the one most directly relevant to SIH26182: it names
**"public labels or name tags"** specifically, and separately bars using
Etherscan data (API or web) for **dataset creation / ML training** without
written permission — which is exactly the kind of thing a "VASP attribution"
research/ML pipeline would want to do.
Source: [Etherscan Terms of Service](https://etherscan.io/terms)

### 3b. API Terms of Service (`etherscan.io/apiterms`)

Quoted directly:

> "Use of any screen-scrapers, hacks, spiders, robots, virus, worms, or any
> tool to access or attack our API Services or affiliated API Services."

> "Engage in any data mining, data scraping leading to interference with our
> website or affiliated websites" / "Send automated requested to the API in
> a manner that exceeds reasonable usage."

> "[No] redistribution, sublicensing, resale, external sharing, or onward
> provision of API Data or Output, whether in raw, processed, or
> substantially similar form" (under the "AI Use" section)

> "[Users] shall not reproduce, transmit, broadcast, publish, modify,
> display, distribute, sell, license, rent, lease or create a derivative
> form of the API Content" without express consent — limited to "personal
> use only but not for commercial use," and the doc notes restrictions
> persist "even after you stop using Etherscan's services" and that "no
> 'fair use' or similar exceptions apply."
Source: [Etherscan API Terms of Service](https://etherscan.io/apiterms)

**Implication for this project:** Even if you pay for Pro Plus and legally
call `getaddresstag`, the ToS's "AI Use" / redistribution clause appears to
restrict building and distributing a derived labeled-address dataset (e.g.
for training/evaluating a VASP-attribution model) without contacting
Etherscan for written permission first. Scraping the free website UI is even
more clearly prohibited by the general anti-scraping clause. This should be
flagged as a compliance risk to the SIH team/mentors, not silently worked
around — the safest paths are (a) use one of the already-public third-party
label datasets in §2.2, whose maintainers have separately taken on that
scraping-ToS risk (still not risk-free — those datasets' own licenses don't
erase Etherscan's ToS claims against the *original* extraction), or (b)
contact Etherscan for permission/partnership given this is a government
hackathon project, or (c) source labels from a VASP-attribution vendor whose
own ToS permits redistribution/derivative use.

---

## 4. Exact steps to extract labels programmatically today

Given everything above, here are the concrete, current options in order of
"most sanctioned" to "most legally exposed":

### Option A — Pay for Pro Plus, use `getaddresstag` (sanctioned, costs $899/mo)
1. Subscribe to the **Pro Plus** plan at `etherscan.io/apis` ($899/mo,
   billed monthly/quarterly/yearly with 10%/15% discounts; limited to one
   app license). Source: [Etherscan API pricing](https://etherscan.io/apis)
2. Generate an API key from your Etherscan account dashboard.
3. Call:
   `GET https://api.etherscan.io/v2/api?chainid=1&module=nametag&action=getaddresstag&address=<addr1,addr2,...up to 100>&apikey=<key>`
4. Parse `result[].nametag`, `result[].labels`, `result[].labels_slug` per
   address. Respect the 2 calls/sec throttle.
5. Read and comply with the ToS "AI Use" clause before persisting/
   redistributing the results as a training dataset (§3).

### Option B — Enterprise bulk export (sanctioned, contact-for-pricing)
1. Contact Etherscan for an Enterprise/Metadata plan.
2. Call `https://api-metadata.etherscan.io/v1/api.ashx?module=nametag&action=exportaddresstags&label=<category|all>&format=csv&apikey=<key>` (100 calls/day cap) to bulk-download the address→label CSV, optionally per category (use `getlabelmasterlist` first to enumerate valid category slugs).
3. Ingest CSV: columns `address; nametag; internal_nametag; url;
   shortdescription; notes_1; notes_2; labels; labels_slug; reputation;
   other_attributes; lastupdatedtimestamp`.

### Option C — Use an existing open dataset (fastest, free, some ToS ambiguity inherited from original scrape)
1. Clone/download [`brianleect/etherscan-labels`](https://github.com/brianleect/etherscan-labels) or [`dawsbot/eth-labels`](https://github.com/dawsbot/eth-labels) (JSON/CSV, MIT-licensed code, pre-scraped label data for Ethereum + other EVM chains).
2. Load the JSON/CSV directly — no scraping performed by your team, but the
   underlying data was originally obtained via scraping by the dataset
   maintainer, so document this provenance clearly in the SIH writeup and
   treat it as a known compliance caveat, not a clean-room source.
3. For freshness, periodically re-pull the dataset's repo (these are
   community-maintained, update cadence varies / some scrapers are
   reported broken at times — verify last-updated date before relying on
   it for a demo).

### Option D — Scrape the address page yourself (NOT recommended — directly against ToS)
Documented only for completeness, since the task asked for the actual
observed method: Etherscan renders the name tag as a text badge in the HTML
near the top of `etherscan.io/address/0x...`. A scraper fetches that page
(increasingly requiring a logged-in session + a real browser to defeat
Cloudflare bot detection, per `dawsbot/eth-labels`' and
`brianleect/etherscan-labels`' approach with Selenium/undetected-chromedriver)
and parses the label text out of the DOM. This directly violates the
anti-scraping clauses quoted in §3a/§3b. **Not advisable for a hackathon
project that may be evaluated/deployed under scrutiny; use Option C or
pursue Option A/B if budget/partnership allows.**

---

## Notes & confidence

- **High confidence:** the free/standard Etherscan API endpoints
  (`balance`, `txlist`, etc.) do not return any label/tag field — verified
  directly against current `docs.etherscan.io` pages.
- **High confidence:** a paid `nametag`/`getaddresstag` API now exists
  (Pro Plus tier) and legacy bulk-export endpoints (`exportaddresstags`,
  `getlabelmasterlist`, Enterprise tier) also exist — verified directly by
  fetching `docs.etherscan.io/etherscan-v2/api-endpoints/nametags` and the
  two legacy endpoint doc pages, plus Etherscan's own announcement on X.
  This is a **relatively recent addition** (the X announcement frames it as
  an "upgrade" from a prior "Metadata API"), which is why most existing
  Stack Overflow answers, GitHub issues, and blog posts from before this
  rollout still say "Etherscan has no label API" — that was true until this
  endpoint shipped, and remains effectively true for anyone not paying for
  Pro Plus/Enterprise.
- **High confidence:** the ToS quotes in §3 are accurate, pulled directly
  from `etherscan.io/terms` and `etherscan.io/apiterms` via direct fetch.
  I was not able to independently confirm the exact section numbers/headings
  those clauses live under (the fetch tool returned extracted quotes, not a
  full clause-by-clause legal document map) — before finalizing any
  compliance writeup for the SIH submission, a human should open
  `etherscan.io/terms` and `etherscan.io/apiterms` directly and confirm
  wording/section context hasn't shifted, since ToS pages change without
  notice and no version/date stamp was captured here.
- **Medium confidence:** exact current pricing ($899/mo for Pro Plus, other
  tier prices in §4) — pulled from a live fetch of `etherscan.io/apis` on
  the research date, but Etherscan pricing has changed multiple times
  historically and should be reconfirmed close to any procurement decision.
- **Medium confidence:** GitHub Issues / Stack Overflow discussion — I was
  not able to pull an exact, citable GitHub Issue thread number or Stack
  Overflow question URL specifically debating "labels not in API" (search
  results surfaced repos and a summarized community consensus rather than
  one canonical thread). The workaround repos in §2 (their READMEs and code)
  are themselves the strongest primary evidence that this was a real,
  commonly-hit limitation prior to the Pro Plus endpoint's existence.
- **Not verified / out of scope here:** whether Etherscan would actually
  grant "prior written permission" to a student hackathon team for
  ML/dataset use under the AI Use clause — this would need direct outreach
  to Etherscan, not something a web search can answer.
