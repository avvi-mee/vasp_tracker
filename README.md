# SIH26182 — VASP Attribution

Automated attribution of unknown cryptocurrency wallets to nearest VASPs
through blockchain intelligence APIs. Smart India Hackathon problem
statement SIH26182.

**Status:** Phase 1 underway — Ethereum end-to-end trace pipeline built,
terminal-tested (see `08-Build-Plan-and-Roadmap.md` in the docs for phases).

## Layout

- `research/` — source research (API docs, legal context, clustering
  heuristics, compliance data), one topic per file. Start with
  `research/00-INDEX.md`.
- `app/` — Streamlit application.
  - `app/api_clients/` — block explorer API clients (Etherscan built; Tronscan,
    Blockchair to follow).
  - `app/graph/` — multi-hop trace engine (`trace.py`).
  - `app/data/` — GraphSense TagPacks (git-cloned), known-mixer list, FIU-IND
    dataset.
  - `app/cli.py` — Phase 1 terminal harness: `python -m app.cli <address>`.
- `tests/` — smoke tests, starting with `test_trace.py`.

## Documentation

Full architecture, workflow, tools matrix, PPT outline, and legal summary:
`C:\Users\Avvi\Documents\SIH26182-VASP-Attribution-Documentation\00-INDEX.md`

## Setup (once logic is written)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then fill in API keys
```
