"""Tronscan API client -- Tron (account-based chain, same deposit-sweep shape
as Ethereum).

Two endpoints, and the second one is the point of this module:

  /api/transaction            native TRX transfers
  /api/token_trc20/transfers  TRC20 transfers -- overwhelmingly USDT

Tron carries more USDT than any other chain, and USDT-TRC20 is what Indian
cyber-fraud proceeds actually move in: the ED froze 160,339 USDT in the
Rs 303 crore syndicate case, and the Gujarat Cyber Cell's Rs 226 crore
terror-funding case moved the same way. Reading only native TRX on Tron means
looking at an empty wallet while the money sits in plain view next to it.

Docs: research/01-block-explorer-apis.md. The native response schema there is
medium-confidence (Tronscan's docs site blocked automated fetching during
research), so parsing stays defensive -- skip anything unexpected rather than
crash. An API key is effectively required for reliable access since Aug 2025;
unauthenticated calls work but are tightly rate-limited (~3 req/sec) and 429.
"""
import os
from concurrent.futures import ThreadPoolExecutor

import requests

from app.data.chain_native_labels import is_junk

BASE_URL = "https://apilist.tronscanapi.com/api"
TRX_DECIMALS = 6  # SUN per TRX is 10**6, not 10**18 -- Tron is not EVM-scaled


def _to_unix_seconds(ms_or_none: int | None) -> int | None:
    """Tronscan's timestamps (both `timestamp` and `block_ts`) are Unix
    milliseconds -- confirmed live (13-digit values) -- while every other
    chain client in this project (Etherscan, Solana/Helius, Blockchair) gives
    Unix seconds. Left unconverted, this silently corrupted anything that
    reads timestamps across chains (sorting by recency, rendering a date).
    Normalize once, here, rather than have every caller guess which chain
    it's looking at."""
    return ms_or_none // 1000 if ms_or_none is not None else None

# Tronscan caps `start + limit` at 10,000.
PAGE_SIZE = 200
MAX_OFFSET = 10_000
DEFAULT_MAX_RECORDS = 600


def _headers(api_key: str | None) -> dict:
    api_key = api_key or os.environ.get("TRONSCAN_API_KEY")
    return {"TRON-PRO-API-KEY": api_key} if api_key else {}


def _clean_tag(value) -> str | None:
    """Tronscan's tag fields arrive in two shapes: a plain string on the
    native endpoint, and a one-key dict on the TRC20 endpoint
    ({"to_address_tag": "Binance-Hot 7", "to_address_tag_logo": ""}) where
    the name may be absent entirely. Normalize both to a name or None."""
    if isinstance(value, dict):
        value = next((v for k, v in value.items() if not k.endswith("_logo")), None)
    if not isinstance(value, str) or is_junk(value):
        return None
    return value.strip()


def _paged(path: str, address: str, headers: dict, max_records: int,
          address_param: str = "address") -> tuple[list[dict], dict]:
    """Page through a Tronscan list endpoint, honouring its start+limit ceiling.

    Returns (rows, address_info) -- the second is Tronscan's own
    `normalAddressInfo`, a per-address {"risk": bool} map it returns alongside
    the rows and that this client used to throw away.
    """
    collected: list[dict] = []
    address_info: dict = {}
    start = 0
    while len(collected) < max_records and start < MAX_OFFSET:
        limit = min(PAGE_SIZE, max_records - len(collected), MAX_OFFSET - start)
        resp = requests.get(f"{BASE_URL}/{path}", headers=headers, timeout=20, params={
            "sort": "-timestamp", "count": "true", "limit": limit,
            "start": start, address_param: address,
        })
        resp.raise_for_status()
        payload = resp.json()
        info = payload.get("normalAddressInfo")
        if isinstance(info, dict):
            address_info.update(info)
        # The two endpoints disagree on the field name for the rows array.
        rows = payload.get("data") or payload.get("token_transfers")
        if not isinstance(rows, list) or not rows:
            break
        collected.extend(r for r in rows if isinstance(r, dict))
        if len(rows) < limit:
            break
        start += limit
    return collected[:max_records], address_info


def _risk_of(address_info: dict, address: str) -> bool | None:
    """Tronscan's own per-address risk flag. None (not False) when Tronscan
    said nothing about the address -- "not flagged" and "not assessed" are
    different claims, and a police tool should not conflate them."""
    entry = address_info.get(address)
    return bool(entry.get("risk")) if isinstance(entry, dict) and "risk" in entry else None


