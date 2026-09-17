"""SAHYOG adapter — contract-first, not a live integration.

SAHYOG is a government-internal portal; a student team can't get live API
access without I4C provisioning it. This module produces a fully-formed,
correctly-structured disclosure/freeze request in exactly the shape a real
integration would need — so the moment real access exists, only
submit_disclosure_request()'s body has to change, nothing upstream of it.

Updated on fresh research: a Bitget press release (23 Jun 2025), independently
corroborated by one trade-press outlet, states 45+ crypto exchanges (WazirX,
KuCoin, Bybit among them) are onboarded to SAHYOG specifically for VASP data-
disclosure requests citing **BNSS 2023 s.94** — still a manual, portal-form
workflow with no public API, but a sharper, real target than a generic
"disclosure request" was. Neither claim is from an official MHA/I4C source,
so this stays honest about that too.

Never claims a live submission happened. Says so explicitly in every report.
"""
from datetime import datetime, timezone

# Which of the four legally operative instruments to lead with — the plan's
# own domain finding #2, made computable. This is a starting recommendation
# for the officer to confirm, never an automated legal determination: the
# routing rule is simple on purpose, and every reason is stated so it can be
# checked, not trusted blindly.
INSTRUMENTS = {
    "s94_bnss": "BNSS 2023 s.94 — summons for documents/KYC records",
    "s107_bnss": "BNSS 2023 s.107 — attachment of proceeds of crime",
    "pmla_s5": "PMLA s.5 — provisional attachment (ED route)",
    "s63_bsa": "BSA 2023 s.63 — evidence certificate only",
}


def recommend_instrument(trace_result, risk_assessment) -> dict:
    """Rule-based recommendation among the four instruments — VASP
    FIU-registered and Indian favors s.94; a high-risk trail with an
    identified destination favors s.107 (available to state police without
    ED); FIU non-compliant/offshore favors the PMLA route; anything else
    still gets the s.63 certificate, since that preserves the evidence
    regardless of which disclosure instrument eventually applies."""
    compliance = risk_assessment.compliance_status
    is_exchange = trace_result.entity_type in ("exchange", "exchange cluster")

    if compliance == "registered_after_penalty" and is_exchange:
        key, reason = "s94_bnss", "VASP is FIU-registered — the standard KYC/records summons route."
    elif risk_assessment.risk_level == "high" and is_exchange:
        key, reason = "s107_bnss", ("High-risk trail with an identified destination — a time-critical "
                                    "attachment route available to state police without going through ED.")
    elif compliance == "flagged_non_compliant":
        key, reason = "pmla_s5", "VASP is FIU non-compliant/offshore — likely needs ED's PMLA route, not a domestic summons."
    else:
        key, reason = "s63_bsa", "No specific disclosure/freeze instrument indicated yet — the evidence certificate still applies."

    return {"instrument": key, "label": INSTRUMENTS[key], "reason": reason}


def build_disclosure_request(chain: str, trace_result, risk_assessment, analyst_note: str = "") -> dict:
    """Builds the investigation-ready report / disclosure request package."""
    return {
        "request_type": "vasp_data_disclosure_request",
        "legal_basis": "BNSS 2023 s.94 (summons for documents, incl. electronic records) — the same "
                       "provision reportedly cited for crypto-exchange onboarding to SAHYOG since mid-2025.",
        "recommended_instrument": recommend_instrument(trace_result, risk_assessment),
        "status": "DRAFT — SAHYOG's crypto-VASP disclosure workflow is manual/portal-based, no public "
                  "API exists to submit this automatically. Ready for manual submission through the "
                  "SAHYOG Portal by an onboarded nodal officer.",
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
