"""Indian VASP address labels — the dataset this tool exists to have.

GraphSense TagPacks, the open labelling dataset everything else in this
project leans on, is effectively blind to Indian exchanges. Measured: WazirX
0 addresses, CoinDCX 0, ZebPay 0, Giottus 0, Mudrex 0, Bitbns 0, BuyUcoin 0,
CoinSwitch 1, Unocoin 1. A tool for Indian police that cannot recognise
India's two largest exchanges cannot do its job — Indian fraud proceeds land
at Indian exchanges.

So the labels are sourced separately, primarily from Dune Analytics'
spellbook (Apache-2.0), cross-checked against Etherscan's public tags and,
for one address, against the exchange's own incident report.

Two things worth knowing about the data:

1. Every address was checksum-validated before being accepted. This matters:
   of 270 candidate rows in the upstream source, 158 failed — spellbook's
   litecoin file is 100%% corrupt (sliced Ethereum fragments), its eos file
   holds 12-character truncations of Bitcoin addresses, its cardano entries
   are cut short, and 27 of 32 ripple addresses fail their checksum. Those
   were all discarded. Shipping a corrupt address in a police tool means
   sending a disclosure request about a wallet that does not exist.

2. Confidence is recorded per address, not assumed:
     operator-confirmed — the exchange itself published it (1 address)
     confirmed          — Etherscan's public tag agrees with spellbook (10)
     single-source      — spellbook only, format-valid (101)

   Upstream tag *numbers* disagree between sources (Etherscan's "CoinDCX 1"
   is spellbook's "CoinDCX 28"), so matching is keyed on the address alone.

EVM addresses are listed once and apply across Ethereum, Polygon and BNB
Chain, since the same key controls the same address on all three.
"""
import csv
from pathlib import Path

from app.addresses import normalize_address

DATASET = Path(__file__).parent / "indian_vasps.csv"

# One EVM address is the same address on every EVM chain.
EVM_CURRENCIES = ("ETH", "MATIC", "BNB")
CHAIN_TO_CURRENCIES = {
    "EVM": EVM_CURRENCIES,
    "BTC": ("BTC",),
    "TRX": ("TRX",),
    "XRP": ("XRP",),
}

# How much to trust a match, by how well corroborated the label is.
CONFIDENCE_SCORE = {
    "operator-confirmed": 0.95,
    "confirmed": 0.90,
    "single-source": 0.75,
}


def load_indian_vasp_labels(dataset: Path = DATASET) -> dict[tuple[str, str], dict]:
    """Returns the same {(currency, address): record} shape as the GraphSense
    loader, so the two merge without either side knowing about the other."""
    labels: dict[tuple[str, str], dict] = {}
    if not dataset.exists():
        return labels

    with dataset.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            address = normalize_address(row["address"].strip())
            record = {
                "label": f"{row['exchange']} ({row['name_tag']})",
                "category": "exchange",
                "source": f"VASP Trace Indian VASP dataset — {row['source']}",
                "confidence": CONFIDENCE_SCORE.get(row["confidence"], 0.75),
                "is_cluster_definer": True,
                "entity": row["exchange"],
                "jurisdiction": "IN",
                "corroboration": row["confidence"],
            }
            for currency in CHAIN_TO_CURRENCIES.get(row["chain"], ()):
                labels[(currency, address)] = record
    return labels


def merge_labels(base: dict, indian: dict | None = None) -> dict:
    """Layer the Indian dataset over GraphSense.

    Indian labels win on collision, deliberately: this dataset is curated and
    checksum-validated for exactly the jurisdiction the tool serves, whereas a
    GraphSense hit on the same address is community-contributed and generally
    staler. Collisions are rare — GraphSense barely covers these exchanges,
    which is the whole reason this file exists.
    """
    merged = dict(base)
    merged.update(load_indian_vasp_labels() if indian is None else indian)
    return merged


def coverage_summary(labels: dict | None = None) -> dict[str, int]:
    """Address count per exchange — used by the UI to state coverage honestly
    rather than implying the dataset is exhaustive."""
    labels = load_indian_vasp_labels() if labels is None else labels
    # Count distinct addresses, not keys: one EVM address is registered under
    # ETH, MATIC and BNB, and counting keys would treble it.
    seen: dict[str, set[str]] = {}
    for (_currency, address), record in labels.items():
        entity = record.get("entity")
        if entity:
            seen.setdefault(entity, set()).add(address)
    return dict(sorted(((k, len(v)) for k, v in seen.items()), key=lambda kv: -kv[1]))
