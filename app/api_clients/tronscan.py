"""Tronscan API client — Tron (account-based chain, same deposit-sweep
shape as Ethereum).

Docs: research/01-block-explorer-apis.md. Response schema there is
medium-confidence (Tronscan's own docs site blocked automated fetching
during research) — parsing here is defensive, skips anything unexpected
rather than crashing. An API key is effectively required for reliable
access since Aug 2025; unauthenticated calls work but are tightly
rate-limited (~3 req/sec) and may 429.
"""
import os
import requests

BASE_URL = "https://apilist.tronscanapi.com/api/transaction"


def fetch_transactions(address: str, api_key: str | None = None, max_records: int = 20) -> list[dict]:
    api_key = api_key or os.environ.get("TRONSCAN_API_KEY")
    headers = {"TRON-PRO-API-KEY": api_key} if api_key else {}

    params = {"sort": "-timestamp", "count": "true", "limit": max_records, "start": 0, "address": address}
    resp = requests.get(BASE_URL, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    payload = resp.json()

    rows = payload.get("data")
    if not isinstance(rows, list):
        return []

    normalized = []
    for tx in rows:
        if not isinstance(tx, dict):
            continue
        tx_hash = tx.get("hash")
        owner = tx.get("ownerAddress")
        to = tx.get("toAddress")
        amount = tx.get("amount")
        if not tx_hash or not owner or not to or amount is None:
            continue  # skip anything not matching the attested schema rather than guess
        normalized.append({
            "tx_hash": tx_hash,
            "block_number": tx.get("block"),
            "timestamp": tx.get("timestamp"),
            "from_addr": owner,       # Tron addresses are base58, not lowercased like hex
            "to_addr": to,
            "value_wei": int(amount),  # SUN, the Tron equivalent of wei
            "asset_type": "TRX",
        })
    return normalized
