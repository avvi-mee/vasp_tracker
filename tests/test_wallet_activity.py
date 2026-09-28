"""app/api/main.py's _wallet_activity() — the seed address's own direct
counterparties, both directions, separate from the ranked-candidate search's
forward-only path. The trace graph never had an edge pointing INTO the seed,
so a wallet funded by 30 people showed nothing pointing at it; this is what
fixes that.

Run: python -m pytest tests/test_wallet_activity.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

import app.api.main as api_main
from app.graph.trace import TraceResult

SEED = "0xseed"


def _tx(frm, to, value, ts, asset="USDT", contract="0xusdt", decimals=6, tx_hash="0xh"):
    return {"tx_hash": tx_hash, "from_addr": frm, "to_addr": to, "value_wei": int(value * 10**decimals),
            "timestamp": ts, "decimals": decimals, "asset_symbol": asset, "asset_contract": contract,
            "block_number": 1}


def _result(asset=("USDT", "0xusdt")):
    return TraceResult(seed_address=SEED, path=[SEED], graph=nx.DiGraph(), hop_count=0,
                       entity_type="unknown", label=None, confidence=0.0, asset=asset)


def test_incoming_and_outgoing_are_both_present_and_correctly_directed():
    """The regression this module exists for: incoming edges must point
    INTO the seed, and must appear at all -- the trace graph alone never
    produced them."""
    txs = [_tx("0xfunder1", SEED, 100, 1000), _tx(SEED, "0xdest1", 40, 2000)]
    wa = api_main._wallet_activity(_result(), txs)

    in_edges = [e for e in wa["edges"] if e["direction"] == "in"]
    out_edges = [e for e in wa["edges"] if e["direction"] == "out"]
    assert in_edges == [{"from": "0xfunder1", "to": SEED, "tx_hash": "0xh", "value_wei": 100_000_000,
                         "amount": 100.0, "asset": "USDT", "timestamp": 1000, "block_number": 1,
                         "direction": "in"}]
    assert out_edges[0]["from"] == SEED and out_edges[0]["to"] == "0xdest1"


def test_multiple_transfers_from_one_counterparty_are_summed_not_listed_twice():
    txs = [_tx("0xfunder1", SEED, 100, 1000, tx_hash="0xa"),
           _tx("0xfunder1", SEED, 250, 1100, tx_hash="0xb")]
    wa = api_main._wallet_activity(_result(), txs)

    assert len(wa["edges"]) == 1
    assert wa["edges"][0]["amount"] == 350.0
    assert wa["incoming_shown"] == 1
    assert wa["incoming_total"] == 1  # one distinct counterparty, not two rows


def test_representative_transaction_is_the_counterpartys_largest_single_transfer():
    txs = [_tx("0xfunder1", SEED, 10, 1000, tx_hash="0xsmall"),
           _tx("0xfunder1", SEED, 900, 1100, tx_hash="0xbig")]
    wa = api_main._wallet_activity(_result(), txs)
    assert wa["edges"][0]["tx_hash"] == "0xbig"


def test_ranked_biggest_first_and_capped_with_total_reported():
    """Real case this fixes: TNnrfcBk7WXJtKFHC76m7V8oAP9V98k5P5 has 16
    distinct funders; the graph used to show 1 edge total. Cap is 15, so
    this pins the cap AND that the 16th (smallest) is the one dropped, with
    the true total still reported rather than silently truncated."""
    txs = [_tx(f"0xfunder{i}", SEED, 100 - i, 1000 + i) for i in range(16)]
    wa = api_main._wallet_activity(_result(), txs)

    assert wa["incoming_shown"] == 15
    assert wa["incoming_total"] == 16
    amounts = [e["amount"] for e in wa["edges"] if e["direction"] == "in"]
    assert amounts == sorted(amounts, reverse=True)
    assert amounts[-1] == 100 - 14  # funder15 (value 100-15=85) was the one dropped, not funder14


def test_asset_filter_keeps_a_different_asset_from_being_summed_in():
    """Never sum raw values across assets of different decimal scale --
    the same rule the rest of this project follows everywhere else."""
    txs = [_tx("0xfunder1", SEED, 500, 1000, asset="USDT", contract="0xusdt"),
           _tx("0xother", SEED, 5, 1100, asset="ETH", contract="", decimals=18)]
    wa = api_main._wallet_activity(_result(asset=("USDT", "0xusdt")), txs)

    assert wa["incoming_total"] == 1
    assert wa["edges"][0]["asset"] == "USDT"


def test_falls_back_to_the_dominant_asset_when_the_trace_never_picked_one():
    """A hop-0 terminal match (the seed itself is already labelled) never
    sets result.asset -- this must not crash, and must not silently mix
    every asset the wallet ever touched into one meaningless total."""
    # The real Ethereum USDT contract: app/assets.py only lets canonical
    # token contracts compete with native coins for "dominant".
    usdt = "0xdac17f958d2ee523a2206206994597c13d831ec7"
    txs = [_tx("0xfunder1", SEED, 500, 1000, asset="USDT", contract=usdt),
           _tx("0xfunder2", SEED, 500, 1100, asset="USDT", contract=usdt),
           _tx("0xother", SEED, 1, 1200, asset="ETH", contract="", decimals=18)]
    wa = api_main._wallet_activity(_result(asset=None), txs)
    assert all(e["asset"] == "USDT" for e in wa["edges"])


def test_zero_value_transfers_are_excluded():
    txs = [_tx("0xfunder1", SEED, 0, 1000), _tx("0xfunder2", SEED, 50, 1100)]
    wa = api_main._wallet_activity(_result(), txs)
    assert wa["incoming_total"] == 1


def test_no_transactions_is_not_a_crash():
    wa = api_main._wallet_activity(_result(), [])
    assert wa == {"edges": [], "incoming_shown": 0, "incoming_total": 0,
                  "outgoing_shown": 0, "outgoing_total": 0}
