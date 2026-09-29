"""Combines a trace result with the FIU-IND compliance data and the known
sanctioned-address watchlist into one risk assessment. Kept separate from
trace.py on purpose: tracing finds the entity, this module judges it —
different jobs, both worth testing independently.
"""
from dataclasses import dataclass, field

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
    # Which of the two questions below drove risk_level, and the behavioural
    # patterns that contributed. Shown to the officer so a verdict is never a
    # bare colour with no stated basis.
    basis: str = "trail"            # "trail" | "behaviour"
    typologies: list[str] = field(default_factory=list)


SANCTIONS_KEYWORDS = ("ofac", "sanction", "sdn")  # matched against label text, case-insensitive

# GraphSense's real category vocabulary (checked against the vendored tag
# packs, not guessed): "mixer" never actually appears — real mixer packs
# (Tornado Cash, Blender.io, Wasabi, Samourai, Sinbad...) are tagged
# "mixing_service" or "coinjoin". An exact match on "mixer" alone silently
# missed all of them, scoring real mixers as low-risk "unattributed."
MIXER_CATEGORIES = {"mixer", "mixing_service", "coinjoin"}
# Darknet markets (e.g. Hydra Market, confirmed present in the vendored
# data) are tagged "market" — the problem statement names "darknet
# activities" explicitly, so this gets its own high-severity case rather
# than falling into case 5's generic "no specific rule" bucket.
DARKNET_MARKET_CATEGORIES = {"market"}
# "illicit" is what chain_native_labels.entity_category() assigns to abuse-
# tagged and hack/scam-worded labels; "black_list" is GraphSense's own.
ILLICIT_CATEGORIES = {"illicit", "black_list"}
# Terminals where funds leave this chain: the trace ends at the bridge or swapper,
# but the money does not — it resurfaces elsewhere.
CHAIN_HOP_CATEGORIES = {"bridge", "swap_service"}
# Same bar trace.py uses for "material" — a branch this big was followed on
# purpose, so what it reached counts.
SIDE_BRANCH_SHARE = 0.10

# Categories whose ordinary business *is* the behaviour the typology
# detectors look for. Checked live: Binance's own Tron hot wallet fires
# rapid_layering at high severity — 25 funders, forwards nearly everything
# within minutes — because that is precisely what a hot wallet does all day.
# Calling an FIU-registered exchange's operating wallet high-risk for
# behaving like an exchange would discredit every other finding on the page.
SELF_EXPLAINING_CATEGORIES = {"exchange", "exchange cluster", "custodian"}


def _explorer_flags_on_path(trace_result) -> list[str]:
    """Addresses on this trail that the block explorer itself marks risky.
    An unexplained third-party boolean: good enough to raise attention and
    demand a look, never good enough to be a verdict by itself — so it only
    ever escalates the two cases below that would otherwise say "low".
    """
    flagged = set(getattr(trace_result, "explorer_flagged", None) or ())
    return [a for a in trace_result.path if a in flagged]


def _chainalysis_hits(trace_result) -> set[str]:
    """Addresses either Chainalysis source lists — the on-chain oracle or the
    Sanctions Screening API.

    Unioned rather than required to agree, because they do not have the same
    reach: the oracle is EVM-only, the API covers every chain but needs a
    key. On a Bitcoin trail only the API can answer; on an EVM trail with no
    key configured, only the oracle can. Demanding both would mean the
    stricter source silently disabling the other.

    None from either client means "not consulted" and must not be read as
    "clean". Flattening to an empty set is safe *here* only because every
    caller below asks "is this address listed", never "was this chain
    covered" — that second question is answered for the officer from the
    trace payload's own oracle_sanctioned / api_sanctioned fields, and in the
    certificate's sanctions_screening block, not from a risk level.
    """
    return (set(getattr(trace_result, "oracle_sanctioned", None) or ())
            | set(getattr(trace_result, "api_sanctioned", None) or ()))


