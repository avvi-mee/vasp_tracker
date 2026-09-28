"""Unattended watchlist sweeping.

The point of the sweep is that nobody is watching it, which means its
failure behaviour matters more than its success behaviour. One watched
address on a chain whose API is down must not stop the other nine from being
checked, and a sweep that throws must not take the monitor loop down with
it — otherwise monitoring silently stops and the Alerts page goes on looking
healthy, which is worse than never having had a scheduler.

Run: python -m pytest tests/test_watchlist_monitor.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import app.api.main as api_main
from app.api.main import Officer, get_current_officer

FAKE_OFFICER = Officer(id=1, username="test.officer", role="officer", display_name="Test Officer")
AUTH = {"Authorization": "Bearer overridden"}

WATCHED = [
    {"id": 1, "address": "0xaaa", "chain": "Ethereum"},
    {"id": 2, "address": "0xbbb", "chain": "Ethereum"},
    {"id": 3, "address": "0xccc", "chain": "Dogecoin"},  # not a wired-up chain
]


class _Result:
    entity_type = "exchange"
    label = "Test Exchange"


class _Risk:
    risk_level = "none"


def _setup(monkeypatch, failing: set[str] = frozenset()):
    recorded = []

    def fake_run_trace(req):
        if req.address in failing:
            raise RuntimeError("explorer unreachable")
        return "Ethereum", {}, _Result(), _Risk(), [], []

    monkeypatch.setattr(api_main, "init_watchlist_db", lambda: None)
    monkeypatch.setattr(api_main, "list_watchlist", lambda: list(WATCHED))
    monkeypatch.setattr(api_main, "_run_trace", fake_run_trace)
    monkeypatch.setattr(api_main, "record_check",
                        lambda wid, etype, label, level: recorded.append(wid))
    monkeypatch.setattr(api_main, "log_action", lambda *a, **k: None)
    monkeypatch.setitem(api_main.CHAINS, "Ethereum",
                        {"enabled": True, "currency": "ETH", "fetch": lambda a: []})
    api_main._monitor_state.update(last_sweep_at=None, last_sweep_checked=0, last_sweep_errors=0)
    return recorded


def test_sweep_checks_every_wired_up_address(monkeypatch):
    recorded = _setup(monkeypatch)
    state = api_main._sweep_watchlist()
    assert recorded == [1, 2]          # 3 skipped: its chain isn't wired up
    assert state["last_sweep_checked"] == 2
    assert state["last_sweep_errors"] == 0
    assert state["last_sweep_at"] is not None


def test_one_failing_address_does_not_abort_the_sweep(monkeypatch):
    """The whole reason this loop has a try/except inside it rather than
    around it."""
    recorded = _setup(monkeypatch, failing={"0xaaa"})
    state = api_main._sweep_watchlist()
    assert recorded == [2]
    assert state["last_sweep_checked"] == 1
    assert state["last_sweep_errors"] == 1


def test_skipped_chain_counts_as_neither_checked_nor_failed(monkeypatch):
    _setup(monkeypatch)
    state = api_main._sweep_watchlist()
    assert state["last_sweep_checked"] + state["last_sweep_errors"] == 2


def test_monitor_endpoint_reports_off_by_default(monkeypatch):
    _setup(monkeypatch)
    monkeypatch.setattr(api_main, "WATCHLIST_INTERVAL_MINUTES", 0)
    api_main.app.dependency_overrides[get_current_officer] = lambda: FAKE_OFFICER
    try:
        body = TestClient(api_main.app).get("/v1/watchlist/monitor", headers=AUTH).json()
    finally:
        api_main.app.dependency_overrides.pop(get_current_officer, None)
    # Must not claim monitoring it isn't doing — the Alerts page renders
    # straight off this flag.
    assert body["enabled"] is False
    assert body["interval_minutes"] == 0


def test_check_all_endpoint_runs_a_sweep(monkeypatch):
    recorded = _setup(monkeypatch)
    api_main.app.dependency_overrides[get_current_officer] = lambda: FAKE_OFFICER
    try:
        r = TestClient(api_main.app).post("/v1/watchlist/check-all", headers=AUTH)
    finally:
        api_main.app.dependency_overrides.pop(get_current_officer, None)
    assert r.status_code == 200
    assert r.json()["last_sweep_checked"] == 2
    assert recorded == [1, 2]


def test_check_all_route_is_not_shadowed_by_the_id_route():
    """POST /v1/watchlist/check-all and POST /v1/watchlist/{watch_id}/check
    are different path shapes, but a future rename could collide them — at
    which point "check-all" would be parsed as a watch_id and 422."""
    paths = {r.path for r in api_main.app.routes if hasattr(r, "path")}
    assert "/v1/watchlist/check-all" in paths
    assert "/v1/watchlist/{watch_id}/check" in paths
