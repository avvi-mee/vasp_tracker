# Block Explorer APIs — Etherscan, BscScan, Tronscan, Blockchair

Research notes for SIH26182 (automated attribution of unknown crypto wallets to nearest VASPs).
Compiled 2026-09-14 from live fetches of official documentation (not from training-data memory — see inline citations).

**Headline finding that affects this whole document:** in the last ~10 months both Etherscan and BscScan have undergone
major structural changes. BscScan's own API is **deprecated** and merged into a unified "Etherscan API V2". Etherscan's
free tier has also been **cut down** — BNB Chain (the chain BscScan serves) is one of the chains explicitly **removed
from the free tier**. This is detailed under the BscScan section below; it is the single most important thing to
account for when planning free-tier ingestion for this project.

---

## Etherscan

**Base URL (current, V2, unified/multichain):** `https://api.etherscan.io/v2/api`
V1 endpoints (`api.etherscan.io/api`) were deprecated after 15 Aug 2025 / final cutoff around 31 May 2025 messaging campaign; all requests should use V2 with an explicit `chainid` parameter.
Source: https://docs.etherscan.io/v2-migration , https://info.etherscan.com/switch-to-etherscan-api-v2-by-may-31-2025/

### Free tier rate limits
- **3 calls/second**, **up to 100,000 calls/day**, on **selected chains only** (~90% of the 60+ supported chain IDs — see coverage note below).
- Paid tiers exist above this: Lite ($49/mo, 5 calls/sec, 100k/day, full chain coverage), Standard ($199/mo, 10 calls/sec, 200k/day), Advanced (20/sec, 500k/day), Professional (30/sec, 1M/day), Pro Plus (30/sec, 1.5M/day).
Source: https://docs.etherscan.io/resources/rate-limits , https://etherscan.io/apis

