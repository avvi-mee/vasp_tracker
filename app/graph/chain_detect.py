"""Best-effort chain detection from address format alone — pattern
matching, not full checksum validation (that's a real enhancement for
later, not needed just to pre-select a UI dropdown).

One real limit, stated plainly: Ethereum, Polygon, and BNB Chain are all
EVM-compatible and share the exact same 0x+40-hex-char format — the same
string is a syntactically valid address on all three. There is no way to
tell which one from the format alone; this defaults to Ethereum and says
so, rather than pretending to know.
"""
import re

EVM_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")
TRON_PATTERN = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
BITCOIN_PATTERN = re.compile(r"^(bc1[0-9a-z]{25,90}|[13][1-9A-HJ-NP-Za-km-z]{25,34})$")
# Solana has no fixed prefix — base58, 32-44 chars, checked last as a fallback
# so it doesn't swallow Bitcoin/Tron matches that also happen to be base58.
SOLANA_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def detect_chain(address: str) -> tuple[str | None, str]:
    """Returns (chain_name_to_preselect, human-readable note). chain_name
    matches a key in main.py's CHAINS dict, or None if unrecognized."""
    address = (address or "").strip()
    if not address:
        return None, ""

    if EVM_PATTERN.match(address):
        return "Ethereum", ("EVM-format address — same format on Ethereum, Polygon, and BNB Chain. "
                            "Defaulting to Ethereum; switch chains above if you meant one of the others.")
    if TRON_PATTERN.match(address):
        return "Tron", "Tron-format address (starts with T)."
    if BITCOIN_PATTERN.match(address):
        return "Bitcoin — coming soon", "Bitcoin-format address — detected, but this chain isn't wired up yet."
    if SOLANA_PATTERN.match(address):
        return "Solana", "Base58 address, best guess Solana (no fixed prefix to be fully certain)."
    return None, "Address format not recognized — pick the chain manually."
