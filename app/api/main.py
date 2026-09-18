"""FastAPI service layer — the same engine app/main.py (Streamlit) calls
in-process, exposed over HTTP. This is what makes the tool "API-driven" per
the problem statement, what a Next.js console calls, and what the eventual
SAHYOG Phase-2 integration would call too: the OpenAPI schema this app
publishes at /openapi.json (or interactively at /docs) is the integration
contract for all three consumers.

Run with: uvicorn app.api.main:app --reload
"""
import logging

from dotenv import load_dotenv

# Must run before any app.* import: app.auth reads JWT_SECRET from the
# environment at import time (a module-level constant, not read per-request),
# so loading .env after that import silently ignores whatever is in it and
# falls back to a random one-time secret every time. Caught live: JWT_SECRET
# was set in .env and still wasn't being picked up until this moved up here.
load_dotenv()

import jwt as pyjwt
import networkx as nx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

logger = logging.getLogger("vasp_trace.api")

from app.auth import create_token, decode_token, verify_password
from app.chains import CHAINS
from app.data.case_store import (
    get_case, get_officer_by_username, init_db, list_case_events, list_cases, log_action,
    save_case, save_sahyog_draft, update_case_legal_refs, update_case_status, update_case_tags,
    update_sahyog_status,
)
from app.data.indian_vasps import coverage_summary, merge_labels
from app.data.known_mixers import KNOWN_MIXERS
from app.data.tagpacks import load_labels
from app.data.watchlist_store import (
    add_to_watchlist,
    get_watch,
)
from app.data.watchlist_store import init_db as init_watchlist_db
from app.data.watchlist_store import (
    list_watchlist,
    record_check,
    remove_from_watchlist,
    update_alert_status,
)
from app.evidence.certificate import _jsonable, build_certificate_bundle
from app.graph.chain_detect import detect_chain
from app.graph.exposure import SeedExposure, compute_exposure, compute_seed_exposure
from app.graph.risk import RiskAssessment, assess
from app.graph.trace import DEFAULT_MAX_HOPS, TraceResult, trace_to_nearest_entity
from app.graph.typology import detect as detect_typologies
from app.sahyog.gateway import build_disclosure_request

app = FastAPI(title="VASP Trace API", version="1.0",
              description="Automated blockchain intelligence & VASP attribution — SIH26182")

# ponytail: wide open for local dev / the hackathon demo; tighten to the
# deployed Next.js origin (allow_credentials stays False either way — no
# cookie auth yet) once there's a real deployment to tighten it to.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_bearer = HTTPBearer()


class Officer(BaseModel):
    id: int
    username: str
    role: str
    display_name: str


