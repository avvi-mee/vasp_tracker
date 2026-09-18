"""Laundering typology detection — the problem statement's "identification of
laundering typologies", and the answer to why every real address came back
"LOW RISK".

The gap this closes: risk.py judges the *entity the trail reaches*. Reach a
mixer and it says high; reach an FIU-registered exchange and it says none.
But "these funds ended up at Binance" is not a statement about whether the
subject wallet is a fraud wallet — it is a statement about who to send the
disclosure request to. A collection wallet that took money from 16 different
victims and swept each payment to an exchange within 11 minutes is provably
suspicious *with no label at all*, and that is what these detectors see.

Everything here is computed from transactions the trace already fetched — no
new API calls, no new keys. Each detection states the numbers behind it, so
an officer (or a defence lawyer) can check the arithmetic rather than being
asked to trust a score.

Deliberately NOT here: any claim that a detection proves criminality. Every
pattern below has innocent explanations (a payroll wallet fans out; an OTC
desk funnels in; a merchant sweeps). These raise questions and set priority.
The thresholds are stated as constants so they can be argued with.
"""
from dataclasses import dataclass, field
from statistics import median, pstdev

from app.addresses import normalize_address as _normalize
from app.assets import amount, asset_key

# --- Thresholds. Stated, not buried: each is a judgement call worth arguing. ---
FUNNEL_MIN_FUNDERS = 5          # distinct senders before "many" means anything
FUNNEL_MAX_DESTINATIONS = 3     # a collection wallet has few places to go
FUNNEL_HIGH_FUNDERS = 15
LAYERING_MEDIAN_HOLD = 3600     # seconds; money that rests an hour isn't layering
LAYERING_FAST_HOLD = 600
LAYERING_MIN_SWEEPS = 3
LAYERING_MIN_FORWARD_RATIO = 0.80
# Above this, the records we hold cannot account for what left: a busy address
# is fetched with a record cap (600 rows on Tron, 2000 on the EVM chains), so
# the window can catch outbound transfers whose matching inbound ones fall
# outside it. Live example: Binance's Tron hot wallet computed a "345977%
# forwarded" ratio. Printing that number in a police report would be absurd;
# the honest statement is that the sample is truncated.
LAYERING_TRUNCATED_ABOVE = 2.0
FANOUT_MIN_DESTINATIONS = 8
FANOUT_HIGH_DESTINATIONS = 20
FANOUT_MAX_CV = 0.35            # coefficient of variation; near-equal splits
FANOUT_WINDOW_SECONDS = 7 * 24 * 3600
PEEL_MIN_HOPS = 3
PEEL_MIN_FORWARD_RATIO = 0.70
STRUCTURING_MIN_REPEATS = 4


@dataclass
class Typology:
    name: str                 # stable machine key, e.g. "many_to_one_funnel"
    title: str                # what an officer reads
    severity: str             # "low" | "medium" | "high", same vocabulary as risk.py
    confidence: float         # 0..1, how well the evidence fits the pattern
    explanation: str          # plain language: what was seen and why it matters
    stats: dict = field(default_factory=dict)       # the arithmetic, for checking
    evidence: list[str] = field(default_factory=list)  # addresses / tx hashes to look at


def _split(seed: str, txs: list[dict]) -> tuple[list[dict], list[dict]]:
    incoming = [t for t in txs if _normalize(t["to_addr"]) == seed and t["value_wei"] > 0]
    outgoing = [t for t in txs if _normalize(t["from_addr"]) == seed and t["value_wei"] > 0]
    return incoming, outgoing


def _hold_times(incoming: list[dict], outgoing: list[dict]) -> list[int]:
    """For each outgoing transfer, how long since the most recent inbound one.
    Short holds across many transfers are the shape of a pass-through wallet,
    not of someone spending their own money."""
    in_times = sorted(t["timestamp"] for t in incoming if t.get("timestamp") is not None)
    holds = []
    for out in outgoing:
        out_ts = out.get("timestamp")
        if out_ts is None:
            continue
        prior = [t for t in in_times if t <= out_ts]
        if prior:
            holds.append(out_ts - prior[-1])
    return holds


