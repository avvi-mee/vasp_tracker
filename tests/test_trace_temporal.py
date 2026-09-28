"""The trace must not follow money backwards in time.

The bug (REVIEW.md defect 2): an outflow from B that happened BEFORE the
seed's funds reached B was followed anyway, so the trace "reached CoinDCX"
through a payment that cannot have carried the suspect's money.

Run: python -m pytest tests/test_trace_temporal.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.trace import trace_to_nearest_entity

LABELS = {("ETH", "0xexch"): {"label": "CoinDCX", "category": "exchange", "source": "t"}}


def _fetch(rows):
    def fetch(address):
        return [r for r in rows if address in (r["from_addr"], r["to_addr"])]
    return fetch


def test_outflow_before_the_funds_arrived_is_not_followed():
    rows = [
        {"from_addr": "0xseed", "to_addr": "0xmid", "value_wei": 100, "tx_hash": "in", "timestamp": 100},
        {"from_addr": "0xmid", "to_addr": "0xexch", "value_wei": 100, "tx_hash": "old", "timestamp": 50},
    ]
    result = trace_to_nearest_entity("0xseed", "ETH", _fetch(rows), LABELS, {}, max_hops=4)
    assert result.label is None
    assert result.entity_type == "unknown"


def test_outflow_after_the_funds_arrived_is_followed():
    rows = [
        {"from_addr": "0xseed", "to_addr": "0xmid", "value_wei": 100, "tx_hash": "in", "timestamp": 100},
        {"from_addr": "0xmid", "to_addr": "0xexch", "value_wei": 100, "tx_hash": "new", "timestamp": 150},
    ]
    result = trace_to_nearest_entity("0xseed", "ETH", _fetch(rows), LABELS, {}, max_hops=4)
    assert result.label == "CoinDCX"


def test_missing_timestamps_do_not_block_the_trace():
    rows = [
        {"from_addr": "0xseed", "to_addr": "0xmid", "value_wei": 100, "tx_hash": "in"},
        {"from_addr": "0xmid", "to_addr": "0xexch", "value_wei": 100, "tx_hash": "x", "timestamp": 50},
    ]
    result = trace_to_nearest_entity("0xseed", "ETH", _fetch(rows), LABELS, {}, max_hops=4)
    assert result.label == "CoinDCX"
