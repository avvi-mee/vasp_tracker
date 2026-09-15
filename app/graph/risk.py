"""Combines a trace result with the FIU-IND compliance data and the known
sanctioned-address watchlist into one risk assessment. Kept separate from
trace.py on purpose: tracing finds the entity, this module judges it —
different jobs, both worth testing independently.
"""
from dataclasses import dataclass

from app.data.fiu_compliance import check_compliance
from app.data.known_illicit import check_illicit


@dataclass
class RiskAssessment:
    compliance_status: str          # "registered_after_penalty" | "flagged_non_compliant" | "unknown"
    compliance_detail: str
    risk_flag: bool
    risk_reason: str | None = None


def assess(trace_result) -> RiskAssessment:
    # 1. Does the trace path pass through any known sanctioned/exploit address?
    for addr in trace_result.path:
        hit = check_illicit(addr)
        if hit:
            return RiskAssessment(
                compliance_status="n/a",
                compliance_detail="Trail leads to a sanctioned/flagged address, not a VASP.",
                risk_flag=True,
                risk_reason=f"{hit['label']} — {hit['reason']}",
            )

    # 2. If the trace landed on a labeled exchange, check its FIU-IND status.
    if trace_result.entity_type in ("exchange", "exchange cluster") and trace_result.label:
        compliance = check_compliance(trace_result.label)
        risk = compliance["status"] == "flagged_non_compliant"
        return RiskAssessment(
            compliance_status=compliance["status"],
            compliance_detail=compliance["detail"],
            risk_flag=risk,
            risk_reason=compliance["detail"] if risk else None,
        )

    # 3. Mixer/bridge/unknown — no VASP compliance question applies, but note it.
    if trace_result.entity_type == "mixer":
        return RiskAssessment(
            compliance_status="n/a",
            compliance_detail="Trail leads to a mixer, not a VASP — compliance check doesn't apply.",
            risk_flag=True,
            risk_reason="Funds passed through a known mixer/tumbler — likely intentional obfuscation.",
        )

    return RiskAssessment(
        compliance_status="unknown",
        compliance_detail="No entity matched, so no compliance status to check.",
        risk_flag=False,
    )
