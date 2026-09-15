# Research Index — SIH26182

All 8 files below were produced by live web research on 2026-09-14 (real fetches
of current docs/sites, not model memory — every claim is cited inline in its
file). Read this index first, then open the specific file you need.

| # | File | One-line summary | Overall confidence |
|---|---|---|---|
| 01 | [block-explorer-apis.md](01-block-explorer-apis.md) | Etherscan/BscScan/Tronscan/Blockchair — endpoints, auth, schemas, real examples | High for Etherscan + the BSC paywall; medium for Blockchair's daily cap and Tronscan's response schema |
| 02 | [graphsense-tagpacks.md](02-graphsense-tagpacks.md) | GraphSense TagPacks repo — MIT-licensed, YAML, actively maintained, git-clonable | High |
| 03 | [etherscan-labels.md](03-etherscan-labels.md) | Etherscan address labels — free tier has none; paid tier exists; ToS blocks scraping + ML use | High |
| 04 | [walletexplorer.md](04-walletexplorer.md) | WalletExplorer.com — free no-key API works today, but label data frozen since 2016 | High on facts; medium on Chainalysis/law-enforcement angle |
| 05 | [fiu-vasp-list.md](05-fiu-vasp-list.md) | FIU-IND VASP list — no public roster exists; 3 enforcement waves are well documented | High for enforcement actions; **low** for any "currently registered" full list |
| 06 | [clustering-heuristics.md](06-clustering-heuristics.md) | Common-input-ownership (Bitcoin) + deposit-sweep (Ethereum/BSC/Tron) heuristics, with academic sources and pseudocode | High |
| 07 | [legal-context.md](07-legal-context.md) | PMLA March 2023 notification + confirmed Jan 2026 FIU-IND guidelines update | High on existence/dates; medium on the exact "what changed" details of the 2026 guidelines |
| 08 | [demo-addresses.md](08-demo-addresses.md) | 3 verified public Ethereum addresses (DAO hack, Tornado Cash, Ronin Bridge) safe for demo data | High |

## Cross-cutting findings that shape the whole project

These showed up independently across multiple files and matter for the
architecture, not just one topic:

1. **Free-tier BSC access basically doesn't exist anymore.** BscScan's standalone
   API is deprecated and merged into Etherscan API V2 — but Etherscan excluded
   BNB Smart Chain from its free tier (effective 22 Nov 2025). A free BSC
   integration needs BSCTrace instead (its exact rate limits weren't
   publishable — file 01 flags this as needing direct sign-up to confirm).
2. **Address labels ("Binance: Hot Wallet"-style tags) are the hardest data
   source to get for free and legally.** Etherscan's free API has none; its
   paid tier explicitly restricts ML/dataset use in its ToS (file 03).
   GraphSense TagPacks (file 02) and WalletExplorer (file 04) are the two
   genuinely free, redistributable label sources — but WalletExplorer's data
   is frozen at 2016, so GraphSense TagPacks is the primary label source this
   project should build on, not Etherscan.
3. **There is no official "list of all FIU-IND registered VASPs."** File 05's
   biggest finding: FIU-IND publishes circulars and penalty orders, not a
   named roster. The project's "ground truth" for registered/compliant VASPs
   will have to be built from named entities in penalty orders (high
   confidence) plus the enforcement-wave flagged/blocked entities (high
   confidence for who was flagged, not for who is currently compliant) — this
   should be stated as a known limitation in the pitch, not papered over.
4. **The "2026 FIU-IND guidelines" the brief asked about are real** — dated 8
   January 2026, confirmed hosted on fiuindia.gov.in — but their exact
   provision-by-provision content is only triangulated from secondary
   (law-firm) sources, not read verbatim from the primary PDF (which resisted
   automated extraction). Worth a human spot-check before final submission.

## Flagged gaps / assumptions (don't paper over these)

- **Etherscan ToS vs. this project's goals is a real tension**, not a minor
  footnote: Etherscan's terms explicitly prohibit using label data for
  "AI, machine learning, ... dataset creation" without written permission.
  Since VASP attribution is exactly that kind of use, the project should
  either (a) rely on GraphSense TagPacks / other openly-licensed sources as
  primary labels and treat Etherscan purely as a transaction-data source, or
  (b) disclose this explicitly to mentors/judges as a compliance
  consideration. This is called out again in `07-legal-context.md` territory
  but is really a data-sourcing decision, not a legal one.
- **FIU-IND "currently registered" entity count is unresolved between three
  conflicting figures** (50 / 49 / 54) from different dates and source
  qualities — treat the named penalty-order entities (Binance, KuCoin, Bybit)
  as solid ground truth, and everything else in that list as "reported, not
  verified."
- **Tronscan's exact response schema is best-effort**, reconstructed from
  attested field names rather than one clean docs page (docs.tronscan.org
  blocked automated fetching). Confirm the real JSON shape with one live
  authenticated call before writing the Tron API client.
- **No verified Bitcoin-chain demo address** was found in the time available
  (file 08) — only 3 Ethereum addresses are demo-ready today. If a
  UTXO-chain demo is wanted, that needs a short follow-up search (PlusToken
  was the most promising lead but no address string could be pinned down).
- **GraphSense's hosted-API contact email is disputed** between two sources
  (`contact@iknaio.com` vs `contact@graphsense.org`) — irrelevant if the
  project uses the git-clone path (recommended anyway for demo reliability),
  matters only if a live hosted-API key is pursued later.
