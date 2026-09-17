"""Smoke test for the SAHYOG contract-first adapter — no live SAHYOG access
needed or claimed. Run: python -m pytest tests/test_sahyog_gateway.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx
from app.graph.trace import TraceResult
from app.graph.risk import RiskAssessment
from app.sahyog.gateway import build_disclosure_request, recommend_instrument, submit_disclosure_request


def _fake_case(entity_type="exchange", label="Binance 1", compliance_status="registered_after_penalty",
              risk_level="none"):
    result = TraceResult(seed_address="0xaaa", path=["0xaaa", "0xbbb"], graph=nx.DiGraph(),
                          hop_count=1, entity_type=entity_type, label=label, confidence=0.9,
                          source="https://etherscan.io/labelcloud")
    risk = RiskAssessment(compliance_status=compliance_status,
                          compliance_detail="Penalized before registering.", risk_flag=False,
                          risk_level=risk_level)
    return result, risk


def test_build_disclosure_request_never_claims_live_submission():
    result, risk = _fake_case()
    request = build_disclosure_request("ETH", result, risk)
    assert "no public API exists" in request["status"]
    assert "s.94" in request["legal_basis"]
    assert request["seed_address"] == "0xaaa"
    assert request["matched_entity"]["label"] == "Binance 1"


def test_registered_exchange_recommends_s94():
    result, risk = _fake_case(compliance_status="registered_after_penalty")
    rec = recommend_instrument(result, risk)
    assert rec["instrument"] == "s94_bnss"


def test_high_risk_exchange_recommends_s107():
    result, risk = _fake_case(compliance_status="unknown", risk_level="high")
    rec = recommend_instrument(result, risk)
    assert rec["instrument"] == "s107_bnss"


def test_non_compliant_vasp_recommends_pmla():
    result, risk = _fake_case(compliance_status="flagged_non_compliant", risk_level="medium")
    rec = recommend_instrument(result, risk)
    assert rec["instrument"] == "pmla_s5"


def test_no_specific_signal_falls_back_to_s63():
    result, risk = _fake_case(entity_type="unknown", label=None, compliance_status="unknown", risk_level="low")
    rec = recommend_instrument(result, risk)
    assert rec["instrument"] == "s63_bsa"


def test_submit_disclosure_request_rejects_incomplete_reports():
    response = submit_disclosure_request({"seed_address": "0xaaa"})  # missing required fields
    assert response["status"] == "error"


def test_submit_disclosure_request_accepts_well_formed_reports():
    result, risk = _fake_case()
    request = build_disclosure_request("ETH", result, risk)
    response = submit_disclosure_request(request)
    assert response["status"] == "mock_accepted"
    assert "not transmitted" in response["detail"]
