"""FastAPI service layer — smoke tests, no live network or database calls.
Run: python -m pytest tests/test_api.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import app.api.main as api_main


def fake_fetch(address):
    chain = {
        "0xaaa": [{"from_addr": "0xaaa", "to_addr": "0xbbb", "value_wei": 100,
                    "tx_hash": "t1", "asset_type": "ETH"}],
    }
    return chain.get(address, [])


def _client(monkeypatch):
    # Keep the whole test offline: no real chain client, no real Postgres.
    monkeypatch.setitem(api_main.CHAINS, "Ethereum",
                        {"enabled": True, "currency": "ETH", "fetch": fake_fetch})
    monkeypatch.setattr(api_main, "_labels", lambda: {
        ("ETH", "0xbbb"): {"label": "Test Exchange", "category": "exchange", "source": "unit-test"},
    })
    monkeypatch.setattr(api_main, "init_db", lambda: None)
    monkeypatch.setattr(api_main, "save_case", lambda *a, **k: 999)
    return TestClient(api_main.app)


def test_trace_endpoint_returns_a_verdict(monkeypatch):
    client = _client(monkeypatch)
    r = client.post("/v1/trace", json={"address": "0xaaa", "chain": "Ethereum"})
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
    r = client.post("/v1/trace", json={"address": "1abc", "chain": "Bitcoin — coming soon"})
    assert r.status_code == 400


def test_chains_endpoint_lists_the_registry(monkeypatch):
    client = _client(monkeypatch)
    r = client.get("/v1/chains")
    assert r.status_code == 200
    assert r.json()["Ethereum"]["enabled"] is True
