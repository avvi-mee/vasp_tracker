"""Bridge / swap-service labels: data, categories, and the chain-hop risk rule.

Run: python -m pytest tests/test_bridges.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import csv

import networkx as nx

from app.data.bridges import BRIDGES_CSV, load_bridges
from app.data.chain_native_labels import categorize
from app.graph.risk import assess
from app.graph.trace import Candidate, TraceResult

HEADER = "chain,address,name,kind,source\n"


def test_load_builds_label_records_keyed_like_the_tracer_looks_them_up(tmp_path):
    f = tmp_path / "b.csv"
    f.write_text(HEADER
                 + "eth,0xAbC0000000000000000000000000000000000001,Some Bridge,bridge,http://src\n"
                 + "TRX,TCaseSensitiveBase58,Some Swapper,swap_service,http://src2\n")
    got = load_bridges(f)
    rec = got[("ETH", "0xabc0000000000000000000000000000000000001")]
    assert (rec["label"], rec["category"], rec["source"]) == ("Some Bridge", "bridge", "http://src")
    assert got[("TRX", "TCaseSensitiveBase58")]["category"] == "swap_service"


def test_load_rejects_a_kind_it_does_not_know(tmp_path):
    """A typo'd kind would silently become an unclassified label and dodge the chain-hop rule."""
    f = tmp_path / "b.csv"
    f.write_text(HEADER + "ETH,0x0000000000000000000000000000000000000001,X,brdige,http://src\n")
    try:
        load_bridges(f)
    except ValueError as exc:
        assert "brdige" in str(exc)
    else:
        raise AssertionError("unknown kind accepted")


def test_every_shipped_row_names_a_source():
    with open(BRIDGES_CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows and all(r["source"].startswith("http") for r in rows)


def test_shipped_list_covers_tron_because_that_is_where_the_usdt_goes():
    got = load_bridges()
    assert got[("TRX", "TAuErcuAtU6BPt6YwL51JZ4RpDCPQASCU2")]["label"].startswith("Allbridge Core")
    assert got[("ETH", "0x3ee18b2214aff97000d974cf647e7c347e8fa585")]["label"] == "Wormhole Token Bridge"


def test_merged_labels_carry_the_bridge_rows():
    from app.api.main import _labels
    rec = _labels()[("TRX", "TAuErcuAtU6BPt6YwL51JZ4RpDCPQASCU2")]
    assert rec["category"] == "bridge"


def test_graphsense_changelly_is_reclassified_from_its_name():
    """GraphSense's Etherscan crawl has Changelly with no category, which used to read as a
    generic exchange to serve a disclosure notice on."""
    from app.api.main import _labels
    from app.data.chain_native_labels import entity_category
    assert entity_category(_labels()[("ETH", "0x96fc4553a00c117c5b0bed950dd625d1c16dc894")]) == "swap_service"


# --- explorer-tag categories ------------------------------------------------

def test_stargate_is_a_bridge_not_an_exchange_despite_containing_gate():
    """"gate" is in the exchange keywords (Gate.io); "Stargate" contains it."""
    assert categorize("Stargate: Router") == "bridge"


def test_instant_swap_services_are_swap_services():
    for tag in ("ChangeNOW", "SimpleSwap Deposit", "FixedFloat", "SideShift.ai", "Changelly Hot"):
        assert categorize(tag) == "swap_service", tag


# --- chain-hop risk rule ----------------------------------------------------

def _cand(path, entity_type, label, share=1.0):
    return Candidate(path=path, hop_count=len(path) - 1, entity_type=entity_type, label=label,
                     confidence=0.8, source="t", reason=None, asset=None, deposit=None, value_share=share)


def _result(primary, *others):
    return TraceResult(seed_address=primary.path[0], path=primary.path, graph=nx.DiGraph(),
                       hop_count=primary.hop_count, entity_type=primary.entity_type, label=primary.label,
                       confidence=0.8, candidates=[primary, *others])


def test_a_bridge_terminal_is_at_least_medium_and_says_the_funds_moved_chains():
    risk = assess(_result(_cand(["0xseed", "0xbridge"], "bridge", "Wormhole Token Bridge")))
    assert risk.risk_level == "medium"
    assert risk.risk_flag is True
    assert "another chain" in risk.risk_reason
    assert "Wormhole Token Bridge" in risk.risk_reason


def test_a_swap_service_terminal_carries_its_fiu_status():
    risk = assess(_result(_cand(["0xseed", "0xswap"], "swap_service", "FixedFloat")))
    assert risk.risk_level == "medium"
    assert risk.compliance_status == "flagged_non_compliant"  # FIU-IND wave 3


def test_a_material_bridge_side_branch_escalates_a_clean_exchange_trail():
    binance = _cand(["0xseed", "0xbin"], "exchange", "Binance: Hot Wallet 20", 0.6)
    bridge = _cand(["0xseed", "0xbridge"], "bridge", "Stargate V2: USDT pool", 0.4)
    risk = assess(_result(binance, bridge))
    assert risk.risk_level == "medium"
    assert "40%" in risk.risk_reason


def test_a_dust_bridge_side_branch_does_not_escalate():
    binance = _cand(["0xseed", "0xbin"], "exchange", "Binance: Hot Wallet 20", 0.95)
    bridge = _cand(["0xseed", "0xbridge"], "bridge", "Stargate V2: USDT pool", 0.05)
    assert assess(_result(binance, bridge)).risk_level == "none"


def test_a_mixer_still_outranks_a_bridge_on_the_same_trail():
    bridge = _cand(["0xseed", "0xbridge"], "bridge", "Wormhole Token Bridge", 0.5)
    mixer = _cand(["0xseed", "0xmix"], "mixer", "Tornado Cash", 0.5)
    assert assess(_result(bridge, mixer)).risk_level == "high"
