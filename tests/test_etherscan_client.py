"""Smoke test for the Etherscan V2 client's multi-chain support (Ethereum +
Polygon share this one client via chainid) — mocked HTTP, no live API needed.
Run: python -m pytest tests/test_etherscan_client.py -v
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api_clients.etherscan import fetch_transactions, ETH_CHAIN_ID, POLYGON_CHAIN_ID

FAKE_RESPONSE = {
    "status": "1", "message": "OK",
    "result": [{
        "hash": "0xabc", "blockNumber": "100", "timeStamp": "1700000000",
        "from": "0xAAA", "to": "0xBBB", "value": "1000000000000000000",
    }],
}


def _mock_get(json_data):
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


@patch("app.api_clients.etherscan.requests.get")
def test_polygon_uses_correct_chainid_and_asset_type(mock_get):
    mock_get.return_value = _mock_get(FAKE_RESPONSE)

    txs = fetch_transactions("0xaaa", api_key="fake", chainid=POLYGON_CHAIN_ID, asset_type="MATIC")

    assert mock_get.call_args.kwargs["params"]["chainid"] == POLYGON_CHAIN_ID
    assert txs[0]["asset_type"] == "MATIC"
    assert txs[0]["from_addr"] == "0xaaa"
    assert txs[0]["to_addr"] == "0xbbb"


@patch("app.api_clients.etherscan.requests.get")
def test_defaults_to_ethereum_mainnet(mock_get):
    mock_get.return_value = _mock_get(FAKE_RESPONSE)
    fetch_transactions("0xaaa", api_key="fake")
    assert mock_get.call_args.kwargs["params"]["chainid"] == ETH_CHAIN_ID
