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


def test_an_exchanges_own_wallet_is_not_called_high_risk_for_behaving_like_one():
    """Live false positive this fixes: Binance's Tron hot wallet fires
    rapid_layering at high severity — 25 funders, forwards nearly everything
    within minutes — because that is exactly what a hot wallet does. The
    pattern is real and stays on the record; the inference does not follow."""
    subject_is_the_exchange = _result(
        path=["0xbinance"], hop_count=0, entity_type="exchange", label="Binance-Hot 7")

    assessment = assess(subject_is_the_exchange, [_typology("rapid_layering", "high")])

    assert assessment.risk_level != "high"
    assert assessment.basis == "trail"
    assert assessment.typologies == ["rapid_layering"]  # recorded, not hidden
    assert "normal operation" in assessment.risk_reason


def test_the_same_pattern_one_hop_away_still_escalates():
    """The suppression is about the subject BEING the service, not about an
    exchange appearing anywhere on the trail — otherwise every scam wallet
    that cashes out at an exchange would be excused by reaching one."""
    suspect_paying_an_exchange = _result(
        path=["0xsuspect", "0xbinance"], hop_count=1, entity_type="exchange", label="Binance-Hot 7")

    assessment = assess(suspect_paying_an_exchange, [_typology("rapid_layering", "high")])

    assert assessment.risk_level == "high"
    assert assessment.basis == "behaviour"


def test_trace_recognises_an_entity_from_the_address_own_tag():
    """An address's own tag arrives inside its OWN transactions — one fetch
    later than the label check. Without a re-check the search walks past an
    address it just proved is a named entity, and the seed can never be
    recognised at all, because nothing fetches its parent's rows: it has none.
    Found by review; the tool reported "unattributed — dead end" about a wallet
    it had already labelled Binance-Hot 7 in the same call."""
    from app.graph.trace import trace_to_nearest_entity

    self_tagged = [{"tx_hash": "0x1", "from_addr": "TSeed", "to_addr": "TDep",
                    "value_wei": 1_000_000, "timestamp": 100, "decimals": 6,
                    "asset_symbol": "USDT", "asset_contract": "TR7N", "block_number": 1,
                    "from_label": "Binance-Hot 7", "to_label": None}]

    traced = trace_to_nearest_entity(
        "TSeed", "TRX", lambda a: self_tagged if a == "TSeed" else [],
        labels_lookup={}, mixers_lookup={}, max_hops=4)

    assert traced.label == "Binance-Hot 7"
    assert traced.entity_type == "exchange"
    assert traced.hop_count == 0  # the subject IS the entity, not one hop from it
    assert traced.reason is None  # not "dead end"
