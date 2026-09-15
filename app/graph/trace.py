"""Multi-hop transaction trace — walks outward from a seed address, hop by
hop, until it hits a known exchange, a known mixer/bridge, or runs out of
hops. See research/06-clustering-heuristics.md for the deposit-sweep
heuristic this follows, and the architecture doc for why this is a graph
search, not single-hop clustering.
"""
from dataclasses import dataclass, field
import networkx as nx


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


def _confidence(hop_count: int, is_cluster_definer: bool) -> float:
    score = 0.9 - 0.15 * hop_count
    if is_cluster_definer:
        score += 0.05
    return round(max(0.3, min(0.95, score)), 2)


def _normalize(address: str) -> str:
    """Hex addresses (0x...) are case-insensitive — lowercase for consistent
    matching. Base58 addresses (Tron, Bitcoin) ARE case-sensitive — leave
    them exactly as given, lowercasing would silently corrupt them."""
    return address.lower() if address.startswith(("0x", "0X")) else address


def trace_to_nearest_entity(
    seed_address: str,
    currency: str,
    fetch_transactions_fn,
    labels_lookup: dict,
    mixers_lookup: dict,
    max_hops: int = 4,
) -> TraceResult:
    """fetch_transactions_fn(address) -> list of normalized tx dicts
    (see app/api_clients/etherscan.py for the shape)."""
    from app.data.tagpacks import lookup_address  # local import avoids a hard circular dep

    seed_address = _normalize(seed_address)
    path = [seed_address]
    g = nx.DiGraph()
    g.add_node(seed_address)
    current = seed_address

    for hop in range(max_hops + 1):
        mixer_label = mixers_lookup.get((currency.upper(), current))
        if mixer_label:
            return TraceResult(seed_address, path, g, hop, "mixer", mixer_label,
                                confidence=_confidence(hop, True), source="curated known-address list")

        label_rec = lookup_address(labels_lookup, currency, current)
        if label_rec:
            entity_type = label_rec.get("category") or "exchange"
            return TraceResult(seed_address, path, g, hop, entity_type, label_rec["label"],
                                confidence=_confidence(hop, label_rec.get("is_cluster_definer", False)),
                                source=label_rec.get("source"))

        if hop == max_hops:
            break  # don't fetch one more hop just to discard it

        txs = fetch_transactions_fn(current)
        outgoing = [t for t in txs if t["from_addr"] == current and t["value_wei"] > 0]
        if not outgoing:
            return TraceResult(seed_address, path, g, hop, "unknown", None,
                                confidence=0.0, reason="dead end — no outgoing transactions found")

        dominant = max(outgoing, key=lambda t: t["value_wei"])
        next_addr = _normalize(dominant["to_addr"])
        g.add_edge(current, next_addr, tx_hash=dominant["tx_hash"], value_wei=dominant["value_wei"])
        path.append(next_addr)
        current = next_addr

    return TraceResult(seed_address, path, g, max_hops, "unknown", None,
                        confidence=0.0, reason=f"hop limit ({max_hops}) reached with no match")
