"""Smoke test for the Solana client's parsed-transfer extraction — mocked
JSON-RPC, no live network needed. Field names verified against live Solana
docs (solana.com/docs/rpc/http/gettransaction), not guessed.
Run: python -m pytest tests/test_solana.py -v
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api_clients.solana import fetch_transactions

SIGNATURES_RESULT = [
    {"signature": "sig1", "slot": 100, "blockTime": 1700000000, "err": None},
    {"signature": "sig2", "slot": 101, "blockTime": 1700000100, "err": "some error"},  # skipped
]

TRANSFER_TX = {
    "slot": 100, "blockTime": 1700000000,
    "transaction": {"message": {"instructions": [
        {"program": "system", "parsed": {"type": "transfer",
                                          "info": {"source": "SRC111", "destination": "DST111", "lamports": 5000000}}},
        {"program": "spl-token", "parsed": {"type": "transfer", "info": {"amount": "999"}}},  # not System — skipped
    ]}},
}


def _mock_post(*json_bodies):
    """Returns a mock whose .json() cycles through the given bodies per call."""
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    responses = [{"jsonrpc": "2.0", "id": 1, "result": body} for body in json_bodies]
    resp.json.side_effect = responses
    return resp


@patch("app.api_clients.solana.requests.post")
def test_extracts_only_system_program_transfers(mock_post):
    mock_post.side_effect = [
        _mock_post(SIGNATURES_RESULT),
        _mock_post(TRANSFER_TX),
    ]

    txs = fetch_transactions("SEEDADDR111")

    assert len(txs) == 1  # sig2 (err) skipped; spl-token instruction ignored
    tx = txs[0]
    assert tx["from_addr"] == "SRC111"
    assert tx["to_addr"] == "DST111"
    assert tx["value_wei"] == 5000000
    assert tx["asset_type"] == "SOL"
    assert tx["tx_hash"] == "sig1"
