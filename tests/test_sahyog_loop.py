"""SAHYOG loop (plan Phase B): payload mapping, HMAC signing, the mock hub,
and VASP-Trace's hub-facing endpoints — all offline, no Postgres.

Run: python -m pytest tests/test_sahyog_loop.py -v
"""
import asyncio
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient

import app.api.main as api_main
import mock_sahyog.app as hub
from app.api.main import Officer, get_current_officer
from app.sahyog.client import SIGNATURE_HEADER, sign, verify
from app.sahyog.gateway import to_sahyog_payload

SECRET = "test-secret"
SUPERVISOR = Officer(id=2, username="sup", role="supervisor", display_name="Sup Officer")
OFFICER = Officer(id=1, username="off", role="officer", display_name="Plain Officer")


def _case(**over):
    case = {"id": 7, "seed_address": "Tseed", "chain": "TRX", "label": "Binance-Hot 7",
            "entity_type": "exchange", "hop_count": 3, "confidence": 0.47, "path": ["Tseed", "Tdep", "Thot"],
            "ncrp_ack_number": "31234567890123", "cctns_fir_number": None, "state": "Karnataka",
            "sahyog_draft": {"request_type": "vasp_data_disclosure_request", "generated_at": "2026-09-28T00:00:00",
                             "deposit_address": "Tdep", "tx_hashes": ["h1", "h2"],
                             "recommended_instrument": {"instrument": "s94_bnss"}}}
    case.update(over)
    return case


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setenv("SAHYOG_SHARED_SECRET", SECRET)
    yield
    api_main.app.dependency_overrides.clear()
    hub.requests_by_ref.clear()
    hub.ref_by_request_id.clear()


# --- signing -----------------------------------------------------------------

def test_signature_round_trip_and_tamper():
    body = b'{"a": 1}'
    assert verify(body, sign(body, SECRET), SECRET)
    assert not verify(b'{"a": 2}', sign(body, SECRET), SECRET)
    assert not verify(body, sign(body, SECRET), None)  # no secret never falls open


# --- payload mapping -----------------------------------------------------------

def test_disclosure_payload_targets_the_vasp_and_the_deposit_address():
    p = to_sahyog_payload(_case(), SUPERVISOR)
    assert p["request_type"] == "DISCLOSURE"
    assert p["target"]["intermediary_id"] == "VASP-BINANCE"
    assert p["legal_basis"]["provision_code"] == "s94_bnss"
    assert {s["role"] for s in p["subjects"]} == {"seed", "deposit_address"}
    assert p["case"]["ncrp_ack_no"] == "31234567890123"
    assert p["request_id"] == to_sahyog_payload(_case(), SUPERVISOR)["request_id"]  # idempotent


def test_non_sahyog_instruments_and_unchosen_freeze_routes_are_refused():
    s63 = _case(sahyog_draft={**_case()["sahyog_draft"], "recommended_instrument": {"instrument": "s63_bsa"}})
    with pytest.raises(ValueError):
        to_sahyog_payload(s63, SUPERVISOR)
    choice = _case(sahyog_draft={**_case()["sahyog_draft"], "request_type": "vasp_freeze_request",
                                 "recommended_instrument": {"instrument": "freeze_officer_choice"}})
    with pytest.raises(ValueError):
        to_sahyog_payload(choice, SUPERVISOR)
    assert to_sahyog_payload(choice, SUPERVISOR, provision_code="s107_bnss")["request_type"] == "FREEZE"


# --- mock hub ------------------------------------------------------------------

def _hub_client(monkeypatch):
    async def no_vasp(ref):
        return None
    monkeypatch.setattr(hub, "_play_vasp", no_vasp)
    return TestClient(hub.app)


def test_hub_directory_lists_registered_vasps_only():
    ids = {v["intermediary_id"] for v in TestClient(hub.app).get("/v1/intermediaries").json()}
    assert "VASP-BINANCE" in ids and "VASP-COINDCX" in ids
    assert "VASP-KRAKEN" not in ids  # FIU non-compliance list, not onboarded


def test_hub_submit_is_idempotent_and_rejects_unknown_targets(monkeypatch):
    client = _hub_client(monkeypatch)
    p = to_sahyog_payload(_case(), SUPERVISOR)
    first = client.post("/v1/vasp-requests", json=p, headers={"Idempotency-Key": p["request_id"]})
    again = client.post("/v1/vasp-requests", json=p, headers={"Idempotency-Key": p["request_id"]})
    assert first.status_code == 202 and again.json()["sahyog_ref"] == first.json()["sahyog_ref"]
    bad = {**p, "request_id": "x", "target": {"intermediary_id": "VASP-KRAKEN"}}
    assert client.post("/v1/vasp-requests", json=bad, headers={"Idempotency-Key": "x"}).status_code == 422


