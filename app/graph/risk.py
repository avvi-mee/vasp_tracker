"""Combines a trace result with the FIU-IND compliance data and the known
sanctioned-address watchlist into one risk assessment. Kept separate from
trace.py on purpose: tracing finds the entity, this module judges it —
different jobs, both worth testing independently.
"""
from dataclasses import dataclass

from app.data.fiu_compliance import check_compliance
from app.data.known_illicit import check_illicit


RISK_LEVELS = ("none", "low", "medium", "high")  # ordered, low->high severity


@dataclass
class RiskAssessment:
    compliance_status: str          # "registered_after_penalty" | "flagged_non_compliant" | "unknown"
    compliance_detail: str
    risk_flag: bool                 # True whenever risk_level != "none" — kept for simple yes/no checks
    risk_level: str = "none"        # "none" | "low" | "medium" | "high" — see RISK_LEVELS
    risk_reason: str | None = None


SANCTIONS_KEYWORDS = ("ofac", "sanction", "sdn")  # matched against label text, case-insensitive


def assess(trace_result) -> RiskAssessment:
    # 1. Does the trace path pass through any known sanctioned/exploit address (our small curated
    #    watchlist)? Highest severity — this isn't a compliance question, it's a direct watchlist hit.
    for addr in trace_result.path:
        hit = check_illicit(addr)
        if hit:
            return RiskAssessment(
                compliance_status="n/a",
                compliance_detail="Trail leads to a sanctioned/flagged address, not a VASP.",
                risk_flag=True, risk_level="high",
                risk_reason=f"{hit['label']} — {hit['reason']}",
            )

    # 2. Does the MATCHED LABEL ITSELF indicate a sanctions listing? This catches the ~1,150 real
    #    OFAC SDN addresses that came in through GraphSense TagPacks (research/02), not just our
    #    small hand-curated list above — those are tagged category="user", so without this check
    #    they'd fall through to case 4 and get scored as low-risk "unattributed," which is wrong:
    #    an OFAC hit is a confirmed match, not an absence of one.
    if trace_result.label and any(kw in trace_result.label.lower() for kw in SANCTIONS_KEYWORDS):
        return RiskAssessment(
            compliance_status="n/a",
            compliance_detail="Address itself is on a sanctions list — not a VASP compliance question.",
            risk_flag=True, risk_level="high",
            risk_reason=f"{trace_result.label} (source: {trace_result.source})",
        )

    # 3. Mixer — also high severity: the whole point of a mixer is obscuring the trail.
    if trace_result.entity_type == "mixer":
        return RiskAssessment(
            compliance_status="n/a",
            compliance_detail="Trail leads to a mixer, not a VASP — compliance check doesn't apply.",
            risk_flag=True, risk_level="high",
            risk_reason="Funds passed through a known mixer/tumbler — likely intentional obfuscation.",
        )

    # 4. Labeled exchange — severity follows its FIU-IND compliance status.
    if trace_result.entity_type in ("exchange", "exchange cluster") and trace_result.label:
        compliance = check_compliance(trace_result.label)
        flagged = compliance["status"] == "flagged_non_compliant"
        return RiskAssessment(
            compliance_status=compliance["status"],
            compliance_detail=compliance["detail"],
            risk_flag=flagged, risk_level="medium" if flagged else "none",
            risk_reason=compliance["detail"] if flagged else None,
        )

    # 5. A label WAS found, but its category isn't one we have specific risk guidance for (e.g.
    #    GraphSense categories like "organization", "defi_dex" outside our exchange/mixer handling).
    #    Different from case 6 below — we DO know something about this address, just not its risk
    #    tier, so say that plainly instead of implying no match was found at all.
    if trace_result.label:
        return RiskAssessment(
            compliance_status="unknown",
            compliance_detail=f"Matched '{trace_result.label}' (category: {trace_result.entity_type}), "
                              f"but no specific compliance/risk rule applies to this category yet.",
            risk_flag=True, risk_level="low",
            risk_reason="Labeled entity outside current risk categories — worth analyst review.",
        )

    # 6. No entity matched at all — genuinely uncertain, not "confirmed clean." Worth a low-severity
    #    flag for analyst attention rather than silently treating "unknown" as "safe."
    return RiskAssessment(
        compliance_status="unknown",
        compliance_detail="No entity matched, so no compliance status to check.",
        risk_flag=True, risk_level="low",
        risk_reason="No known entity or watchlist match — unattributed trail, not verified safe.",
    )