def _many_to_one_funnel(seed: str, incoming: list[dict], outgoing: list[dict]) -> Typology | None:
    funders = {_normalize(t["from_addr"]) for t in incoming}
    destinations = {_normalize(t["to_addr"]) for t in outgoing}
    if len(funders) < FUNNEL_MIN_FUNDERS or len(destinations) > FUNNEL_MAX_DESTINATIONS:
        return None
    severity = "high" if len(funders) >= FUNNEL_HIGH_FUNDERS else "medium"
    return Typology(
        name="many_to_one_funnel",
        title="Many-to-one funnel (collection wallet)",
        severity=severity,
        confidence=round(min(0.90, 0.40 + 0.03 * len(funders)), 2),
        explanation=(
            f"{len(funders)} different addresses paid into this wallet, and everything it sent went "
            f"to just {len(destinations)} destination(s). That is the shape of a collection point — "
            f"one wallet aggregating payments from many payers — which is how both scam-victim "
            f"proceeds and mule networks concentrate funds before moving them on. A shop or an OTC "
            f"desk looks the same way, so this raises the question rather than answering it."),
        stats={"distinct_funders": len(funders), "distinct_destinations": len(destinations),
               "incoming_transfers": len(incoming), "outgoing_transfers": len(outgoing)},
        evidence=sorted(funders)[:20],
    )


def _rapid_layering(seed: str, incoming: list[dict], outgoing: list[dict]) -> Typology | None:
    holds = _hold_times(incoming, outgoing)
    if len(holds) < LAYERING_MIN_SWEEPS:
        return None
    total_in = sum(amount(t) for t in incoming)
    total_out = sum(amount(t) for t in outgoing)
    ratio = total_out / total_in if total_in else 0.0
    med = int(median(holds))
    if med > LAYERING_MEDIAN_HOLD or ratio < LAYERING_MIN_FORWARD_RATIO:
        return None
    fast = med <= LAYERING_FAST_HOLD and len(holds) >= 10
    truncated = ratio > LAYERING_TRUNCATED_ABOVE
    forwarding = ("more value left than the records we hold show arriving, so this address's history "
                  "is truncated by the fetch limit and the forwarding ratio is not meaningful"
                  if truncated else f"{ratio:.0%} of everything received was forwarded on")
    return Typology(
        name="rapid_layering",
        title="Rapid layering (funds do not rest here)",
        # A truncated sample can still show short hold times, but it cannot
        # support the strongest reading of them.
        severity="high" if fast and not truncated else "medium",
        confidence=round(min(0.90, 0.45 + 0.02 * len(holds)) * (0.7 if truncated else 1.0), 2),
        explanation=(
            f"Money left this wallet a median of {med // 60} minute(s) after arriving, across "
            f"{len(holds)} transfers, and {forwarding}. "
            f"A wallet someone actually keeps funds in holds a balance; this one is a conduit. "
            f"Short, repeated hold times are the defining measurable feature of the layering stage."),
        stats={"median_hold_seconds": med, "sweeps": len(holds),
               "forwarded_ratio": round(ratio, 4), "sample_truncated": truncated},
        evidence=[t["tx_hash"] for t in outgoing[:10] if t.get("tx_hash")],
    )


def _fan_out(seed: str, outgoing: list[dict]) -> Typology | None:
    by_dest: dict[str, float] = {}
    for t in outgoing:
        by_dest[_normalize(t["to_addr"])] = by_dest.get(_normalize(t["to_addr"]), 0.0) + amount(t)
    if len(by_dest) < FANOUT_MIN_DESTINATIONS:
        return None
    values = list(by_dest.values())
    mean = sum(values) / len(values)
    cv = (pstdev(values) / mean) if mean else 0.0
    if cv > FANOUT_MAX_CV:
        return None
    times = [t["timestamp"] for t in outgoing if t.get("timestamp") is not None]
    window = (max(times) - min(times)) if times else 0
    if window > FANOUT_WINDOW_SECONDS:
        return None
    return Typology(
        name="fan_out_smurfing",
        title="Fan-out in near-equal amounts (smurfing)",
        severity="high" if len(by_dest) >= FANOUT_HIGH_DESTINATIONS else "medium",
        confidence=round(min(0.90, 0.45 + 0.02 * len(by_dest)), 2),
        explanation=(
            f"This wallet split its funds across {len(by_dest)} destinations in amounts that barely "
            f"vary (spread of {cv:.0%} around the average), all within {window // 3600} hour(s). "
            f"Deliberately even splits across many addresses is structuring — it exists to keep each "
            f"piece small enough to look unremarkable, and to defeat a tracer that follows only the "
            f"largest edge."),
        stats={"destinations": len(by_dest), "coefficient_of_variation": round(cv, 4),
               "window_seconds": window, "mean_amount": round(mean, 6)},
        evidence=sorted(by_dest, key=by_dest.get, reverse=True)[:20],
    )


