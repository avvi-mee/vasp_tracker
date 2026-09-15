"""Regression test: Tron addresses are case-sensitive base58, unlike
Ethereum's case-insensitive hex — a naive .lower() everywhere would
silently corrupt Tron matching. This locks in the fix in both
app/graph/trace.py and app/data/tagpacks.py.
Run: python -m pytest tests/test_address_case_sensitivity.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.trace import trace_to_nearest_entity
from app.data.tagpacks import lookup_address


def test_tron_label_lookup_is_case_sensitive_and_matches():
    # Real-shaped Tron address (mixed-case base58) — must match itself exactly.
    labels = {("TRX", "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"):
              {"label": "Test Tron Exchange", "category": "exchange", "source": "unit-test",
               "confidence": "high", "is_cluster_definer": False}}
    hit = lookup_address(labels, "TRX", "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9")
    assert hit is not None
    assert hit["label"] == "Test Tron Exchange"


def test_trace_preserves_tron_address_case_through_hops():
    def fake_fetch(address):
        if address == "TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA":
            return [{"from_addr": "TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                     "to_addr": "TBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
                     "value_wei": 100, "tx_hash": "t1"}]
        return []

    labels = {("TRX", "TBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"):
              {"label": "Test Exchange", "category": "exchange", "source": "unit-test",
               "confidence": "high", "is_cluster_definer": False}}

    result = trace_to_nearest_entity(
        seed_address="TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", currency="TRX",
        fetch_transactions_fn=fake_fetch, labels_lookup=labels, mixers_lookup={}, max_hops=4,
    )
    # If case had been lowercased, this wouldn't match the labels dict (real base58 is case-sensitive)
    assert result.entity_type == "exchange"
    assert result.path == ["TAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "TBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"]


def test_ethereum_address_still_matches_case_insensitively():
    labels = {("ETH", "0xaaa"): {"label": "Test Exchange", "category": "exchange",
                                 "source": "unit-test", "confidence": "high", "is_cluster_definer": False}}
    hit = lookup_address(labels, "ETH", "0xAAA")  # different case than stored
    assert hit is not None
    assert hit["label"] == "Test Exchange"
