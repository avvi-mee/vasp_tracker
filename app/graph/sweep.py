"""Deposit-address detection (the sweep heuristic).

Why this exists: "the funds reached Binance" is not actionable. Binance has
millions of users. What a disclosure request has to name is the *deposit
address* — the address Binance generated for one specific customer. That
address maps 1:1 to one KYC'd account, so naming it turns a dead end into a
identity request an exchange can actually answer.

The pattern (Victor, Financial Cryptography 2020 — see
research/06-clustering-heuristics.md): an exchange hands each customer a
fresh address. Funds sent there are automatically "swept" into the exchange's
hot wallet, usually quickly and usually in full. So a deposit address looks
like a funnel: money in from anywhere, money out to exactly one place,
balance left behind ≈ zero.

Note the direction of inference. Matching the pattern says an address behaves
like a deposit address. It does not prove which customer owns it — only the
exchange knows that, which is the entire point of sending them a request.
"""
from dataclasses import dataclass, field
from statistics import median

from app.addresses import normalize_address
from app.assets import amount, asset_key, dominant_asset

# A deposit address forwards nearly everything it receives. Leaving a little
# behind is normal (gas, dust, rounding), so this is not 1.0.
FORWARDING_RATIO_STRONG = 0.90
# Share of outgoing value that must go to the single top destination.
SINGLE_DESTINATION_STRONG = 0.95
# Sweeps are automated and prompt. A week is generous; most are minutes.
PROMPT_SWEEP_SECONDS = 7 * 24 * 3600
# Score at or above which we call it a deposit address. Ratio + single
# destination alone (0.35 + 0.30) clears it: that is the minimal honest
# signature of a pass-through funnel.
DEPOSIT_THRESHOLD = 0.60
# At or above this many fetched transfers, assume the client hit its cap and
# say so. Matches the smallest DEFAULT_MAX_RECORDS across the chain clients.
LIKELY_TRUNCATED_AT = 600


@dataclass
class DepositEvidence:
    """Evidence that one address behaves as a VASP deposit address."""
    address: str
    vasp_address: str
    is_deposit_address: bool
    confidence: float
    forwarded_ratio: float          # value swept to the VASP / total value received
    destination_share: float        # share of all outgoing value going to the VASP
    distinct_funders: int
    sweep_count: int
    median_hold_seconds: int | None  # time from funding to sweep; None if unknown
    signals: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    asset: str = ""               # the asset these ratios were measured in

    def summary(self) -> str:
        if not self.is_deposit_address:
            return (f"{self.address} does not match the deposit-address pattern "
                    f"(forwarded {self.forwarded_ratio:.0%} of what it received).")
        in_asset = f" in {self.asset}" if self.asset else ""
        return (f"{self.address} behaves as a deposit address controlled by the VASP: "
                f"it forwarded {self.forwarded_ratio:.0%} of everything it received{in_asset} to "
                f"{self.vasp_address}, across {self.sweep_count} sweep(s).")


def _hold_times(inbound: list[dict], sweeps: list[dict]) -> list[int]:
    """For each sweep, how long the funds sat before being moved on — measured
    from the most recent deposit preceding that sweep."""
    in_times = sorted(t["timestamp"] for t in inbound if t.get("timestamp"))
    gaps = []
    for sweep in sweeps:
        swept_at = sweep.get("timestamp")
        if not swept_at:
            continue
        prior = [t for t in in_times if t <= swept_at]
        if prior:
            gaps.append(swept_at - prior[-1])
    return gaps


