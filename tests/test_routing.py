"""Legal routing — which instrument, through which channel, for which request.

Pins REVIEW.md defect 4 and RESEARCH.md B.5:
  - CoinDCX / WazirX / CoinSwitch / ZebPay are named FIU-IND registrants
    (Lok Sabha, 4 Dec 2023) and were routed to "s.63 certificate only".
  - Disclosure and freeze are different instruments. s.94 is production of
    documents and cannot freeze (Bombay HC 30 Jul 2026; AP HC 31 Mar 2026).
  - Freeze is s.106 in Karnataka / Bombay, s.107 (Magistrate) in Andhra
    Pradesh; elsewhere unsettled — the officer chooses, never auto-selected.

Run: python -m pytest tests/test_routing.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

from app.data.fiu_compliance import check_compliance
from app.graph.risk import RiskAssessment, assess
from app.graph.trace import TraceResult
from app.sahyog.gateway import build_disclosure_request, recommend_instrument


def _case(label="CoinDCX Hot Wallet", entity_type="exchange", asset=("USDT", "TR7N"), graph=None):
    result = TraceResult(seed_address="Tseed", path=["Tseed", "Tdep", "Thot"], graph=graph or nx.DiGraph(),
                         hop_count=2, entity_type=entity_type, label=label, confidence=0.8, asset=asset)
    return result, assess(result)


# --- VASP directory ---------------------------------------------------------

def test_indian_registrants_are_registered_not_unknown():
    for name in ("CoinDCX", "WazirX", "CoinSwitch", "ZebPay"):
        c = check_compliance(f"{name} Hot Wallet")
        assert c["status"] == "registered", name
        assert c["jurisdiction"] == "IN"
        assert c["source"].startswith("http")


def test_offshore_registered_vasp_names_its_law_enforcement_channel():
    c = check_compliance("Binance-Hot 7")
    assert c["status"] == "registered_after_penalty"
    assert "Kodex" in c["le_channel"] or "law-enforcement" in c["le_channel"].lower()


def test_all_three_notice_waves_are_covered():
    # names the old list missed: wave 2 (Huione, Paxful) and wave 3 swap services
    for name in ("Huione", "Paxful", "SimpleSwap", "FixedFloat", "Guardarian"):
        assert check_compliance(name)["status"] == "flagged_non_compliant", name


# --- disclosure --------------------------------------------------------------

def test_indian_registered_exchange_disclosure_is_s94_via_nodal_officer():
    result, risk = _case()
    rec = recommend_instrument(result, risk, request_type="disclosure")
    assert rec["instrument"] == "s94_bnss"
    assert "nodal" in rec["channel"].lower()


def test_flagged_offshore_vasp_disclosure_goes_via_letter_of_request():
    result, risk = _case(label="Huione Pay")
    rec = recommend_instrument(result, risk, request_type="disclosure")
    assert rec["instrument"] == "lor_mlat"
    assert "FIU-IND" in rec["channel"]


def test_no_custodian_on_the_trail_means_nobody_to_serve():
    result, risk = _case(label=None, entity_type="unknown")
    rec = recommend_instrument(result, risk, request_type="disclosure")
    assert rec["instrument"] == "s63_bsa"


# --- freeze -------------------------------------------------------------------

def test_freeze_follows_the_state_high_court_position():
    result, risk = _case()
    assert recommend_instrument(result, risk, "freeze", state="Karnataka")["instrument"] == "s106_bnss"
    assert recommend_instrument(result, risk, "freeze", state="Maharashtra")["instrument"] == "s106_bnss"
    assert recommend_instrument(result, risk, "freeze", state="Andhra Pradesh")["instrument"] == "s107_bnss"


def test_freeze_in_an_unsettled_state_is_never_auto_selected():
    result, risk = _case()
    rec = recommend_instrument(result, risk, "freeze", state="Delhi")
    assert rec["instrument"] == "freeze_officer_choice"
    keys = {o["instrument"] for o in rec["options"]}
    assert {"s106_bnss", "s107_bnss"} <= keys


def test_freeze_never_recommends_s94():
    result, risk = _case()
    for state in (None, "Karnataka", "Andhra Pradesh", "Delhi"):
        rec = recommend_instrument(result, risk, "freeze", state=state)
        assert rec["instrument"] != "s94_bnss"
        assert "s94_bnss" not in {o["instrument"] for o in rec["options"]}


def test_funds_still_in_usdt_offer_an_issuer_freeze():
    result, risk = _case(asset=("USDT", "TR7N"))
    rec = recommend_instrument(result, risk, "freeze", state="Karnataka")
    assert "issuer_freeze" in {o["instrument"] for o in rec["options"]}


# --- the draft ------------------------------------------------------------------

def test_draft_legal_basis_follows_the_request_not_a_fixed_s94():
    result, risk = _case()
    freeze = build_disclosure_request("Tron", result, risk, request_type="freeze", state="Karnataka")
    assert "s.106" in freeze["legal_basis"]
    assert "s.94" not in freeze["legal_basis"]
    disclosure = build_disclosure_request("Tron", result, risk)
    assert "s.94" in disclosure["legal_basis"]


def test_draft_names_the_transaction_hashes_on_the_path():
    g = nx.DiGraph()
    g.add_edge("Tseed", "Tdep", tx_hash="h1")
    g.add_edge("Tdep", "Thot", tx_hash="h2")
    result, risk = _case(graph=g)
    draft = build_disclosure_request("Tron", result, risk)
    assert draft["tx_hashes"] == ["h1", "h2"]
