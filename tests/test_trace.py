"""Smoke test for the multi-hop trace engine — no network calls.
Run: python -m pytest tests/test_trace.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.trace import trace_to_nearest_entity


def fake_fetch(address: str) -> list[dict]:
    """A -> B -> C (labeled exchange). Two hops."""
    chain = {
        "0xaaa": [{"from_addr": "0xaaa", "to_addr": "0xbbb", "value_wei": 100, "tx_hash": "t1"}],
        "0xbbb": [{"from_addr": "0xbbb", "to_addr": "0xccc", "value_wei": 90, "tx_hash": "t2"}],
    }
    return chain.get(address, [])


def test_trace_finds_labeled_exchange_after_two_hops():
    labels = {("ETH", "0xccc"): {"label": "Test Exchange", "category": "exchange",
                                  "source": "unit-test", "confidence": "high", "is_cluster_definer": False}}
    result = trace_to_nearest_entity(
        seed_address="0xaaa", currency="ETH",
        fetch_transactions_fn=fake_fetch,
        labels_lookup=labels, mixers_lookup={}, max_hops=4,
    )
    assert result.entity_type == "exchange"
    assert result.label == "Test Exchange"
    assert result.hop_count == 2
    assert result.path == ["0xaaa", "0xbbb", "0xccc"]
    assert 0.3 <= result.confidence <= 0.95


def test_trace_reports_unknown_on_dead_end():
    result = trace_to_nearest_entity(
        seed_address="0xccc", currency="ETH",  # 0xccc has no outgoing txs in fake_fetch
        fetch_transactions_fn=fake_fetch,
        labels_lookup={}, mixers_lookup={}, max_hops=4,
    )
    assert result.entity_type == "unknown"
    assert result.label is None
    assert "dead end" in result.reason


def test_trace_flags_known_mixer_immediately():
    mixers = {("ETH", "0xaaa"): "Test Mixer"}
    result = trace_to_nearest_entity(
        seed_address="0xaaa", currency="ETH",
        fetch_transactions_fn=fake_fetch,
        labels_lookup={}, mixers_lookup=mixers, max_hops=4,
    )
    assert result.entity_type == "mixer"
    assert result.hop_count == 0
