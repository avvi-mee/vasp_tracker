"""Known sanctioned/exploit addresses — a curated risk watchlist, not a
mixer/entity-type list (see known_mixers.py for that). Sourced from
research/08-demo-addresses.md. MVP scope: a small hand-curated list, not a
live feed — an address not listed here simply isn't flagged, which is a
coverage limit, not a "confirmed clean" result.
"""

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


def check_illicit(address: str) -> dict | None:
    return KNOWN_ILLICIT.get(address.lower())