def _assess_trail(trace_result) -> RiskAssessment:
    # 1. Does the trace path pass through a sanctioned/exploit address? Highest severity — this
    #    isn't a compliance question, it's a direct watchlist hit.
    #
    #    Independent sources answer it. Our own curated list + the vendored OFAC SDN dump
    #    (known_illicit.py) is a snapshot: exactly as current as the last `git pull` in that
    #    directory, and OFAC-only. Chainalysis — via its on-chain oracle, its Screening API, or
    #    both — is read at query time and covers EU and UN designations too. Any one firing is
    #    enough for HIGH; which ones fired goes in the reason, because "two sources agree" and
    #    "only the live one knows about this yet" are different strengths of evidence and an
    #    officer should see which they have.
    chainalysis = _chainalysis_hits(trace_result)
    # Every followed path, primary first. A sanctioned address is a hit on
    # any branch, whatever its share.
    on_trail = list(dict.fromkeys(
        [*trace_result.path, *(a for c in getattr(trace_result, "candidates", None) or () for a in c.path)]))
    for addr in on_trail:
        hit = check_illicit(addr)
        on_chainalysis = addr in chainalysis
        if hit or on_chainalysis:
            if hit and on_chainalysis:
                reason = (f"{hit['label']} — {hit['reason']}. Independently confirmed by "
                          f"Chainalysis sanctions data.")
            elif hit:
                reason = f"{hit['label']} — {hit['reason']}"
            else:
                reason = (f"{addr} is listed by Chainalysis sanctions data "
                          f"(US/EU/UN designations, read at query time). Not present in this "
                          f"build's vendored OFAC SDN snapshot — refresh it, or treat Chainalysis "
                          f"as the more current of the two.")
            return RiskAssessment(
                compliance_status="n/a",
                compliance_detail="Trail leads to a sanctioned/flagged address, not a VASP.",
                risk_flag=True, risk_level="high",
                risk_reason=reason,
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
    #    Matches the curated known_mixers.py list (literal "mixer") and any
    #    GraphSense-labeled mixing service (see MIXER_CATEGORIES above).
    entity_category = (trace_result.entity_type or "").lower()
    if entity_category in MIXER_CATEGORIES:
        return RiskAssessment(
            compliance_status="n/a",
            compliance_detail="Trail leads to a mixer, not a VASP — compliance check doesn't apply.",
            risk_flag=True, risk_level="high",
            risk_reason="Funds passed through a known mixer/tumbler — likely intentional obfuscation.",
        )

    # 3b. Darknet market — same severity tier as a mixer, and one of the
    #     problem statement's own named categories.
    if entity_category in DARKNET_MARKET_CATEGORIES:
        return RiskAssessment(
            compliance_status="n/a",
            compliance_detail="Trail leads to a darknet market, not a VASP — compliance check doesn't apply.",
            risk_flag=True, risk_level="high",
            risk_reason=f"Funds reached a labeled darknet market ({trace_result.label}).",
        )

    # 3c. Illicit actor — ransomware, scam, phishing, hack, terrorism
    #     campaigns. GraphSense marks these with `abuse` rather than a
    #     category (see chain_native_labels.entity_category).
    if entity_category in ILLICIT_CATEGORIES:
        return RiskAssessment(
            compliance_status="n/a",
            compliance_detail="Trail leads to an address labelled as a criminal actor, not a VASP.",
            risk_flag=True, risk_level="high",
            risk_reason=f"Funds reached an address labelled '{trace_result.label}' "
                        f"(ransomware / scam / hack source: {trace_result.source}).",
        )

    # 3d. A material side branch reached a mixer, darknet market or criminal
    #     actor. The primary path is only the largest share, not the whole
    #     story: 60% to Binance and 40% to Tornado is not a clean trail.
    for c in getattr(trace_result, "candidates", None) or ():
        category = (c.entity_type or "").lower()
        risky = (category in MIXER_CATEGORIES or category in DARKNET_MARKET_CATEGORIES
                 or category in ILLICIT_CATEGORIES
                 or (c.label and any(kw in c.label.lower() for kw in SANCTIONS_KEYWORDS)))
        if c.path != trace_result.path and c.value_share >= SIDE_BRANCH_SHARE and risky:
            return RiskAssessment(
                compliance_status="n/a",
                compliance_detail="A material share of the funds left the main path for a high-risk entity.",
                risk_flag=True, risk_level="high",
                risk_reason=(f"{c.value_share:.0%} of the traced value reached {c.label} ({c.entity_type}) "
                             f"on a side branch, while the main path reached "
                             f"{trace_result.label or 'no named entity'}."),
            )

    # 3e. Chain-hop — the primary path, or a material side branch, ends at a bridge or an
    #     instant-swap service. Not evidence of wrongdoing (bridges are ordinary), but it is
    #     exactly where a single-chain trace goes blind, so the officer has to be told the
    #     trail continues. Medium, never lower: a "no risk" verdict here would be false comfort.
    for c in getattr(trace_result, "candidates", None) or ():
        category = (c.entity_type or "").lower()
        if category in CHAIN_HOP_CATEGORIES and (c.path == trace_result.path or c.value_share >= SIDE_BRANCH_SHARE):
            swap = category == "swap_service"
            compliance = check_compliance(c.label) if swap else None
            return RiskAssessment(
                compliance_status=compliance["status"] if swap else "n/a",
                compliance_detail=(compliance["detail"] if swap else
                                   "Trail leads to a cross-chain bridge, not a VASP account — the funds "
                                   "continue on another chain."),
                risk_flag=True, risk_level="medium",
                risk_reason=(f"Chain-hop: {c.value_share:.0%} of the traced value went through {c.label}, "
                             f"so the funds continue on another chain and this trace stops here. "
                             f"Resolve the destination and continue the trace there."),
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
    flagged = _explorer_flags_on_path(trace_result)
    if trace_result.label:
        return RiskAssessment(
            compliance_status="unknown",
            compliance_detail=f"Matched '{trace_result.label}' (category: {trace_result.entity_type}), "
                              f"but no specific compliance/risk rule applies to this category yet.",
            risk_flag=True, risk_level="medium" if flagged else "low",
            risk_reason=(f"Labeled entity outside current risk categories, and the block explorer "
                         f"flags {len(flagged)} address(es) on this trail as risky — worth analyst review."
                         if flagged else
                         "Labeled entity outside current risk categories — worth analyst review."),
        )

    # 6. No entity matched at all — genuinely uncertain, not "confirmed clean." Worth a low-severity
    #    flag for analyst attention rather than silently treating "unknown" as "safe."
    if flagged:
        return RiskAssessment(
            compliance_status="unknown",
            compliance_detail="No entity matched, so no compliance status to check.",
            risk_flag=True, risk_level="medium",
            risk_reason=(f"Unattributed trail, and the block explorer independently flags "
                         f"{len(flagged)} address(es) on it as risky ({', '.join(flagged[:3])}). "
                         f"Corroboration only — the explorer does not publish its reasoning."),
        )
    return RiskAssessment(
        compliance_status="unknown",
        compliance_detail="No entity matched, so no compliance status to check.",
        risk_flag=True, risk_level="low",
        risk_reason="No known entity or watchlist match — unattributed trail, not verified safe.",
    )


def assess(trace_result, typologies=()) -> RiskAssessment:
    """Two different questions, deliberately answered separately and then
    combined by taking the worse of the two:

      trail      — what did the money reach? A mixer, a sanctioned address, a
                   darknet market, an FIU-registered exchange? This is what
                   _assess_trail() has always answered.
      behaviour  — how does the subject wallet itself behave? Funnelling,
                   layering, smurfing, peeling (see app/graph/typology.py).

    Conflating the two is what produced the bug this fixes. Before chain-native
    labels landed, every real address fell through to "no entity matched → LOW"
    and the tool said LOW RISK to everything. After they landed it got worse in
    a subtler way: a scam wallet that sweeps victim money straight into Binance
    reaches an FIU-registered exchange, so the trail question answers "compliant
    → NONE" — and a wallet funded by 16 victims was scored clean.

    "Where the money went" and "is this wallet dirty" are not the same question.
    The exchange being compliant is good news about *who to serve a BNSS s.94
    notice on*, not evidence that the subject is innocent. So behaviour is
    assessed independently and the higher of the two levels wins, with the
    basis named either way.
    """
    trail = _assess_trail(trace_result)
    typologies = list(typologies or ())
    if not typologies:
        return trail

    # The officer pasted an exchange's own wallet, not a suspect's. The
    # patterns are real and stay on the record, but they describe that
    # business operating normally, so they do not escalate. See
    # SELF_EXPLAINING_CATEGORIES above for the live false positive this fixes.
    subject = getattr(trace_result, "subject_entity", None) or (
        {"label": trace_result.label, "category": trace_result.entity_type}
        if trace_result.hop_count == 0 and trace_result.label else None)
    if subject and (subject.get("category") or "").lower() in SELF_EXPLAINING_CATEGORIES:
        trail.typologies = [t.name for t in typologies]
        trail.risk_reason = (
            (trail.risk_reason + " " if trail.risk_reason else "")
            + f"Behavioural patterns were detected ({', '.join(t.name for t in typologies)}) but did "
              f"not raise the risk level: this address is {subject.get('label')}, and high-throughput "
              f"pass-through activity is that service's normal operation, not a signal about it.")
        return trail

    from app.graph.typology import highest_severity  # local: typology imports nothing from here
    behaviour_level = highest_severity(typologies)
    if RISK_LEVELS.index(behaviour_level) <= RISK_LEVELS.index(trail.risk_level):
        trail.typologies = [t.name for t in typologies]
        return trail

    top = typologies[0]
    return RiskAssessment(
        compliance_status=trail.compliance_status,
        compliance_detail=trail.compliance_detail,
        risk_flag=True,
        risk_level=behaviour_level,
        risk_reason=(f"{top.title}: {top.explanation}"
                     + (f" ({len(typologies) - 1} further pattern(s) also matched.)"
                        if len(typologies) > 1 else "")),
        basis="behaviour",
        typologies=[t.name for t in typologies],
    )
