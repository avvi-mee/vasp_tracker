"""Risk must answer "is this wallet dirty", not "was the exchange it paid
compliant". Those are different questions and conflating them produced two
bugs in a row.

  Before chain-native labels: every real address fell through to "no entity
  matched" and the tool said LOW RISK to everything, which is what the user
  saw on a genuine scam wallet.

  After they landed, it got quieter and worse: that same wallet resolved to an
  FIU-registered exchange, so the compliance branch answered NONE — a wallet
  funded by 16 victims and swept within 11 minutes was scored clean.

Run: python -m pytest tests/test_risk_behaviour.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

from app.graph.risk import assess
from app.graph.trace import TraceResult
from app.graph.typology import Typology


def _result(**kw):
    base = dict(seed_address="0xseed", path=["0xseed", "0xdest"], graph=nx.DiGraph(),
                hop_count=1, entity_type="unknown", label=None, confidence=0.5)
    return TraceResult(**{**base, **kw})


def _typology(name="many_to_one_funnel", severity="high"):
    return Typology(name=name, title="Many-to-one funnel (collection wallet)", severity=severity,
                    confidence=0.88, explanation="16 different addresses paid into this wallet.",
                    stats={"distinct_funders": 16}, evidence=[])


COMPLIANT_EXCHANGE = dict(entity_type="exchange", label="Binance-Hot 7", source="Tronscan address tag")


def test_reaching_a_compliant_exchange_alone_is_not_a_clean_bill_of_health():
    """The regression this file exists for."""
    clean = assess(_result(**COMPLIANT_EXCHANGE))
    assert clean.risk_level == "none"  # trail question, answered honestly

    dirty = assess(_result(**COMPLIANT_EXCHANGE), [_typology()])
    assert dirty.risk_level == "high"
    assert dirty.basis == "behaviour"
    assert "many_to_one_funnel" in dirty.typologies
    # The compliance finding is preserved, not overwritten — it is still how
    # the officer knows a BNSS s.94 notice is the right instrument.
    assert dirty.compliance_status == clean.compliance_status


def test_behaviour_never_lowers_a_trail_verdict():
    """A mixer is high regardless of how unremarkable the wallet's own
    behaviour looks — obfuscation is the point of a mixer."""
    mixer = _result(entity_type="mixing_service", label="Tornado Cash")
    assessment = assess(mixer, [_typology(severity="low")])
    assert assessment.risk_level == "high"
    assert assessment.basis == "trail"
    assert assessment.typologies == ["many_to_one_funnel"]  # still recorded, just not decisive


def test_no_typologies_leaves_the_trail_verdict_untouched():
    plain = _result()
    assert assess(plain).risk_level == assess(plain, []).risk_level == "low"


def test_the_stated_reason_names_the_pattern_the_officer_can_check():
    assessment = assess(_result(**COMPLIANT_EXCHANGE), [_typology()])
    assert "Many-to-one funnel" in assessment.risk_reason
    assert "16 different addresses" in assessment.risk_reason


def test_several_patterns_are_all_recorded_and_the_worst_one_leads():
    typologies = [_typology(), _typology("rapid_layering", "medium")]
    assessment = assess(_result(**COMPLIANT_EXCHANGE), typologies)
    assert assessment.risk_level == "high"
    assert assessment.typologies == ["many_to_one_funnel", "rapid_layering"]
    assert "1 further pattern" in assessment.risk_reason


def test_an_explorer_risk_flag_lifts_an_otherwise_unattributed_trail():
    flagged = _result(explorer_flagged=["0xdest"])
    assert assess(flagged).risk_level == "medium"
    assert "explorer" in assess(flagged).risk_reason.lower()
    # ...but only for addresses actually on this trail.
    assert assess(_result(explorer_flagged=["0xelsewhere"])).risk_level == "low"
