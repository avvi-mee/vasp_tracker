"""Ranked-candidate search behavior added this session: converging paths get
merged into one candidate, and the frontier cap's drops are recorded as a
caveat instead of vanishing silently. No network calls.
Run: python -m pytest tests/test_trace_candidates.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.trace import trace_to_nearest_entity

EXCHANGE = "0xexchange"


def tx(frm, to, value, h):
    return {"from_addr": frm, "to_addr": to, "value_wei": value, "tx_hash": h}


def test_converging_branches_merge_into_one_candidate():
    """SEED -> A (60%) and SEED -> B (40%), both of which forward everything
    to the same labeled exchange. Two independent paths, one true entity —
    the report should say so once, with the shares summed, not list the same
    exchange twice."""
    ledger = {
        "0xseed": [tx("0xseed", "0xa", 60, "t1"), tx("0xseed", "0xb", 40, "t2")],
        "0xa": [tx("0xa", EXCHANGE, 60, "t3")],
        "0xb": [tx("0xb", EXCHANGE, 40, "t4")],
    }
    labels = {("ETH", EXCHANGE): {"label": "Test Exchange", "category": "exchange",
                                   "source": "unit-test", "is_cluster_definer": False}}

    result = trace_to_nearest_entity(
        seed_address="0xseed", currency="ETH",
        fetch_transactions_fn=lambda a: ledger.get(a, []),
        labels_lookup=labels, mixers_lookup={}, max_hops=4,
    )

    exchange_candidates = [c for c in result.candidates if c.label == "Test Exchange"]
    assert len(exchange_candidates) == 1
    merged = exchange_candidates[0]
    assert merged.merged_path_count == 2
    assert merged.value_share == 1.0  # 0.6 + 0.4, the whole seed's value accounted for


def test_unlabeled_dead_ends_are_never_merged():
    """Two different unresolved addresses are not "the same entity" just
    because both terminated as unknown."""
    ledger = {
        "0xseed": [tx("0xseed", "0xa", 60, "t1"), tx("0xseed", "0xb", 40, "t2")],
    }
    result = trace_to_nearest_entity(
        seed_address="0xseed", currency="ETH",
        fetch_transactions_fn=lambda a: ledger.get(a, []),
        labels_lookup={}, mixers_lookup={}, max_hops=4,
    )
    assert len(result.candidates) == 2
    assert all(c.label is None for c in result.candidates)


def test_frontier_cap_records_a_caveat_instead_of_vanishing():
    """3 branches at hop 0, each splitting 3 ways at hop 1 -> 9 live branches,
    one over the 8-branch cap. The dropped branch must show up as a caveat,
    not just disappear with the total value_share silently short of 1.0."""
    ledger = {"0xseed": [tx("0xseed", f"0x{c}", amt, f"seed-{c}")
                         for c, amt in zip("abc", (40, 35, 25))]}
    for parent in "abc":
        ledger[f"0x{parent}"] = [tx(f"0x{parent}", f"0x{parent}{i}", amt, f"{parent}-{i}")
                                 for i, amt in zip((1, 2, 3), (40, 35, 25))]

    result = trace_to_nearest_entity(
        seed_address="0xseed", currency="ETH",
        fetch_transactions_fn=lambda a: ledger.get(a, []),
        labels_lookup={}, mixers_lookup={}, max_hops=4,
    )

    assert len(result.candidates) == 8  # 9 branches spawned, 1 pruned
    assert result.caveats
    assert "not followed" in result.caveats[0]
    total_share = sum(c.value_share for c in result.candidates)
    assert total_share < 1.0  # the dropped branch's share is honestly missing, not hidden