def test_hub_plays_the_vasp_and_its_callbacks_verify_at_vasp_trace(monkeypatch):
    """The contract end to end in-process: the hub signs, VASP-Trace verifies."""
    applied = []
    monkeypatch.setattr(api_main, "record_sahyog_event", lambda e: applied.append(e) or 7)
    vt = TestClient(api_main.app)

    async def via_testclient(path, payload):
        body = json.dumps(payload).encode()
        return vt.post(path, content=body, headers={SIGNATURE_HEADER: sign(body, SECRET)})
    monkeypatch.setattr(hub, "_post_signed", via_testclient)
    monkeypatch.setattr(hub, "ACK_SECONDS", 0)
    monkeypatch.setattr(hub, "RESPOND_SECONDS", 0)

    p = to_sahyog_payload(_case(), SUPERVISOR)
    hub.requests_by_ref["R1"] = {"request_id": p["request_id"], "status": "SUBMITTED", "request": p,
                                 "events": [], "callback_errors": []}
    asyncio.run(hub._play_vasp("R1"))

    assert [e["type"] for e in applied] == ["ACKNOWLEDGED", "RESPONDED"]
    assert applied[1]["payload"]["notice"] == hub.MOCK_NOTICE
    assert hub.requests_by_ref["R1"]["callback_errors"] == []


# --- VASP-Trace hub-facing endpoints -------------------------------------------

def _signed_post(client, path, payload, secret=SECRET):
    body = json.dumps(payload).encode()
    return client.post(path, content=body, headers={SIGNATURE_HEADER: sign(body, secret)})


def test_events_reject_bad_signatures_and_stale_events(monkeypatch):
    monkeypatch.setattr(api_main, "record_sahyog_event", lambda e: 7)
    client = TestClient(api_main.app)
    event = {"event_id": "e1", "sahyog_ref": "R1", "type": "ACKNOWLEDGED", "iat": int(time.time())}
    assert _signed_post(client, "/v1/sahyog/events", event, secret="wrong").status_code == 401
    assert _signed_post(client, "/v1/sahyog/events", {**event, "iat": 1}).status_code == 401
    assert _signed_post(client, "/v1/sahyog/events", event).json() == {"applied": True, "case_id": 7}


def test_submit_is_supervisor_only(monkeypatch):
    submitted = []
    monkeypatch.setattr(api_main, "get_case", lambda cid: _case())
    monkeypatch.setattr(api_main.SahyogClient, "submit", lambda self, p: {"sahyog_ref": "MOCK-1", "status": "SUBMITTED"})
    monkeypatch.setattr(api_main, "mark_sahyog_submitted", lambda *a, **k: submitted.append(a))
    monkeypatch.setattr(api_main, "log_action", lambda *a, **k: None)
    client = TestClient(api_main.app)
    auth = {"Authorization": "Bearer x"}

    api_main.app.dependency_overrides[get_current_officer] = lambda: OFFICER
    assert client.post("/v1/cases/7/sahyog/submit", headers=auth).status_code == 403
    api_main.app.dependency_overrides[get_current_officer] = lambda: SUPERVISOR
    assert client.post("/v1/cases/7/sahyog/submit", headers=auth).status_code == 200
    assert submitted[0][1] == "MOCK-1"


def test_resubmit_keeps_the_status_the_hub_already_reached(monkeypatch):
    calls = []
    monkeypatch.setattr(api_main, "get_case", lambda cid: _case())
    monkeypatch.setattr(api_main.SahyogClient, "submit",
                        lambda self, p: {"sahyog_ref": "MOCK-1", "status": "RESPONDED", "duplicate": True})
    monkeypatch.setattr(api_main, "mark_sahyog_submitted", lambda *a, **k: calls.append(k))
    monkeypatch.setattr(api_main, "log_action", lambda *a, **k: None)
    api_main.app.dependency_overrides[get_current_officer] = lambda: SUPERVISOR
    TestClient(api_main.app).post("/v1/cases/7/sahyog/submit", headers={"Authorization": "Bearer x"})
    assert calls == [{"status": "responded"}]


def test_intake_traces_each_wallet_into_a_case(monkeypatch):
    monkeypatch.setitem(api_main.CHAINS, "Ethereum", {"enabled": True, "currency": "ETH", "fetch": lambda a: []})
    monkeypatch.setattr(api_main, "_labels", lambda: {})
    monkeypatch.setattr(api_main, "init_db", lambda: None)
    monkeypatch.setattr(api_main, "save_case", lambda *a, **k: 41)
    intake, drafts = [], []
    monkeypatch.setattr(api_main, "set_case_intake", lambda *a: intake.append(a))
    monkeypatch.setattr(api_main, "save_sahyog_draft", lambda *a: drafts.append(a))
    client = TestClient(api_main.app)

    r = _signed_post(client, "/v1/sahyog/cases",
                     {"ncrp_ack_no": "N1", "state": "Goa", "wallets": [{"address": "0xaaa", "chain": "Ethereum"}]})
    assert r.status_code == 200 and r.json()["cases"][0]["case_id"] == 41
    assert intake == [(41, "N1", "Goa")] and len(drafts) == 1
    assert _signed_post(client, "/v1/sahyog/cases", {"wallets": []}).status_code == 422