def get_current_officer(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> Officer:
    try:
        payload = decode_token(creds.credentials)
    except pyjwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired session — log in again.")
    return Officer(id=int(payload["sub"]), username=payload["username"],
                   role=payload["role"], display_name=payload["display_name"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


@app.post("/v1/auth/login")
def login(req: LoginRequest):
    officer = get_officer_by_username(req.username)
    if not officer or not verify_password(req.password, officer["password_hash"]):
        raise HTTPException(401, "Incorrect username or password.")
    token = create_token(officer["id"], officer["username"], officer["role"], officer["display_name"])
    try:
        log_action(officer["id"], "login")
    except Exception:
        logger.exception("Audit log write failed for login by %s", officer["username"])
    return {"token": token, "officer": {"id": officer["id"], "username": officer["username"],
                                        "role": officer["role"], "display_name": officer["display_name"]}}

_labels_cache: dict | None = None


def _labels() -> dict:
    # ponytail: process-lifetime cache, same effect as Streamlit's
    # @st.cache_resource on get_labels(). A real TTL/refresh policy is Redis's
    # job (already deferred in the plan) — this just avoids re-parsing the
    # TagPacks dataset on every request.
    global _labels_cache
    if _labels_cache is None:
        _labels_cache = merge_labels(load_labels())
    return _labels_cache


class TraceRequest(BaseModel):
    address: str = Field(min_length=1, description="Wallet address to trace")
    chain: str | None = None  # omit to auto-detect from address format
    case_reference: str = ""
    analyst_note: str = ""
    # Real laundering chains run well past 4 hops, which is what this was
    # pinned to. Capped at 20 so a single request can't be turned into an
    # unbounded crawl; the real cost ceiling is trace.MAX_FETCHES.
    max_hops: int = Field(default=DEFAULT_MAX_HOPS, ge=1, le=20)


def _run_trace(req: TraceRequest):
    chain = req.chain
    if not chain:
        detected, _ = detect_chain(req.address)
        chain = detected or "Ethereum"
    chain_cfg = CHAINS.get(chain)
    if not chain_cfg or not chain_cfg["enabled"]:
        live = ", ".join(name for name, cfg in CHAINS.items() if cfg["enabled"])
        raise HTTPException(400, f"{chain} isn't wired up in this build yet — try {live}.")
    try:
        result = trace_to_nearest_entity(
            seed_address=req.address, currency=chain_cfg["currency"],
            fetch_transactions_fn=chain_cfg["fetch"],
            labels_lookup=_labels(), mixers_lookup=KNOWN_MIXERS, max_hops=req.max_hops,
        )
    except Exception as exc:
        raise HTTPException(502, f"Trace failed: {exc}")

    # The seed's own transactions, both directions. The trace already fetched
    # these at hop 0 and app/cache.py holds them, so this is a dict lookup, not
    # a second network call — and it is what the behavioural detectors and the
    # receiving/sending exposure wheel both read.
    seed_txs = _seed_txs(result, chain_cfg)
    typologies = detect_typologies(result, seed_txs, asset=result.asset)
    risk = assess(result, typologies)
    return chain, chain_cfg, result, risk, typologies, seed_txs


def _edges(result) -> list[dict]:
    return [
        {"from": src, "to": dst, "tx_hash": edge.get("tx_hash"),
         "value_wei": edge.get("value_wei"), "amount": edge.get("amount"),
         "asset": edge.get("asset"), "timestamp": edge.get("timestamp"),
         "block_number": edge.get("block_number")}
        for src, dst, edge in result.graph.edges(data=True)
    ]


def _seed_txs(result, chain_cfg: dict) -> list[dict]:
    """The seed's own transactions in both directions. Served from
    app/cache.py — the trace's first hop fetched exactly this a moment ago.
    Failure here must never break a trace that already succeeded, so it is
    swallowed and degrades to "no behavioural analysis", not to a 502."""
    try:
        return chain_cfg["fetch"](result.seed_address)
    except Exception:
        logger.exception("Seed transaction fetch failed for %s", result.seed_address)
        return []


def _labels_for(result, currency: str) -> dict:
    """Curated labels plus the ones this trace harvested from the explorer.
    Curated wins on collision — an explorer tag is a third-party convenience
    label, our Indian VASP dataset is checksum-validated. Without this merge
    the exposure wheels reported "100% unattributed" about the very hop the
    verdict had just named, which is precisely how the screenshots looked."""
    discovered = {(currency.upper(), a): rec for a, rec in (result.discovered_labels or {}).items()}
    return {**discovered, **_labels()}


def _trace_json(result, chain_cfg: dict, typologies=(), seed_txs=()) -> dict:
    currency = chain_cfg["currency"]
    labels = _labels_for(result, currency)
    payload = _jsonable(result)
    payload.pop("graph", None)  # str(DiGraph) is noise, not data
    payload["edges"] = _edges(result)
    payload["exposure"] = _jsonable(compute_exposure(result, currency, labels, KNOWN_MIXERS))
    payload["typologies"] = [_jsonable(t) for t in typologies]
    try:
        payload["seed_exposure"] = _jsonable(compute_seed_exposure(
            result.seed_address, list(seed_txs), currency, labels, KNOWN_MIXERS, asset=result.asset))
    except Exception:
        logger.exception("Seed exposure failed for %s", result.seed_address)
        payload["seed_exposure"] = _jsonable(SeedExposure())
    return payload


def _log_action_safely(officer_id: int, action: str, target: str, details: dict | None = None) -> None:
    try:
        log_action(officer_id, action, target, details)
    except Exception:
        logger.exception("Audit log write failed for %s by officer %s", action, officer_id)


@app.post("/v1/trace")
def trace(req: TraceRequest, officer: Officer = Depends(get_current_officer)):
    """Trace a wallet to its nearest exchange/VASP. Auto-saves a case row
    (best-effort — a missing DATABASE_URL degrades to case_id: null, same as
    the Streamlit UI does)."""
    chain, chain_cfg, result, risk, typologies, seed_txs = _run_trace(req)

    case_id = None
    try:
        init_db()
        case_id = save_case(chain_cfg["currency"], result, risk, officer_id=officer.id)
    except Exception:
        # Best-effort, same posture as the Streamlit UI — a missing
        # DATABASE_URL shouldn't fail the trace. But swallowing it silently
        # would hide a real bug in save_case just as easily, so log it.
        logger.exception("Case save failed for %s", result.seed_address)

    _log_action_safely(officer.id, "trace", result.seed_address,
                       {"chain": chain, "entity_type": result.entity_type, "case_id": case_id})

    return {
        "chain": chain,
        "case_id": case_id,
        "trace": _trace_json(result, chain_cfg, typologies, seed_txs),
        "risk": _jsonable(risk),
        "sahyog_draft": build_disclosure_request(chain, result, risk, analyst_note=req.analyst_note),
    }


@app.post("/v1/certificate")
def certificate(req: TraceRequest, officer: Officer = Depends(get_current_officer)):
    """Re-runs the trace and returns the s.63 BSA evidence pack (zip:
    record + Part A + Part B + hash report) as a direct download."""
    chain, _chain_cfg, result, risk, typologies, _seed = _run_trace(req)
    pack, bundle = build_certificate_bundle(
        chain, result, risk, case_reference=req.case_reference, analyst_note=req.analyst_note)
    filename = f"s63-evidence-{result.seed_address[:10]}.zip"
    _log_action_safely(officer.id, "certificate", result.seed_address,
                       {"case_reference": req.case_reference, "record_sha256": pack.record_sha256})
    return Response(bundle, media_type="application/zip",
                     headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/v1/cases")
def cases(limit: int = 200, officer: Officer = Depends(get_current_officer)):
    try:
        init_db()
        return list_cases(limit=limit)
    except Exception as exc:
        raise HTTPException(503, f"Case database unreachable: {exc}")


def _require_case(case_id: int) -> dict:
    case = get_case(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found.")
    return case


def _case_to_trace_and_risk(case: dict):
    """Reconstructs just enough of TraceResult/RiskAssessment from a stored
    case row to (re)build a SAHYOG draft without re-tracing — the case table
    only ever stored the flattened verdict, not the full objects, so `source`
    comes back empty and the graph comes back empty; build_disclosure_request
    doesn't touch either."""
    result = TraceResult(
        seed_address=case["seed_address"], path=case["path"] or [case["seed_address"]],
        graph=nx.DiGraph(), hop_count=case["hop_count"] or 0,
        entity_type=case["entity_type"] or "unknown", label=case["label"],
        confidence=float(case["confidence"]) if case["confidence"] is not None else 0.0,
    )
    risk = RiskAssessment(
        compliance_status=case["compliance_status"] or "unknown",
        compliance_detail=case["compliance_detail"] or "",
        risk_flag=case["risk_flag"], risk_level=case["risk_level"] or "none",
        risk_reason=case["risk_reason"],
    )
    return result, risk


@app.get("/v1/cases/{case_id}")
def case_detail(case_id: int, officer: Officer = Depends(get_current_officer)):
    case = _require_case(case_id)
    case["events"] = list_case_events(case_id)
    return case


class CaseUpdateRequest(BaseModel):
    status: str | None = None
    tags: list[str] | None = None
    ncrp_ack_number: str | None = None
    cctns_fir_number: str | None = None


@app.patch("/v1/cases/{case_id}")
def update_case(case_id: int, req: CaseUpdateRequest, officer: Officer = Depends(get_current_officer)):
    case = _require_case(case_id)
    if req.status is not None:
        try:
            update_case_status(case_id, req.status, officer.id)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
    if req.tags is not None:
        update_case_tags(case_id, req.tags, officer.id)
    if req.ncrp_ack_number is not None or req.cctns_fir_number is not None:
        update_case_legal_refs(case_id, req.ncrp_ack_number or case.get("ncrp_ack_number"),
                               req.cctns_fir_number or case.get("cctns_fir_number"), officer.id)
    return get_case(case_id)


@app.post("/v1/cases/{case_id}/sahyog")
def generate_sahyog_draft(case_id: int, officer: Officer = Depends(get_current_officer)):
    """(Re)generates the disclosure-request draft for an existing case —
    always resets its status to 'draft', since a fresh draft supersedes
    whatever submission state the old one was in."""
    case = _require_case(case_id)
    result, risk = _case_to_trace_and_risk(case)
    draft = build_disclosure_request(case["chain"], result, risk)
    save_sahyog_draft(case_id, draft["recommended_instrument"]["instrument"], draft, officer.id)
    return get_case(case_id)


class SahyogStatusRequest(BaseModel):
    status: str


@app.patch("/v1/cases/{case_id}/sahyog")
def update_sahyog(case_id: int, req: SahyogStatusRequest, officer: Officer = Depends(get_current_officer)):
    """Manual status tracking — Draft -> Ready for submission -> Submitted ->
    Acknowledged -> Fulfilled. Nothing syncs this automatically; no real
    SAHYOG API exists to sync against (see the plan's SAHYOG research)."""
    _require_case(case_id)
    try:
        update_sahyog_status(case_id, req.status, officer.id)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return get_case(case_id)


@app.get("/v1/coverage")
def coverage():
    """Indian VASP dataset address counts — same numbers the Streamlit
    sidebar shows, so both UIs state coverage honestly and identically."""
    return coverage_summary()


@app.get("/v1/chains")
def chains():
    """Chain registry (name -> enabled/currency), without the fetch lambdas —
    lets a frontend build its chain picker from one source of truth instead
    of hardcoding a second copy of app/chains.py."""
    return {name: {"enabled": cfg["enabled"], "currency": cfg.get("currency")}
            for name, cfg in CHAINS.items()}


class WatchlistAddRequest(BaseModel):
    address: str = Field(min_length=1)
    chain: str | None = None  # omit to auto-detect, same as /v1/trace


@app.post("/v1/watchlist")
def watchlist_add(req: WatchlistAddRequest, officer: Officer = Depends(get_current_officer)):
    chain = req.chain or detect_chain(req.address)[0] or "Ethereum"
    init_watchlist_db()
    watch_id = add_to_watchlist(req.address, chain, officer.id)
    _log_action_safely(officer.id, "watchlist_add", req.address, {"chain": chain})
    return get_watch(watch_id)


@app.get("/v1/watchlist")
def watchlist_list(officer: Officer = Depends(get_current_officer)):
    try:
        init_watchlist_db()
        return list_watchlist()
    except Exception as exc:
        raise HTTPException(503, f"Watchlist database unreachable: {exc}")


@app.post("/v1/watchlist/{watch_id}/check")
def watchlist_check(watch_id: int, officer: Officer = Depends(get_current_officer)):
    """Re-runs the trace for a watched address and records whether anything
    alert-worthy changed. No scheduler yet — this is the manual "Check now"
    button; automatic periodic re-checking is a stated future step, not
    silently implied as already happening."""
    watch = get_watch(watch_id)
    if not watch:
        raise HTTPException(404, f"Watchlist entry {watch_id} not found.")

    chain_cfg = CHAINS.get(watch["chain"])
    if not chain_cfg or not chain_cfg["enabled"]:
        raise HTTPException(400, f"{watch['chain']} isn't wired up in this build.")

    try:
        result = trace_to_nearest_entity(
            seed_address=watch["address"], currency=chain_cfg["currency"],
            fetch_transactions_fn=chain_cfg["fetch"],
            labels_lookup=_labels(), mixers_lookup=KNOWN_MIXERS, max_hops=DEFAULT_MAX_HOPS,
        )
    except Exception as exc:
        raise HTTPException(502, f"Re-check failed: {exc}")
    risk = assess(result)

    updated = record_check(watch_id, result.entity_type, result.label, risk.risk_level)
    _log_action_safely(officer.id, "watchlist_check", watch["address"],
                       {"risk_level": risk.risk_level, "alert_status": updated["alert_status"]})
    return updated


class WatchlistStatusRequest(BaseModel):
    status: str


@app.patch("/v1/watchlist/{watch_id}")
def watchlist_update(watch_id: int, req: WatchlistStatusRequest, officer: Officer = Depends(get_current_officer)):
    if not get_watch(watch_id):
        raise HTTPException(404, f"Watchlist entry {watch_id} not found.")
    try:
        update_alert_status(watch_id, req.status)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return get_watch(watch_id)


@app.delete("/v1/watchlist/{watch_id}")
def watchlist_remove(watch_id: int, officer: Officer = Depends(get_current_officer)):
    if not get_watch(watch_id):
        raise HTTPException(404, f"Watchlist entry {watch_id} not found.")
    remove_from_watchlist(watch_id)
    return {"status": "removed"}
