"""Loads GraphSense TagPacks (YAML) into an address -> label lookup.

TagPack format (see research/02-graphsense-tagpacks.md): each file has a
header (label/currency/category/source/confidence/is_cluster_definer) that
every tag inherits, unless a tag overrides a field itself.

Measured live: parsing the vendored dataset (86 files, ~500K individual
tags) took 69 SECONDS on a cold process — by far the largest single
contributor to "the app feels slow", well past anything API-fetch latency
accounts for. Two fixes, both safe and reversible:
  1. yaml.CSafeLoader (libyaml's C parser) instead of the pure-Python
     SafeLoader safe_load() defaults to.
  2. A disk-cached parsed result, invalidated by the dataset's own newest
     file mtime — this is a static vendored git clone that doesn't change
     between runs, so re-parsing it every process start is pure waste.
"""
import pickle
from pathlib import Path

import yaml

from app.addresses import normalize_address as _normalize

TAGPACKS_DIR = Path(__file__).parent / "graphsense-tagpacks" / "packs"
CACHE_FILE = Path(__file__).parent / "graphsense-tagpacks" / ".labels_cache.pkl"

HEADER_FIELDS = ("label", "currency", "category", "source", "confidence", "is_cluster_definer", "actor")

# The C-accelerated loader if libyaml is available (it is, in this project's
# venv — checked live); pure-Python SafeLoader otherwise rather than fail.
_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _dataset_fingerprint(tagpacks_dir: Path) -> float:
    """Newest file mtime in the dataset — a cheap, good-enough proxy for
    "has this changed since the cache was written"."""
    return max((f.stat().st_mtime for f in tagpacks_dir.rglob("*.yaml")), default=0.0)


def load_labels(tagpacks_dir: Path = TAGPACKS_DIR, use_cache: bool = True) -> dict[tuple[str, str], dict]:
    """Returns {(currency, address_lowercased): {label, category, source, confidence, is_cluster_definer}}"""
    if not tagpacks_dir.exists():
        raise FileNotFoundError(
            f"{tagpacks_dir} not found — git clone https://github.com/graphsense/graphsense-tagpacks "
            f"into app/data/ first."
        )

    fingerprint = _dataset_fingerprint(tagpacks_dir)
    cache_file = tagpacks_dir.parent / CACHE_FILE.name
    if use_cache and cache_file.exists():
        try:
            with cache_file.open("rb") as f:
                cached_fingerprint, cached_lookup = pickle.load(f)
            if cached_fingerprint == fingerprint:
                return cached_lookup
        except Exception:
            pass  # corrupt or old-format cache file — fall through and rebuild it

    lookup: dict[tuple[str, str], dict] = {}
    for yaml_file in tagpacks_dir.rglob("*.yaml"):
        try:
            doc = yaml.load(yaml_file.read_text(encoding="utf-8"), Loader=_YAML_LOADER)
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
            key = (currency, _normalize(address))
            # keep the first match, unless this one is a stronger (cluster-defining) tag
            if key not in lookup or merged.get("is_cluster_definer"):
                lookup[key] = {
                    "label": merged.get("label"),
                    "category": merged.get("category"),
                    "source": merged.get("source"),
                    "confidence": merged.get("confidence"),
                    "is_cluster_definer": bool(merged.get("is_cluster_definer")),
                }

    if use_cache:
        try:
            with cache_file.open("wb") as f:
                pickle.dump((fingerprint, lookup), f)
        except OSError:
            pass  # best-effort -- a write failure shouldn't break the load that just succeeded

    return lookup


def lookup_address(lookup: dict, currency: str, address: str) -> dict | None:
    return lookup.get((currency.upper(), _normalize(address)))
