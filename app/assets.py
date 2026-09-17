"""Asset-aware value comparison.

Once token transfers enter the same transaction list as native transfers, the
trace can no longer compare raw integer values. 1 ETH is 10**18 wei; 1 USDT
on Ethereum is 10**6 units. Comparing the integers picks the ETH every time,
which is exactly how a tracer walks past the 50,000 USDT sitting next to
0.1 ETH -- and USDT is what Indian fraud proceeds actually move in.

So values are compared in *decimal units* (value / 10**decimals), never as
raw integers.

# ponytail: decimal units, not fiat. A wallet holding 1 BTC and 60,000 USDT
# will rank the USDT higher. That is the right call for following fraud
# proceeds; swap in a price feed if true cross-asset value ranking ever
# matters more than following one asset consistently.
"""

DEFAULT_DECIMALS = 18


def asset_key(tx: dict) -> tuple[str, str]:
    """Identity of the asset a transaction moved.

    Symbol alone is not enough -- USDT exists on several chains and fake
    tokens reuse real symbols freely, so the contract address disambiguates.
    Native transfers carry an empty contract.
    """
    symbol = tx.get("asset_symbol") or tx.get("asset_type") or ""
    return (symbol, tx.get("asset_contract") or "")


def amount(tx: dict) -> float:
    """Transaction value in whole units of its own asset."""
    decimals = tx.get("decimals")
    if decimals is None:
        decimals = DEFAULT_DECIMALS
    try:
        return tx["value_wei"] / (10 ** int(decimals))
    except (TypeError, ValueError):
        return tx["value_wei"] / (10 ** DEFAULT_DECIMALS)


def dominant_asset(transactions: list[dict]) -> tuple[str, str] | None:
    """Which asset carried the most value across these transactions.

    This is how the trace decides what to follow when an address moved several
    assets: follow the one the money actually went out in.
    """
    totals: dict[tuple[str, str], float] = {}
    for tx in transactions:
        totals[asset_key(tx)] = totals.get(asset_key(tx), 0.0) + amount(tx)
    return max(totals, key=totals.get) if totals else None
