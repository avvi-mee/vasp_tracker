"""Smoke test for the Blockchair client's UTXO-to-normalized-tx parsing —
mocked HTTP, no live API needed. Verifies the "follow the dominant output"
logic, since Blockchair's IP-level rate limiting made live testing flaky
(see research/01-block-explorer-apis.md — this is a documented real risk,
not a hypothetical one; we hit it during Phase 4 testing).
Run: python -m pytest tests/test_blockchair.py -v
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api_clients.blockchair import fetch_transactions

ADDRESS_DASHBOARD_RESPONSE = {
    "data": {
        "1testaddr": {
            "transactions": [
                {"hash": "txA", "time": "2026-01-01 00:00:00", "balance_change": -5000},  # outgoing
                {"hash": "txB", "time": "2026-01-02 00:00:00", "balance_change": 3000},   # incoming, skip
            ]
        }
    }
}

TX_DETAIL_RESPONSE = {
    "data": {
        "txA": {
            "transaction": {"block_id": 800000},
            "outputs": [
                {"recipient": "1changeaddr", "value": 500},   # small — likely change, not dominant
                {"recipient": "1testaddr", "value": 100},      # self — excluded
                {"recipient": "1destination", "value": 4400},  # largest — the dominant hop
            ],
        }
    }
}


def _mock_response(json_data):
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


@patch("app.api_clients.blockchair.requests.get")
def test_follows_dominant_output_and_skips_incoming(mock_get):
    mock_get.side_effect = [_mock_response(ADDRESS_DASHBOARD_RESPONSE), _mock_response(TX_DETAIL_RESPONSE)]

    txs = fetch_transactions("1testaddr")

    assert len(txs) == 1  # only the outgoing tx (txB was incoming, correctly skipped)
    tx = txs[0]
    assert tx["from_addr"] == "1testaddr"
    assert tx["to_addr"] == "1destination"   # the largest output, not the change address
    assert tx["value_wei"] == 4400
    assert tx["asset_type"] == "BTC"
