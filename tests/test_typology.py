"""Laundering typology detection — synthetic fixtures, no network.

Validated against two real addresses as well (see the plan's verification
step): the Tron scam address TNnrfcBk7WXJtKFHC76m7V8oAP9V98k5P5 fires
many_to_one_funnel (16 funders -> 1 destination) and rapid_layering (median
11-minute hold over 18 sweeps). Those numbers are reproduced below as a
fixture so the check survives without a live API key.

Run: python -m pytest tests/test_typology.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

from app.graph.trace import Candidate, TraceResult
from app.graph.typology import detect, highest_severity

SEED = "0xseed"
HOUR = 3600


def _tx(frm, to, value, ts, tx_hash="0xh"):
    return {"tx_hash": tx_hash, "from_addr": frm, "to_addr": to, "value_wei": int(value * 10**6),
            "timestamp": ts, "decimals": 6, "asset_symbol": "USDT", "asset_contract": "0xusdt",
            "block_number": 1}


def _result(seed=SEED, candidates=None, graph=None):
    return TraceResult(seed_address=seed, path=[seed], graph=graph or nx.DiGraph(),
                       hop_count=0, entity_type="unknown", label=None, confidence=0.0,
                       candidates=candidates or [])


def _names(typologies):
    return {t.name for t in typologies}


# --- many-to-one funnel ----------------------------------------------------

def test_funnel_fires_on_many_funders_and_one_destination():
    """The real scam address's shape: 16 payers in, one exchange out."""
    txs = [_tx(f"0xvictim{i}", SEED, 500, 1000 + i * 60) for i in range(16)]
    txs += [_tx(SEED, "0xexchange", 500, 1200 + i * 60) for i in range(16)]

    found = detect(_result(), txs)
    funnel = next(t for t in found if t.name == "many_to_one_funnel")
    assert funnel.severity == "high"  # >= 15 distinct funders
    assert funnel.stats["distinct_funders"] == 16
    assert funnel.stats["distinct_destinations"] == 1


def test_funnel_does_not_fire_on_ordinary_two_party_activity():
    txs = [_tx("0xalice", SEED, 100, 1000), _tx(SEED, "0xbob", 100, 2000)]
    assert "many_to_one_funnel" not in _names(detect(_result(), txs))


def test_funnel_does_not_fire_when_funds_go_many_places():
    """Many in AND many out is a hub, not a collection point — different shape,
    and the fan-out detector is the one that should have an opinion on it."""
    txs = [_tx(f"0xin{i}", SEED, 100, 1000 + i) for i in range(10)]
    txs += [_tx(SEED, f"0xout{i}", 100, 2000 + i) for i in range(10)]
    assert "many_to_one_funnel" not in _names(detect(_result(), txs))


# --- rapid layering --------------------------------------------------------

def test_rapid_layering_fires_on_short_holds_and_full_forwarding():
    txs = []
    for i in range(12):
        txs.append(_tx(f"0xin{i}", SEED, 1000, i * HOUR))
        txs.append(_tx(SEED, "0xnext", 1000, i * HOUR + 600))  # swept 10 min later
    layering = next(t for t in detect(_result(), txs) if t.name == "rapid_layering")
    assert layering.severity == "high"  # <= 10 min median across >= 10 sweeps
    assert layering.stats["median_hold_seconds"] == 600


def test_rapid_layering_does_not_fire_when_funds_rest():
    txs = []
    for i in range(12):
        txs.append(_tx(f"0xin{i}", SEED, 1000, i * 30 * HOUR))
        txs.append(_tx(SEED, "0xnext", 1000, i * 30 * HOUR + 20 * HOUR))  # held 20 hours
    assert "rapid_layering" not in _names(detect(_result(), txs))


def test_rapid_layering_does_not_fire_when_most_value_stays_put():
    """A wallet that keeps 90% of what it receives is not a conduit, however
    quickly it moves the other 10%."""
    txs = []
    for i in range(12):
        txs.append(_tx(f"0xin{i}", SEED, 1000, i * HOUR))
        txs.append(_tx(SEED, "0xnext", 50, i * HOUR + 300))
    assert "rapid_layering" not in _names(detect(_result(), txs))


# --- fan-out / smurfing ----------------------------------------------------

def test_fan_out_fires_on_many_near_equal_splits():
    txs = [_tx("0xfunder", SEED, 10_000, 0)]
    txs += [_tx(SEED, f"0xmule{i}", 500 + (i % 3), 1000 + i * 60) for i in range(24)]
    fan = next(t for t in detect(_result(), txs) if t.name == "fan_out_smurfing")
    assert fan.severity == "high"  # >= 20 destinations
    assert fan.stats["destinations"] == 24
    assert fan.stats["coefficient_of_variation"] < 0.35


def test_fan_out_does_not_fire_on_lopsided_splits():
    """One big payment plus small change is normal spending, not structuring."""
    txs = [_tx(SEED, "0xbig", 100_000, 1000)]
    txs += [_tx(SEED, f"0xsmall{i}", 5, 1000 + i) for i in range(10)]
    assert "fan_out_smurfing" not in _names(detect(_result(), txs))


def test_fan_out_does_not_fire_when_spread_over_months():
    txs = [_tx(SEED, f"0xdest{i}", 500, i * 20 * 24 * HOUR) for i in range(12)]
    assert "fan_out_smurfing" not in _names(detect(_result(), txs))


