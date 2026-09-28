"""The plain-language summary is the part of the output a non-specialist
will actually read, which makes overstatement the only failure worth
guarding hard against.

Three claims it must never make, each of which the underlying data does not
support and each of which is an easy sentence to write by accident:

  - "no entity matched" rendered as "clean"
  - "the oracle was not consulted" rendered as "no sanctions hit"
  - "no typology matched" rendered as "no laundering behaviour"

The rest of the tests pin determinism, which is the whole reason this is a
template and not a language model.

Run: python -m pytest tests/test_summary.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

from app.graph.risk import assess
from app.graph.summary import summarise
from app.graph.trace import TraceResult
from app.graph.typology import Typology

SANCTIONED = "0x7f367cc41522ce07553e823bf3be79a889debe1b"


def _result(**kw):
    base = dict(seed_address="0x1111111111111111111111111111111111111111",
                path=["0x1111111111111111111111111111111111111111", "0xdest"],
                graph=nx.DiGraph(), hop_count=1, entity_type="unknown", label=None,
                confidence=0.0, asset=("ETH", ""), max_hops=12)
    return TraceResult(**{**base, **kw})


def _summary(result, typologies=()):
    return summarise(result, assess(result, typologies), typologies, chain="Ethereum")


def _typology():
    return Typology(name="many_to_one_funnel", title="Many-to-one funnel (collection wallet)",
                    severity="high", confidence=0.88,
                    explanation="16 different addresses paid into this wallet.",
                    stats={"distinct_funders": 16}, evidence=[])


def test_same_input_produces_the_same_sentence():
    """A defence expert re-running the trace must get the text they are
    contesting, verbatim. This is the property an LLM could not give."""
    result = _result(oracle_sanctioned=[])
    assert _summary(result) == _summary(result)


def test_unattributed_is_never_called_clean():
    text = _summary(_result(oracle_sanctioned=[])).lower()
    assert "unattributed trail" in text
    assert "not a clean one" in text
    assert "no risk" not in text


def test_neither_source_consulted_says_coverage_is_narrower_than_it_looks():
    """On Bitcoin with no API key, neither Chainalysis source can answer.
    Silence there is absence of evidence, and the sentence has to say so
    rather than let the OFAC snapshot imply full coverage."""
    text = _summary(_result(oracle_sanctioned=None, api_sanctioned=None))
    assert "Neither Chainalysis source was consulted" in text
    assert "narrower coverage than it looks" in text
    assert "nothing on this trail is listed" not in text


def test_one_source_silent_is_named_rather_than_glossed_over():
    """The common EVM case before a key is issued: the oracle answered, the
    API could not. Saying only "nothing is listed" would overstate it."""
    text = _summary(_result(oracle_sanctioned=[], api_sanctioned=None))
    assert "Chainalysis (on-chain oracle); nothing on this trail is listed." in text
    assert "Screening API did not answer" in text


def test_both_sources_clean_reports_no_gap():
    text = _summary(_result(oracle_sanctioned=[], api_sanctioned=[]))
    assert "on-chain oracle, Screening API" in text
    assert "did not answer" not in text


def test_hit_is_named_with_the_address_and_the_source():
    result = _result(path=["0xseed", SANCTIONED], oracle_sanctioned=[SANCTIONED])
    text = _summary(result)
    assert "(the on-chain oracle) lists 1 address" in text
    assert SANCTIONED[:10] in text
    assert "HIGH risk" in text


def test_api_only_hit_reaches_a_chain_the_oracle_cannot():
    """A Bitcoin trail: the oracle has no deployment, so the API is the only
    Chainalysis source that can flag it — and it must still drive HIGH."""
    btc = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
    result = _result(path=["bc1qseed", btc], oracle_sanctioned=None, api_sanctioned=[btc])
    text = _summary(result)
    assert "(the Screening API) lists 1 address" in text
    assert "HIGH risk" in text


def test_both_sources_listing_it_names_both():
    result = _result(path=["0xseed", SANCTIONED],
                     oracle_sanctioned=[SANCTIONED], api_sanctioned=[SANCTIONED])
    text = _summary(result)
    assert "(the on-chain oracle and the Screening API) lists 1 address" in text


def test_no_typology_match_is_not_a_clean_bill():
    text = _summary(_result(oracle_sanctioned=[]))
    assert "only cover five patterns" in text
    assert "silence from them, not a finding of good behaviour" in text


def test_typologies_are_counted_and_named():
    text = _summary(_result(oracle_sanctioned=[]), [_typology()])
    assert "1 laundering pattern matched" in text
    assert "many-to-one funnel" in text
    assert "16 different addresses" in text


def test_attributed_entity_reports_hops_confidence_and_source():
    result = _result(entity_type="exchange", label="Binance", confidence=0.9,
                     hop_count=3, source="Indian VASP dataset",
                     asset=("USDT", ""), oracle_sanctioned=[])
    text = _summary(result)
    assert "reaches Binance (exchange) at 3 hops" in text
    assert "90% confidence" in text
    assert "per Indian VASP dataset" in text
    assert "USDT" in text


def test_subject_that_is_itself_a_known_entity_is_flagged_up_front():
    """If the officer pasted an exchange's own hot wallet, everything after
    describes that exchange operating normally — risk.py already declines to
    escalate on it, and the summary has to lead with the same context."""
    result = _result(subject_entity={"label": "Binance-Hot 7", "category": "exchange"},
                     oracle_sanctioned=[])
    assert _summary(result).startswith("The Ethereum wallet 0x11111111…111111 is itself a known entity — Binance-Hot 7 (exchange).")


def test_search_limits_are_carried_into_the_paragraph():
    caveat = "4 branch(es) below the top-8 by value share were not followed."
    text = _summary(_result(oracle_sanctioned=[], caveats=[caveat]))
    assert "Limits on this search:" in text
    assert caveat in text


def test_no_caveats_adds_no_empty_clause():
    text = _summary(_result(oracle_sanctioned=[]))
    assert "Limits on this search" not in text
    assert "  " not in text  # no double spaces from dropped empty parts


def _deposit(is_deposit):
    from app.graph.sweep import DepositEvidence
    return DepositEvidence(address="0xdep", vasp_address="0xhot", is_deposit_address=is_deposit,
                           confidence=0.9 if is_deposit else 0.3, forwarded_ratio=0.95,
                           destination_share=1.0, distinct_funders=15, sweep_count=3,
                           median_hold_seconds=600)


def test_rejected_deposit_check_is_not_reported_as_a_deposit_address():
    """REVIEW.md defect 3: the classifier said no, the summary said yes."""
    text = _summary(_result(entity_type="exchange", label="Binance", confidence=0.8,
                            oracle_sanctioned=[], deposit=_deposit(False)))
    assert "behaves like an exchange deposit address" not in text
    assert "did not match a deposit-address pattern" in text


def test_confirmed_deposit_address_is_reported():
    text = _summary(_result(entity_type="exchange", label="Binance", confidence=0.8,
                            oracle_sanctioned=[], deposit=_deposit(True)))
    assert "behaves like an exchange deposit address" in text


def test_summary_stays_out_of_the_hashed_record():
    """Derived restatement, not a finding. Putting it in build_record() would
    make the evidence pack's digest churn on a wording change."""
    import inspect
    from app.evidence import certificate
    assert "summary" not in inspect.getsource(certificate.build_record)
