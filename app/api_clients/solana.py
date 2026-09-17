"""Helius parsed-transaction API — Solana (native SOL + SPL tokens).

Replaces the previous raw-RPC client, which only decoded native System
Program transfers. SPL token transfers (Solana's ERC-20 equivalent, e.g.
USDC-SPL — very common in practice) need the token program's instruction
shape decoded separately; Helius's enhanced/parsed transaction API already
does that, so there's no hand-rolled instruction parsing here. Needs a free
HELIUS_API_KEY (dev.helius.xyz, 1M credits/mo, no card required).

Response shape live-verified against a real busy address (a known exchange
Solana wallet) via `GET /v0/addresses/{address}/transactions?api-key=...`:
`nativeTransfers[]` carry integer lamports (`fromUserAccount`/
`toUserAccount`/`amount`); `tokenTransfers[]` carry an ALREADY decimal-scaled
`tokenAmount` plus the token's `mint` address, but no symbol or decimals
field — `decimals: 0` is used for these so `app.assets.amount()` returns
`tokenAmount` unchanged, and a small known-mint table supplies a readable
symbol for major stablecoins, falling back to a shortened mint address for
anything else (the trace still works correctly either way — only the label
shown is less friendly).

No pagination beyond one page (Helius caps `limit` at 100) — same documented
simplification the other clients had before Phase A's pagination pass; add
`before=<signature>` cursoring if a trace needs to look further back.
"""
import os
import requests

API_URL_TEMPLATE = "https://api.helius.xyz/v0/addresses/{address}/transactions"
PAGE_SIZE = 100
SOL_DECIMALS = 9  # lamports per SOL

# The handful of SPL mints worth naming — anything else still traces
# correctly, it just shows the mint address instead of a ticker.
KNOWN_MINTS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
}


def fetch_transactions(address: str, api_key: str | None = None, max_records: int = 200) -> list[dict]:
    api_key = api_key or os.environ.get("HELIUS_API_KEY")
    if not api_key:
        raise RuntimeError("Set HELIUS_API_KEY in your .env file — free key from dev.helius.xyz.")

    resp = requests.get(
        API_URL_TEMPLATE.format(address=address),
        params={"api-key": api_key, "limit": min(max_records, PAGE_SIZE)}, timeout=20,
    )
    resp.raise_for_status()
    transactions = resp.json()
    if not isinstance(transactions, list):
        raise RuntimeError(f"Unexpected Helius response shape: {transactions}")

    normalized = []
    for tx in transactions:
        if not isinstance(tx, dict) or tx.get("transactionError"):
            continue  # skip failed transactions, same posture as every other client
        signature, slot, timestamp = tx.get("signature"), tx.get("slot"), tx.get("timestamp")
        if not signature:
            continue

        for nt in tx.get("nativeTransfers") or []:
            source, dest, lamports = nt.get("fromUserAccount"), nt.get("toUserAccount"), nt.get("amount")
            if not source or not dest or not lamports:
                continue
            normalized.append({
                "tx_hash": signature, "block_number": slot, "timestamp": timestamp,
                "from_addr": source, "to_addr": dest, "value_wei": lamports,
                "asset_type": "SOL", "asset_symbol": "SOL", "asset_contract": "",
                "decimals": SOL_DECIMALS, "transfer_type": "native",
            })

        for tt in tx.get("tokenTransfers") or []:
            source, dest = tt.get("fromUserAccount"), tt.get("toUserAccount")
            token_amount, mint = tt.get("tokenAmount"), tt.get("mint")
            if not source or not dest or token_amount is None:
                continue
            normalized.append({
                "tx_hash": signature, "block_number": slot, "timestamp": timestamp,
                "from_addr": source, "to_addr": dest,
                "value_wei": token_amount,  # already decimal-scaled — decimals=0 below leaves it as-is
                "asset_type": "SOL",  # native chain ticker, kept for back-compat like tronscan.py's TRX
                "asset_symbol": KNOWN_MINTS.get(mint, (mint or "SPL")[:8]),
                "asset_contract": mint or "",
                "decimals": 0,
                "transfer_type": "token",
            })

    normalized.sort(key=lambda t: (t.get("timestamp") or 0, t["tx_hash"]))
    return normalized[:max_records]
