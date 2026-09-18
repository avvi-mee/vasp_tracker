"""Multi-hop transaction trace — walks outward from a seed address, hop by
hop, ranking every material destination at each hop rather than following a
single dominant edge. A single-path greedy walk is defeated by construction
by splits, peel chains and smurfing (see research/06-clustering-heuristics.md
and the plan's P0 gap #2); this keeps every destination that carries a
meaningful share of the value, and returns every terminal (label, mixer, dead
end, hop limit) it reaches, ranked by how much of the seed's value followed
that path.
"""
from dataclasses import dataclass, field
import networkx as nx

from app.addresses import normalize_address
from app.assets import amount, asset_key, dominant_asset
from app.graph.sweep import DepositEvidence, classify_deposit_address

# ponytail: branches within a hop ARE independent I/O and parallelizing their
# fetches was tried here — reverted. Each chain client (etherscan.py,
# tronscan.py) already fans a single address's own fetch out across 2-3
# endpoints concurrently, which is what actually cut per-address latency
# ~8x. Stacking cross-branch concurrency on top of that multiplied requests
# past Etherscan's real limit and live-broke a trace ("Max calls per sec
# rate limit reached (3/sec)") — caught by testing against the real API,
# not assumed safe. Revisit with a real shared rate limiter (per the
# already-deferred Redis plan) before adding this back.

# A destination carrying less than this share of a branch's outgoing value in
# the followed asset is dust for tracing purposes — always keep the single
# biggest edge regardless, so a branch never dead-ends solely because every
# split happened to be small.
MATERIALITY_SHARE = 0.10
# Cap branches spawned per hop per parent, and total branches alive across the
# whole frontier — both bound real API calls per trace (no caching/rate-limit
# layer exists yet, see the plan's Phase B step 7), not just compute.
MAX_BRANCHES_PER_HOP = 3
MAX_ACTIVE_BRANCHES = 8
# Hard ceiling on address lookups per trace. Raising max_hops from 4 to 12
# (real laundering chains are far longer than 4) multiplies the worst case by
# three, and every lookup is a real, rate-limited API call — so bound the cost
# that actually matters instead of the hop count that only proxies for it.
# Branches cut short by this are reported in `caveats`, never hidden. In
# practice it rarely binds: a branch stops the moment it hits a labeled
# address, which since chain-native tags landed is usually hop 1 or 2.
MAX_FETCHES = 60
DEFAULT_MAX_HOPS = 12


@dataclass
class Candidate:
    """One ranked path the search followed to a terminal verdict — the same
    fields TraceResult carries for its primary path, plus the fraction of the
    seed's outgoing value that followed this particular path."""
    path: list[str]
    hop_count: int
    entity_type: str
    label: str | None
    confidence: float
    source: str | None
    reason: str | None
    asset: tuple[str, str] | None
    deposit: DepositEvidence | None
    value_share: float  # 0..1, how much of the seed's value reached this terminal
    # >1 when independent paths converged on the same labeled entity — their
    # value_share is summed into one candidate rather than listed twice.
    merged_path_count: int = 1


@dataclass
class TraceResult:
    seed_address: str
    path: list[str]
    graph: nx.DiGraph
    hop_count: int
    entity_type: str        # "exchange" | "mixer" | "bridge" | "unknown"
    label: str | None
    confidence: float
    source: str | None = None
    reason: str | None = None
    # Which asset the trace followed, e.g. ("USDT", "0xdac17f...") — the money
    # usually moves in one asset, and saying which one is part of the evidence.
    asset: tuple[str, str] | None = None
    # Set when the trace ends at an exchange and the hop before it behaves like
    # a deposit address — that address, not the exchange, is what a disclosure
    # request must name. See app/graph/sweep.py.
    deposit: DepositEvidence | None = None
    # Every terminal the search reached, ranked by value_share then confidence.
    # candidates[0] is always the same path/verdict as this result's own
    # top-level fields — a plain single-path trace is just the case where this
    # list has one entry.
    candidates: list[Candidate] = field(default_factory=list)
    # Honesty notes about the search itself — e.g. branches dropped by the
    # frontier cap — distinct from Candidate.reason, which explains one path's
    # own outcome. Empty for the common case where nothing was dropped.
    caveats: list[str] = field(default_factory=list)
    # Addresses the block explorer itself flags as risky, restricted to ones
    # actually on a followed path. Corroboration for risk.py, and something
    # the graph can highlight — never a verdict on its own.
    explorer_flagged: list[str] = field(default_factory=list)
    # How many hops the search was allowed, so the officer can tell
    # "no VASP within reach" from "we stopped looking".
    max_hops: int = 0
    # Entity labels harvested from the explorer's own responses during this
    # search, keyed by address (the currency is fixed for one trace). Exposed
    # because everything downstream that asks "who is this address?" —
    # exposure, the certificate — would otherwise report "unattributed" about
    # addresses this very trace just named. See app/data/chain_native_labels.py.
    discovered_labels: dict[str, dict] = field(default_factory=dict)
    # The label for the SUBJECT address itself, when it turns out to have one.
    # Distinct from `label`, which describes the entity the trail *reached*.
    # An officer who pastes an exchange's own wallet needs the tool to know
    # that — otherwise its ordinary high-throughput behaviour gets read as
    # laundering. See app/graph/risk.py SELF_EXPLAINING_CATEGORIES.
    subject_entity: dict | None = None


