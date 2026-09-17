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
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = logging.getLogger("vasp_trace.api")

from app.chains import CHAINS
from app.data.case_store import init_db, list_cases, save_case
from app.data.indian_vasps import coverage_summary, merge_labels
from app.data.known_mixers import KNOWN_MIXERS
from app.data.tagpacks import load_labels
from app.evidence.certificate import _jsonable, build_certificate_bundle
from app.graph.chain_detect import detect_chain
from app.graph.exposure import compute_exposure
from app.graph.risk import assess
from app.graph.trace import trace_to_nearest_entity
from app.sahyog.gateway import build_disclosure_request

load_dotenv()

app = FastAPI(title="VASP Trace API", version="1.0",
              description="Automated blockchain intelligence & VASP attribution — SIH26182")

# ponytail: wide open for local dev / the hackathon demo; tighten to the
# deployed Next.js origin (allow_credentials stays False either way — no
# cookie auth yet) once there's a real deployment to tighten it to.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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
            labels_lookup=_labels(), mixers_lookup=KNOWN_MIXERS, max_hops=4,
        )
    except Exception as exc:
        raise HTTPException(502, f"Trace failed: {exc}")
    risk = assess(result)
    return chain, chain_cfg, result, risk


def _edges(result) -> list[dict]:
    return [
        {"from": src, "to": dst, "tx_hash": edge.get("tx_hash"),
         "value_wei": edge.get("value_wei"), "amount": edge.get("amount"),
         "asset": edge.get("asset"), "timestamp": edge.get("timestamp"),
         "block_number": edge.get("block_number")}
        for src, dst, edge in result.graph.edges(data=True)
    ]


def _trace_json(result, currency: str) -> dict:
    payload = _jsonable(result)
    payload.pop("graph", None)  # str(DiGraph) is noise, not data
    payload["edges"] = _edges(result)
    payload["exposure"] = _jsonable(compute_exposure(result, currency, _labels(), KNOWN_MIXERS))
    return payload


@app.post("/v1/trace")
def trace(req: TraceRequest):
    """Trace a wallet to its nearest exchange/VASP. Auto-saves a case row
    (best-effort — a missing DATABASE_URL degrades to case_id: null, same as
    the Streamlit UI does)."""
    chain, chain_cfg, result, risk = _run_trace(req)

    case_id = None
    try:
        init_db()
        case_id = save_case(chain_cfg["currency"], result, risk)
    except Exception:
        # Best-effort, same posture as the Streamlit UI — a missing
        # DATABASE_URL shouldn't fail the trace. But swallowing it silently
        # would hide a real bug in save_case just as easily, so log it.
        logger.exception("Case save failed for %s", result.seed_address)

    return {
        "chain": chain,
        "case_id": case_id,
        "trace": _trace_json(result, chain_cfg["currency"]),
        "risk": _jsonable(risk),
        "sahyog_draft": build_disclosure_request(chain, result, risk, analyst_note=req.analyst_note),
    }


@app.post("/v1/certificate")
def certificate(req: TraceRequest):
    """Re-runs the trace and returns the s.63 BSA evidence pack (zip:
    record + Part A + Part B + hash report) as a direct download."""
    chain, _chain_cfg, result, risk = _run_trace(req)
    pack, bundle = build_certificate_bundle(
        chain, result, risk, case_reference=req.case_reference, analyst_note=req.analyst_note)
    filename = f"s63-evidence-{result.seed_address[:10]}.zip"
    return Response(bundle, media_type="application/zip",
                     headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/v1/cases")
def cases(limit: int = 200):
    try:
        init_db()
        return list_cases(limit=limit)
    except Exception as exc:
        raise HTTPException(503, f"Case database unreachable: {exc}")


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