### Free-tier chain coverage change (important, recent)
Effective **22 November 2025**, Etherscan reduced free-tier chain coverage from "all chains" to "selected chains" (~90%). Confirmed **paid-only chains** (no free access at all, any endpoint that isn't contract-verification related): **BNB Smart Chain (chain ID 56), Base, Optimism (OP Mainnet), Avalanche** — and their testnets. Ethereum mainnet (chain ID 1), Polygon, Arbitrum, Linea, Blast, and most others remain free.
Exception: verified-contract endpoints (source code, ABI, verification status) stay free on **all** chains including BNB/Base/Avalanche/Optimism.
Sources: https://info.etherscan.com/whats-changing-in-the-free-api-tier-coverage-and-why/ , https://docs.etherscan.io/supported-chains , https://www.ccn.com/news/technology/etherscan-cuts-free-access-block-explorers-struggle/

### Authentication
- Query parameter `apikey` on every request. A key is **required** (unauthenticated requests are not served).
- Free key: sign up at https://etherscan.io/myapikey ("Start for Free" self-checkout flow described on the pricing page). No cost, no credit card for the Free tier.
Source: https://etherscan.io/apis

### Endpoint: Get all normal transactions for an address
- **Method:** GET
- **URL:** `https://api.etherscan.io/v2/api`
- **Required params:** `chainid` (e.g. `1` for Ethereum), `module=account`, `action=txlist`, `address`, `apikey`
- **Optional params:** `startblock` (default 0), `endblock` (default 999999999), `page` (default 1), `offset` (records/page, default 100), `sort` (`asc`/`desc`)

Separate endpoints exist for other transaction types on the same address (all under `module=account`, same base URL/params pattern, swap `action`):
- `action=tokentx` — ERC-20 token transfer events (requires `address` and/or `contractaddress`)
- `action=tokennfttx` — ERC-721 (NFT) transfers (not fetched in detail here, same shape)
- `action=token1155tx` — ERC-1155 transfers (not fetched in detail here, same shape)
- `action=txlistinternal` — internal transactions (contract-to-contract/EOA transfers triggered by a contract call)

Source: https://docs.etherscan.io/api-reference/endpoint/txlist , https://docs.etherscan.io/api-reference/endpoint/tokentx , https://docs.etherscan.io/api-reference/endpoint/txlistinternal

#### Response schema — `txlist` (normal transactions)
Top level: `status` ("1"=success, "0"=error/no records), `message` ("OK" or error string), `result` (array of tx objects).

Each transaction object:
| Field | Meaning |
|---|---|
| `blockNumber` | Block the tx was mined in |
| `blockHash` | Hash of that block |
| `timeStamp` | Unix timestamp the block was mined |
| `hash` | Transaction hash |
| `nonce` | Sender's tx count before this tx |
| `transactionIndex` | Position of tx within the block |
| `from` | Sender address |
| `to` | Recipient address |
| `value` | Amount transferred, in wei |
| `gas` | Gas limit supplied |
| `gasPrice` | Gas price paid, in wei |
| `input` | Raw input data (hex) |
| `methodId` | First 4 bytes of input (function selector) |
| `functionName` | Decoded function signature, if known |
| `contractAddress` | Address of contract created (empty if not a contract-creation tx) |
| `cumulativeGasUsed` | Total gas used in the block up to and including this tx |
| `txreceipt_status` | "1" success / "0" failed (only meaningful post-Byzantium) |
| `gasUsed` | Actual gas consumed |
| `confirmations` | Blocks mined since this tx |
| `isError` | "0" success, "1" error |

#### Example request
```
GET https://api.etherscan.io/v2/api?chainid=1&module=account&action=txlist&address=0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC&startblock=0&endblock=99999999&page=1&offset=100&sort=asc&apikey=YOUR_API_KEY
```

#### Example response (fields from official schema; values illustrative)
```json
{
  "status": "1",
  "message": "OK",
  "result": [
    {
      "blockNumber": "21050000",
      "blockHash": "0x8a3c...ff21",
      "timeStamp": "1732012345",
      "hash": "0x5c9e...aa11",
      "nonce": "42",
      "transactionIndex": "88",
      "from": "0xc5102fe9359fd9a28f877a67e36b0f050d81a3cc",
      "to": "0x28c6c06298d514db089934071355e5743bf21d60",
      "value": "250000000000000000",
      "gas": "21000",
      "gasPrice": "18000000000",
      "input": "0x",
      "methodId": "0x",
      "functionName": "",
      "contractAddress": "",
      "cumulativeGasUsed": "9123456",
      "txreceipt_status": "1",
      "gasUsed": "21000",
      "confirmations": "18213",
      "isError": "0"
    }
  ]
}
```

#### `tokentx` (ERC-20 transfers) — additional/changed fields vs. `txlist`
Adds `tokenName`, `tokenSymbol`, `tokenDecimal` (and keeps `contractAddress` as the *token contract*, not a created-contract address); drops `txreceipt_status`.
Example request:
```
GET https://api.etherscan.io/v2/api?chainid=1&module=account&action=tokentx&address=0x4e83362442b8d1bec281594cea3050c8eb01311c&page=1&offset=100&sort=desc&apikey=YOUR_API_KEY
```
Source: https://docs.etherscan.io/api-reference/endpoint/tokentx

#### `txlistinternal` (internal transactions) — fields
`blockNumber`, `timeStamp`, `hash`, `from`, `to`, `value`, `contractAddress`, `input`, `type` (`call`/`create`/`create2`/`selfdestruct`), `gas`, `gasUsed`, `traceId`, `isError`, `errCode`.
Source: https://docs.etherscan.io/api-reference/endpoint/txlistinternal

---

## BscScan

**Critical status change:** BNB Chain officially announced (blog dated 9 Dec 2025) that the classic **BscScan API is deprecated** — traffic is redirected to the unified **Etherscan API V2** (`https://api.etherscan.io/v2/api`, same shape as the Etherscan section above, with `chainid=56` for BNB Smart Chain mainnet / `chainid=97` for testnet). There is **no separate BscScan API surface to document anymore** — it is Etherscan V2 with a different chain ID.
Source: https://www.bnbchain.org/en/blog/migration-guide-bscscan-api-to-bsctrace-api-via-meganode

**However — this chain has no Etherscan free tier at all.** Per Etherscan's own supported-chains documentation, BNB Smart Chain (chain ID 56) is now **paid-plan-only** (Lite plan or above, $49/mo minimum) for all data endpoints; only contract-verification endpoints (source/ABI) stay free.
Source: https://docs.etherscan.io/supported-chains

**Recommended free alternative:** BNB Chain is directing developers toward **BSCTrace**, a NodeReal/MegaNode-powered explorer API, which does offer a free tier for BSC. Exact free-tier rate limits for BSCTrace were **not found in any document/page I could fetch** (see Notes & confidence) — only that a free tier "for small projects" exists, with one paid tier above it.
Source: https://www.bnbchain.org/en/blog/migration-guide-bscscan-api-to-bsctrace-api-via-meganode , https://nodereal.io/blog/en/bsctrace-a-new-blockchain-explorer-on-bnb-chain-powered-by-nodereal-meganode/

### Endpoint (via Etherscan V2, chainid=56) — Get all normal transactions for a BSC address
Identical shape to the Etherscan `txlist` endpoint documented above, with `chainid=56` substituted.

- **Method:** GET
- **URL:** `https://api.etherscan.io/v2/api`
- **Required params:** `chainid=56`, `module=account`, `action=txlist`, `address`, `apikey` (must be on a paid Etherscan plan to get data back for this chain)
- **Optional params:** same as Etherscan — `startblock`, `endblock`, `page`, `offset`, `sort`
- Token transfers: `action=tokentx` (BEP-20); internal txns: `action=txlistinternal` — same param/response shape as Ethereum.

#### Example request
```
GET https://api.etherscan.io/v2/api?chainid=56&module=account&action=txlist&address=0x8894e0a0c962cb723c1976a4421c95949be2d4e3&page=1&offset=100&sort=asc&apikey=YOUR_API_KEY
```
(This is the documented pattern; on a Free-tier key it is expected to return an error/empty result because BSC data now requires a paid plan — see above.)

#### Response schema
Same field list as Etherscan `txlist` (see table above) — Etherscan V2 uses one unified schema across all EVM chains it serves.

### Legacy/historical reference (deprecated, do not build against this)
Prior to the merge, BscScan's own docs (`docs.bscscan.com`) described a standalone API at base URL `https://api.bscscan.com/api` with the same `module=account&action=txlist&address=...&apikey=...` pattern and a **5 calls/sec** free-tier limit (per-IP, valid key). This is now defunct/redirected; documented here only so it's recognizable if encountered in older code samples or tutorials.
Source: https://info.bscscan.com/apis/ , https://bscscan.freshdesk.com/support/solutions/articles/67000662530-api-key-rate-limit-errors

---

## Tronscan

**Base URL:** `https://apilist.tronscanapi.com` (documentation also references the older host `apilist.tronscan.org`, which appears to still resolve/alias to the same service).
Source: https://github.com/tronscan/tronscan-frontend/blob/master/document/api.md

### Free tier rate limits / authentication
Tronscan has been progressively tightening unauthenticated access:
- Unauthenticated requests were throttled down over time: 20 req/sec → 10 req/sec (10 Jul 2023) → 5 req/sec (17 Jul 2023) → **3 req/sec** (3 Aug 2023), and since **31 Aug 2025** Tronscan **no longer guarantees any fixed QPS** for requests made without a valid API key (i.e., an API key is effectively mandatory now for reliable access).
- **Authentication:** HTTP header `TRON-PRO-API-KEY: <your_api_key>` on every request.
- **Obtaining a key (free):** log in at tronscan.org → Account → API Keys (`https://tronscan.org/#/myaccount/apiKeys/`) → "Add" → name the application → copy the generated key. No price/paid-tier information was found in the sources I could access — the key itself appears to be free to generate, though the exact authenticated-tier QPS ceiling was **not stated** in any document I could reach (flagged below).
Sources: https://support.tronscan.org/hc/en-us/articles/20506296714521-Announcement-on-without-an-API-key-access-frequency-limitations , https://support.tronscan.org/hc/en-us/articles/49272903085465-Follow-up-Announcement-on-the-Mandatory-Requirement-of-API-Key-for-All-Requests

**Independently confirmed live:** while researching this, unauthenticated calls to the live API were rate-limited by the server, returning:
```json
{"Error":"request rate exceeded the allowed_rps(3), and the query server is suspended for 68 s. To obtain higher request quotas and a more stable service, it is recommended to authenticate with an API Key. Please refer to the documentation: https://docs.tronscan.org/#get-an-api-key"}
```
This confirms the documented **3 requests/sec unauthenticated cap** first-hand (this is a real captured response, not from docs).

### Endpoint: Get all transactions for an address
- **Method:** GET
- **URL:** `https://apilist.tronscanapi.com/api/transaction`
- **Required params:** `address` (the account to query)
- **Optional params:** `sort` (e.g. `-timestamp` for newest-first), `limit` (page size), `start` (offset), `count` (`true`/`false` — whether to return a total record count), `start_timestamp` / `end_timestamp` (date-range filter)
- Constraint: `start + limit` must be ≤ 10,000 (deep pagination beyond that is not supported); the endpoint documentation itself also states it only surfaces "the latest 2,000 data records in the query time range."

Separate endpoints exist for other transfer types on the same address (per the Tronscan docs site navigation — I could not fetch full parameter tables for these due to the 403s described in Notes & confidence, so only names/paths are listed):
- **TRC20 & TRC721 token transfers** — "Get TRC20 & TRC721 Transfer List"
- **TRC1155 transfers** — "Get TRC1155 Transfer List"
- **TRX & TRC10 transfers** — "Get TRX & TRC10 Transfer List" (likely under `/api/transfer/trx` per one secondary source, not independently confirmed)
- **Internal transactions** — "Get Internal Transaction List"
Source (endpoint names/nav only): https://docs.tronscan.org/api-endpoints/transactions-and-transfers

#### Example request
```
GET https://apilist.tronscanapi.com/api/transaction?sort=-timestamp&count=true&limit=20&start=0&address=TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9
Header: TRON-PRO-API-KEY: YOUR_API_KEY
```
Source: https://github.com/tronscan/tronscan-frontend/blob/master/document/api.md

#### Response schema
I was **not able to retrieve one clean, complete official field table** for this endpoint (see Notes & confidence — docs.tronscan.org blocked automated fetching, and the live API rate-limited every retry). The field list below is reconstructed **only from field names actually attested** across the GitHub-hosted community docs mirror and search-indexed snippets of the official docs — no field name here is invented, but the list should be treated as **incomplete**, and exact nesting (e.g., whether fields live in a `data[]` array under a `total`/`rangeTotal` wrapper) should be verified against a live authenticated call before coding against it.

| Field (attested) | Meaning |
|---|---|
| `hash` | Transaction ID |
| `block` | Block number |
| `timestamp` | Unix ms timestamp |
| `ownerAddress` | Sender (initiator) address |
| `toAddress` | Recipient address |
| `contractType` | Numeric contract-type enum (e.g. `1` = TransferContract) |
| `contractData` | Raw contract call payload/params |
| `contractRet` | Execution result string, e.g. `"SUCCESS"` |
| `confirmed` | Boolean — whether the tx is confirmed |
| `confirmations` | Number of confirmations |
| `revert` | Boolean — whether the tx was reverted |
| `amount` | Transferred amount (in SUN for TRX) |
| `cost` | Object with fee/energy/bandwidth cost breakdown (sub-fields not confirmed) |
| `result` | Execution result (may duplicate/overlap with `contractRet`) |

#### Example response (constructed strictly from the attested field names above — NOT copy-pasted from a fetched page, since I could not retrieve one; treat as best-effort, not verbatim)
```json
{
  "total": 1,
  "rangeTotal": 4821,
  "data": [
    {
      "hash": "3e2a...c91f",
      "block": 63920115,
      "timestamp": 1757845200000,
      "ownerAddress": "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9",
      "toAddress": "TXYZ1234567890abcdefghijklmnopqrstu",
      "contractType": 1,
      "contractData": { "amount": 5000000, "owner_address": "...", "to_address": "..." },
      "contractRet": "SUCCESS",
      "confirmed": true,
      "confirmations": 210,
      "revert": false,
      "amount": 5000000,
      "cost": { "fee": 1100000, "energy_usage": 0, "net_usage": 268 },
      "result": "SUCCESS"
    }
  ]
}
```

---

## Blockchair

**Base URL:** `https://api.blockchair.com`
Source: https://raw.githubusercontent.com/Blockchair/Blockchair.Support/master/API.md (mirror of https://blockchair.com/api/docs, which blocked automated fetching — see Notes & confidence)

### Free tier rate limits
- **Soft limit: 30 requests/minute** for occasional/no-key use (this is a "soft" limit only strictly enforced under high server load).
- A secondary figure of **1,000 calls/day** for the no-key/testing tier was found via web search of third-party summaries of Blockchair's pricing page, but I could **not independently confirm this exact number against the primary `blockchair.com/api/plans` page**, which returned HTTP 401 to every fetch attempt (see Notes & confidence).
- Exceeding limits or sending too many resource-heavy requests can get an IP **banned for the request** (`HTTP 430`) or **banned for one hour** (`HTTP 429`, after repeatedly hitting `402`). With an API key, exceeding the max-parallel-requests limit returns `HTTP 435`.
Source: https://raw.githubusercontent.com/Blockchair/Blockchair.Support/master/API.md

### Authentication
- Query parameter `key`. **Not required** for light/occasional use (works without a key up to the soft limits above), but the docs state a key has been required "for all applications" using the API in production since **19 July 2019** — in practice, treat it as optional-but-strongly-recommended for anything beyond ad-hoc testing.
- The docs explicitly warn the key is a secret and should never be exposed in client-side code.
Source: https://raw.githubusercontent.com/Blockchair/Blockchair.Support/master/API.md

### Endpoint: Get all transactions for an address
- **Method:** GET
- **URL pattern:** `https://api.blockchair.com/{chain}/dashboards/address/{address}` — this is the generic "dashboards" endpoint, valid for both UTXO chains (Bitcoin, Litecoin, Dogecoin, Bitcoin Cash, Dash, Zcash, Bitcoin SV, Groestlcoin, ...) and Ethereum (`{chain}` = `bitcoin`, `ethereum`, etc.). This is the one endpoint documented for "all transactions of an address" — Blockchair does not split normal/internal/token transfers into separate top-level endpoints the way Etherscan does; token-transfer data for Ethereum is instead pulled in via query parameters on this same endpoint.
- **Key optional params:**
  - `limit` — transactions to return (default 100, max 10,000)
  - `offset` — pagination offset
  - `transaction_details=true` — return full transaction objects instead of just hashes in the `transactions` array (costs more — noted as an extra request in the cost/quota accounting)
  - `state=latest` — only confirmed data, excludes mempool/unconfirmed
  - `erc_20=<comma-separated token addresses>` — (Ethereum only) include ERC-20 token balance/detail data for the address
  - `contract_details=true` — extra data if the address is itself a contract (for ERC-20 contracts: `token_name`, `token_symbol`, `token_decimals`)
  - `assets_in_usd=true` — adds USD-denominated balance fields
Source: https://raw.githubusercontent.com/Blockchair/Blockchair.Support/master/API.md , https://github.com/Blockchair/Blockchair.Support/issues/1482 (search-indexed snippet)

#### Response schema
| Field | Meaning |
|---|---|
| `data.<address>.address.type` | Address type classification |
| `data.<address>.address.balance` | Confirmed balance, smallest unit (satoshi/wei) |
| `data.<address>.address.balance_usd` | Balance in USD |
| `data.<address>.address.received` | Total received, smallest unit |
| `data.<address>.address.spent` | Total spent, smallest unit |
| `data.<address>.address.transaction_count` | Total number of transactions |
| `data.<address>.transactions[]` | Array of transaction hashes (or full tx objects if `transaction_details=true`) |
| `data.<address>.utxo[]` | Unspent outputs (UTXO chains only): `block_id`, `transaction_hash`, `index`, `value` |
| `data.<address>.layer_2.erc_20[]` | (Ethereum, with `erc_20=` param) token balances: `token_address`, `token_name`, `token_symbol`, `token_decimals`, `balance`, `balance_approximate`, (`balance_usd` if `assets_in_usd=true`) |
| `context.api.version` | API version string |
| `context.state` | Latest indexed block height |
| `context.market_price_usd` | Current market price of the chain's native asset, in USD |

When `transaction_details=true`, each transaction object (documented explicitly only for UTXO/Bitcoin-like chains) additionally carries: `hash`, `time` (UTC timestamp), `balance_change` (net effect on the queried address's balance).

#### Example request
```
GET https://api.blockchair.com/ethereum/dashboards/address/0xe5369978e3d65f2f823a3e564310a7e01b0b46f1?transaction_details=true&limit=100&key=YOUR_API_KEY
```

#### Example response (abbreviated; Bitcoin shown per the schema fields the docs give a worked example for)
```json
{
  "data": {
    "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa": {
      "address": {
        "type": "pubkeyhash",
        "balance": 66995308,
        "balance_usd": 41234.12,
        "received": 66995308,
        "spent": 0,
        "transaction_count": 4
      },
      "transactions": [
        { "hash": "0f5a...b210", "time": "2011-01-13 07:34:33", "balance_change": 5000000 },
        { "hash": "4c2e...ff91", "time": "2011-01-13 08:01:12", "balance_change": -1000000 }
      ],
      "utxo": [
        { "block_id": 123456, "transaction_hash": "0f5a...b210", "index": 0, "value": 66995308 }
      ]
    }
  },
  "context": {
    "code": 200,
    "api": { "version": "2.0.95" },
    "state": 773456,
    "market_price_usd": 42500.00
  }
}
```

---

## Notes & confidence

**High confidence (verified against primary/official docs, current):**
- Etherscan `txlist` / `tokentx` / `txlistinternal` endpoint shapes and field lists — pulled directly from `docs.etherscan.io` pages, which rendered fully.
- Etherscan free-tier numbers (3 calls/sec, 100k/day) and the tiered pricing table — corroborated across two independent official-domain pages.
- The BscScan → Etherscan V2 deprecation, and the fact that **BNB Chain has no Etherscan free tier** — corroborated by three independent sources (BNB Chain's own blog, Etherscan's own supported-chains doc, and press coverage). This is the most load-bearing finding for the project's design and I'm confident in it.
- Blockchair base URL, `key` param, `dashboards/address` endpoint, its optional params, and the 30 req/min soft limit / error codes — from a community-maintained GitHub mirror of Blockchair's own docs (`Blockchair/Blockchair.Support`), which explicitly presents itself as tracking the official docs.
- Tronscan's 3 req/sec unauthenticated cap — confirmed **twice**: once via official Tronscan support-center announcements, and once by a live captured 429 response from the actual API during this research session.

**Medium confidence / partially verified — flagged, double-check before building:**
- **Tronscan response schema**: I could not load `docs.tronscan.org` directly (every direct fetch returned HTTP 403, including via a Jina reader proxy and `.md`-suffix raw attempts) and could not get a clean live JSON sample either (every attempt hit the 3 req/sec limit and the retry-after window kept growing rather than shrinking, suggesting the limit may be shared across many users of this network egress, not just my own calls). The field table in the Tronscan section is reconstructed from search-engine-indexed snippets of the real docs plus a GitHub-hosted community mirror (`tronscan/tronscan-frontend`) — every field name shown was attested somewhere, but the list is likely **incomplete**, and I could not confirm the exact response envelope (`total`/`rangeTotal`/`data` wrapper) firsthand. Treat the Tronscan example JSON as illustrative, not verbatim.
- **Blockchair exact free-tier daily cap**: the 30 req/min soft limit is solidly sourced; the "1,000 calls/day" figure came only from third-party secondary sources summarizing Blockchair's pricing page, since `blockchair.com/api/docs` and `/api/plans` both returned HTTP 401 to every fetch attempt (direct and via proxy). Recommend re-verifying directly against `blockchair.com/api/plans` in a normal browser before relying on this number.
- **BSCTrace (the recommended free BSC alternative) exact rate limits**: could not find a published number anywhere; only "a free tier exists." If the project actually plans to ingest BSC data for free, this needs direct investigation (sign up and read the dashboard/docs) rather than relying on this file.
- **Etherscan "10,000 → 1,000 max records per call for Free tier, effective 1 July 2026"**: this appeared in one AI-generated search-result summary only; I could not independently confirm it against a primary Etherscan page. Given today's date (14 Sep 2026) this would already be in effect if true — worth a direct check against `docs.etherscan.io/api-reference/endpoint/txlist` for the current `offset` param max before writing ingestion code that assumes a 10,000-row page size.

**Outdated info encountered (do not use):** the legacy BscScan-specific docs (`docs.bscscan.com`, `api.bscscan.com`) still exist/rank in search results describing a standalone 5-calls/sec free API — this is superseded by the BscScan-deprecation/Etherscan-V2-merge described above and should not be used as the basis for new integration work, even though older tutorials and StackOverflow answers still reference it.

**Conflicting information across sources:** one search-engine AI summary claimed "Etherscan free tier is 5 req/sec and BNB/Base/Arbitrum are all included," which directly contradicts the primary-source rate-limit table (3 req/sec) and the primary-source supported-chains page (BNB Chain excluded from free tier). That summary appears to reflect stale/cached pre-November-2025 information. I trusted the two official `docs.etherscan.io` / `info.etherscan.com` pages over it, since they were dated to the actual policy-change announcement and are the primary source.
