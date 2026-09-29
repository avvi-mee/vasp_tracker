"""Bridge and swap-service addresses, loaded from bridges.csv
(`chain,address,name,kind,source`) — the addresses where funds leave one chain
to appear on another. Sourced rows only: official contract lists, each row
carrying the URL it came from.

Not here, on purpose:
  * THORChain vault addresses rotate every few days, so app/graph/crosschain.py
    reads them live; only the (stable) routers are in the CSV.
  * Swap-service deposit addresses with no published source. Instant swappers
    hand out a fresh address per order, so an address list would be a guess.
    Explorer tags for them still classify via chain_native_labels.
"""
import csv
from pathlib import Path

from app.addresses import normalize_address

BRIDGES_CSV = Path(__file__).with_name("bridges.csv")
KINDS = {"bridge", "swap_service"}
# An official contract list, not a crawl: the same tier as GraphSense "forensic".
CONFIDENCE = 0.90


def load_bridges(path: Path = BRIDGES_CSV) -> dict[tuple[str, str], dict]:
    """Same {(currency, address): record} shape as the GraphSense and Indian
    VASP loaders, so lookup_address() consumes it unchanged."""
    labels: dict[tuple[str, str], dict] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["kind"] not in KINDS:
                raise ValueError(f"{path.name}: unknown kind {row['kind']!r} for {row['address']}")
            labels[(row["chain"].upper(), normalize_address(row["address"]))] = {
                "label": row["name"], "category": row["kind"], "source": row["source"],
                "confidence": CONFIDENCE, "is_cluster_definer": False,
            }
    return labels
