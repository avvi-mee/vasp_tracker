"""Rupee valuation for on-chain amounts.

Every figure this tool produces is currently in token units — 0.42 ETH,
50,000 USDT. Everyone who reads its output works in rupees: the investigating
officer sizing a case, the magistrate reading an attachment application under
BNSS s.107, the FIU-IND threshold that decides whether something is
reportable at all. Making them convert in their head is a small tax paid on
every single number on the page.

CoinGecko's Demo tier: no API key, no account, 100 calls/min. One batched
call covers every asset this project traces, and app/cache.py collapses the
repeats, so a trace costs at most one price lookup.

Deliberately no fallback provider. The obvious candidate (coins.llama.fi) is
USD-only, so wiring it in would mean sourcing a USD->INR rate from somewhere
else as well — two more things that can be down or disagree, to protect a
number that is contextual rather than evidential. When the rate is unknown
this module returns None and the UI shows token units alone, which is where
it started. That is a better failure than a confidently wrong rupee figure.

NOT used in the certified evidence record, on purpose. build_record() in
app/evidence/certificate.py excludes anything that changes between runs of
the same trace so its SHA-256 stays reproducible for a defence expert, and a
market price changes every minute by definition. Rupee figures are decision
support on screen, not a certified finding.
"""
import os
import time

import requests

API_URL = "https://api.coingecko.com/api/v3/simple/price"

# Asset symbol as it appears in our normalized tx dicts -> CoinGecko id.
# Only the assets app/chains.py can actually produce, plus the two stables
# that carry most Indian fraud proceeds. An unmapped symbol (some random
# BEP-20) yields None rather than a guess.
_COINGECKO_IDS = {
    "ETH": "ethereum",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "TRX": "tron",
    "SOL": "solana",
    "BTC": "bitcoin",
    "BNB": "binancecoin",
    "USDT": "tether",
    "USDC": "usd-coin",
}

# Longer than app/cache.py's 60s: a forensic figure does not need to be
# minute-fresh, and this keeps us far inside the free tier on a demo day
# where the same trace gets re-run repeatedly in front of judges.
_TTL_SECONDS = 600
_cache: tuple[float, dict[str, float]] | None = None


def _fetch_rates() -> dict[str, float]:
    ids = ",".join(sorted(set(_COINGECKO_IDS.values())))
    resp = requests.get(API_URL, params={"ids": ids, "vs_currencies": "inr"}, timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    return {symbol: payload[cg]["inr"]
            for symbol, cg in _COINGECKO_IDS.items()
            if isinstance(payload.get(cg), dict) and "inr" in payload[cg]}


def rates() -> dict[str, float]:
    """{symbol: INR per whole unit}. Empty dict when the lookup fails — the
    caller shows token units, same as before this module existed.
    """
    global _cache
    if os.environ.get("DISABLE_PRICE_FEED"):
        return {}
    now = time.monotonic()
    if _cache is not None and now - _cache[0] < _TTL_SECONDS:
        return _cache[1]
    try:
        fetched = _fetch_rates()
    except (requests.RequestException, ValueError, KeyError):
        # Keep serving a stale table if we have one: an hour-old rate still
        # tells an officer whether a case is worth thousands or crores, which
        # is the actual question. Only a cold start shows nothing.
        return _cache[1] if _cache else {}
    _cache = (now, fetched)
    return fetched


def inr_rate(symbol: str) -> float | None:
    return rates().get((symbol or "").upper())


def to_inr(amount: float, symbol: str) -> float | None:
    rate = inr_rate(symbol)
    return None if rate is None else amount * rate


def clear_cache() -> None:
    """For tests — mirrors app/cache.py's escape hatch."""
    global _cache
    _cache = None