def _peel_chain(result) -> Typology | None:
    """A peel chain forwards most of its value onward at every hop while
    shaving a small piece off — so the followed amounts fall, slowly, over a
    long single-file run. Read off the traced graph's own edges."""
    graph = getattr(result, "graph", None)
    if graph is None:
        return None
    best: list[str] = []
    best_amounts: list[float] = []
    best_ratios: list[float] = []
    for candidate in getattr(result, "candidates", None) or []:
        path = candidate.path
        if len(path) - 1 < PEEL_MIN_HOPS:
            continue
        amounts = []
        for src, dst in zip(path, path[1:]):
            edge = graph.get_edge_data(src, dst) or {}
            if edge.get("amount") is None:
                amounts = []
                break
            amounts.append(edge["amount"])
        if len(amounts) < PEEL_MIN_HOPS:
            continue
        ratios = [b / a for a, b in zip(amounts, amounts[1:]) if a]
        if len(ratios) == len(amounts) - 1 and all(PEEL_MIN_FORWARD_RATIO <= r < 1.0 for r in ratios):
            if len(path) > len(best):
                best, best_amounts, best_ratios = path, amounts, ratios
    if not best:
        return None
    retained = best_amounts[0] - best_amounts[-1]
    return Typology(
        name="peel_chain",
        title="Peel chain",
        severity="medium",
        confidence=round(min(0.85, 0.45 + 0.05 * len(best_ratios)), 2),
        explanation=(
            f"Across {len(best) - 1} consecutive hops the same funds were forwarded on each time "
            f"({min(best_ratios):.0%}–{max(best_ratios):.0%} of the incoming amount), with a small "
            f"slice peeled off at every step — {retained:,.2f} in total. This is a peel chain: it "
            f"launders by attrition, moving the bulk along while cashing out a little at a time, and "
            f"it is specifically designed to exhaust an investigator following hop by hop."),
        stats={"hops": len(best) - 1, "first_amount": best_amounts[0],
               "last_amount": best_amounts[-1], "retained": round(retained, 6),
               "forward_ratios": [round(r, 4) for r in best_ratios]},
        evidence=best,
    )


def _round_amount_structuring(outgoing: list[dict]) -> Typology | None:
    """Repeated identical, suspiciously round transfers — the signature of
    amounts chosen by a person against a threshold, not by what was owed."""
    counts: dict[float, int] = {}
    for t in outgoing:
        value = amount(t)
        if value >= 100 and value == int(value) and int(value) % 100 == 0:
            counts[value] = counts.get(value, 0) + 1
    if not counts:
        return None
    value, repeats = max(counts.items(), key=lambda kv: kv[1])
    if repeats < STRUCTURING_MIN_REPEATS:
        return None
    share = repeats / len(outgoing)
    return Typology(
        name="round_amount_structuring",
        title="Repeated round-number transfers",
        severity="medium" if share >= 0.5 else "low",
        confidence=round(min(0.80, 0.35 + 0.05 * repeats), 2),
        explanation=(
            f"The exact amount {value:,.0f} was sent {repeats} separate times "
            f"({share:.0%} of all outgoing transfers). Genuine payments are rarely identical round "
            f"numbers repeated this way; amounts picked by hand, against a limit or a price list, are."),
        stats={"amount": value, "repeats": repeats, "share_of_outgoing": round(share, 4)},
        evidence=[t["tx_hash"] for t in outgoing if amount(t) == value][:10],
    )


def detect(result, seed_txs: list[dict], asset: tuple[str, str] | None = None) -> list[Typology]:
    """Run every detector over one traced address.

    `seed_txs` is the seed's own transactions in both directions — the same
    fetch the trace's first hop already made. `asset` restricts the behavioural
    detectors to one asset when the trace followed one, for the same reason
    nothing else in this project sums values across different decimal scales.
    Returned highest-severity first.
    """
    seed = _normalize(getattr(result, "seed_address", "") or "")
    if asset is not None:
        seed_txs = [t for t in seed_txs if asset_key(t) == asset]
    incoming, outgoing = _split(seed, seed_txs)

    found = [
        _many_to_one_funnel(seed, incoming, outgoing) if incoming and outgoing else None,
        _rapid_layering(seed, incoming, outgoing) if incoming and outgoing else None,
        _fan_out(seed, outgoing) if outgoing else None,
        _peel_chain(result),
        _round_amount_structuring(outgoing) if outgoing else None,
    ]
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted((f for f in found if f), key=lambda t: (order[t.severity], -t.confidence))


def highest_severity(typologies: list[Typology]) -> str:
    """"none" when nothing fired — the same vocabulary risk.RISK_LEVELS uses."""
    order = ("none", "low", "medium", "high")
    return max((t.severity for t in typologies), key=order.index, default="none")
