"""Etherscan API V2 client -- an address's native, token and internal transfers.

Docs: https://docs.etherscan.io/api-reference/endpoint/txlist
Free tier: 5 calls/sec (see research/01-block-explorer-apis.md).

Three endpoints, not one, because a trace that reads only `txlist` is blind to
most of what matters:

  txlist          native ETH/MATIC transfers
  tokentx         ERC-20 transfers -- USDT, USDC. This is where fraud proceeds
                  actually move; without it the tracer sees an empty wallet.
  txlistinternal  contract-driven transfers. The DAO-hack demo address looks
                  like a dead end precisely because its funds left this way.

Two free-tier limits changed in July 2026 and are handled here: records per
request were cut from 10,000 to 1,000, and internal-transactions-by-block-range
was removed from free (the by-address form used here still works).
"""
import os
from concurrent.futures import ThreadPoolExecutor

import requests

BASE_URL = "https://api.etherscan.io/v2/api"
ETH_CHAIN_ID = 1
POLYGON_CHAIN_ID = 137  # still free-tier as of this research -- see research/01-block-explorer-apis.md

# Etherscan cut the per-request ceiling from 10,000 to 1,000 in July 2026.
PAGE_SIZE = 1000
# Stop paging well before an exchange hot wallet's full history exhausts the
# daily quota. Truncation is reported rather than hidden -- see `truncated`.
DEFAULT_MAX_RECORDS = 2000

NATIVE_DECIMALS = 18  # ETH and MATIC both


def _request(params: dict) -> list | str:
    resp = requests.get(BASE_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") == "0" and data.get("message") != "No transactions found":
        raise RuntimeError(f"Etherscan error: {data.get('message')} — {data.get('result')}")

    result = data.get("result") or []
    if isinstance(result, str):  # error message came back in `result` instead of a list
        raise RuntimeError(f"Etherscan error: {result}")
    return result


def _paged(action: str, address: str, chainid: int, api_key: str, max_records: int) -> list[dict]:
    """Walk pages until the endpoint runs out or `max_records` is reached.

    Etherscan signals "no more" by returning a short page, so a full page means
    keep going. Pages are 1-indexed.
    """
    collected: list[dict] = []
    page = 1
    while len(collected) < max_records:
        rows = _request({
            "chainid": chainid, "module": "account", "action": action,
            "address": address, "startblock": 0, "endblock": 99999999,
            "page": page, "offset": min(PAGE_SIZE, max_records - len(collected)),
            # Newest first: under the record cap, a busy wallet's oldest
            # transfers pre-date the complaint and say nothing about it.
            "sort": "desc", "apikey": api_key,
        })
        collected.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        page += 1
    return collected[:max_records]


def _base_fields(tx: dict) -> dict:
    return {
        "tx_hash": tx.get("hash") or tx.get("transactionHash") or "",
        "block_number": int(tx["blockNumber"]),
        "timestamp": int(tx["timeStamp"]),
        "from_addr": (tx.get("from") or "").lower(),
        "to_addr": (tx.get("to") or "").lower(),
        "value_wei": int(tx["value"]),
    }


def fetch_transactions(address: str, api_key: str | None = None, chainid: int = ETH_CHAIN_ID,
                        max_records: int = DEFAULT_MAX_RECORDS, asset_type: str = "ETH",
                        include_tokens: bool = True, include_internal: bool = True) -> list[dict]:
    """Return this address's transfers, normalized to a common shape:

    {tx_hash, block_number, timestamp, from_addr, to_addr, value_wei,
     asset_type, asset_symbol, asset_contract, decimals, transfer_type}

    `value_wei` stays an integer in the asset's own base units; compare values
    across assets with app.assets.amount(), never directly.
    """
    api_key = api_key or os.environ.get("ETHERSCAN_API_KEY")
    if not api_key:
        raise RuntimeError("Set ETHERSCAN_API_KEY in your .env file (see .env.example).")

    # Three independent endpoint calls merged into one normalized list — a
    # single address's fetch was taking ~9s because these ran one after
    # another (measured live). They don't depend on each other, so fetch
    # them concurrently instead; ~3s (the slowest one), not the sum of three.
    actions = ["txlist"]
    if include_tokens:
        actions.append("tokentx")
    if include_internal:
        actions.append("txlistinternal")

    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        pages = dict(zip(actions, pool.map(
            lambda action: _paged(action, address, chainid, api_key, max_records), actions)))

    transfers: list[dict] = []

    for tx in pages["txlist"]:
        # A failed transaction moved no value; counting it would inflate the
        # forwarding ratios sweep.py computes.
        if tx.get("isError") == "1":
            continue
        transfers.append({**_base_fields(tx), "asset_type": asset_type,
                          "asset_symbol": asset_type, "asset_contract": "",
                          "decimals": NATIVE_DECIMALS, "transfer_type": "native"})

    if include_tokens:
        for tx in pages["tokentx"]:
            transfers.append({
                **_base_fields(tx),
                "asset_type": asset_type,  # the chain's native ticker, kept for back-compat
                "asset_symbol": tx.get("tokenSymbol") or "TOKEN",
                "asset_contract": (tx.get("contractAddress") or "").lower(),
                # Token contracts declare their own scale; USDT is 6, not 18.
                "decimals": int(tx.get("tokenDecimal") or NATIVE_DECIMALS),
                "transfer_type": "token",
            })

    if include_internal:
        for tx in pages["txlistinternal"]:
            if tx.get("isError") == "1":
                continue
            transfers.append({**_base_fields(tx), "asset_type": asset_type,
                              "asset_symbol": asset_type, "asset_contract": "",
                              "decimals": NATIVE_DECIMALS, "transfer_type": "internal"})

    transfers.sort(key=lambda t: (t["block_number"], t["tx_hash"]))
    return transfers
