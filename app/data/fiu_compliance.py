"""FIU-IND compliance status for named VASPs — compiled from
research/05-fiu-vasp-list.md. No official public roster exists (see that
file's Notes & Confidence section), so this is deliberately partial:
named entities from official penalty orders and PIB enforcement releases
only. Never treat "not listed here" as "confirmed compliant."
"""

# High confidence — named in an official FIU-IND penalty/compliance order,
# corroborated by 2+ independent press sources.
PENALIZED_THEN_REGISTERED = {
    "binance": {
        "detail": "Penalized ₹18.82 crore (Order 19 Jun 2024), registered and resumed India operations.",
        "source": "fiuindia.gov.in Order No. 10/DIR/FIU-IND/2024",
    },
    "kucoin": {
        "detail": "Penalized ₹34.5 lakh (~22 Mar 2024), first offshore VASP to register with FIU-IND.",
        "source": "fiuindia.gov.in Order PGL_Order_08_2024",
    },
    "bybit": {
        "detail": "Penalized ₹9.27 crore (Order 31 Jan 2025), cleared for India operations after settlement.",
        "source": "fiuindia.gov.in Order Bybit_Order_15_2024",
    },
}

# Confirmed by official PIB release + 2+ independent press sources — offshore
# platforms FIU-IND issued Section-13 PMLA non-compliance notices to.
FLAGGED_NON_COMPLIANT = {
    # Wave 1 — 28 Dec 2023 (9 entities; Binance/KuCoin later moved to registered above)
    "kraken": "Wave 1, 28 Dec 2023 show-cause notice",
    "huobi": "Wave 1, 28 Dec 2023 show-cause notice",
    "gate.io": "Wave 1, 28 Dec 2023 show-cause notice",
    "bittrex": "Wave 1, 28 Dec 2023 show-cause notice",
    "bitstamp": "Wave 1, 28 Dec 2023 show-cause notice",
    "mexc": "Wave 1, 28 Dec 2023 show-cause notice",
    "bitfinex": "Wave 1, 28 Dec 2023 show-cause notice",
    # Wave 2 — 1 Oct 2025 (25 entities; roster is medium confidence, see research file)
    "bingx": "Wave 2, 1 Oct 2025 non-compliance notice",
    "lbank": "Wave 2, 1 Oct 2025 non-compliance notice",
    "coinw": "Wave 2, 1 Oct 2025 non-compliance notice",
    "poloniex": "Wave 2, 1 Oct 2025 non-compliance notice",
    "cex.io": "Wave 2, 1 Oct 2025 non-compliance notice",
    "ascendex": "Wave 2, 1 Oct 2025 non-compliance notice",
    "bitmex": "Wave 2, 1 Oct 2025 non-compliance notice",
    "btcc": "Wave 2, 1 Oct 2025 non-compliance notice",
    "probit": "Wave 2, 1 Oct 2025 non-compliance notice",
    "zoomex": "Wave 2, 1 Oct 2025 non-compliance notice",
    # Wave 3 — 9 Sept 2026 (15 entities, confirmed 2+ sources)
    "weex": "Wave 3, 9 Sep 2026 non-compliance notice",
    "blofin": "Wave 3, 9 Sep 2026 non-compliance notice",
    "bitunix": "Wave 3, 9 Sep 2026 non-compliance notice",
    "digifinex": "Wave 3, 9 Sep 2026 non-compliance notice",
    "toobit": "Wave 3, 9 Sep 2026 non-compliance notice",
    "xt.com": "Wave 3, 9 Sep 2026 non-compliance notice",
    "latoken": "Wave 3, 9 Sep 2026 non-compliance notice",
    "pionex": "Wave 3, 9 Sep 2026 non-compliance notice",
    "changenow": "Wave 3, 9 Sep 2026 non-compliance notice",
    "whitebit": "Wave 3, 9 Sep 2026 non-compliance notice",
}


def check_compliance(label: str) -> dict:
    """Given a matched entity label (e.g. 'Binance: Hot Wallet 20'), return
    the best-effort FIU-IND compliance status. Matching is a simple
    substring check against known VASP names — transparent, not fuzzy ML,
    so a wrong match is easy to spot and fix."""
    if not label:
        return {"status": "unknown", "detail": "No entity matched — nothing to check."}

    norm = label.lower()

    for name, info in PENALIZED_THEN_REGISTERED.items():
        if name in norm:
            return {"status": "registered_after_penalty", "vasp": name, **info}

    for name, note in FLAGGED_NON_COMPLIANT.items():
        if name in norm:
            return {"status": "flagged_non_compliant", "vasp": name, "detail": note,
                    "source": "FIU-IND / PIB enforcement release"}

    return {"status": "unknown",
            "detail": "No FIU-IND enforcement record found for this name — not proof of compliance, "
                      "since no complete public registry exists (research/05-fiu-vasp-list.md)."}
