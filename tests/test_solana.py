"""Smoke test for the Helius-backed Solana client — mocked HTTP response, no
live network needed. Response shape is copied from a real, live-verified
Helius call (see solana.py's docstring), not guessed.
Run: python -m pytest tests/test_solana.py -v
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app.api_clients.solana import fetch_transactions

# Shaped exactly like a real Helius /v0/addresses/{address}/transactions
# response: one native SOL transfer, one USDC-SPL transfer, one failed tx
# that must be skipped.
TRANSACTIONS = [
    {
        "signature": "sig1", "slot": 100, "timestamp": 1700000000, "transactionError": None,
        "nativeTransfers": [{"fromUserAccount": "SRC111", "toUserAccount": "DST111", "amount": 5000000}],
        "tokenTransfers": [],
    },
    {
        "signature": "sig2", "slot": 101, "timestamp": 1700000100, "transactionError": None,
        "nativeTransfers": [],
        "tokenTransfers": [{
            "fromUserAccount": "SRC222", "toUserAccount": "DST222", "tokenAmount": 250.5,
            "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        }],
    },
    {
        "signature": "sig3", "slot": 102, "timestamp": 1700000200, "transactionError": "some error",
        "nativeTransfers": [{"fromUserAccount": "SRC333", "toUserAccount": "DST333", "amount": 1}],
        "tokenTransfers": [],
    },
]


def _mock_get(json_body):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = json_body
    return resp


@patch.dict("os.environ", {"HELIUS_API_KEY": "test-key"})
@patch("app.api_clients.solana.requests.get")
def test_native_and_spl_transfers_are_both_extracted(mock_get):
    mock_get.return_value = _mock_get(TRANSACTIONS)

    txs = fetch_transactions("SEEDADDR111")

    assert len(txs) == 2  # sig3's failed transaction is dropped
    native, token = txs[0], txs[1]

    assert native["from_addr"] == "SRC111" and native["to_addr"] == "DST111"
    assert native["value_wei"] == 5000000
    assert native["decimals"] == 9  # lamports
    assert native["transfer_type"] == "native"

    assert token["from_addr"] == "SRC222" and token["to_addr"] == "DST222"
    assert token["value_wei"] == 250.5  # Helius already returns this decimal-scaled
    assert token["decimals"] == 0       # so amount() must not rescale it again
    assert token["asset_symbol"] == "USDC"
    assert token["transfer_type"] == "token"


@patch.dict("os.environ", {"HELIUS_API_KEY": ""}, clear=True)
def test_missing_api_key_fails_loud_not_silent():
    with pytest.raises(RuntimeError, match="HELIUS_API_KEY"):
        fetch_transactions("SEEDADDR111")
