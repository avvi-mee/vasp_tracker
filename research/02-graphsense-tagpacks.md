# GraphSense / Iknaio TagPacks — Research Notes

Research for SIH26182 (automated attribution of unknown crypto wallets to nearest VASPs). Compiled 2026-09-14 by live-fetching the actual GitHub repos and API docs (not from memory).

## Repo URL(s) — which one actually holds the tag data

The **tag data itself** (the YAML files mapping addresses to labels/entities) lives in one repo:

- **https://github.com/graphsense/graphsense-tagpacks** — "A collection of public TagPacks." This is the repo to clone/pull for actual attribution data. Created 2019-05-08, still receiving commits as of 2026-09-11 (see [Maintenance activity](#maintenance-activity--last-checked-2026-09-14)). [github.com/graphsense/graphsense-tagpacks](https://github.com/graphsense/graphsense-tagpacks)

Related repos (tooling, not data — confirmed by fetching each):

- **https://github.com/graphsense/graphsense-tagpack-tool** — the CLI that used to validate TagPacks against schemas, ingest them into a Postgres "TagStore," compute quality metrics, and serve a REST API for tag lookups. **Archived/read-only as of 2025-09-04**; its functionality moved into `graphsense-lib`. [source](https://github.com/graphsense/graphsense-tagpack-tool)
- **https://github.com/graphsense/graphsense-lib** — the current, actively maintained "core" repo. It absorbed the tagpack-tool: README documents "Validate tagpacks," "Insert tagpack into tagstore," "Show quality measures," "Initialize tagstore database" as CLI subcommands, plus a REST interface used by the GraphSense dashboard frontend. This is now the tool you'd use to validate/ingest TagPacks, but it does **not** itself contain the tag data. [source](https://github.com/graphsense/graphsense-lib)
- **https://github.com/graphsense** (org) and **https://github.com/iknaio** (org) — Iknaio Cryptoasset Analytics GmbH is the company (spun out of AIT Austrian Institute of Technology) that maintains GraphSense and hosts the public API. [github.com/graphsense](https://github.com/graphsense), [github.com/iknaio](https://github.com/iknaio)
- **https://github.com/graphsense/graphsense-python** — Python client for the hosted REST API, auto-generated from the OpenAPI spec. **Archived 2025-09-05**; notice points to `graphsense-rest/client/python`.
- **https://github.com/graphsense/graphsense-rest** — Flask/Cassandra REST service consumed by the (older) graphsense-dashboard. Its own README states it is now **retired/archived (2026-02-18)**, folded into the `graphsense-lib` stack. Note: this is a *different* REST service than the hosted `api.ikna.io` product described below — it was for self-hosted GraphSense deployments.

**Bottom line for this project:** clone `graphsense/graphsense-tagpacks` for the raw attribution data; treat `graphsense-lib` as the current (if you need to validate/ingest) tooling; don't bother with `graphsense-tagpack-tool`, `graphsense-python`, or `graphsense-rest` — all three are archived.

## Repo structure

Fetched directly via the GitHub API (`api.github.com/repos/graphsense/graphsense-tagpacks/contents/...`) on 2026-09-14:

Top level:
```
.github/        - CI workflows (a "Validate TagPacks" GitHub Actions workflow runs on PRs)
actors/         - ActorPack(s): metadata about real-world entities (exchanges, services)
packs/          - the TagPacks themselves (77+ files at top level, 1 subfolder: defi_updated)
CHANGELOG.md
CITATION.cff    - citation metadata (this is citable as a dataset)
LICENSE         - MIT
README.md
```

