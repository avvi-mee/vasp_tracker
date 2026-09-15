"""Loads GraphSense TagPacks (YAML) into an address -> label lookup.

TagPack format (see research/02-graphsense-tagpacks.md): each file has a
header (label/currency/category/source/confidence/is_cluster_definer) that
every tag inherits, unless a tag overrides a field itself.
"""
from pathlib import Path
import yaml

TAGPACKS_DIR = Path(__file__).parent / "graphsense-tagpacks" / "packs"

HEADER_FIELDS = ("label", "currency", "category", "source", "confidence", "is_cluster_definer", "actor")


def load_labels(tagpacks_dir: Path = TAGPACKS_DIR) -> dict[tuple[str, str], dict]:
    """Returns {(currency, address_lowercased): {label, category, source, confidence, is_cluster_definer}}"""
    lookup: dict[tuple[str, str], dict] = {}
    if not tagpacks_dir.exists():
        raise FileNotFoundError(
            f"{tagpacks_dir} not found — git clone https://github.com/graphsense/graphsense-tagpacks "
            f"into app/data/ first."
        )

    for yaml_file in tagpacks_dir.rglob("*.yaml"):
        try:
            doc = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue  # skip malformed files rather than crash the whole load
        if not doc or "tags" not in doc:
            continue

        header = {k: doc.get(k) for k in HEADER_FIELDS}

        for tag in doc["tags"]:
            address = tag.get("address")
            if not address:
                continue
            merged = {**header, **{k: v for k, v in tag.items() if k in HEADER_FIELDS}}
            currency = (merged.get("currency") or "").upper()
            key = (currency, address.lower())
            # keep the first match, unless this one is a stronger (cluster-defining) tag
            if key not in lookup or merged.get("is_cluster_definer"):
                lookup[key] = {
                    "label": merged.get("label"),
                    "category": merged.get("category"),
                    "source": merged.get("source"),
                    "confidence": merged.get("confidence"),
                    "is_cluster_definer": bool(merged.get("is_cluster_definer")),
                }
    return lookup


def lookup_address(lookup: dict, currency: str, address: str) -> dict | None:
    return lookup.get((currency.upper(), address.lower()))
