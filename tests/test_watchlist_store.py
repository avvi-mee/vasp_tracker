"""Watchlist storage — mocks psycopg2, no live Supabase connection needed.
Run: python -m pytest tests/test_watchlist_store.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app.data.watchlist_store import (
    add_to_watchlist, record_check, update_alert_status,
)


def _fake_conn(fetchone_sequence=None, fetchone_value=None):
    conn = MagicMock()
    cursor = MagicMock()
    if fetchone_sequence is not None:
        cursor.fetchone.side_effect = fetchone_sequence
    else:
        cursor.fetchone.return_value = fetchone_value
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn, cursor


def _watch_row(**overrides):
    row = {
        "id": 1, "address": "0xaaa", "chain": "ETH", "added_by_officer_id": 7,
        "added_at": "2026-01-01", "last_checked_at": "2026-01-01",
        "last_entity_type": "exchange", "last_label": "Binance 1",
        "last_risk_level": "none", "alert_status": "clear", "alert_reason": None,
    }
    row.update(overrides)
    return row


def test_add_to_watchlist_upserts_on_conflict():
    conn, cursor = _fake_conn(fetchone_value=(1,))
    watch_id = add_to_watchlist("0xaaa", "ETH", officer_id=7, conn=conn)
    assert watch_id == 1
    args = cursor.execute.call_args[0]
    assert "ON CONFLICT (address, chain)" in args[0]


def test_record_check_opens_an_alert_when_risk_worsens():
    current = _watch_row(last_risk_level="none")
    updated = _watch_row(last_risk_level="high", alert_status="open")
    conn, cursor = _fake_conn(fetchone_sequence=[current, updated])

    result = record_check(1, "mixer", "Tornado Cash", "high", conn=conn)

    update_call = next(c for c in cursor.execute.call_args_list if "UPDATE watchlist" in c[0][0])
    params = update_call[0][1]
    assert params[3] == "open"           # alert_status
    assert "Risk changed to high" in params[4]  # alert_reason
    assert result == updated


def test_record_check_opens_an_alert_when_entity_changes_at_same_risk():
    current = _watch_row(last_entity_type="exchange", last_label="Binance 1", last_risk_level="none")
    updated = _watch_row(last_label="Kraken 10", alert_status="open")
    conn, cursor = _fake_conn(fetchone_sequence=[current, updated])

    record_check(1, "exchange", "Kraken 10", "none", conn=conn)

    update_call = next(c for c in cursor.execute.call_args_list if "UPDATE watchlist" in c[0][0])
    params = update_call[0][1]
    assert params[3] == "open"
    assert "Now attributed to Kraken 10" in params[4]


def test_record_check_stays_clear_when_nothing_changed():
    current = _watch_row(last_entity_type="exchange", last_label="Binance 1", last_risk_level="none")
    conn, cursor = _fake_conn(fetchone_sequence=[current, current])

    record_check(1, "exchange", "Binance 1", "none", conn=conn)

    update_call = next(c for c in cursor.execute.call_args_list if "UPDATE watchlist" in c[0][0])
    assert update_call[0][1][3] == "clear"


def test_record_check_does_not_alert_on_the_very_first_check():
    """last_checked_at is NULL before the first check -- going from "never
    checked" to "attributed to X" is normal, not a change worth alerting on."""
    current = _watch_row(last_checked_at=None, last_entity_type=None, last_label=None)
    updated = _watch_row(last_label="Binance 1")
    conn, cursor = _fake_conn(fetchone_sequence=[current, updated])

    record_check(1, "exchange", "Binance 1", "none", conn=conn)

    update_call = next(c for c in cursor.execute.call_args_list if "UPDATE watchlist" in c[0][0])
    assert update_call[0][1][3] == "clear"


def test_record_check_rejects_an_unknown_watchlist_id():
    conn, cursor = _fake_conn(fetchone_value=None)
    with pytest.raises(ValueError):
        record_check(999, "exchange", "Binance 1", "none", conn=conn)


def test_update_alert_status_rejects_an_unknown_status():
    conn, _ = _fake_conn()
    with pytest.raises(ValueError):
        update_alert_status(1, "not-a-real-status", conn=conn)
