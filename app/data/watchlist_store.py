"""Watchlist storage — addresses under continuous/recurring monitoring, not
a one-off trace. Kept separate from case_store.py's `cases` table on
purpose: a case is a specific investigation's finding; a watchlist entry is
an address someone wants re-checked over time, which may or may not ever
become a case. Same Postgres database, same connection helper — no new
infrastructure, just a table this project didn't need until continuous
monitoring (the problem statement's "alerting for high-risk wallets") did.
"""
import psycopg2.extras

from app.data.case_store import get_connection, _release_connection

SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    address TEXT NOT NULL,
    chain TEXT NOT NULL,
    added_by_officer_id INTEGER REFERENCES officers(id),
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_checked_at TIMESTAMPTZ,
    last_entity_type TEXT,
    last_label TEXT,
    last_risk_level TEXT NOT NULL DEFAULT 'none',
    alert_status TEXT NOT NULL DEFAULT 'clear',  -- 'clear' | 'open' | 'acknowledged'
    alert_reason TEXT,
    UNIQUE (address, chain)
);
"""

# Ordered low -> high, same severities the risk engine already produces —
# no new taxonomy needed for "alerting on high-risk wallets".
RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}
ALERT_STATUSES = ("clear", "open", "acknowledged")


def init_db(conn=None) -> None:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    finally:
        if owns_conn:
            _release_connection(conn)


def add_to_watchlist(address: str, chain: str, officer_id: int | None, conn=None) -> int:
    """Idempotent — re-adding the same (address, chain) returns the existing
    entry's id rather than erroring or duplicating it."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO watchlist (address, chain, added_by_officer_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (address, chain) DO UPDATE SET address = EXCLUDED.address
                RETURNING id
                """,
                (address, chain, officer_id),
            )
            watch_id = cur.fetchone()[0]
        conn.commit()
        return watch_id
    finally:
        if owns_conn:
            _release_connection(conn)


def list_watchlist(conn=None) -> list[dict]:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM watchlist ORDER BY added_at DESC")
            return [dict(row) for row in cur.fetchall()]
    finally:
        if owns_conn:
            _release_connection(conn)


def get_watch(watch_id: int, conn=None) -> dict | None:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM watchlist WHERE id = %s", (watch_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        if owns_conn:
            _release_connection(conn)


def record_check(watch_id: int, entity_type: str, label: str | None, risk_level: str, conn=None) -> dict:
    """Updates a watchlist entry with a fresh trace result, opening an alert
    if risk got worse or the attributed entity changed since the last check.
    A drop in risk, or the same entity again, is not alert-worthy on its own
    — an ever-growing pile of "still fine" alerts trains an officer to
    ignore the queue, which defeats the point of alerting at all."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        current = get_watch(watch_id, conn=conn)
        if current is None:
            raise ValueError(f"Watchlist entry {watch_id} not found.")

        risk_worsened = RISK_ORDER.get(risk_level, 0) > RISK_ORDER.get(current["last_risk_level"], 0)
        previously_seen = current["last_checked_at"] is not None
        previous_identity = current["last_label"] or current["last_entity_type"]
        entity_changed = previously_seen and (label or entity_type) != previous_identity

        alert_status, alert_reason = current["alert_status"], current["alert_reason"]
        if risk_worsened:
            alert_status = "open"
            alert_reason = f"Risk changed to {risk_level} (was {current['last_risk_level']})"
        elif entity_changed:
            alert_status = "open"
            alert_reason = f"Now attributed to {label or entity_type} (was {previous_identity or 'unattributed'})"

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE watchlist
                SET last_checked_at = now(), last_entity_type = %s, last_label = %s,
                    last_risk_level = %s, alert_status = %s, alert_reason = %s
                WHERE id = %s
                """,
                (entity_type, label, risk_level, alert_status, alert_reason, watch_id),
            )
        conn.commit()
        return get_watch(watch_id, conn=conn)
    finally:
        if owns_conn:
            _release_connection(conn)


def update_alert_status(watch_id: int, status: str, conn=None) -> None:
    if status not in ALERT_STATUSES:
        raise ValueError(f"status must be one of {ALERT_STATUSES}, got {status!r}")
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE watchlist SET alert_status = %s WHERE id = %s", (status, watch_id))
        conn.commit()
    finally:
        if owns_conn:
            _release_connection(conn)


def remove_from_watchlist(watch_id: int, conn=None) -> None:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM watchlist WHERE id = %s", (watch_id,))
        conn.commit()
    finally:
        if owns_conn:
            _release_connection(conn)
