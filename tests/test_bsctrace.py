"""Smoke test for the BSCTrace client's response parsing — mocked HTTP,
no live API key needed (none has been provisioned yet — see the module
docstring in app/api_clients/bsctrace.py for why this is the one client
in this codebase not yet exercised against a real response).
Run: python -m pytest tests/test_bsctrace.py -v
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api_clients.bsctrace import fetch_transactions

FAKE_RESPONSE = {
    "jsonrpc": "2.0", "id": 1,
    "result": {"transfers": [
        {"hash": "0xabc", "from": "0xAAA", "to": "0xBBB", "value": "0xDE0B6B3A7640000",
         "blockNum": "0x64", "blockTimeStamp": "0x670f0000", "category": "external"},
    ]},
}


@patch("app.api_clients.bsctrace.requests.post")
def test_parses_hex_value_and_normalizes_fields(mock_post):
    resp = MagicMock()
    resp.json.return_value = FAKE_RESPONSE
    resp.raise_for_status.return_value = None
    mock_post.return_value = resp

    txs = fetch_transactions("0xaaa", api_key="fake-key")

    assert len(txs) == 1
    tx = txs[0]
    assert tx["from_addr"] == "0xaaa"
    assert tx["to_addr"] == "0xbbb"
    assert tx["value_wei"] == int("0xDE0B6B3A7640000", 16)  # 1 BNB in wei
    assert tx["asset_type"] == "BNB"


def test_raises_clear_error_without_api_key():
    import os
    os.environ.pop("NODEREAL_API_KEY", None)
    try:
        fetch_transactions("0xaaa", api_key=None)
        assert False, "should have raised"
    except RuntimeError as e:
        assert "NODEREAL_API_KEY" in str(e)
