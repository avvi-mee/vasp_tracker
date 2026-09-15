"""SAHYOG adapter — contract-first, not a live integration.

SAHYOG is a government-internal portal; a student team can't get live API
access without I4C provisioning it. This module produces a fully-formed,
correctly-structured disclosure/freeze request in exactly the shape a real
integration would need — so the moment real access exists, only
submit_disclosure_request()'s body has to change, nothing upstream of it.

Never claims a live submission happened. Says so explicitly in every report.
"""
from datetime import datetime, timezone


def build_disclosure_request(chain: str, trace_result, risk_assessment, analyst_note: str = "") -> dict:
    """Builds the investigation-ready report / disclosure request package."""
    return {
        "request_type": "freeze_or_disclosure_request",
        "status": "DRAFT — SAHYOG live API access pending I4C provisioning. "
                  "This report is fully formatted and ready for manual or future "
                  "automated submission through the SAHYOG Portal.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chain": chain,
        "seed_address": trace_result.seed_address,
        "traced_path": trace_result.path,
        "hop_count": trace_result.hop_count,
        "matched_entity": {
            "type": trace_result.entity_type,
            "label": trace_result.label,
            "confidence": trace_result.confidence,
            "source": trace_result.source,
        },
        "compliance": {
            "status": risk_assessment.compliance_status,
            "detail": risk_assessment.compliance_detail,
        },
        "risk_flag": risk_assessment.risk_flag,
        "risk_reason": risk_assessment.risk_reason,
        "analyst_note": analyst_note or "(none provided)",
        "evidence_summary": _summarize(chain, trace_result, risk_assessment),
    }


def submit_disclosure_request(request: dict) -> dict:
    """MOCK — would POST to the real SAHYOG API once I4C provisions access.
    Currently just confirms the report is well-formed and logs it locally."""
    required = ("seed_address", "chain", "matched_entity", "compliance", "risk_flag")
    missing = [f for f in required if f not in request]
    if missing:
        return {"status": "error", "detail": f"Report missing fields: {missing}"}
    return {
        "status": "mock_accepted",
        "detail": "No live SAHYOG connection exists yet — this report was validated and "
                  "logged locally, not transmitted. Wire this function to the real SAHYOG "
                  "API endpoint once access is granted.",
    }


def _summarize(chain: str, trace_result, risk_assessment) -> str:
    entity = trace_result.label or "an unlabeled address"
    lines = [
        f"On {chain}, address {trace_result.seed_address} was traced {trace_result.hop_count} "
        f"hop(s) to {entity} (type: {trace_result.entity_type}, confidence {trace_result.confidence}).",
    ]
    if risk_assessment.risk_flag:
        lines.append(f"RISK FLAGGED: {risk_assessment.risk_reason}")
    lines.append(f"Compliance status: {risk_assessment.compliance_status} — {risk_assessment.compliance_detail}")
    return " ".join(lines)
