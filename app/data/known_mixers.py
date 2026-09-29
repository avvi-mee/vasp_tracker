"""Known mixer contracts, loaded from mixers.csv (`chain,address,name,kind,source`).

Sourced rows only: every row carries the URL it came from. Tornado Cash rows
come from the project's own deployment config; Blender.io, Sinbad and the
Wasabi/Samourai coinjoin addresses are not repeated here because they already
reach the tracer as GraphSense `mixing_service`/`coinjoin` labels (see
risk.MIXER_CATEGORIES). A trail through an address not listed in either place
looks like a dead end, not a mixer — this is a curated list, not a classifier.

`chain` is the trace's currency code (ETH, MATIC, BNB...), the same key
trace.py looks up with.
"""
import csv
from pathlib import Path

from app.addresses import normalize_address

MIXERS_CSV = Path(__file__).with_name("mixers.csv")


def load_mixers(path: Path = MIXERS_CSV) -> dict[tuple[str, str], str]:
    with open(path, newline="", encoding="utf-8") as fh:
        return {(r["chain"].upper(), normalize_address(r["address"])): r["name"]
                for r in csv.DictReader(fh) if r["kind"] == "mixer"}


KNOWN_MIXERS = load_mixers()
