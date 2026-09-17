"""Direct vs. indirect risk exposure — Chainalysis's own stated distinction
(direct = the seed's immediate counterparty; indirect = anything reached
through intermediary hops, regardless of distance, because most illicit
actors sit one or two unattributed hops from a mixer, not zero) — applied to
data this project already computes. The exact chart geometry Chainalysis
uses is not publicly documented anywhere we could verify, so this is an
original implementation of the *concept*, not a copy of anything seen.

Walks every candidate's full path, not just its terminal — a candidate that
passes through a mixer at hop 1 before continuing on to an exchange at hop 3
is exposed to *both*, and both should show up here even though only the
exchange is that candidate's final verdict.

Important: unlike TraceResult.candidates (mutually exclusive terminal
outcomes, value_share sums to ~1.0 minus anything pruned), exposure category
totals are NOT mutually exclusive slices of one pie — a single candidate's
value can count toward more than one category if its path touches more than
one labeled/risky address, exactly mirroring how a real flow of funds can be
"20% exposed to a mixer AND 20% exposed to a darknet market" if it passed
through both. Don't expect these percentages to sum to 100%.
"""
from dataclasses import dataclass, field

from app.data.known_illicit import check_illicit
from app.data.tagpacks import lookup_address
from app.graph.risk import DARKNET_MARKET_CATEGORIES, MIXER_CATEGORIES


@dataclass
class ExposureCategory:
    category: str            # "mixer" | "market" | "sanctioned" | "exchange" | ... (raw label category)
    label: str | None        # a representative entity label, for display
    value_share: float       # summed value_share of every candidate whose path touched this category


@dataclass
class ExposureBreakdown:
    direct: list[ExposureCategory] = field(default_factory=list)
    indirect: list[ExposureCategory] = field(default_factory=list)


def _classify(addr: str, currency: str, labels_lookup: dict, mixers_lookup: dict) -> tuple[str, str] | None:
    """Returns (category, label) for one address, or None if nothing matched."""
    mixer_label = mixers_lookup.get((currency.upper(), addr))
    if mixer_label:
        return "mixer", mixer_label

    illicit = check_illicit(addr)
    if illicit:
        return "sanctioned", illicit["label"]

    rec = lookup_address(labels_lookup, currency, addr)
    if rec:
        category = (rec.get("category") or "exchange").lower()
        # Fold GraphSense's real vocabulary into the same buckets risk.py
        # uses, so the wheel and the verdict never disagree with each other.
        if category in MIXER_CATEGORIES:
            category = "mixer"
        elif category in DARKNET_MARKET_CATEGORIES:
            category = "market"
        return category, rec.get("label")

    return None


def compute_exposure(result, currency: str, labels_lookup: dict, mixers_lookup: dict) -> ExposureBreakdown:
    """result: a TraceResult (needs .candidates, each with .path and .value_share)."""
    direct_totals: dict[str, float] = {}
    indirect_totals: dict[str, float] = {}
    label_for_category: dict[str, str] = {}

    for candidate in result.candidates:
        for i, addr in enumerate(candidate.path):
            if i == 0:
                continue  # the seed itself is not "exposure"
            hit = _classify(addr, currency, labels_lookup, mixers_lookup)
            if not hit:
                continue
            category, label = hit
            bucket = direct_totals if i == 1 else indirect_totals
            bucket[category] = bucket.get(category, 0.0) + candidate.value_share
            label_for_category.setdefault(category, label)

    def _to_list(totals: dict[str, float]) -> list[ExposureCategory]:
        return sorted(
            (ExposureCategory(cat, label_for_category.get(cat), share) for cat, share in totals.items()),
            key=lambda e: e.value_share, reverse=True,
        )

    return ExposureBreakdown(direct=_to_list(direct_totals), indirect=_to_list(indirect_totals))
