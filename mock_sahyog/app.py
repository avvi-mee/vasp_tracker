"""MOCK SAHYOG hub — a stand-in, not I4C's system. No public SAHYOG API
exists; this process speaks the PROPOSED contract in docs/sahyog-openapi.yaml
(RESEARCH.md A.4) so the VASP-Trace side can be exercised over real HTTP with
real signed callbacks. Every response it fabricates says MOCK DATA.

What it stands in for, and what it simplifies:
- The hub routes a request to the VASP's SAHYOG account; here a timer plays
  the VASP: ACKNOWLEDGED after SAHYOG_ACK_SECONDS, then RESPONDED (disclosure)
  or ACTIONED (freeze) after SAHYOG_RESPOND_SECONDS.
- Callbacks are signed with HMAC-SHA256 (app/sahyog/client.py). A real hub
  would use mutual TLS and JWS-signed payloads.
- State is in memory; a restart forgets every request.

Run: uvicorn mock_sahyog.app:app --port 8100
Needs SAHYOG_SHARED_SECRET (same value as VASP-Trace) and VASP_TRACE_URL.
"""
import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request

from app.data.fiu_compliance import PENALIZED_THEN_REGISTERED, REGISTERED_INDIAN
from app.sahyog.client import SIGNATURE_HEADER, shared_secret, sign
from app.sahyog.gateway import intermediary_id

load_dotenv()

VASP_TRACE_URL = os.environ.get("VASP_TRACE_URL", "http://localhost:8000").rstrip("/")
ACK_SECONDS = float(os.environ.get("SAHYOG_ACK_SECONDS", "10"))
RESPOND_SECONDS = float(os.environ.get("SAHYOG_RESPOND_SECONDS", "30"))
MOCK_NOTICE = "MOCK DATA — NOT A REAL DISCLOSURE"

app = FastAPI(title="MOCK SAHYOG hub (not an official I4C API)", version="0.1.0")

# Only FIU-registered VASPs are modelled as onboarded to the hub. The
# non-compliant offshore ones are not, so a request to them is refused —
# which is the real-world outcome too.
DIRECTORY = {
    intermediary_id(name): {
        "intermediary_id": intermediary_id(name), "brands": [name],
        "legal_name": info.get("entity", name.title()),
        "request_types": ["DISCLOSURE", "FREEZE", "RELEASE", "PRESERVE"],
    }
    for name, info in {**REGISTERED_INDIAN, **PENALIZED_THEN_REGISTERED}.items()
}
REQUIRED = ("request_id", "request_type", "case", "requesting_agency", "legal_basis", "target", "subjects", "evidence")

requests_by_ref: dict[str, dict] = {}
ref_by_request_id: dict[str, str] = {}
_tasks: set[asyncio.Task] = set()  # keeps timers from being garbage-collected mid-sleep


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _post_signed(path: str, payload: dict) -> httpx.Response:
    secret = shared_secret()
    if not secret:
        raise httpx.HTTPError("SAHYOG_SHARED_SECRET is not set — callbacks cannot be signed.")
    body = json.dumps(payload).encode()
    async with httpx.AsyncClient(timeout=120) as client:
        return await client.post(f"{VASP_TRACE_URL}{path}", content=body, headers={
            "Content-Type": "application/json", SIGNATURE_HEADER: sign(body, secret)})


def _mock_response(req: dict) -> dict:
    subject = next((s for s in req["subjects"] if s.get("role") != "seed"), req["subjects"][0])
    if req["request_type"] == "FREEZE":
        return {"notice": MOCK_NOTICE, "action": "Account debit-frozen (mock)",
                "address": subject["address"], "frozen_balance": "MOCK — 0.00"}
    return {"notice": MOCK_NOTICE, "address": subject["address"],
            "account_holder": "MOCK HOLDER (fabricated)", "kyc_document": "MOCK-PAN-XXXXX0000X",
            "registered_mobile": "+91-00000-00000 (mock)", "login_ips": ["198.51.100.7 (documentation range)"],
            "linked_bank": "MOCK BANK — A/C XXXX0000", "note": "Every value here is fabricated for a demo."}


async def _emit(ref: str, event_type: str, payload: dict | None = None) -> None:
    req = requests_by_ref[ref]
    req["status"] = event_type
    event = {"event_id": str(uuid.uuid4()), "sahyog_ref": ref, "request_id": req["request_id"],
             "type": event_type, "at": _now(), "iat": int(time.time()), "payload": payload or {}}
    req["events"].append(event)
    try:
        r = await _post_signed("/v1/sahyog/events", event)
        if r.status_code >= 300:
            req["callback_errors"].append(f"{event_type}: VASP-Trace answered {r.status_code} {r.text[:200]}")
    except httpx.HTTPError as exc:
        # VASP-Trace can still poll GET /v1/vasp-requests/{ref}.
        req["callback_errors"].append(f"{event_type}: {exc}")


async def _play_vasp(ref: str) -> None:
    await asyncio.sleep(ACK_SECONDS)
    await _emit(ref, "ACKNOWLEDGED")
    await asyncio.sleep(RESPOND_SECONDS)
    req = requests_by_ref[ref]["request"]
    await _emit(ref, "ACTIONED" if req["request_type"] == "FREEZE" else "RESPONDED", _mock_response(req))


@app.get("/v1/intermediaries")
def intermediaries(category: str = "VASP"):
    return list(DIRECTORY.values()) if category == "VASP" else []


@app.post("/v1/vasp-requests", status_code=202)
async def submit(request: Request, idempotency_key: str = Header(alias="Idempotency-Key")):
    req = await request.json()
    missing = [f for f in REQUIRED if f not in req]
    if missing:
        raise HTTPException(422, f"Missing fields: {missing}")
    if idempotency_key != req["request_id"]:
        raise HTTPException(422, "Idempotency-Key must equal request_id.")
    if idempotency_key in ref_by_request_id:
        ref = ref_by_request_id[idempotency_key]
        return {"sahyog_ref": ref, "status": requests_by_ref[ref]["status"], "duplicate": True}
    if req["target"].get("intermediary_id") not in DIRECTORY:
        raise HTTPException(422, f"{req['target'].get('intermediary_id')} is not onboarded to this hub.")

    ref = f"MOCK-SHY-{datetime.now(timezone.utc):%Y%m%d}-{len(requests_by_ref) + 1:05d}"
    ref_by_request_id[idempotency_key] = ref
    requests_by_ref[ref] = {"sahyog_ref": ref, "request_id": idempotency_key, "status": "SUBMITTED",
                            "received_at": _now(), "request": req, "events": [], "callback_errors": []}
    task = asyncio.create_task(_play_vasp(ref))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"sahyog_ref": ref, "status": "SUBMITTED"}


@app.get("/v1/vasp-requests/{ref}")
def status(ref: str):
    if ref not in requests_by_ref:
        raise HTTPException(404, f"{ref} not found.")
    return requests_by_ref[ref]


@app.post("/v1/complaints/push")
async def push_complaint(complaint: dict):
    """Plays NCRP/SAHYOG forwarding a complaint's reported wallets to the
    investigating agency. Body: {ncrp_ack_no, state, wallets: [{address, chain?}]}."""
    if not complaint.get("wallets"):
        raise HTTPException(422, "wallets is required.")
    complaint.setdefault("ncrp_ack_no", f"MOCK-NCRP-{int(time.time())}")
    try:
        r = await _post_signed("/v1/sahyog/cases", complaint)
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"VASP-Trace unreachable at {VASP_TRACE_URL}: {exc}")
    return {"forwarded_to": VASP_TRACE_URL, "status_code": r.status_code, "response": r.json()}
