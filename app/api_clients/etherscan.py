"""Etherscan API V2 client — fetches an address's normal transactions.

Docs: https://docs.etherscan.io/api-reference/endpoint/txlist
Free tier: 3 calls/sec, 100k calls/day (see research/01-block-explorer-apis.md).
"""
import os
import requests

BASE_URL = "https://api.etherscan.io/v2/api"
ETH_CHAIN_ID = 1
POLYGON_CHAIN_ID = 137  # still free-tier as of this research — see research/01-block-explorer-apis.md


def fetch_transactions(address: str, api_key: str | None = None, chainid: int = ETH_CHAIN_ID,
                        max_records: int = 100, asset_type: str = "ETH") -> list[dict]:
    """Return this address's normal transactions, normalized to a common shape:
    {tx_hash, block_number, timestamp, from_addr, to_addr, value_wei, asset_type}
    """
    api_key = api_key or os.environ.get("ETHERSCAN_API_KEY")
    if not api_key:
        raise RuntimeError("Set ETHERSCAN_API_KEY in your .env file (see .env.example).")

    params = {
        "chainid": chainid,
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": max_records,
        "sort": "asc",
        "apikey": api_key,
    }
    resp = requests.get(BASE_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") == "0" and data.get("message") != "No transactions found":
        raise RuntimeError(f"Etherscan error: {data.get('message')} — {data.get('result')}")

    result = data.get("result") or []
    if isinstance(result, str):  # error message came back in `result` instead of a list
        raise RuntimeError(f"Etherscan error: {result}")

    return [
        {
            "tx_hash": tx["hash"],
            "block_number": int(tx["blockNumber"]),
            "timestamp": int(tx["timeStamp"]),
            "from_addr": tx["from"].lower(),
            "to_addr": (tx["to"] or "").lower(),
            "value_wei": int(tx["value"]),
            "asset_type": asset_type,
        }
        for tx in result
    ]
