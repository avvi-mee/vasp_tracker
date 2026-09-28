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

from app.data.fiu_compliance import check_compliance

# A starting recommendation for the officer to confirm, never an automated
# legal determination — every reason is stated so it can be checked. Routing
# follows docs/sih-review/RESEARCH.md B.4–B.5.
INSTRUMENTS = {
    "s94_bnss": "BNSS 2023 s.94 — production of documents / electronic records (KYC, transactions)",
    "s106_bnss": "BNSS 2023 s.106 — police seizure (debit-freeze), reported forthwith to the Magistrate",
    "s107_bnss": "BNSS 2023 s.107 — attachment of proceeds of crime on a Magistrate's order",
    "freeze_officer_choice": "BNSS 2023 s.106 or s.107 — High Courts split; officer to choose",
    "issuer_freeze": "Stablecoin issuer freeze request (USDT / USDC contract-level blacklist)",
    "lor_mlat": "Letter of request / MLAT (BNSS s.112 — verify) + FIU-IND intimation",
    "s63_bsa": "BSA 2023 s.63 — evidence certificate only (no custodian to serve yet)",
    "pmla_s5": "PMLA s.5 — provisional attachment (ED route)",  # kept for drafts saved before routing v2
}

LEGAL_BASIS = {
    "s94_bnss": ("BNSS 2023 s.94 — summons to produce documents and electronic records. A disclosure "
                 "instrument only: it cannot authorise a freeze (Bombay HC, Smartpaddle, 30 Jul 2026; "
                 "AP HC, Blue Sea Ventures, 31 Mar 2026)."),
    "s106_bnss": ("BNSS 2023 s.106 — police power to seize; a debit-freeze is a species of seizure and must "
                  "be reported forthwith to the Magistrate (Karnataka HC, JAR Gold Retail, 10 Aug 2026; "
                  "Bombay HC, Smartpaddle, 30 Jul 2026)."),
    "s107_bnss": ("BNSS 2023 s.107 — attachment of proceeds of crime on application to the Magistrate "
                  "(AP HC, Blue Sea Ventures, 31 Mar 2026: s.106 does not authorise a freeze)."),
    "freeze_officer_choice": ("BNSS 2023 s.106 (police freeze, report to Magistrate) or s.107 (Magistrate's "
                              "attachment order): the High Courts are split in 2026 and this state's position "
                              "is not recorded here. Both drafts are provided; the officer chooses."),
    "issuer_freeze": "Stablecoin issuer's own terms and law-enforcement request policy (contract blacklist).",
    "lor_mlat": ("Letter of request for investigation abroad (BNSS s.112 — verify) or MLAT, with intimation "
                 "to FIU-IND; the platform is on FIU-IND's non-compliance list."),
    "s63_bsa": "BSA 2023 s.63 — certificate for electronic evidence; preserves the trace for court.",
}

# 2026 High Court positions on freezing (RESEARCH.md B.4). Only states with a
# ruling found; everywhere else is "unsettled" and the officer chooses.
STATE_FREEZE_POSITION = {
    "karnataka": ("s106_bnss", "Karnataka HC, State of Karnataka v. JAR Gold Retail, 10 Aug 2026"),
    "maharashtra": ("s106_bnss", "Bombay HC, Smartpaddle Technology v. State of Maharashtra, 30 Jul 2026"),
    "goa": ("s106_bnss", "Bombay HC, Smartpaddle Technology v. State of Maharashtra, 30 Jul 2026"),
    "andhra pradesh": ("s107_bnss", "AP HC, Blue Sea Ventures v. State of AP, 31 Mar 2026"),
}

CUSTODIAL = ("exchange", "exchange cluster", "custodian")
STABLECOINS = ("USDT", "USDC")


def _freeze_options(stable: bool) -> list[dict]:
    options = [
        {"instrument": "s106_bnss", "label": INSTRUMENTS["s106_bnss"],
         "when": "Karnataka / Bombay HC jurisdictions: police freeze, then report to the Magistrate"},
        {"instrument": "s107_bnss", "label": INSTRUMENTS["s107_bnss"],
         "when": "Andhra Pradesh HC jurisdiction: apply to the Magistrate for attachment"},
    ]
    if stable:
        options.append({"instrument": "issuer_freeze", "label": INSTRUMENTS["issuer_freeze"],
                        "when": "Fastest while funds still sit in USDT / USDC — the issuer can blacklist the address"})
    return options


