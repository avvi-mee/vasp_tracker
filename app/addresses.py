"""Address normalization — one rule, one place.

This lived in three files with comments saying "kept in sync", which is how
a case-sensitivity bug gets reintroduced. It is here instead.
"""


def normalize_address(address: str) -> str:
    """Hex addresses (0x...) are case-insensitive — lowercase them so the same
    address always matches itself. Base58 addresses (Tron, Bitcoin, Solana) ARE
    case-sensitive: lowercasing one silently corrupts it into a different
    address that will never match a label.
    """
    return address.lower() if address.startswith(("0x", "0X")) else address
