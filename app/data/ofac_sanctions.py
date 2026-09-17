"""OFAC sanctioned-address ingestion — 0xB10C/ofac-sanctioned-digital-currency-addresses
(`lists` branch), a nightly-refreshed parse of Treasury's SDN Advanced XML.
Replaces what used to be a 2-address hand-curated watchlist in
known_illicit.py with the real Treasury list. Vendored the same way as
graphsense-tagpacks: a shallow clone sitting alongside this file, refreshed
with `git pull` there when it's stale.

Keyed on address alone, not (currency, address): an EVM 0x-address, a base58
Tron/Bitcoin address and a Solana address never collide in format, so there's
no ambiguity to resolve and no need to thread the trace's currency through
risk.py just to look this up.
"""
import json
from pathlib import Path

from app.addresses import normalize_address as _normalize

OFAC_DIR = Path(__file__).parent / "ofac-sanctioned-digital-currency-addresses"

# repo filename suffix -> chains this project actually traces (app/chains.py).
# BSC is included pre-emptively for when BNB Chain goes live; the rest of the
# repo's chains (LTC, XMR, XRP, DASH, ...) aren't ones this tool traces.
_FILES = ("ETH", "XBT", "TRX", "SOL", "BSC")


def load_ofac_addresses(ofac_dir: Path = OFAC_DIR) -> dict[str, dict]:
    """Returns {address: {label, reason}} — same shape as
    known_illicit.KNOWN_ILLICIT's values, so the two merge directly."""
    out: dict[str, dict] = {}
    if not ofac_dir.exists():
        return out  # a coverage limit, not a crash — same posture as indian_vasps.py

    for suffix in _FILES:
        path = ofac_dir / f"sanctioned_addresses_{suffix}.json"
        if not path.exists():
            continue
        try:
            addresses = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for address in addresses:
            out[_normalize(address)] = {
                "label": "OFAC SDN-listed address",
                "reason": "US Treasury OFAC SDN list, via "
                          "github.com/0xB10C/ofac-sanctioned-digital-currency-addresses",
            }
    return out