def _native(rows: list[dict], address_info: dict | None = None) -> list[dict]:
    address_info = address_info or {}
    out = []
    for tx in rows:
        tx_hash, owner, to, amount = (tx.get("hash"), tx.get("ownerAddress"),
                                      tx.get("toAddress"), tx.get("amount"))
        if not tx_hash or not owner or not to or amount is None:
            continue  # skip anything not matching the attested schema rather than guess
        out.append({
            "tx_hash": tx_hash,
            "block_number": tx.get("block"),
            "timestamp": _to_unix_seconds(tx.get("timestamp")),
            "from_addr": owner,       # Tron addresses are base58, not lowercased like hex
            "to_addr": to,
            "value_wei": int(amount),  # SUN, the Tron equivalent of wei
            "asset_type": "TRX",
            "asset_symbol": "TRX",
            "asset_contract": "",
            "decimals": TRX_DECIMALS,
            "transfer_type": "native",
            # Tronscan names entities it recognises right here in the response.
            # This is the nearest-VASP answer the tool exists to find, and it
            # was being parsed past and discarded until now.
            "from_label": _clean_tag(tx.get("ownerAddressTag")),
            "to_label": _clean_tag(tx.get("toAddressTag")),
            "from_risk": _risk_of(address_info, owner),
            "to_risk": _risk_of(address_info, to),
        })
    return out


def _trc20(rows: list[dict], address_info: dict | None = None) -> list[dict]:
    address_info = address_info or {}
    out = []
    for tx in rows:
        info = tx.get("tokenInfo") or {}
        tx_hash = tx.get("transaction_id") or tx.get("hash")
        frm, to = tx.get("from_address"), tx.get("to_address")
        amount = tx.get("quant") if tx.get("quant") is not None else tx.get("amount_str")
        if not tx_hash or not frm or not to or amount is None:
            continue
        try:
            value = int(amount)
        except (TypeError, ValueError):
            continue  # quant arrives as a string of base units; anything else is not parseable
        out.append({
            "tx_hash": tx_hash,
            "block_number": tx.get("block"),
            "timestamp": _to_unix_seconds(tx.get("block_ts") or tx.get("timestamp")),
            "from_addr": frm,
            "to_addr": to,
            "value_wei": value,
            "asset_type": "TRX",  # the chain's native ticker, kept for back-compat
            "asset_symbol": info.get("tokenAbbr") or info.get("tokenName") or "TRC20",
            "asset_contract": tx.get("contract_address") or info.get("tokenId") or "",
            "decimals": int(info.get("tokenDecimal") or 6),
            "transfer_type": "token",
            "from_label": _clean_tag(tx.get("from_address_tag")),
            "to_label": _clean_tag(tx.get("to_address_tag")),
            "from_risk": _risk_of(address_info, frm),
            "to_risk": _risk_of(address_info, to),
        })
    return out


def fetch_transactions(address: str, api_key: str | None = None,
                       max_records: int = DEFAULT_MAX_RECORDS,
                       include_tokens: bool = True) -> list[dict]:
    """Return this address's TRX and TRC20 transfers in the common shape.

    Compare values across assets with app.assets.amount() -- TRX and USDT both
    use 6 decimals here, but other TRC20 tokens do not.
    """
    headers = _headers(api_key)

    # Two independent endpoints -- fetch concurrently rather than one after
    # the other, same fix and same reasoning as etherscan.py's three-endpoint
    # merge (measured there: ~9s sequential vs. ~3s concurrent for one address).
    with ThreadPoolExecutor(max_workers=2) as pool:
        native_future = pool.submit(_paged, "transaction", address, headers, max_records)
        trc20_future = (
            pool.submit(_paged, "token_trc20/transfers", address, headers, max_records,
                       address_param="relatedAddress")
            if include_tokens else None
        )
        native_rows, address_info = native_future.result()
        trc20_rows, trc20_info = trc20_future.result() if trc20_future is not None else ([], {})
        # Risk is a property of an address, not of the endpoint that mentioned
        # it, so both endpoints' flags apply to every row.
        address_info = {**address_info, **trc20_info}
        transfers = _native(native_rows, address_info)
        if trc20_future is not None:
            # Live-verified with a real key: /api/token_trc20/transfers silently
            # ignores `address` and returns an unrelated global feed instead of
            # erroring — it must be scoped with `relatedAddress`. Confirmed by
            # direct comparison: `address=X` returned transfers between other
            # wallets entirely; `relatedAddress=X` correctly returned X's own
            # transfers, tagged by Tronscan itself (e.g. "Binance-Hot 11"). This
            # was silently returning noise instead of the queried address's USDT
            # activity — the exact data the Tron adapter exists to see.
            transfers += _trc20(trc20_rows, address_info)

    transfers.sort(key=lambda t: (t.get("timestamp") or 0, t["tx_hash"]))
    return transfers
