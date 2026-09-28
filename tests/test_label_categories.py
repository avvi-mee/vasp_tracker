"""Uncategorised labels must never be read as "exchange".

The bug (REVIEW.md defect 1): 81,815 GraphSense labels carry no `category` —
they are ransomware (Locky, Ryuk, Conti), sextortion, "defi fraud", "upbit
hack", terrorism campaigns — and trace.py defaulted every one of them to
"exchange". The trail then scored risk "none" and the UI offered a
disclosure-target badge for a ransomware wallet. GraphSense marks these with
an `abuse` field the loader was dropping.

Run: python -m pytest tests/test_label_categories.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

from app.data.chain_native_labels import categorize
from app.data.tagpacks import load_labels
from app.graph.risk import assess
from app.graph.trace import TraceResult, trace_to_nearest_entity


def _one_hop(address):
    return {"0xaaa": [{"from_addr": "0xaaa", "to_addr": "0xbbb", "value_wei": 100, "tx_hash": "t1"}]}.get(address, [])


def _trace(label_rec):
    return trace_to_nearest_entity("0xaaa", "ETH", _one_hop, {("ETH", "0xbbb"): label_rec}, {}, max_hops=3)


def test_loader_keeps_the_abuse_field(tmp_path):
    packs = tmp_path / "packs"
    packs.mkdir()
    (packs / "r.yaml").write_text(
        "label: Locky\ncurrency: BTC\nabuse: ransomware\nconfidence: forensic\n"
        "tags:\n  - address: 1abc\n", encoding="utf-8")
    rec = load_labels(packs, use_cache=False)[("BTC", "1abc")]
    assert rec["abuse"] == "ransomware"


def test_uncategorised_label_with_abuse_is_illicit_not_exchange():
    result = _trace({"label": "Locky", "category": None, "abuse": "ransomware", "source": "t"})
    assert result.entity_type == "illicit"


def test_uncategorised_label_without_abuse_falls_back_to_its_text():
    assert _trace({"label": "Tornado Cash: Router", "category": None, "source": "t"}).entity_type == "mixer"
    assert _trace({"label": "Acme Payments", "category": None, "source": "t"}).entity_type == "service"


def test_hack_of_an_exchange_is_illicit_not_the_exchange():
    # "upbit" is an exchange keyword; the hack wording must win.
    assert categorize("upbit hack") == "illicit"
    assert categorize("Poloniex hack") == "illicit"
    assert categorize("Binance-Hot 7") == "exchange"


def test_mixer_and_bridge_keywords():
    assert categorize("Tornado Cash") == "mixer"
    assert categorize("Wormhole Bridge") == "bridge"


def test_illicit_trail_is_high_risk():
    result = TraceResult(seed_address="0xaaa", path=["0xaaa", "0xbbb"], graph=nx.DiGraph(),
                         hop_count=1, entity_type="illicit", label="Locky", confidence=0.8)
    risk = assess(result)
    assert risk.risk_level == "high"
    assert "Locky" in risk.risk_reason
