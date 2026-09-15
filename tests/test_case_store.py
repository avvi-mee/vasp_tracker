"""Smoke test for case storage — mocks psycopg2, no live Supabase connection
needed. Verifies save_case builds the right query, not that Postgres itself
works (that's an integration concern, tested manually against the real DB).
Run: python -m pytest tests/test_case_store.py -v
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx
from app.graph.trace import TraceResult
from app.graph.risk import RiskAssessment
from app.data.case_store import save_case, list_cases


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
                           compliance_detail="test", risk_flag=False)

    case_id = save_case("ETH", result, risk, conn=conn)

    assert case_id == 42
    conn.commit.assert_called_once()
    args = cursor.execute.call_args[0]
    assert "INSERT INTO cases" in args[0]
    assert args[1][0] == "0xaaa"   # seed_address
    assert args[1][1] == "ETH"     # chain


def test_list_cases_returns_rows_as_dicts():
    conn, cursor = _fake_conn_returning(fetchall_value=[
        {"id": 1, "seed_address": "0xaaa", "entity_type": "exchange", "label": "Binance 1",
         "confidence": 0.9, "risk_flag": False, "created_at": "2026-09-15"},
    ])
    rows = list_cases(limit=10, conn=conn)
    assert len(rows) == 1
    assert rows[0]["seed_address"] == "0xaaa"
