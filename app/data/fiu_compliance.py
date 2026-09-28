"""VASP directory: FIU-IND status, jurisdiction and law-enforcement channel
for named VASPs, compiled from docs/sih-review/RESEARCH.md B.2–B.5 (every
entry carries its source). No complete official roster is public — FIU-IND
reported 50 registrants by ~Oct 2025 but names only reached the record once,
in a Lok Sabha answer (4 Dec 2023). So this is deliberately partial: never
treat "not listed here" as "confirmed compliant" or "confirmed unregistered".

Matching is a plain substring check against the entity label, checked in
this order (Indian registrants, then registered-after-penalty, then the
notice waves) — transparent, so a wrong match is easy to spot and fix.
"""

LOK_SABHA_2023 = "https://inc42.com/buzz/coindcx-wazirx-28-vda-service-providers-registered-fiu-govt/"
INDIAN_LE_CHANNEL = ("Exchange's nodal / grievance officer (PMLA reporting entity — must hold KYC); "
                     "SAHYOG portal per the problem statement")

# Named FIU-IND registrants — Lok Sabha reply, 4 Dec 2023 (MoS Finance).
# "coinswitchx" before "coinswitch" so the more specific entity wins.
REGISTERED_INDIAN = {
    "coindcx": {"entity": "Neblio Technologies Pvt Ltd"},
    "wazirx": {"entity": "Zanmai Labs Pvt Ltd",
               "note": "Operating/registration status after the Singapore restructuring not re-verified."},
    "coinswitchx": {"entity": "Nextgendev Solutions Pvt Ltd"},
    "coinswitch": {"entity": "Bitcipher Labs LLP"},
    "zebpay": {"entity": "Awlencan Innovations India Ltd"},
}

# High confidence — named in an official FIU-IND penalty order, then registered.
PENALIZED_THEN_REGISTERED = {
    "binance": {
        "detail": "Penalized ₹18.82 crore (Order 19 Jun 2024), registered and resumed India operations.",
        "source": "fiuindia.gov.in Order No. 10/DIR/FIU-IND/2024",
        "le_channel": ("Binance Government Law Enforcement Request System (Kodex) — "
                       "https://www.binance.com/en/support/law-enforcement"),
    },
    "kucoin": {
        "detail": "Penalized ₹34.5 lakh (~22 Mar 2024), first offshore VASP to register with FIU-IND.",
        "source": "fiuindia.gov.in Order PGL_Order_08_2024",
        "le_channel": "KuCoin law-enforcement request channel (verify current portal)",
    },
    "bybit": {
        "detail": "Penalized ₹9.27 crore (Order 31 Jan 2025), cleared for India operations after settlement.",
        "source": "fiuindia.gov.in Order Bybit_Order_15_2024",
        "le_channel": "Bybit law-enforcement request channel (verify current portal)",
    },
}

WAVE_1 = ("Wave 1, 28 Dec 2023 show-cause notice", "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1991372")
WAVE_2 = ("Wave 2, ~1 Oct 2025 non-compliance notice",
          "https://coingeek.com/indian-regulator-issues-notices-to-25-offshore-crypto-platforms/")
WAVE_3 = ("Wave 3, 9 Sep 2026 non-compliance notice",
          "https://www.business-standard.com/markets/cryptocurrency/fiu-issues-notice-to-15-crypto-service-"
          "providers-asks-to-take-down-urls-126090900585_1.html")

# Offshore platforms FIU-IND issued PMLA non-compliance notices to (RESEARCH.md B.3).
# Binance and KuCoin were in wave 1 and have since registered (above).
FLAGGED_NON_COMPLIANT = {
    **{name: WAVE_1 for name in ("kraken", "huobi", "gate.io", "bittrex", "bitstamp", "mexc", "bitfinex")},
    **{name: WAVE_2 for name in (
        "ascendex", "bc.game", "bingx", "bitmex", "bitrue", "btcc", "btse", "cex.io", "changelly",
        "coincola", "coinex", "coinw", "huione", "hitbtc", "lbank", "lcx", "localcoinswap", "paxful",
        "phemex", "poloniex", "primexbt", "probit", "remitano", "youhodler", "zoomex")},
    **{name: WAVE_3 for name in (
        "weex", "blofin", "rezorex", "bitunix", "digifinex", "toobit", "xt.com", "latoken", "woo x", "woox",
        "pionex", "changenow", "simpleswap", "fixedfloat", "whitebit", "guardarian")},
}
FLAGGED_LE_CHANNEL = ("The platform's voluntary law-enforcement portal if one exists; otherwise a letter of "
                      "request / MLAT, plus intimation to FIU-IND (the platform is on its non-compliance list)")


def check_compliance(label: str) -> dict:
    """Given a matched entity label (e.g. 'Binance: Hot Wallet 20'), return
    the best-effort FIU-IND status, jurisdiction and law-enforcement channel."""
    if not label:
        return {"status": "unknown", "detail": "No entity matched — nothing to check."}

    norm = label.lower()

    for name, info in REGISTERED_INDIAN.items():
        if name in norm:
            detail = f"Named FIU-IND registrant ({info['entity']}), Lok Sabha reply 4 Dec 2023."
            if info.get("note"):
                detail += " " + info["note"]
            return {"status": "registered", "vasp": name, "jurisdiction": "IN", "detail": detail,
                    "source": LOK_SABHA_2023, "le_channel": INDIAN_LE_CHANNEL}

    for name, info in PENALIZED_THEN_REGISTERED.items():
        if name in norm:
            return {"status": "registered_after_penalty", "vasp": name, "jurisdiction": "offshore", **info}

    for name, (note, source) in FLAGGED_NON_COMPLIANT.items():
        if name in norm:
            return {"status": "flagged_non_compliant", "vasp": name, "jurisdiction": "offshore",
                    "detail": note, "source": source, "le_channel": FLAGGED_LE_CHANNEL}

    return {"status": "unknown",
            "detail": "No FIU-IND registration or enforcement record found for this name — not proof of "
                      "compliance, since no complete public registry exists.",
            "le_channel": "Not in the directory — find the platform's law-enforcement contact and check its "
                          "FIU-IND registration before serving"}