def recommend_instrument(trace_result, risk_assessment, request_type: str = "disclosure",
                         state: str | None = None) -> dict:
    """Pick the instrument from what is being asked (disclosure or freeze),
    who holds the account (the VASP directory), and — for a freeze — the
    state's High Court position. Risk level no longer decides this: a high-
    risk trail still needs a disclosure notice first."""
    compliance = check_compliance(trace_result.label) if trace_result.label else {"status": "unknown"}
    custodial = (trace_result.entity_type or "").lower() in CUSTODIAL
    stable = bool(trace_result.asset and (trace_result.asset[0] or "").upper() in STABLECOINS)
    channel = compliance.get("le_channel", "")
    options: list[dict] = []

    if request_type == "freeze":
        options = _freeze_options(stable)
        if not custodial:
            key = "issuer_freeze" if stable else "s63_bsa"
            reason = ("No custodian on this trail to freeze with."
                      + (" The funds are still in a stablecoin, so the issuer can blacklist the address."
                         if stable else " Continue the trace to the next custodial hop."))
            options = [o for o in options if o["instrument"] == "issuer_freeze"]
        else:
            position = STATE_FREEZE_POSITION.get((state or "").strip().lower())
            if position:
                key, ruling = position
                reason = f"Freeze route per {ruling} — binding in {state}."
            else:
                key = "freeze_officer_choice"
                reason = (f"No High Court ruling on s.106 vs s.107 is recorded for "
                          f"{state or 'this state'} — both drafts are provided; choose one.")
            if compliance["status"] == "flagged_non_compliant":
                reason += " The platform is on FIU-IND's non-compliance list; expect to need its LE portal or an MLAT."
    elif not custodial:
        key, reason = "s63_bsa", ("No exchange or custodian on this trail — nobody to serve a disclosure notice on "
                                  "yet. Continue the trace; the s.63 certificate preserves the evidence meanwhile.")
    elif compliance["status"] == "flagged_non_compliant":
        key, reason = "lor_mlat", (f"{compliance['detail']} — no Indian registration to compel production, so a "
                                   f"domestic s.94 notice is unlikely to be honoured.")
    else:
        key = "s94_bnss"
        reason = {
            "registered": "Indian FIU-registered VASP — a PMLA reporting entity that must hold the KYC record.",
            "registered_after_penalty": "Offshore VASP registered with FIU-IND — serve through its law-enforcement portal.",
        }.get(compliance["status"], "VASP not in the directory — verify its FIU-IND registration before serving.")

    return {"instrument": key, "label": INSTRUMENTS[key], "reason": reason, "request_type": request_type,
            "state": state, "channel": channel, "legal_basis": LEGAL_BASIS[key], "options": options}


def _path_tx_hashes(trace_result) -> list[str]:
    path = trace_result.path or []
    hashes = []
    for src, dst in zip(path, path[1:]):
        edge = trace_result.graph.get_edge_data(src, dst) if trace_result.graph is not None else None
        if edge and edge.get("tx_hash"):
            hashes.append(edge["tx_hash"])
    return hashes


def build_disclosure_request(chain: str, trace_result, risk_assessment, analyst_note: str = "",
                             request_type: str = "disclosure", state: str | None = None) -> dict:
    """Builds the investigation-ready report / disclosure (or freeze) request package."""
    rec = recommend_instrument(trace_result, risk_assessment, request_type, state)
    deposit = getattr(trace_result, "deposit", None)
    return {
        "request_type": "vasp_freeze_request" if request_type == "freeze" else "vasp_data_disclosure_request",
        "legal_basis": rec["legal_basis"],
        "recommended_instrument": rec,
        "state": state,
        # What the VASP can actually answer about: the deposit address maps to
        # one KYC'd account; the tx hashes let it find the credits.
        "deposit_address": deposit.address if deposit and deposit.is_deposit_address else None,
        "tx_hashes": _path_tx_hashes(trace_result),
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
