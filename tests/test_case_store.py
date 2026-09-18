"""Smoke test for case storage — mocks psycopg2, no live Supabase connection
needed. Verifies save_case builds the right query, not that Postgres itself
works (that's an integration concern, tested manually against the real DB).
Run: python -m pytest tests/test_case_store.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import networkx as nx
from app.graph.trace import TraceResult
from app.graph.risk import RiskAssessment
from app.data.case_store import (
    save_case, list_cases, update_case_status, save_sahyog_draft,
    update_sahyog_status, log_case_event,
    add_upi_hop, list_upi_hops, delete_upi_hop,
)


def _fake_conn_returning(fetchone_value=None, fetchall_value=None):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_value
    cursor.fetchall.return_value = fetchall_value or []
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn, cursor


def test_save_case_inserts_and_returns_new_id():
    conn, cursor = _fake_conn_returning(fetchone_value=(42,))
    result = TraceResult(seed_address="0xaaa", path=["0xaaa", "0xbbb"], graph=nx.DiGraph(),
                          hop_count=1, entity_type="exchange", label="Binance 1", confidence=0.9)
    risk = RiskAssessment(compliance_status="registered_after_penalty",
                           compliance_detail="test", risk_flag=False, risk_level="none")

    case_id = save_case("ETH", result, risk, conn=conn)

    assert case_id == 42
    conn.commit.assert_called_once()
    args = cursor.execute.call_args[0]
    assert "INSERT INTO cases" in args[0]
    assert args[1][0] == "0xaaa"   # seed_address
    assert args[1][1] == "ETH"     # chain
    assert "none" in args[1]       # risk_level made it into the insert params


def test_list_cases_returns_rows_as_dicts():
    conn, cursor = _fake_conn_returning(fetchall_value=[
        {"id": 1, "seed_address": "0xaaa", "entity_type": "exchange", "label": "Binance 1",
         "confidence": 0.9, "risk_flag": False, "created_at": "2026-09-15"},
    ])
    rows = list_cases(limit=10, conn=conn)
    assert len(rows) == 1
    assert rows[0]["seed_address"] == "0xaaa"


def test_save_case_with_an_officer_logs_a_case_event():
    """Attributing a case to a real officer is what makes the audit trail
    real -- confirm it actually happens, not just that the column exists."""
    conn, cursor = _fake_conn_returning(fetchone_value=(42,))
    result = TraceResult(seed_address="0xaaa", path=["0xaaa", "0xbbb"], graph=nx.DiGraph(),
                          hop_count=1, entity_type="exchange", label="Binance 1", confidence=0.9)
    risk = RiskAssessment(compliance_status="registered_after_penalty",
                          compliance_detail="test", risk_flag=False, risk_level="none")

    save_case("ETH", result, risk, officer_id=7, conn=conn)

    event_call = next(c for c in cursor.execute.call_args_list if "INSERT INTO case_events" in c[0][0])
    assert event_call[0][1] == (42, 7, "trace_saved", "{}")


def test_update_case_status_rejects_an_unknown_status():
    conn, _ = _fake_conn_returning()
    with pytest.raises(ValueError):
        update_case_status(1, "archived-by-mistake", officer_id=1, conn=conn)


def test_update_case_status_updates_and_logs():
    conn, cursor = _fake_conn_returning()
    update_case_status(1, "closed", officer_id=7, conn=conn)
    update_call = cursor.execute.call_args_list[0]
    assert "UPDATE cases SET status" in update_call[0][0]
    assert update_call[0][1] == ("closed", 1)


def test_save_sahyog_draft_sets_status_to_draft():
    conn, cursor = _fake_conn_returning()
    save_sahyog_draft(1, "s94_bnss", {"seed_address": "0xaaa"}, officer_id=7, conn=conn)
    update_call = cursor.execute.call_args_list[0]
    assert "sahyog_status = 'draft'" in update_call[0][0]
    assert update_call[0][1][0] == "s94_bnss"


def test_update_sahyog_status_rejects_an_unknown_status():
    conn, _ = _fake_conn_returning()
    with pytest.raises(ValueError):
        update_sahyog_status(1, "not_a_real_status", officer_id=1, conn=conn)


def test_log_case_event_inserts_a_row():
    conn, cursor = _fake_conn_returning()
    log_case_event(1, 7, "status_changed", {"status": "closed"}, conn=conn)
    args = cursor.execute.call_args[0]
    assert "INSERT INTO case_events" in args[0]
    assert args[1] == (1, 7, "status_changed", '{"status": "closed"}')


# --- UPI/bank hops: the hand-entered money trail, see the module docstring
# on upi_hops in case_store.py for why this can't be anything but hand-entered ---

def test_add_upi_hop_assigns_the_next_order_after_existing_hops():
    """A case with 2 hops already recorded gets order 3 for a new one --
    hops are disclosed and entered in chain order, so this needs no
    separate reordering step."""
    conn, cursor = _fake_conn_returning()
    cursor.fetchone.side_effect = [(2,), (55,)]  # COUNT(*) -> 2, RETURNING id -> 55

    hop_id = add_upi_hop(1, {"payer_vpa": "victim@paytm", "amount": 5000.0}, officer_id=7, conn=conn)

    assert hop_id == 55
    insert_call = cursor.execute.call_args_list[1]
    assert "INSERT INTO upi_hops" in insert_call[0][0]
    params = insert_call[0][1]
    assert params[0] == 1          # case_id
    assert params[1] == 3          # hop_order = 2 existing + 1
    assert params[2] == "victim@paytm"


def test_add_upi_hop_on_an_empty_case_starts_at_order_one():
    conn, cursor = _fake_conn_returning()
    cursor.fetchone.side_effect = [(0,), (1,)]
    add_upi_hop(1, {"payer_vpa": "victim@paytm"}, officer_id=7, conn=conn)
    params = cursor.execute.call_args_list[1][0][1]
    assert params[1] == 1


def test_add_upi_hop_logs_a_case_event():
    conn, cursor = _fake_conn_returning()
    cursor.fetchone.side_effect = [(0,), (9,)]
    add_upi_hop(1, {"payer_vpa": "victim@paytm"}, officer_id=7, conn=conn)
    event_call = cursor.execute.call_args_list[2]  # third execute: log_case_event's insert
    assert "INSERT INTO case_events" in event_call[0][0]
    assert event_call[0][1][2] == "upi_hop_added"


def test_add_upi_hop_accepts_a_partial_hop_without_crashing():
    """A bank disclosure rarely arrives complete -- confirm a hop with only
    a couple of fields known doesn't KeyError, and that the fields that ARE
    known land in the right column position rather than shifting."""
    conn, cursor = _fake_conn_returning()
    cursor.fetchone.side_effect = [(0,), (1,)]
    add_upi_hop(1, {"payer_vpa": "victim@paytm", "amount": 200.0}, officer_id=7, conn=conn)
    params = cursor.execute.call_args_list[1][0][1]
    # case_id, hop_order, payer_vpa, payer_bank, payee_vpa, payee_bank, amount, utr, transferred_at, source, note, officer_id
    assert params == (1, 1, "victim@paytm", None, None, None, 200.0, None, None, None, None, 7)


def test_list_upi_hops_orders_by_hop_order():
    conn, cursor = _fake_conn_returning(fetchall_value=[
        {"id": 1, "case_id": 1, "hop_order": 1, "payer_vpa": "victim@paytm"},
        {"id": 2, "case_id": 1, "hop_order": 2, "payer_vpa": "mule1@ybl"},
    ])
    rows = list_upi_hops(1, conn=conn)
    assert [r["hop_order"] for r in rows] == [1, 2]
    query = cursor.execute.call_args[0][0]
    assert "ORDER BY hop_order ASC" in query


def test_delete_upi_hop_scopes_to_both_hop_id_and_case_id():
    """Scoped to case_id too, not just the hop's own id -- an officer on
    case A must not be able to delete a hop belonging to case B by guessing
    or mistyping its id."""
    conn, cursor = _fake_conn_returning()
    delete_upi_hop(case_id=1, hop_id=99, officer_id=7, conn=conn)
    delete_call = cursor.execute.call_args_list[0]
    assert "DELETE FROM upi_hops WHERE id = %s AND case_id = %s" in delete_call[0][0]
    assert delete_call[0][1] == (99, 1)


def test_delete_upi_hop_logs_a_case_event():
    conn, cursor = _fake_conn_returning()
    delete_upi_hop(case_id=1, hop_id=99, officer_id=7, conn=conn)
    event_call = cursor.execute.call_args_list[1]
    assert event_call[0][1][2] == "upi_hop_removed"