def _confidence(hop_count: int, is_cluster_definer: bool) -> float:
    score = 0.9 - 0.15 * hop_count
    if is_cluster_definer:
        score += 0.05
    return round(max(0.3, min(0.95, score)), 2)


_normalize = normalize_address  # kept as a local alias; the rule lives in app/addresses.py


class _Branch:
    """One live path through the frontier. Plain class, not a dataclass —
    it's mutated nowhere and only ever constructed positionally, so a
    dataclass's generated boilerplate buys nothing here."""
    __slots__ = ("path", "prev_txs", "followed_asset", "value_share")

    def __init__(self, path, prev_txs, followed_asset, value_share):
        self.path = path
        self.prev_txs = prev_txs
        self.followed_asset = followed_asset
        self.value_share = value_share


def trace_to_nearest_entity(
    seed_address: str,
    currency: str,
    fetch_transactions_fn,
    labels_lookup: dict,
    mixers_lookup: dict,
    max_hops: int = DEFAULT_MAX_HOPS,
) -> TraceResult:
    """fetch_transactions_fn(address) -> list of normalized tx dicts
    (see app/api_clients/etherscan.py for the shape)."""
    from app.data.chain_native_labels import harvest, harvest_risk_flags
    from app.data.tagpacks import lookup_address  # local import avoids a hard circular dep

    seed_address = _normalize(seed_address)
    g = nx.DiGraph()
    g.add_node(seed_address)

    frontier = [_Branch([seed_address], [], None, 1.0)]
    terminals: list[Candidate] = []
    pruned_count = 0
    # Labels the explorer published inside the transactions we fetch anyway.
    # Kept separate from `labels_lookup` and consulted only after it, so a
    # curated Indian-VASP or GraphSense match always wins over a third-party
    # convenience tag. See app/data/chain_native_labels.py.
    discovered: dict[tuple[str, str], dict] = {}
    explorer_flags: dict[str, bool] = {}
    fetch_count = 0
    budget_exhausted = False

    for hop in range(max_hops + 1):
        next_frontier: list[_Branch] = []
        needs_fetch: list[_Branch] = []

        for branch in frontier:
            current = branch.path[-1]

            mixer_label = mixers_lookup.get((currency.upper(), current))
            if mixer_label:
                terminals.append(Candidate(
                    branch.path, hop, "mixer", mixer_label,
                    _confidence(hop, True), "curated known-address list", None,
                    branch.followed_asset, None, branch.value_share))
                continue

            label_rec = (lookup_address(labels_lookup, currency, current)
                         or lookup_address(discovered, currency, current))
            if label_rec:
                entity_type = label_rec.get("category") or "exchange"
                # The hop immediately before an exchange is the candidate
                # deposit address — the one that maps to a single KYC'd account.
                deposit = None
                if hop >= 1 and "exchange" in entity_type.lower() and branch.prev_txs:
                    deposit = classify_deposit_address(
                        branch.path[-2], branch.prev_txs, current, asset=branch.followed_asset)
                terminals.append(Candidate(
                    branch.path, hop, entity_type, label_rec["label"],
                    _confidence(hop, label_rec.get("is_cluster_definer", False)),
                    label_rec.get("source"), None, branch.followed_asset, deposit,
                    branch.value_share))
                continue

            if hop == max_hops:
                terminals.append(Candidate(
                    branch.path, hop, "unknown", None, 0.0, None,
                    f"hop limit ({max_hops}) reached with no match",
                    branch.followed_asset, None, branch.value_share))
                continue

            needs_fetch.append(branch)

        for branch in needs_fetch:
            current = branch.path[-1]
            if fetch_count >= MAX_FETCHES:
                terminals.append(Candidate(
                    branch.path, hop, "unknown", None, 0.0, None,
                    f"search budget ({MAX_FETCHES} address lookups) exhausted before this branch "
                    f"could be followed further",
                    branch.followed_asset, None, branch.value_share))
                budget_exhausted = True
                continue
            fetch_count += 1
            txs = fetch_transactions_fn(current)
            # The response that tells us where the money went also tells us who
            # the explorer thinks owns the far end. Read it before ranking, so
            # the next hop's label check can see it.
            discovered.update(harvest(txs, currency))
            explorer_flags.update(harvest_risk_flags(txs))
            outgoing = [t for t in txs
                        if _normalize(t["from_addr"]) == current and t["value_wei"] > 0]
            if not outgoing:
                terminals.append(Candidate(
                    branch.path, hop, "unknown", None, 0.0, None,
                    "dead end — no outgoing transactions found",
                    branch.followed_asset, None, branch.value_share))
                continue

            # Follow one asset, not raw integers — 0.1 ETH is a bigger integer
            # than 50,000 USDT, so comparing value_wei across assets is
            # meaningless once token transfers are in the list.
            followed_asset = branch.followed_asset
            if followed_asset is None:
                followed_asset = dominant_asset(outgoing)
            same_asset = [t for t in outgoing if asset_key(t) == followed_asset]
            if not same_asset:
                # The trail changed asset — a swap, or the funds were
                # converted. Re-pick rather than treat as a dead end.
                followed_asset = dominant_asset(outgoing)
                same_asset = [t for t in outgoing if asset_key(t) == followed_asset]

            # Collapse to one edge per destination — a destination can appear
            # in several transactions within the same hop — before ranking.
            by_dest: dict[str, float] = {}
            edge_for_dest: dict[str, dict] = {}
            for t in same_asset:
                dest = _normalize(t["to_addr"])
                by_dest[dest] = by_dest.get(dest, 0.0) + amount(t)
                if dest not in edge_for_dest or amount(t) > amount(edge_for_dest[dest]):
                    edge_for_dest[dest] = t

            total = sum(by_dest.values()) or 1.0
            ranked = sorted(by_dest.items(), key=lambda kv: kv[1], reverse=True)
            material = [(d, a) for d, a in ranked if a / total >= MATERIALITY_SHARE]
            if not material:
                material = ranked[:1]  # always follow the biggest edge, dust or not
            material = material[:MAX_BRANCHES_PER_HOP]

            for dest, dest_amount in material:
                edge = edge_for_dest[dest]
                g.add_edge(current, dest, tx_hash=edge["tx_hash"], value_wei=edge["value_wei"],
                           amount=amount(edge), asset=followed_asset[0] if followed_asset else None,
                           timestamp=edge.get("timestamp"), block_number=edge.get("block_number"))
                next_frontier.append(_Branch(
                    branch.path + [dest], txs, followed_asset,
                    branch.value_share * (dest_amount / total)))

        frontier = next_frontier
        if not frontier:
            break
        if len(frontier) > MAX_ACTIVE_BRANCHES:
            frontier.sort(key=lambda b: b.value_share, reverse=True)
            pruned_count += len(frontier) - MAX_ACTIVE_BRANCHES
            frontier = frontier[:MAX_ACTIVE_BRANCHES]

    if not terminals:
        terminals.append(Candidate(
            [seed_address], max_hops, "unknown", None, 0.0, None,
            f"hop limit ({max_hops}) reached with no match", None, None, 1.0))

    # Independent branches sometimes converge on the same labeled entity
    # (a diamond in the transaction graph) — list that once, with its value
    # shares summed, rather than as separate rows an investigator would have
    # to notice and add up themselves. Unlabeled terminals (unknown/dead-end)
    # are never merged: two different unresolved addresses are not "the same
    # entity" just because both say "unknown".
    merged: dict[tuple[str, str], Candidate] = {}
    unmerged: list[Candidate] = []
    for c in terminals:
        if c.label is None:
            unmerged.append(c)
            continue
        key = (c.entity_type, c.label)
        existing = merged.get(key)
        if existing is None:
            merged[key] = c
        else:
            winner = c if c.hop_count < existing.hop_count else existing  # the closer path is the representative
            merged[key] = Candidate(
                winner.path, winner.hop_count, winner.entity_type, winner.label,
                winner.confidence, winner.source, winner.reason, winner.asset, winner.deposit,
                existing.value_share + c.value_share, existing.merged_path_count + c.merged_path_count,
            )
    terminals = list(merged.values()) + unmerged

    terminals.sort(key=lambda c: (c.value_share, c.confidence), reverse=True)
    best = terminals[0]

    caveats = []
    if pruned_count:
        caveats.append(
            f"{pruned_count} branch(es) below the top-{MAX_ACTIVE_BRANCHES} by value share were "
            f"not followed — this trace's coverage is not exhaustive, and a deliberately small "
            f"split (structuring) is exactly what this limit could miss.")
    if budget_exhausted:
        caveats.append(
            f"The search budget of {MAX_FETCHES} address lookups was reached, so at least one "
            f"branch was left unfollowed. Re-run with a narrower asset or a shorter hop limit to "
            f"spend that budget on fewer branches.")

    # Only resolvable now: an address's own tag arrives inside its own
    # transactions, which are not fetched until after the hop-0 label check.
    subject_entity = (lookup_address(labels_lookup, currency, seed_address)
                      or lookup_address(discovered, currency, seed_address))

    on_path = {addr for c in terminals for addr in c.path}
    flagged = sorted(a for a in on_path if explorer_flags.get(a))

    return TraceResult(
        seed_address=seed_address, path=best.path, graph=g, hop_count=best.hop_count,
        entity_type=best.entity_type, label=best.label, confidence=best.confidence,
        source=best.source, reason=best.reason, asset=best.asset, deposit=best.deposit,
        candidates=terminals, caveats=caveats, explorer_flagged=flagged, max_hops=max_hops,
        discovered_labels={address: rec for (_currency, address), rec in discovered.items()},
        subject_entity=subject_entity,
    )
