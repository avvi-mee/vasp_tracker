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
#
# Dust steering (a million units of a worthless token outranking 2 ETH) is
# closed by TRUSTED_CONTRACTS below rather than by pricing: prices stay a
# display concern, see app/prices.py's docstring.
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


# Canonical contracts of the assets fraud proceeds actually move in, per
# chain, compared lowercased. Anyone can mint a token called "USDT"; only
# these contracts are the real thing. Native coins (empty contract) are
# always trusted.
# ponytail: allow-list, not pricing. An unlisted but genuine token (say a
# small-cap alt) loses to native value moving alongside it; add its contract
# here, or wire app/prices.py per-contract pricing if that becomes common.
TRUSTED_CONTRACTS = {c.lower() for c in (
    # Ethereum: USDT, USDC, DAI, WETH, WBTC
    "0xdac17f958d2ee523a2206206994597c13d831ec7", "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "0x6b175474e89094c44da98b954eedeac495271d0f", "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
    # Tron: USDT, USDC
    "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8",
    # BNB Chain: USDT, USDC
    "0x55d398326f99059ff775485246999027b3197955", "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    # Polygon: USDT, USDC (native), USDC.e (bridged)
    "0xc2132d05d31c914a87c6611c10748aeb04b58e8f", "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359",
    "0x2791bca1f2de4661ed88a30c99a7a9449aa84174",
    # Solana: USDT, USDC mints
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
)}


def is_trusted_asset(key: tuple[str, str]) -> bool:
    return not key[1] or key[1].lower() in TRUSTED_CONTRACTS


def dominant_asset(transactions: list[dict]) -> tuple[str, str] | None:
    """Which asset carried the most value across these transactions.

    This is how the trace decides what to follow when an address moved several
    assets: follow the one the money actually went out in. Only native coins
    and canonical token contracts compete, so a flood of junk tokens cannot
    steer the trace; unlisted tokens are followed only if nothing trusted moved.
    """
    totals: dict[tuple[str, str], float] = {}
    for tx in transactions:
        totals[asset_key(tx)] = totals.get(asset_key(tx), 0.0) + amount(tx)
    trusted = {k: v for k, v in totals.items() if is_trusted_asset(k) and v > 0}
    pool = trusted or totals
    return max(pool, key=pool.get) if pool else None