`packs/` is **mostly a flat list of YAML files named by source or topic**, not strictly one-folder-per-contributor. Examples actually present (from the API listing): `binance.yaml`, `binance_hack.yaml`, `blender_io.yaml`, `demo.yaml`, `electrum_phishing.yaml`, `etherscamdb_tagpack.yaml`, `etherscan-wordcloud-exchange.yaml`, `eosio-gambling_part1.yaml` … `part9.yaml`, `ransomware.yaml`, `lazarus.yaml`, `tornado_cash.yaml`, `hydra.yaml`, `ofac.yaml`, `ponzi_scheme.yaml`, `exchange-wallets-binance.yaml`, `exchange-wallets-bitmex_0.yaml` … `_6.yaml`, and many more. One subfolder, `defi_updated/`, groups a related batch. The README states the convention explicitly: large datasets should be split into multiple files, and *related* TagPacks can be grouped into subfolders (it gives `packs/walletexplorer_exchanges` as the documented example), but in practice most packs sit as individual flat files named after the exchange/incident/list they came from. [raw README](https://raw.githubusercontent.com/graphsense/graphsense-tagpacks/master/README.md)

`actors/` currently contains a single file, `graphsense.actorpack.yaml`, holding many actor entries (exchanges, DeFi protocols, etc.) in one ActorPack.

## License

**MIT License** (SPDX id `MIT`, confirmed via the GitHub API `license.spdx_id` field and by fetching the raw `LICENSE` file). Copyright holders per the LICENSE file: **Iknaio Cryptoasset Analytics GmbH (2022)** and **AIT Austrian Institute of Technology (2018–2022)**. [LICENSE](https://raw.githubusercontent.com/graphsense/graphsense-tagpacks/master/LICENSE)

This is permissive — safe to use/redistribute/modify the tag data for the hackathon project with attribution, no copyleft concerns.

## File format and schema

**YAML.** Each TagPack file has a header (shared metadata, inheritable by every tag in the file) and a `tags:` list. A field set on the header is inherited by every tag unless a tag overrides it.

Fields observed/documented (mandatory ones must be present either on the header or per-tag):

| Field | Mandatory | Meaning |
|---|---|---|
| `title` | header only | Name of the TagPack |
| `creator` | header only | Who produced it |
| `lastmod` | no | Last-modified date |
| `address` | yes (per tag) | The blockchain address being tagged |
| `label` | yes | Human-readable entity name (e.g. "Internet Archive") |
| `source` | yes | Dereferenceable link/citation for where the attribution came from |
| `currency` | yes | Asset ticker (BTC, ETH, BCH, XRP, ZEC, …) |
| `category` | no | Entity type (e.g. `organization`, `exchange`, `defi_dex`) |
| `abuse` | no | Abuse-type taxonomy value (e.g. scam, ransomware) — used for illicit-address tags |
| `confidence` | no | Trust level of the tag (e.g. `service_data`, ownership vs. forensic-inferred) |
| `context` | no | Free-form extra metadata |
| `is_cluster_definer` | no | Boolean — whether the tag should propagate to the whole address cluster/entity, not just this one address |
| `actor` | no | Links the tag to an entry in an ActorPack (see below) |

Tags are de-duplicated/identified by the combination of `address` + `label` + `source`.

**Real example** — the actual, full content of `packs/demo.yaml`, fetched verbatim:

```yaml
title: GraphSense Demo TagPack
creator: GraphSense Core Team
confidence: service_data
is_cluster_definer: true
description: A collection of tags commonly used for demonstrating GraphSense features
category: organization
label: Internet Archive
lastmod: 2021-11-12
source: https://archive.org/donate/cryptocurrency
actor: internet_archive
tags:
- address: 1Archive1n2C579dMsAu3iC6tWzuQJz8dN
  currency: BTC
- address: 1K1rgZ1dz9w7dsR1HGS1drmzfUHMtqx1Tc
  currency: BCH
- address: '0xFA8E3920daF271daB92Be9B87d9998DDd94FEF08'
  currency: ETH
- address: rGeyCsqc6vKXuyTGF39WJxmTRemoV3c97h
  currency: XRP
- address: t1ZmpK4QFcvyQZ3ghTgSboBW8b4HgiZHQF9
  currency: ZEC
```
Source: [raw.githubusercontent.com/.../packs/demo.yaml](https://raw.githubusercontent.com/graphsense/graphsense-tagpacks/master/packs/demo.yaml)

Note how `label`, `currency`, `category`, `source`, `confidence`, `is_cluster_definer` are all set once at the header level and only `address`/`currency` are given per tag — this "header inheritance, per-tag override" pattern is used throughout `packs/`.

**ActorPack schema** (companion format, for entities rather than individual tags) — opening lines of `actors/graphsense.actorpack.yaml`:

```yaml
%YAML 1.1
---
title: Graphsense Actors
creator: Graphsense Core Team
description: A curated list of cryptocurrency actors.
lastmod: '2023-02-17'
actors:
- id: '01'
  label: '01'
  jurisdictions: []
  categories:
  - defi_dex
  uri: 01.xyz
  context:
    defilama_ids:
    - '01'
    refs:
    - api.llama.fi/protocol/01
    images:
    - icons.llama.fi/01.jpg
    twitter_handle: 01_exchange
```
Source: [raw.githubusercontent.com/.../actors/graphsense.actorpack.yaml](https://raw.githubusercontent.com/graphsense/graphsense-tagpacks/master/actors/graphsense.actorpack.yaml)

Fields: `id`, `label`, `jurisdictions` (ISO country codes), `categories` (taxonomy, e.g. `defi_dex`, `exchange`, `mining_service`), `uri`, `context` (arbitrary nested metadata — external IDs, refs, images, social handles), and `aliases` (alternate names).

**Contribution criteria** (from the README, quoted): tags must (1) contain **no personally identifiable information (PII)**, (2) originate from **public sources**, and (3) provide **a dereferenceable pointer (link) to the source**. All submitted TagPacks must pass schema validation (originally via `graphsense-tagpack-tool`, now via `graphsense-lib`) before merge. [raw README](https://raw.githubusercontent.com/graphsense/graphsense-tagpacks/master/README.md)

## How to query or download

Two very different access paths — pick based on what the hackathon project needs:

**1. Bulk download of raw tag data (no auth needed):**
- `git clone https://github.com/graphsense/graphsense-tagpacks.git` — gets every YAML file. This is almost certainly what SIH26182 wants: a static, offline dataset of address→label mappings to build the "nearest VASP" attribution logic against.
- Alternatively, fetch individual files directly, e.g. `https://raw.githubusercontent.com/graphsense/graphsense-tagpacks/master/packs/<file>.yaml` — no authentication required, it's a public repo.
- To validate/parse/ingest at scale, `graphsense-lib` (pip-installable, MIT) provides the CLI (`pip install graphsense-lib` per its docs) with subcommands to validate TagPacks against the schema and load them into a Postgres "TagStore." [github.com/graphsense/graphsense-lib](https://github.com/graphsense/graphsense-lib)

**2. Querying a hosted, already-ingested instance by address (needs an API key):**
- Iknaio runs a public GraphSense REST API at **https://api.ikna.io**, with interactive/ReDoc docs at **https://api.ikna.io/docs** and a "try it" Swagger UI at `/ui`. It exposes addresses, entities/clusters, transactions, blocks, and **tags** across multiple ledgers (BTC, ETH, and others), so you can query "what tags exist for address X" directly rather than parsing YAML yourself. [api.ikna.io/docs](https://api.ikna.io/docs)
- **Access requires a free API key** obtained by emailing Iknaio. The `iknaio-api-tutorial` repo (which has example Jupyter notebooks demonstrating `lookup_address`, `tags_for()`, bulk queries, and path search) says: *"You need an API key provided by Iknaio. If you would like to get an API key, drop an email to contact@iknaio.com."* [github.com/iknaio/iknaio-api-tutorial](https://github.com/iknaio/iknaio-api-tutorial) — a separate search result instead gave `contact@graphsense.org` as the contact address for API-key requests; see the Notes section below, this is unresolved.
- The formerly-recommended Python client (`graphsense-python`) is archived; the API is otherwise plain REST/OpenAPI, so it can be queried with plain `requests`/`curl` plus the `api_key` header once you have a key.

For a hackathon on a deadline, **path 1 (git clone the tagpacks repo) is almost certainly the right approach** — it needs no key, no approval wait, and gives you the full dataset to build your own "nearest VASP" matching against, rather than depending on a third-party API's rate limits/availability during a demo.

## Maintenance activity (last checked 2026-09-14)

Checked directly via the GitHub REST API (`api.github.com/repos/...`), not scraped guesses:

**graphsense-tagpacks** (the data repo):
- Created: 2019-05-08
- Last push: **2026-09-11** (3 days before this research was compiled) — actively maintained
- Recent commit log (most recent first): `2026-09-11` "Merge pull request #54 from graphsense/add/relay-link", `2026-09-11` "Add Relay (relay.link) actor", `2026-06-29` "remove dex from cex", `2026-05-12` "Add 8888.com cryptocurrency trading platform details", `2026-04-14` "deduplicate coingecko ids"
- Open issues: **0**; open pull requests: **2** (checked separately via the GitHub search API, since the repo's combined `open_issues_count` of 2 conflates issues+PRs)
- 39 stars, 26 forks, not archived
- Activity pattern: bursty rather than steady — clusters of commits (adding a new actor/exchange/incident) separated by multi-week gaps, consistent with a community-contribution dataset rather than a product with a sprint cadence.

**graphsense-lib** (current tooling, replaces tagpack-tool):
- Last push: **2026-09-14** (today) — very actively developed
- 18 open issues, 19 stars, not archived — this is the actively-developed component of the stack.

**Archived/retired repos** (do not build against these):
- `graphsense-tagpack-tool` — archived 2025-09-04, "moved to graphsense-lib"
- `graphsense-python` — archived 2025-09-05, client folded into `graphsense-rest`
- `graphsense-rest` — itself archived/retired 2026-02-18, folded into `graphsense-lib`

Net assessment: the **data repo is healthy and current** (commits within the last week as of this writing), and the **tooling ecosystem consolidated into `graphsense-lib`** over the past year, with the older split-repo tools (tagpack-tool, python client, rest service) all deprecated in favor of it. Anyone integrating with GraphSense today should target `graphsense-tagpacks` for data and `graphsense-lib` for tooling, and treat the other repos as historical.

## Notes & confidence

- **High confidence**: repo identity (`graphsense-tagpacks` is the data repo), license (MIT, verified from the raw LICENSE file and the GitHub API's `license.spdx_id`), the TagPack YAML schema and the `demo.yaml` example (fetched raw file content directly, quoted verbatim above), and the maintenance/activity numbers (pulled from `api.github.com` JSON, not scraped page text).
- **Medium confidence**: the claim that `packs/` is "mostly flat, occasionally grouped into subfolders." I only confirmed one subfolder (`defi_updated`) exists via the API listing; the README's documented convention names a different example (`walletexplorer_exchanges`) that wasn't visible in the current top-level listing I pulled — it may have been renamed/merged since the README was last updated, or my directory listing (capped at what the API/tool returned) simply didn't surface it. Worth a `git clone` + `find packs -type d` before you build tooling that assumes a particular folder convention.
- **Unresolved contradiction**: the email address for requesting a free `api.ikna.io` API key came back two different ways from two sources — `contact@iknaio.com` (from the `iknaio-api-tutorial` repo, which I fetched directly and is likely more authoritative since it's Iknaio's own tutorial) vs. `contact@graphsense.org` (from a WebSearch results summary I did not independently fetch/verify). If the project actually needs live API access, verify the current contact channel on `https://graphsense.org` or `https://api.ikna.io/docs` before emailing, since one of these may be stale.
- **Assumption flagged**: I did not attempt to actually register for an API key or exercise `api.ikna.io` end-to-end (e.g., confirm response schema for a tags-by-address query) — that's a runtime/functional detail, not something WebFetch against docs pages can fully confirm. Before designing the "nearest VASP" pipeline around the hosted API, do a live test call once a key is obtained.
- **Not verified**: exact total commit count (386) and star/fork counts for `graphsense-tagpacks` came from an earlier WebFetch summary of the GitHub web UI rather than a re-confirmed API call in this session; treat the *direction* (active, non-trivial history) as solid but don't cite "386 commits" as exact in a report without re-checking.
- Given the MIT license and public, PII-free-by-policy nature of the data, there are no obvious legal blockers to using this dataset for the hackathon; the main open question is a build decision (bulk-clone vs. live API), which this research recommends resolving in favor of bulk-clone for demo reliability.
