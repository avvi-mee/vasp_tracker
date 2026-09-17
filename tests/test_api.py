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

    r = client.get("/v1/cases/1", headers=AUTH_HEADERS)
    assert r.status_code == 200
    assert r.json()["events"] == [{"action": "trace_saved"}]


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
