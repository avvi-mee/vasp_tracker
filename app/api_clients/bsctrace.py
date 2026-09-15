"""BSCTrace (NodeReal MegaNode) client — BNB Smart Chain.

BscScan's own API is deprecated and Etherscan V2 excludes BNB Chain from
its free tier (see research/01-block-explorer-apis.md) — BSCTrace is the
documented free-tier replacement BNB Chain itself recommends.

Needs a free API key from https://dashboard.nodereal.io (the key is
embedded in the URL path, not a query param — different auth style than
our other clients). Schema verified live against docs.nodereal.io — NOT
live-tested against the real API, since no key has been provisioned yet.
Written from confirmed documentation, not guessed, but flag this as the
one chain client in this codebase that hasn't been exercised against a
real response — verify the field names hold before relying on it.
"""
import os
import requests

BASE_URL_TEMPLATE = "https://bsc-mainnet.nodereal.io/v1/{api_key}"


def fetch_transactions(address: str, api_key: str | None = None, max_records: int = 100) -> list[dict]:
    api_key = api_key or os.environ.get("NODEREAL_API_KEY")
    if not api_key:
        raise RuntimeError("Set NODEREAL_API_KEY in your .env file — free key from dashboard.nodereal.io.")

    url = BASE_URL_TEMPLATE.format(api_key=api_key)
    body = {
        "jsonrpc": "2.0", "id": 1, "method": "nr_getAssetTransfers",
        "params": [{
            "fromAddress": address,
            "category": ["external"],  # native BNB transfers only — matches our other EVM clients' MVP scope
            "maxCount": hex(min(max_records, 1000)),
        }],
    }
    resp = requests.post(url, json=body, timeout=20)
    resp.raise_for_status()
    payload = resp.json()

    if "error" in payload:
        raise RuntimeError(f"BSCTrace error: {payload['error']}")

    transfers = (payload.get("result") or {}).get("transfers") or []
    normalized = []
    for t in transfers:
        if not isinstance(t, dict):
            continue
        tx_hash, frm, to, value = t.get("hash"), t.get("from"), t.get("to"), t.get("value")
        if not tx_hash or not frm or not to or value is None:
            continue
        try:
            value_wei = int(value, 16) if isinstance(value, str) else int(value)
        except (TypeError, ValueError):
            continue
        normalized.append({
            "tx_hash": tx_hash,
            "block_number": t.get("blockNum"),
            "timestamp": t.get("blockTimeStamp"),
            "from_addr": frm.lower(),
            "to_addr": to.lower(),
            "value_wei": value_wei,
            "asset_type": "BNB",
        })
    return normalized