# --- peel chain ------------------------------------------------------------

def _peel_graph(amounts):
    g = nx.DiGraph()
    path = [SEED] + [f"0xhop{i}" for i in range(1, len(amounts) + 1)]
    for (src, dst), value in zip(zip(path, path[1:]), amounts):
        g.add_edge(src, dst, amount=value, tx_hash="0xh", value_wei=int(value * 10**6))
    return g, path


def test_peel_chain_fires_on_a_long_slowly_decreasing_run():
    graph, path = _peel_graph([1000, 940, 890, 850, 800])
    result = _result(candidates=[Candidate(path, 5, "unknown", None, 0.0, None, None, None, None, 1.0)],
                     graph=graph)
    peel = next(t for t in detect(result, []) if t.name == "peel_chain")
    assert peel.stats["hops"] == 5
    assert peel.stats["retained"] == 200  # 1000 in, 800 still moving


def test_peel_chain_does_not_fire_on_a_big_drop():
    """Losing 90% at one hop is a split, not a peel — the bulk went elsewhere
    and following the remainder would be following the wrong money."""
    graph, path = _peel_graph([1000, 900, 80, 70])
    result = _result(candidates=[Candidate(path, 4, "unknown", None, 0.0, None, None, None, None, 1.0)],
                     graph=graph)
    assert "peel_chain" not in _names(detect(result, []))


def test_peel_chain_does_not_fire_on_a_short_hop():
    graph, path = _peel_graph([1000, 950])
    result = _result(candidates=[Candidate(path, 2, "unknown", None, 0.0, None, None, None, None, 1.0)],
                     graph=graph)
    assert "peel_chain" not in _names(detect(result, []))


# --- round-amount structuring ---------------------------------------------

def test_structuring_fires_on_repeated_identical_round_amounts():
    txs = [_tx(SEED, f"0xdest{i}", 9000, 1000 + i * HOUR) for i in range(6)]
    s = next(t for t in detect(_result(), txs) if t.name == "round_amount_structuring")
    assert s.stats["amount"] == 9000
    assert s.stats["repeats"] == 6
    assert s.severity == "medium"  # every outgoing transfer is the same round figure


def test_structuring_ignores_organic_amounts():
    txs = [_tx(SEED, f"0xdest{i}", 1234.56 + i, 1000 + i * HOUR) for i in range(8)]
    assert "round_amount_structuring" not in _names(detect(_result(), txs))


# --- ordering, asset scoping, and the empty case ---------------------------

def test_results_are_ordered_worst_first():
    txs = [_tx(f"0xvictim{i}", SEED, 500, 1000 + i * 60) for i in range(16)]
    txs += [_tx(SEED, "0xexchange", 500, 1200 + i * 60) for i in range(16)]
    found = detect(_result(), txs)
    assert found[0].severity == "high"
    assert highest_severity(found) == "high"


def test_asset_filter_keeps_scales_from_being_mixed():
    """An ETH transfer and a USDT transfer must never be counted in the same
    total — the same rule the rest of the project follows."""
    usdt = [_tx(f"0xin{i}", SEED, 500, 1000 + i) for i in range(16)]
    usdt += [_tx(SEED, "0xexchange", 500, 2000 + i) for i in range(16)]
    eth = [{**_tx("0xother", SEED, 1, 3000), "asset_symbol": "ETH", "asset_contract": "", "decimals": 18}]
    found = detect(_result(), usdt + eth, asset=("USDT", "0xusdt"))
    funnel = next(t for t in found if t.name == "many_to_one_funnel")
    assert funnel.stats["distinct_funders"] == 16  # the ETH sender is not counted


def test_quiet_wallet_produces_no_findings():
    txs = [_tx("0xalice", SEED, 100, 1000), _tx(SEED, "0xbob", 40, 90 * HOUR)]
    assert detect(_result(), txs) == []
    assert highest_severity([]) == "none"


def test_no_transactions_at_all_is_not_a_crash():
    assert detect(_result(), []) == []


def test_a_truncated_history_does_not_print_a_nonsense_forwarding_ratio():
    """Live: Binance's Tron hot wallet computed 345977% forwarded, because the
    600-row fetch window caught outbound transfers whose matching inbound ones
    fell outside it. A police report cannot carry that number."""
    txs = [_tx("0xin", SEED, 1, 0)]
    txs += [_tx(SEED, "0xnext", 1000, i * 60 + 30) for i in range(20)]

    layering = next(t for t in detect(_result(), txs) if t.name == "rapid_layering")

    assert layering.stats["sample_truncated"] is True
    assert "truncated" in layering.explanation
    assert "%" not in layering.explanation  # no 2,000,000% figure anywhere in the prose
    assert layering.severity == "medium"  # short holds still shown, strongest reading withheld


def test_an_untruncated_sample_still_states_the_ratio():
    txs = []
    for i in range(12):
        txs.append(_tx(f"0xin{i}", SEED, 1000, i * HOUR))
        txs.append(_tx(SEED, "0xnext", 1000, i * HOUR + 300))
    layering = next(t for t in detect(_result(), txs) if t.name == "rapid_layering")
    assert layering.stats["sample_truncated"] is False
    assert "100% of everything received was forwarded on" in layering.explanation
