"""Smoke test for the SAHYOG contract-first adapter — no live SAHYOG access
needed or claimed. Run: python -m pytest tests/test_sahyog_gateway.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx
from app.graph.trace import TraceResult
from app.graph.risk import RiskAssessment
from app.sahyog.gateway import build_disclosure_request, submit_disclosure_request


def _fake_case():
    result = TraceResult(seed_address="0xaaa", path=["0xaaa", "0xbbb"], graph=nx.DiGraph(),
                          hop_count=1, entity_type="exchange", label="Binance 1", confidence=0.9,
                          source="https://etherscan.io/labelcloud")
    risk = RiskAssessment(compliance_status="registered_after_penalty",
                          compliance_detail="Penalized before registering.", risk_flag=False)
    return result, risk


def test_build_disclosure_request_never_claims_live_submission():
    result, risk = _fake_case()
    request = build_disclosure_request("ETH", result, risk)
    assert "pending I4C provisioning" in request["status"]
    assert request["seed_address"] == "0xaaa"
    assert request["matched_entity"]["label"] == "Binance 1"


def test_submit_disclosure_request_rejects_incomplete_reports():
    response = submit_disclosure_request({"seed_address": "0xaaa"})  # missing required fields
    assert response["status"] == "error"


def test_submit_disclosure_request_accepts_well_formed_reports():
    result, risk = _fake_case()
    request = build_disclosure_request("ETH", result, risk)
    response = submit_disclosure_request(request)
    assert response["status"] == "mock_accepted"
    assert "not transmitted" in response["detail"]
