"""Blockchair API client — Bitcoin (UTXO chain).

Bitcoin transactions have multiple inputs and multiple outputs, unlike
Ethereum's simple from/to. To fit the same trace-engine interface (one
"dominant next hop" per outgoing transaction), we normalize each outgoing
transaction to: address -> its largest-value output address, the same
"follow the dominant value forward" principle the Ethereum deposit-sweep
trace uses. Common-input-ownership clustering (identifying co-owned INPUT
addresses within one tx) is a separate, documented technique — not wired
into hop-following here, same as it isn't for Ethereum.

Docs: research/01-block-explorer-apis.md. Blockchair's docs site blocked
automated fetching during research, so the transaction-detail schema below
is best-effort from a community mirror — verified live below, parsing is
defensive (skips anything unexpected rather than crashing).
"""
import os
import requests

BASE_URL = "https://api.blockchair.com"


def _key_param(api_key: str | None) -> dict:
    api_key = api_key or os.environ.get("BLOCKCHAIR_API_KEY")
    return {"key": api_key} if api_key else {}


def fetch_transaction_detail(tx_hash: str, chain: str = "bitcoin", api_key: str | None = None) -> dict:
    resp = requests.get(f"{BASE_URL}/{chain}/dashboards/transaction/{tx_hash}",
                        params=_key_param(api_key), timeout=20)
    resp.raise_for_status()
    data = resp.json().get("data", {})
    return data.get(tx_hash, {})


def fetch_transactions(address: str, chain: str = "bitcoin", api_key: str | None = None,
                        max_records: int = 20) -> list[dict]:
    """Normalized to the same shape as etherscan.fetch_transactions:
    {tx_hash, block_number, timestamp, from_addr, to_addr, value_wei, asset_type}
    (value_wei here means satoshis — field name kept for interface consistency).
    """
    params = {"limit": max_records, "transaction_details": "true", **_key_param(api_key)}
    resp = requests.get(f"{BASE_URL}/{chain}/dashboards/address/{address}", params=params, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    addr_data = (payload.get("data") or {}).get(address, {})
    tx_summaries = addr_data.get("transactions") or []

    normalized = []
    for tx in tx_summaries:
        if not isinstance(tx, dict):
            continue
        tx_hash = tx.get("hash")
        balance_change = tx.get("balance_change", 0)
        if not tx_hash or balance_change is None or balance_change >= 0:
            continue  # only follow transactions where value LEFT this address

        try:
            detail = fetch_transaction_detail(tx_hash, chain=chain, api_key=api_key)
        except requests.RequestException:
            continue  # one bad lookup shouldn't kill the whole trace

        outputs = detail.get("outputs") or []
        candidates = [
            o for o in outputs
            if isinstance(o, dict)
            # Case-insensitive here only to decide "is this a change output
            # back to the querying address" — the recipient value actually
            # stored below stays exactly as Blockchair returned it, case and
            # all, since that's what must survive into normalize_address().
            and (o.get("recipient") or "").lower() != address.lower()
            and (o.get("value") or 0) > 0
        ]
        if not candidates:
            continue

        dominant = max(candidates, key=lambda o: o["value"])
        normalized.append({
            "tx_hash": tx_hash,
            "block_number": detail.get("transaction", {}).get("block_id"),
            "timestamp": tx.get("time"),
            # Bitcoin addresses are base58/bech32 and case-sensitive — do NOT
            # .lower() them, that silently corrupts legacy (1.../3...)
            # addresses into ones that will never match a label again (see
            # app/addresses.py and test_base58_addresses_are_not_lowercased).
            "from_addr": address,
            "to_addr": dominant["recipient"],
            "value_wei": dominant["value"],  # satoshis
            "asset_type": "BTC",
            "asset_symbol": "BTC",
            "asset_contract": "",
            "decimals": 8,  # 1 BTC = 1e8 satoshis, not the EVM-default 1e18
            "transfer_type": "native",
        })
    return normalized
