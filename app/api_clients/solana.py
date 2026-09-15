"""Solana JSON-RPC client — free public mainnet endpoint, no key required.

Solana has no simple from/to like Ethereum; transactions contain multiple
instructions. We only follow native SOL transfers (System Program
"transfer" instructions) — the same two-step pattern as Bitcoin/Blockchair:
list an address's transaction signatures, then fetch each one's parsed
detail to extract the actual transfer.

SPL token transfers (the Solana equivalent of ERC-20 — very common in
practice, e.g. USDC-SPL) are NOT covered here; that's a real, documented
gap (different instruction shape, "spl-token" program), not built yet.

Docs verified live: solana.com/docs/rpc/http/getsignaturesforaddress,
solana.com/docs/rpc/http/gettransaction. Public endpoint rate limit is
~10 req/sec per IP, no SLA — fine for occasional demo use, not production.
"""
import requests

RPC_URL = "https://api.mainnet-beta.solana.com"
SYSTEM_PROGRAM = "system"


def _rpc(method: str, params: list) -> dict:
    resp = requests.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                          timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    if "error" in payload:
        raise RuntimeError(f"Solana RPC error: {payload['error']}")
    return payload.get("result")


def fetch_transactions(address: str, max_records: int = 20) -> list[dict]:
    signatures = _rpc("getSignaturesForAddress", [address, {"limit": max_records}]) or []

    normalized = []
    for sig_info in signatures:
        signature = sig_info.get("signature")
        if not signature or sig_info.get("err"):
            continue  # skip failed transactions

        try:
            tx = _rpc("getTransaction", [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
        except (requests.RequestException, RuntimeError):
            continue  # one bad lookup shouldn't kill the whole trace

        if not tx:
            continue
        instructions = (tx.get("transaction", {}).get("message", {}) or {}).get("instructions", [])
        for instr in instructions:
            if not isinstance(instr, dict) or instr.get("program") != SYSTEM_PROGRAM:
                continue
            parsed = instr.get("parsed") or {}
            if parsed.get("type") != "transfer":
                continue
            info = parsed.get("info") or {}
            source, destination, lamports = info.get("source"), info.get("destination"), info.get("lamports")
            if not source or not destination or lamports is None:
                continue
            normalized.append({
                "tx_hash": signature,
                "block_number": tx.get("slot"),
                "timestamp": tx.get("blockTime"),
                "from_addr": source,
                "to_addr": destination,
                "value_wei": lamports,
                "asset_type": "SOL",
            })
    return normalized
