"""Smoke test for the compliance/risk assessment — no network needed.
Run: python -m pytest tests/test_risk.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.trace import TraceResult
from app.graph.risk import assess
import networkx as nx


def _fake_result(path, entity_type, label):
    return TraceResult(
        seed_address=path[0], path=path, graph=nx.DiGraph(), hop_count=len(path) - 1,
        entity_type=entity_type, label=label, confidence=0.8,
    )


def test_penalized_then_registered_vasp_is_not_flagged_as_risk():
    result = _fake_result(["0xaaa", "0xbbb"], "exchange", "Binance: Hot Wallet 20")
    risk = assess(result)
    assert risk.compliance_status == "registered_after_penalty"
    assert risk.risk_flag is False
    assert risk.risk_level == "none"


def test_flagged_non_compliant_vasp_is_risk_flagged_medium():
    result = _fake_result(["0xaaa", "0xbbb"], "exchange", "Kraken: Deposit")
    risk = assess(result)
    assert risk.compliance_status == "flagged_non_compliant"
    assert risk.risk_flag is True
    assert risk.risk_level == "medium"


def test_labeled_exchange_not_in_fiu_data_reports_unknown_not_fabricated():
    result = _fake_result(["0xaaa", "0xbbb"], "exchange", "Some Random Exchange")
    risk = assess(result)
    assert risk.compliance_status == "unknown"
    assert risk.risk_flag is False
    assert risk.risk_level == "none"


def test_no_entity_matched_is_low_risk_not_silently_safe():
    """Genuinely unattributed — different from 'unknown VASP name' above.
    Should NOT be silently treated as risk-free; deserves analyst attention."""
    result = _fake_result(["0xaaa", "0xbbb"], "unknown", None)
    risk = assess(result)
    assert risk.risk_flag is True
    assert risk.risk_level == "low"


def test_path_through_sanctioned_address_is_flagged_high_even_if_final_entity_is_clean():
    result = _fake_result(
        ["0xaaa", "0x098B716B8Aaf21512996dC57EB0615e2383E2f96", "0xbbb"],
        "exchange", "Binance: Hot Wallet 20",
    )
    risk = assess(result)
    assert risk.risk_flag is True
    assert risk.risk_level == "high"
    assert "Ronin Bridge" in risk.risk_reason


def test_mixer_is_always_risk_flagged_high():
    result = _fake_result(["0xaaa"], "mixer", "Tornado Cash: Donation address")
    risk = assess(result)
    assert risk.risk_flag is True
    assert risk.risk_level == "high"
    assert risk.compliance_status == "n/a"
