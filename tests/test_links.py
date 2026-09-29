"""Cross-case linking — the same deposit address across NCRP complaints from
different states means the same beneficiary: one notice resolves many FIRs.

Run: python -m pytest tests/test_links.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

from app.data.case_store import save_case
from app.graph.links import case_link_keys, group_linked_rows
from app.graph.risk import RiskAssessment
from app.graph.sweep import DepositEvidence
from app.graph.trace import TraceResult


def _result(path, label="Binance-Hot 7", deposit_addr=None):
    deposit = None
    if deposit_addr:
        deposit = DepositEvidence(address=deposit_addr, vasp_address=path[-1], is_deposit_address=True,
                                  confidence=0.9, forwarded_ratio=0.95, destination_share=1.0,
                                  distinct_funders=15, sweep_count=3, median_hold_seconds=600)
    return TraceResult(seed_address=path[0], path=path, graph=nx.DiGraph(), hop_count=len(path) - 1,
                       entity_type="exchange" if label else "unknown", label=label, confidence=0.8,
                       deposit=deposit)


def test_link_keys_are_seed_intermediates_and_deposit_but_not_the_exchange():
    keys = case_link_keys(_result(["Tseed", "Tmid", "Tdep", "Thot"], deposit_addr="Tdep"))
    assert ("Tseed", "seed") in keys
    assert ("Tmid", "path") in keys
    assert ("Tdep", "deposit") in keys
    # an exchange hot wallet would link every case that touched Binance
    assert all(addr != "Thot" for addr, _ in keys)


def test_unlabelled_terminal_is_a_link_key():
    """A dead-end address nobody has named may be the mule wallet itself."""
    keys = case_link_keys(_result(["Tseed", "Tmule"], label=None))
    assert ("Tmule", "path") in keys


def test_rejected_deposit_check_does_not_create_a_deposit_link():
    r = _result(["Tseed", "Tdep", "Thot"], deposit_addr="Tdep")
    r.deposit.is_deposit_address = False
    assert ("Tdep", "deposit") not in case_link_keys(r)


def test_grouping_ranks_a_shared_deposit_address_as_same_beneficiary():
    rows = [
        {"case_id": 7, "address": "Tdep", "my_role": "deposit", "their_role": "deposit",
         "seed_address": "Tother", "chain": "TRX", "label": "Binance-Hot 7", "ncrp_ack_number": "3120",
         "cctns_fir_number": None, "status": "open", "created_at": "2026-09-20"},
        {"case_id": 8, "address": "Tmid", "my_role": "path", "their_role": "path",
         "seed_address": "Tx", "chain": "TRX", "label": None, "ncrp_ack_number": None,
         "cctns_fir_number": None, "status": "open", "created_at": "2026-09-21"},
    ]
    linked = group_linked_rows(rows)
    assert [c["case_id"] for c in linked] == [7, 8]  # strongest link first
    assert linked[0]["strength"] == "same_beneficiary"
    assert linked[1]["strength"] == "shared_intermediary"
    assert linked[0]["shared"] == [{"address": "Tdep", "my_role": "deposit", "their_role": "deposit"}]


def test_save_case_records_its_link_keys_in_the_same_transaction():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (42,)
    conn.cursor.return_value.__enter__.return_value = cursor
    risk = RiskAssessment(compliance_status="registered", compliance_detail="", risk_flag=False)

    save_case("TRX", _result(["Tseed", "Tdep", "Thot"], deposit_addr="Tdep"), risk, conn=conn)

    sql, rows = cursor.executemany.call_args[0]
    assert "INSERT INTO case_addresses" in sql
    assert (42, "Tdep", "TRX", "deposit", "Thot") in rows   # sink = the hot wallet it sweeps into
    assert (42, "Tseed", "TRX", "seed", None) in rows
    conn.commit.assert_called_once()


# --- exchange clusters -------------------------------------------------------

from app.graph.links import confirmed_deposits, exchange_clusters
from app.graph.trace import Candidate


def _cand(path, label, deposit_addr):
    d = DepositEvidence(address=deposit_addr, vasp_address=path[-1], is_deposit_address=True, confidence=0.9,
                        forwarded_ratio=0.95, destination_share=1.0, distinct_funders=4, sweep_count=2,
                        median_hold_seconds=60)
    return Candidate(path=path, hop_count=len(path) - 1, entity_type="exchange", label=label, confidence=0.8,
                     source="t", reason=None, asset=None, deposit=d, value_share=0.5)


def test_side_branch_deposits_are_link_keys_and_cluster_under_their_hot_wallet():
    r = _result(["Tseed", "TdepA", "Thot"], deposit_addr="TdepA")
    r.candidates = [_cand(["Tseed", "TdepA", "Thot"], "Binance-Hot 7", "TdepA"),
                    _cand(["Tseed", "TdepB", "Thot"], "Binance-Hot 7", "TdepB"),
                    _cand(["Tseed", "TdepC", "Tokx"], "OKX 3", "TdepC")]
    keys = case_link_keys(r)
    assert {("TdepA", "deposit"), ("TdepB", "deposit"), ("TdepC", "deposit")} <= set(keys)
    assert len(confirmed_deposits(r)) == 3  # TdepA counted once, not twice
    clusters = exchange_clusters(r)
    assert clusters[0] == {"hot_wallet": "Thot", "label": "Binance-Hot 7", "deposit_addresses": ["TdepA", "TdepB"]}
    assert clusters[1]["hot_wallet"] == "Tokx" and clusters[1]["deposit_addresses"] == ["TdepC"]


def test_no_confirmed_deposit_means_no_cluster():
    r = _result(["Tseed", "Thot"])
    assert exchange_clusters(r) == []
