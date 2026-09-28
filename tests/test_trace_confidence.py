"""Attribution confidence must reflect how good the label is, not just hops.

The bug (REVIEW.md defect 5): a 0.95 operator-confirmed Indian-VASP label and
a 0.60 explorer tag at the same distance both scored 0.80 — "why 95%?" had
no answer. GraphSense also stores confidence as strings (forensic,
web_crawl …), which the old code never read at all.

Run: python -m pytest tests/test_trace_confidence.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.trace import label_confidence, trace_to_nearest_entity


def _one_hop(address):
    return {"0xaaa": [{"from_addr": "0xaaa", "to_addr": "0xbbb", "value_wei": 100, "tx_hash": "t1"}]}.get(address, [])


def _conf(label_conf):
    rec = {"label": "X Exchange", "category": "exchange", "source": "t", "confidence": label_conf}
    return trace_to_nearest_entity("0xaaa", "ETH", _one_hop, {("ETH", "0xbbb"): rec}, {}, max_hops=3).confidence


def test_stronger_label_gives_higher_confidence_at_same_distance():
    assert _conf(0.95) > _conf(0.75) > _conf(0.60)


def test_graphsense_string_confidences_are_read():
    assert label_confidence("authority_data") > label_confidence("web_crawl")
    assert label_confidence("forensic") > label_confidence("untrusted_transaction")
    assert _conf("forensic") > _conf("web_crawl")


def test_unknown_or_missing_label_confidence_is_neutral_not_zero():
    assert 0.5 <= label_confidence(None) <= 0.8
    assert 0.5 <= label_confidence("something-new") <= 0.8
