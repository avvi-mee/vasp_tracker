"""FastAPI service layer — smoke tests, no live network or database calls.
Run: python -m pytest tests/test_api.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import app.api.main as api_main
from app.api.main import Officer, get_current_officer

FAKE_OFFICER = Officer(id=1, username="test.officer", role="officer", display_name="Test Officer")
AUTH_HEADERS = {"Authorization": "Bearer fake-token-not-checked-due-to-override"}


def fake_fetch(address):
    chain = {
        "0xaaa": [{"from_addr": "0xaaa", "to_addr": "0xbbb", "value_wei": 100,
                    "tx_hash": "t1", "asset_type": "ETH"}],
    }
    return chain.get(address, [])


def _client(monkeypatch, authenticated: bool = True):
    # Keep the whole test offline: no real chain client, no real Postgres.
    monkeypatch.setitem(api_main.CHAINS, "Ethereum",
                        {"enabled": True, "currency": "ETH", "fetch": fake_fetch})
    monkeypatch.setattr(api_main, "_labels", lambda: {
        ("ETH", "0xbbb"): {"label": "Test Exchange", "category": "exchange", "source": "unit-test"},
    })
    monkeypatch.setattr(api_main, "init_db", lambda: None)
    monkeypatch.setattr(api_main, "save_case", lambda *a, **k: 999)
    monkeypatch.setattr(api_main, "log_action", lambda *a, **k: None)
    if authenticated:
        # FastAPI's own recommended way to bypass a real auth dependency in
        # tests -- overrides the dependency, not the JWT machinery itself.
        api_main.app.dependency_overrides[get_current_officer] = lambda: FAKE_OFFICER
    else:
        api_main.app.dependency_overrides.pop(get_current_officer, None)
    return TestClient(api_main.app)


def test_trace_endpoint_returns_a_verdict(monkeypatch):
    client = _client(monkeypatch)
    r = client.post("/v1/trace", json={"address": "0xaaa", "chain": "Ethereum"}, headers=AUTH_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["case_id"] == 999
    assert body["trace"]["entity_type"] == "exchange"
    assert body["trace"]["label"] == "Test Exchange"
    assert body["trace"]["candidates"][0]["label"] == "Test Exchange"
    assert "graph" not in body["trace"]  # stripped in favour of "edges"
    assert body["trace"]["edges"][0]["from"] == "0xaaa"
    assert body["sahyog_draft"]["seed_address"] == "0xaaa"


def test_unwired_chain_is_rejected(monkeypatch):
    client = _client(monkeypatch)
    r = client.post("/v1/trace", json={"address": "1abc", "chain": "Bitcoin — coming soon"}, headers=AUTH_HEADERS)
    assert r.status_code == 400


def test_chains_endpoint_lists_the_registry(monkeypatch):
    client = _client(monkeypatch)
    r = client.get("/v1/chains")
    assert r.status_code == 200
    assert r.json()["Ethereum"]["enabled"] is True


def test_trace_without_a_token_is_rejected(monkeypatch):
    """The whole point of Phase 2 -- an unauthenticated request must not be
    able to run a trace or touch case data."""
    client = _client(monkeypatch, authenticated=False)
    r = client.post("/v1/trace", json={"address": "0xaaa", "chain": "Ethereum"})
    assert r.status_code in (401, 403)


def test_login_issues_a_working_token(monkeypatch):
    from app.auth import hash_password

    fake_officer_row = {
        "id": 1, "username": "test.officer", "role": "officer", "display_name": "Test Officer",
        "password_hash": hash_password("correct-password"),
    }
    monkeypatch.setattr(api_main, "get_officer_by_username", lambda u: fake_officer_row if u == "test.officer" else None)
    monkeypatch.setattr(api_main, "log_action", lambda *a, **k: None)
    monkeypatch.setattr(api_main, "init_db", lambda: None)
    monkeypatch.setattr(api_main, "list_cases", lambda limit=200: [])
    client = TestClient(api_main.app)
    api_main.app.dependency_overrides.pop(get_current_officer, None)

    bad = client.post("/v1/auth/login", json={"username": "test.officer", "password": "wrong"})
    assert bad.status_code == 401

    good = client.post("/v1/auth/login", json={"username": "test.officer", "password": "correct-password"})
    assert good.status_code == 200
    token = good.json()["token"]

    r = client.get("/v1/cases", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code != 401  # a real issued token is accepted downstream


def _fake_case_row(**overrides):
    row = {
        "id": 1, "seed_address": "0xaaa", "chain": "ETH", "entity_type": "exchange",
        "label": "Binance 1", "confidence": 0.9, "hop_count": 1, "path": ["0xaaa", "0xbbb"],
        "compliance_status": "registered_after_penalty", "compliance_detail": "test",
        "risk_flag": False, "risk_level": "none", "risk_reason": None,
        "status": "open", "tags": [], "ncrp_ack_number": None, "cctns_fir_number": None,
        "sahyog_status": None, "sahyog_instrument": None, "sahyog_draft": None,
    }
    row.update(overrides)
    return row


def test_case_detail_includes_its_event_timeline(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_case", lambda case_id: _fake_case_row())
    monkeypatch.setattr(api_main, "list_case_events", lambda case_id: [{"action": "trace_saved"}])
    monkeypatch.setattr(api_main, "list_upi_hops", lambda case_id: [])

    r = client.get("/v1/cases/1", headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert r.json()["events"] == [{"action": "trace_saved"}]


def test_case_detail_includes_its_upi_hops(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_case", lambda case_id: _fake_case_row())
    monkeypatch.setattr(api_main, "list_case_events", lambda case_id: [])
    monkeypatch.setattr(api_main, "list_upi_hops",
                        lambda case_id: [{"id": 1, "hop_order": 1, "payer_vpa": "victim@paytm"}])

    r = client.get("/v1/cases/1", headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert r.json()["upi_hops"] == [{"id": 1, "hop_order": 1, "payer_vpa": "victim@paytm"}]


def test_add_upi_hop_saves_it_and_returns_the_updated_case(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_case", lambda case_id: _fake_case_row())
    monkeypatch.setattr(api_main, "list_case_events", lambda case_id: [])
    saved = {}
    monkeypatch.setattr(api_main, "add_upi_hop",
                        lambda case_id, hop, officer_id: saved.update(case_id=case_id, hop=hop) or 1)
    monkeypatch.setattr(api_main, "list_upi_hops", lambda case_id: [{"id": 1, **saved["hop"]}])

    r = client.post("/v1/cases/1/upi-hops",
                    json={"payer_vpa": "victim@paytm", "amount": 5000}, headers=AUTH_HEADERS)

    assert r.status_code == 200
    assert saved["case_id"] == 1
    assert saved["hop"]["payer_vpa"] == "victim@paytm"
    assert r.json()["upi_hops"][0]["payer_vpa"] == "victim@paytm"


def test_add_upi_hop_on_an_unknown_case_is_a_404(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_case", lambda case_id: None)
    r = client.post("/v1/cases/999/upi-hops", json={"payer_vpa": "x"}, headers=AUTH_HEADERS)
    assert r.status_code == 404


def test_remove_upi_hop_deletes_and_returns_the_updated_case(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_case", lambda case_id: _fake_case_row())
    monkeypatch.setattr(api_main, "list_case_events", lambda case_id: [])
    monkeypatch.setattr(api_main, "list_upi_hops", lambda case_id: [])
    deleted = {}
    monkeypatch.setattr(api_main, "delete_upi_hop",
                        lambda case_id, hop_id, officer_id: deleted.update(case_id=case_id, hop_id=hop_id))

    r = client.delete("/v1/cases/1/upi-hops/9", headers=AUTH_HEADERS)

    assert r.status_code == 200
    assert deleted == {"case_id": 1, "hop_id": 9}


def test_unknown_case_id_is_a_404(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_case", lambda case_id: None)
    r = client.get("/v1/cases/999", headers=AUTH_HEADERS)
    assert r.status_code == 404


def test_update_case_status_rejects_an_invalid_value(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_case", lambda case_id: _fake_case_row())

    def _reject(*a, **k):
        raise ValueError("bad status")
    monkeypatch.setattr(api_main, "update_case_status", _reject)

    r = client.patch("/v1/cases/1", json={"status": "archived-by-mistake"}, headers=AUTH_HEADERS)
    assert r.status_code == 422


def test_generate_sahyog_draft_saves_the_recommended_instrument(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_case", lambda case_id: _fake_case_row())
    saved = {}
    monkeypatch.setattr(
        api_main, "save_sahyog_draft",
        lambda case_id, instrument, draft, officer_id: saved.update(instrument=instrument, draft=draft),
    )

    r = client.post("/v1/cases/1/sahyog", headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert saved["instrument"] == "s94_bnss"  # registered_after_penalty + exchange
    assert saved["draft"]["seed_address"] == "0xaaa"


def _fake_watch_row(**overrides):
    row = {
        "id": 1, "address": "0xaaa", "chain": "Ethereum", "added_by_officer_id": 1,
        "added_at": "2026-01-01", "last_checked_at": None, "last_entity_type": None,
        "last_label": None, "last_risk_level": "none", "alert_status": "clear", "alert_reason": None,
    }
    row.update(overrides)
    return row


def test_watchlist_add_detects_chain_when_omitted(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "init_watchlist_db", lambda: None)
    monkeypatch.setattr(api_main, "add_to_watchlist", lambda address, chain, officer_id: 1)
    monkeypatch.setattr(api_main, "get_watch", lambda watch_id: _fake_watch_row())

    r = client.post("/v1/watchlist", json={"address": "0xaaa"}, headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert r.json()["address"] == "0xaaa"


def test_watchlist_check_reruns_the_trace_and_records_it(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_watch", lambda watch_id: _fake_watch_row(chain="Ethereum"))
    recorded = {}
    monkeypatch.setattr(
        api_main, "record_check",
        lambda watch_id, entity_type, label, risk_level: recorded.update(
            entity_type=entity_type, label=label, risk_level=risk_level) or _fake_watch_row(),
    )

    r = client.post("/v1/watchlist/1/check", headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert recorded["entity_type"] == "exchange"  # from fake_fetch -> 0xbbb, labeled Test Exchange


def test_watchlist_check_on_unknown_id_is_404(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_watch", lambda watch_id: None)
    r = client.post("/v1/watchlist/999/check", headers=AUTH_HEADERS)
    assert r.status_code == 404


def test_watchlist_update_rejects_an_invalid_status(monkeypatch):
    client = _client(monkeypatch)
    monkeypatch.setattr(api_main, "get_watch", lambda watch_id: _fake_watch_row())

    def _reject(*a, **k):
        raise ValueError("bad status")
    monkeypatch.setattr(api_main, "update_alert_status", _reject)

    r = client.patch("/v1/watchlist/1", json={"status": "not-a-real-status"}, headers=AUTH_HEADERS)
    assert r.status_code == 422


def _funnelling_wallet(address):
    """A wallet whose trail is clean (it pays a labelled exchange) but whose
    own behaviour is not: 16 distinct payers in, one destination out."""
    if address != "0xaaa":
        return []
    txs = [{"from_addr": f"0xvictim{i}", "to_addr": "0xaaa", "value_wei": 500,
            "tx_hash": f"in{i}", "asset_type": "ETH", "asset_symbol": "ETH",
            "asset_contract": "", "decimals": 0, "timestamp": 1000 + i * 60}
           for i in range(16)]
    txs += [{"from_addr": "0xaaa", "to_addr": "0xbbb", "value_wei": 500,
             "tx_hash": f"out{i}", "asset_type": "ETH", "asset_symbol": "ETH",
             "asset_contract": "", "decimals": 0, "timestamp": 1200 + i * 60}
            for i in range(16)]
    return txs


def test_watchlist_check_sees_behavioural_risk_the_same_way_investigate_does(monkeypatch):
    """Found by review. This endpoint ran its own trace and then called
    assess() with no typologies, so its risk level was trail-only. A watched
    wallet that started funnelling victim payments into a compliant exchange
    read HIGH on the Investigate page and "none" here — and since an alert
    only opens when the recorded level worsens, "Check now" raised nothing.
    Both paths must reach the same verdict about the same address."""
    client = _client(monkeypatch)
    monkeypatch.setitem(api_main.CHAINS, "Ethereum",
                        {"enabled": True, "currency": "ETH", "fetch": _funnelling_wallet})
    monkeypatch.setattr(api_main, "get_watch", lambda watch_id: _fake_watch_row(chain="Ethereum"))
    recorded = {}
    monkeypatch.setattr(
        api_main, "record_check",
        lambda watch_id, entity_type, label, risk_level: recorded.update(
            entity_type=entity_type, label=label, risk_level=risk_level) or _fake_watch_row(),
    )

    investigate = client.post("/v1/trace", json={"address": "0xaaa", "chain": "Ethereum"},
                              headers=AUTH_HEADERS).json()
    assert investigate["risk"]["risk_level"] == "high"
    assert investigate["risk"]["basis"] == "behaviour"

    assert client.post("/v1/watchlist/1/check", headers=AUTH_HEADERS).status_code == 200
    assert recorded["risk_level"] == investigate["risk"]["risk_level"]
