"""Mixer list is data (app/data/mixers.csv), not a hardcoded dict.

Run: python -m pytest tests/test_known_mixers.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import csv

from app.data.known_mixers import KNOWN_MIXERS, load_mixers, MIXERS_CSV

HEADER = "chain,address,name,kind,source\n"


def test_load_normalises_keys_like_the_tracer_looks_them_up(tmp_path):
    """trace.py asks for (currency.upper(), normalize_address(addr)): hex lowercased,
    base58 untouched. A key built any other way would never match."""
    f = tmp_path / "m.csv"
    f.write_text(HEADER
                 + "eth,0xAbC0000000000000000000000000000000000001,Pool A,mixer,http://src\n"
                 + "BTC,1BaseFiftyEightMixedCASE,Coinjoin B,mixer,http://src\n")
    assert load_mixers(f) == {
        ("ETH", "0xabc0000000000000000000000000000000000001"): "Pool A",
        ("BTC", "1BaseFiftyEightMixedCASE"): "Coinjoin B",
    }


def test_load_skips_rows_that_are_not_mixers(tmp_path):
    """The file shape is shared with bridges.csv later; KNOWN_MIXERS must only ever hold mixers."""
    f = tmp_path / "m.csv"
    f.write_text(HEADER
                 + "ETH,0x0000000000000000000000000000000000000001,A mixer,mixer,http://src\n"
                 + "ETH,0x0000000000000000000000000000000000000002,A bridge,bridge,http://src\n")
    assert list(load_mixers(f).values()) == ["A mixer"]


def test_shipped_list_keeps_the_old_hardcoded_entry():
    """Regression: the single address this list used to hold must survive the move to CSV."""
    assert ("ETH", "0x8589427373d6d84e98730d7795d8f6f8731fda16") in KNOWN_MIXERS


def test_shipped_list_covers_every_evm_chain_tornado_is_traced_on():
    chains = {chain for chain, _ in KNOWN_MIXERS}
    assert {"ETH", "MATIC", "BNB"} <= chains
    # Tornado's 0.1 ETH pool: on the OFAC-delisted list, but still a mixer.
    assert ("ETH", "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc") in KNOWN_MIXERS


def test_every_shipped_row_names_a_source():
    """Policy for this file: sourced addresses only. A row with no source is a guess."""
    with open(MIXERS_CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    assert all(r["source"].startswith("http") for r in rows), "row without a source URL"
    assert all(r["kind"] == "mixer" for r in rows)
