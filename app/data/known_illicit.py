"""Known sanctioned/exploit addresses — a curated risk watchlist, not a
mixer/entity-type list (see known_mixers.py for that).

Two sources, merged: a couple of hand-curated entries worth naming
specifically (research/08-demo-addresses.md), and the real US Treasury OFAC
SDN list via app/data/ofac_sanctions.py (~900 addresses across the chains
this tool traces, versus 2 by hand). The hand-curated entries win on
collision — they carry a more specific label than "OFAC SDN-listed address"
alone. An address matching neither is still a coverage limit, not a
"confirmed clean" result.
"""
from app.addresses import normalize_address as _normalize
from app.data.ofac_sanctions import load_ofac_addresses

KNOWN_ILLICIT = {
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96": {
        "label": "Ronin Bridge Exploiter (Lazarus Group)",
        "reason": "OFAC SDN-listed 14 Apr 2022 — ~$600M Ronin/Axie Infinity bridge hack",
    },
    "0xf835a0247b0063c04ef22006ebe57c5f11977cc4": {
        "label": "The DAO hack attacker contract",
        "reason": "2016 reentrancy exploit — ~3.6M ETH drained; not sanctioned, but publicly documented",
    },
}

_ofac_cache: dict | None = None


def _ofac() -> dict:
    global _ofac_cache
    if _ofac_cache is None:
        _ofac_cache = load_ofac_addresses()
    return _ofac_cache


def check_illicit(address: str) -> dict | None:
    normalized = _normalize(address)
    return KNOWN_ILLICIT.get(normalized) or _ofac().get(normalized)