def classify_deposit_address(address: str, transactions: list[dict],
                             vasp_address: str,
                             asset: tuple[str, str] | None = None) -> DepositEvidence:
    """Decide whether `address` looks like a deposit address sweeping into
    `vasp_address`. Pure function over the transaction list the trace already
    fetched — makes no API calls of its own.

    Ratios are measured **within one asset**. Summing raw values across assets
    would be meaningless once token transfers are in the list — 1 ETH and
    1 USDT are 10**18 and 10**6 base units respectively, so a mixed sum is
    dominated by whichever asset has more decimals, not more value. `asset`
    names the one to measure; when omitted, the asset carrying the most value
    to the VASP is chosen.
    """
    address = normalize_address(address)
    vasp_address = normalize_address(vasp_address)

    relevant = [t for t in transactions
                if normalize_address(t["from_addr"]) == address
                or normalize_address(t["to_addr"]) == address]
    if asset is None:
        to_vasp = [t for t in relevant
                   if normalize_address(t["from_addr"]) == address
                   and normalize_address(t["to_addr"]) == vasp_address]
        asset = dominant_asset(to_vasp) or dominant_asset(relevant)
    if asset is not None:
        relevant = [t for t in relevant if asset_key(t) == asset]

    inbound = [t for t in relevant
               if normalize_address(t["to_addr"]) == address and t["value_wei"] > 0]
    outbound = [t for t in relevant
                if normalize_address(t["from_addr"]) == address and t["value_wei"] > 0]
    sweeps = [t for t in outbound if normalize_address(t["to_addr"]) == vasp_address]

    total_in = sum(amount(t) for t in inbound)
    total_out = sum(amount(t) for t in outbound)
    swept = sum(amount(t) for t in sweeps)

    forwarded_ratio = swept / total_in if total_in else 0.0
    destination_share = swept / total_out if total_out else 0.0
    funders = {normalize_address(t["from_addr"]) for t in inbound}
    gaps = _hold_times(inbound, sweeps)
    median_hold = int(median(gaps)) if gaps else None

    score, signals, caveats = 0.0, [], []

    if forwarded_ratio >= FORWARDING_RATIO_STRONG:
        score += 0.35
        signals.append(f"forwards {forwarded_ratio:.0%} of received value onward — "
                       f"retains almost nothing, as a pass-through address does")
    elif forwarded_ratio > 0:
        caveats.append(f"only {forwarded_ratio:.0%} of received value went to the VASP — "
                       f"a deposit address normally forwards nearly all of it")

    if destination_share >= SINGLE_DESTINATION_STRONG:
        score += 0.30
        signals.append(f"{destination_share:.0%} of everything it sends goes to this one "
                       f"VASP address — a single fixed destination, not general spending")
    elif destination_share > 0:
        caveats.append(f"sends to other destinations too ({destination_share:.0%} of outgoing "
                       f"value goes to the VASP) — may be a user wallet, not a deposit address")

    if len(funders) >= 2:
        score += 0.20
        signals.append(f"funded by {len(funders)} distinct addresses — deposit addresses "
                       f"aggregate incoming payments")

    if median_hold is not None and median_hold <= PROMPT_SWEEP_SECONDS:
        score += 0.15
        signals.append(f"swept onward within {_humanize(median_hold)} of being funded — "
                       f"consistent with an automated sweep")
    elif median_hold is not None:
        caveats.append(f"funds sat for {_humanize(median_hold)} before moving — slower than "
                       f"a typical automated sweep")

    if not inbound:
        caveats.append("no inbound transactions in the fetched history — cannot measure "
                       "forwarding behaviour")
    # The clients cap how much history they pull (see DEFAULT_MAX_RECORDS in
    # each api_client). A list at or near that cap probably had more behind it,
    # so the ratios describe the fetched window, not the address's whole life.
    if len(transactions) >= LIKELY_TRUNCATED_AT:
        caveats.append(f"history may be truncated — {len(transactions)} transfers fetched, at or "
                       f"near the client's page cap; ratios cover the fetched window only")

    confidence = round(min(score, 0.95), 2)
    return DepositEvidence(
        address=address,
        vasp_address=vasp_address,
        is_deposit_address=confidence >= DEPOSIT_THRESHOLD,
        confidence=confidence,
        forwarded_ratio=round(forwarded_ratio, 4),
        destination_share=round(destination_share, 4),
        distinct_funders=len(funders),
        sweep_count=len(sweeps),
        median_hold_seconds=median_hold,
        signals=signals,
        caveats=caveats,
        asset=asset[0] if asset else "",
    )


def _humanize(seconds: int) -> str:
    if seconds < 90:
        return f"{seconds} seconds"
    if seconds < 5400:
        return f"{round(seconds / 60)} minutes"
    if seconds < 172800:
        return f"{round(seconds / 3600)} hours"
    return f"{round(seconds / 86400)} days"
