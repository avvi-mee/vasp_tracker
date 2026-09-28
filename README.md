# SIH26182 — VASP Attribution

Automated attribution of unknown cryptocurrency wallets to their nearest
VASP, through blockchain intelligence APIs. Smart India Hackathon problem
statement SIH26182 (MHA / I4C).

Paste a wallet address. The tool follows the money across up to 12 hops,
names the nearest exchange or service it can attribute, says how confident it
is and on what evidence, judges the risk, and drafts the legal instrument an
officer would actually serve to get the KYC behind it.

**Status:** all six chains live, Next.js console and FastAPI service in place,
evidence pack producing court-format certificates. See "Known limits" below
for what it still cannot do — that list is deliberately maintained, not
hidden.

## What it does

**Attribution.** Multi-hop ranked-candidate search (`app/graph/trace.py`) —
not a single greedy path. Converging paths merge, branches below a materiality
threshold are pruned *and reported*, and one asset is followed at a time so a
USDT trail is never lost behind a dust-sized native transfer.

Labels come from three sources in a strict confidence order, and the verdict
always names which one answered: the curated Indian VASP dataset
(0.75–0.95, checksum-validated) → GraphSense TagPacks → block-explorer tags
(fixed 0.60, never cluster-defining). An address nothing names is reported as
**unattributed**, never as clean.

**Risk.** Two independent questions, combined by taking the worse and naming
the basis (`app/graph/risk.py`): *where did the money go* (sanctions, mixers,
darknet markets, FIU-IND compliance status) and *how does this wallet behave*
(five laundering typologies with published thresholds — funnelling, rapid
layering, fan-out smurfing, peel chains, round-amount structuring). An
exchange's own hot wallet is not called a launderer for behaving like one.

**Sanctions screening, three sources** (`app/api_clients/chainalysis.py`). A
vendored OFAC SDN snapshot that works offline, plus both of the things
Chainalysis gives away free: its **on-chain sanctions oracle**, read live from
chain with no API key and no vendor agreement (EVM chains only), and its
**Sanctions Screening API**, which needs a requested key but reaches Bitcoin,
Tron and Solana too and returns the designation text itself.

Each source reports separately, and one that could not answer says "not
consulted" rather than implying a clean result — including when only part of
a trail could be screened. Everything else Chainalysis sells is licensed and
is not used here.

**Plain language.** Every trace also comes back as one paragraph anyone can
read (`app/graph/summary.py`). Deterministic template over the fields above,
not a language model: nothing in it can be invented, and the same trace
always produces the same sentence.

**Evidence.** A s.63 BSA certificate pack (`app/evidence/certificate.py`) —
zip containing the frozen JSON record, Part A, Part B, and a hash report.
The record deliberately excludes clock readings so its SHA-256 is
reproducible by a defence expert. Every sworn statement is left blank.

**Case workflow.** Officer login with roles, case list and detail, NCRP
acknowledgement and CCTNS FIR numbers, SAHYOG disclosure drafts routed to the
right instrument (BNSS s.94 / s.107, PMLA s.5, BSA s.63), manual UPI/bank
money-trail entry, watchlist alerts, and a Coverage page that publishes this
tool's own thresholds and limits.

## Chains

| Chain | Source | Coverage |
|---|---|---|
| Ethereum | Etherscan API V2 | Native + ERC-20 + internal |
| Polygon | Etherscan API V2 | Native + ERC-20 + internal |
| Tron | Tronscan | Native TRX + TRC-20 |
| Solana | Helius parsed-tx | Native SOL + SPL |
| Bitcoin | Blockchair | Dominant-output following |
| BNB Chain | NodeReal MegaNode | Native BNB only |

## Layout

```
app/
  api/main.py        FastAPI service — every HTTP endpoint
  api_clients/       One module per chain, all normalising to one tx shape,
                     plus the keyless Chainalysis sanctions oracle client
  graph/             trace · risk · typology · sweep · exposure · summary
  data/              Label datasets (Indian VASPs, TagPacks, OFAC) + Postgres stores
  evidence/          s.63 BSA certificate pack
  sahyog/            Disclosure-request builder and instrument routing
  prices.py          Keyless CoinGecko INR valuation (display only)
  main.py            Streamlit UI (older, behind the FastAPI path)
frontend/            Next.js 16 console — Cytoscape graph, exposure wheels, cases
research/            Source research, one topic per file. Start at 00-INDEX.md
tests/               pytest, all network mocked
```

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # fill in the chain API keys
python scripts\create_officer.py

uvicorn app.api.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Everything in `.env` past the chain keys is optional — the Chainalysis oracle
and the rupee price feed both work with no key and no account.

```
python -m pytest tests/ -q     # no network; safe offline
python -m app.cli <address>    # terminal harness, Ethereum
```

## Known limits

Stated here because the Coverage page states them to users, and a tool that
produces court evidence should not be coy about where it stops.

- **No common-input-ownership clustering for Bitcoin.** Dominant-output
  following only. The problem statement names CIOH; this is the largest
  outstanding gap.
- **No cross-chain tracing.** A trail that crosses a bridge ends there.
- **BNB Chain adapter is not live-tested** and covers native BNB only, no
  BEP-20. Etherscan V2 excludes BNB from its free tier.
- **Solana fetches one page**, no cursor pagination.
- **The Chainalysis oracle is EVM-only** — not consulted on Bitcoin, Tron or
  Solana, and the UI says so. Their Screening API closes that gap but needs a
  key requested from Chainalysis; set `CHAINALYSIS_API_KEY` once you have one.
- **The Screening API client has never seen a real 200.** The endpoint is
  confirmed reachable, but its success-path shape comes from documentation,
  not observation. It is written to return "not consulted" for any payload it
  does not recognise, so a wrong guess cannot produce a false hit or a false
  all-clear — but verify it against a real key before relying on it.
- **SAHYOG submission is mocked.** Drafts are generated and stored; nothing
  is transmitted, because no such API exists to call.
- **No FIU-IND registered-VASP list exists publicly.** Ground truth is
  assembled from named entities in penalty orders — a stated limitation, not
  a solved problem.
- Rupee figures are display-only and never enter the certified record, since
  a market price changes with time and the record's hash must not.
- JWT in `localStorage`, client-side route guard, CORS wide open. All
  disclosed simplifications, all wrong for a real deployment.

## Documentation

Architecture, workflow, tools matrix, PPT outline, legal summary:
`C:\Users\Avvi\Documents\SIH26182-VASP-Attribution-Documentation\00-INDEX.md`
