"""Case storage — Postgres (Supabase), chosen over SQLite because the app
deploys to Streamlit Community Cloud, whose filesystem is ephemeral and
would silently drop a local SQLite file on every restart.

Needs DATABASE_URL in .env (Supabase: Project Settings -> Database ->
Connection string -> URI). Uses plain psycopg2, not the full supabase-py
SDK — we only need basic CRUD on one table, not auth/storage/realtime.
"""
import os
import json
import threading
import psycopg2
import psycopg2.extras
import psycopg2.extensions
import psycopg2.pool

from app.graph.links import case_link_keys, group_linked_rows

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id SERIAL PRIMARY KEY,
    seed_address TEXT NOT NULL,
    chain TEXT NOT NULL,
    entity_type TEXT,
    label TEXT,
    confidence NUMERIC,
    hop_count INTEGER,
    path JSONB,
    compliance_status TEXT,
    compliance_detail TEXT,
    risk_flag BOOLEAN NOT NULL DEFAULT FALSE,
    risk_level TEXT NOT NULL DEFAULT 'none',
    risk_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS officers (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'officer',  -- 'officer' | 'supervisor' | 'admin'
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    officer_id INTEGER REFERENCES officers(id),
    action TEXT NOT NULL,       -- e.g. 'trace', 'certificate', 'login'
    target TEXT,                -- the address/case touched, if any
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Added in Phase 3 with IF NOT EXISTS / ADD COLUMN IF NOT EXISTS rather than
-- a separate migration tool -- this project has no migration framework, and
-- one for six columns and one table would be more machinery than the thing
-- it manages.
ALTER TABLE cases ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE cases ADD COLUMN IF NOT EXISTS officer_id INTEGER REFERENCES officers(id);
ALTER TABLE cases ADD COLUMN IF NOT EXISTS ncrp_ack_number TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS cctns_fir_number TEXT;
-- SAHYOG-style disclosure request tracking, kept on the case itself rather
-- than a separate table: in practice a case has at most one live disclosure
-- request, and giving it its own table would just be a 1:1 join every read.
ALTER TABLE cases ADD COLUMN IF NOT EXISTS sahyog_status TEXT;       -- NULL until a draft exists
ALTER TABLE cases ADD COLUMN IF NOT EXISTS sahyog_instrument TEXT;   -- a key of app/sahyog/gateway.py INSTRUMENTS
ALTER TABLE cases ADD COLUMN IF NOT EXISTS sahyog_draft JSONB;
-- Set once the request is submitted to a SAHYOG hub (today: mock_sahyog).
ALTER TABLE cases ADD COLUMN IF NOT EXISTS sahyog_ref TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS state TEXT;  -- complainant's state; picks the freeze route

CREATE TABLE IF NOT EXISTS case_events (
    id SERIAL PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id),
    officer_id INTEGER REFERENCES officers(id),
    action TEXT NOT NULL,   -- 'trace_saved' | 'status_changed' | 'sahyog_draft_generated' | 'sahyog_status_changed' | 'certificate_downloaded' | 'upi_hop_added' | 'upi_hop_removed'
    detail JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Backstop for record_sahyog_event's de-dupe check if two retries of the
-- same hub callback race each other.
CREATE UNIQUE INDEX IF NOT EXISTS case_events_sahyog_event
    ON case_events ((detail->>'event_id')) WHERE action = 'sahyog_callback';

-- UPI/bank leg of a money trail, entered by hand -- there is no API or
-- public dataset that maps a UPI transaction to anything (unlike a
-- blockchain, UPI/bank ledgers are private, held by banks and NPCI, and
-- only ever surface here because an officer has already obtained them
-- through a bank disclosure or an NCRP complaint). Every field is nullable
-- on purpose: a disclosure rarely arrives complete, and a hop with only an
-- amount and a bank name is still worth recording rather than blocked from
-- entry until every field is known.
CREATE TABLE IF NOT EXISTS upi_hops (
    id SERIAL PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id),
    hop_order INTEGER NOT NULL,   -- chain sequence, assigned at insert time
    payer_vpa TEXT,
    payer_bank TEXT,
    payee_vpa TEXT,
    payee_bank TEXT,
    amount NUMERIC,
    utr TEXT,                     -- UPI transaction reference number, bank-disclosed
    transferred_at TIMESTAMPTZ,
    source TEXT,                  -- where this hop came from, e.g. "Bank disclosure, 12/09/2026"
    note TEXT,
    officer_id INTEGER REFERENCES officers(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Cross-case linking: every address a case can be matched on (see
-- app/graph/links.py for which ones, and why the exchange hot wallet isn't).
CREATE TABLE IF NOT EXISTS case_addresses (
    case_id INTEGER NOT NULL REFERENCES cases(id),
    address TEXT NOT NULL,
    chain TEXT NOT NULL,
    role TEXT NOT NULL,           -- 'seed' | 'path' | 'deposit'
    PRIMARY KEY (case_id, address, role)
);
CREATE INDEX IF NOT EXISTS case_addresses_lookup ON case_addresses (chain, address);

-- Backfill cases saved before linking existed, from their stored path. Only
-- touches cases with no rows yet, so re-running on every init_db is cheap.
-- (Deposit addresses were never stored on the case, so old cases link on
-- seed and path only.)
INSERT INTO case_addresses (case_id, address, chain, role)
SELECT c.id, p.addr, c.chain, CASE WHEN p.n = 1 THEN 'seed' ELSE 'path' END
FROM cases c, jsonb_array_elements_text(c.path) WITH ORDINALITY AS p(addr, n)
WHERE NOT EXISTS (SELECT 1 FROM case_addresses a WHERE a.case_id = c.id)
  AND (c.label IS NULL OR p.n < jsonb_array_length(c.path))
ON CONFLICT DO NOTHING;
"""

SAHYOG_STATUSES = ("draft", "ready_for_submission", "submitted", "acknowledged", "fulfilled",
                   # Hub callback types (docs/sahyog-openapi.yaml), lowercased.
                   "clarification_sought", "responded", "actioned", "rejected", "overdue", "withdrawn")
CASE_STATUSES = ("open", "pending", "closed")


# Measured live: a fresh psycopg2.connect() to Supabase from this environment
# takes 2-5 SECONDS -- the TCP+TLS handshake and Postgres auth, not the query
# itself. Every function below used to pay that cost on every call, and a
# single request touching three of them (e.g. case_detail's
# get_case + list_case_events + list_upi_hops) paid it three times. A pooled
# connection is reused instead of reopened, cutting a page load from several
# seconds to roughly the query time alone.
#
# ThreadedConnectionPool specifically (not SimpleConnectionPool, which isn't
# documented thread-safe): FastAPI runs a plain `def` endpoint in a real OS
# thread via Starlette's threadpool, so concurrent requests genuinely borrow
# from this pool from different threads at once.
_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:  # a second thread may have built it while this one waited
                url = os.environ.get("DATABASE_URL")
                if not url:
                    raise RuntimeError("Set DATABASE_URL in your .env file — see .env.example.")
                _pool = psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=url)
    return _pool


def get_connection():
    return _get_pool().getconn()


def _release_connection(conn) -> None:
    """Returns a connection to the pool instead of closing the socket. A
    connection released mid-transaction (an exception before the caller's own
    commit) would otherwise poison the next borrower with "current
    transaction is aborted" -- rolled back defensively first, best-effort.

    Measured live: unconditionally calling rollback() here cost ~0.18s of its
    own -- ROLLBACK is a real round trip to Postgres, not a local no-op --
    and every read-only call (the large majority) was paying it for nothing.
    get_transaction_status() is answered from state psycopg2 already tracks
    client-side, no network call, so this skips the round trip whenever the
    connection is already clean (every success path, which already commits).
    """
    try:
        if conn.get_transaction_status() != psycopg2.extensions.TRANSACTION_STATUS_IDLE:
            conn.rollback()
    except Exception:
        pass
    _get_pool().putconn(conn)


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


def save_case(chain: str, trace_result, risk_assessment, officer_id: int | None = None, conn=None) -> int:
    """trace_result: app.graph.trace.TraceResult
    risk_assessment: app.graph.risk.RiskAssessment
    Returns the new case's id."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cases
                    (seed_address, chain, entity_type, label, confidence, hop_count, path,
                     compliance_status, compliance_detail, risk_flag, risk_level, risk_reason, officer_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    trace_result.seed_address, chain, trace_result.entity_type, trace_result.label,
                    trace_result.confidence, trace_result.hop_count, json.dumps(trace_result.path),
                    risk_assessment.compliance_status, risk_assessment.compliance_detail,
                    risk_assessment.risk_flag, risk_assessment.risk_level, risk_assessment.risk_reason,
                    officer_id,
                ),
            )
            case_id = cur.fetchone()[0]
            # executemany, not execute: one round trip's worth of intent, and
            # the case row and its link keys commit together or not at all.
            cur.executemany(
                "INSERT INTO case_addresses (case_id, address, chain, role) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                [(case_id, addr, chain, role) for addr, role in case_link_keys(trace_result)],
            )
        conn.commit()
        if officer_id is not None:
            log_case_event(case_id, officer_id, "trace_saved", conn=conn)
        return case_id
    finally:
        if owns_conn:
            _release_connection(conn)


def list_cases(limit: int = 50, conn=None) -> list[dict]:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM cases ORDER BY created_at DESC LIMIT %s", (limit,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        if owns_conn:
            _release_connection(conn)


def find_linked_cases(case_id: int, conn=None) -> list[dict]:
    """Other cases sharing any link address with this one, strongest first."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT other.case_id, other.address, mine.role AS my_role, other.role AS their_role,
                       c.seed_address, c.chain, c.label, c.ncrp_ack_number, c.cctns_fir_number,
                       c.status, c.created_at
                FROM case_addresses mine
                JOIN case_addresses other
                  ON other.chain = mine.chain AND other.address = mine.address
                 AND other.case_id <> mine.case_id
                JOIN cases c ON c.id = other.case_id
                WHERE mine.case_id = %s
                """,
                (case_id,),
            )
            return group_linked_rows([dict(row) for row in cur.fetchall()])
    finally:
        if owns_conn:
            _release_connection(conn)


def list_link_clusters(limit: int = 20, conn=None) -> list[dict]:
    """Addresses shared by two or more cases — the dashboard's view of
    likely mule / beneficiary networks. Deposit-address clusters first."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT chain, address, array_agg(DISTINCT role) AS roles,
                       COUNT(DISTINCT case_id) AS case_count,
                       array_agg(DISTINCT case_id) AS case_ids
                FROM case_addresses
                GROUP BY chain, address
                HAVING COUNT(DISTINCT case_id) > 1
                ORDER BY bool_or(role = 'deposit') DESC, COUNT(DISTINCT case_id) DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        if owns_conn:
            _release_connection(conn)


def get_case(case_id: int, conn=None) -> dict | None:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        if owns_conn:
            _release_connection(conn)


def update_case_status(case_id: int, status: str, officer_id: int | None, conn=None) -> None:
    if status not in CASE_STATUSES:
        raise ValueError(f"status must be one of {CASE_STATUSES}, got {status!r}")
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE cases SET status = %s WHERE id = %s", (status, case_id))
        conn.commit()
        log_case_event(case_id, officer_id, "status_changed", {"status": status}, conn=conn)
    finally:
        if owns_conn:
            _release_connection(conn)


def update_case_tags(case_id: int, tags: list[str], officer_id: int | None, conn=None) -> None:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE cases SET tags = %s WHERE id = %s", (tags, case_id))
        conn.commit()
        log_case_event(case_id, officer_id, "tags_changed", {"tags": tags}, conn=conn)
    finally:
        if owns_conn:
            _release_connection(conn)


def update_case_legal_refs(case_id: int, ncrp_ack_number: str | None, cctns_fir_number: str | None,
                           officer_id: int | None, conn=None) -> None:
    """NCRP acknowledgement (earliest, citizen-facing) and CCTNS FIR number
    (durable, legal) — the case identity anchors this plan's domain finding
    #4 asked for."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE cases SET ncrp_ack_number = %s, cctns_fir_number = %s WHERE id = %s",
                (ncrp_ack_number, cctns_fir_number, case_id),
            )
        conn.commit()
        log_case_event(case_id, officer_id, "legal_refs_changed",
                       {"ncrp_ack_number": ncrp_ack_number, "cctns_fir_number": cctns_fir_number}, conn=conn)
    finally:
        if owns_conn:
            _release_connection(conn)


def save_sahyog_draft(case_id: int, instrument: str, draft: dict, officer_id: int | None, conn=None) -> None:
    """First disclosure-request draft on a case, or a regenerated one —
    always resets status to 'draft', since a new draft supersedes whatever
    submission state the previous one was in."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                # sahyog_ref cleared: callbacks for the superseded submission
                # must not overwrite the new draft's status.
                "UPDATE cases SET sahyog_status = 'draft', sahyog_instrument = %s, sahyog_draft = %s, "
                "sahyog_ref = NULL WHERE id = %s",
                (instrument, json.dumps(draft), case_id),
            )
        conn.commit()
        log_case_event(case_id, officer_id, "sahyog_draft_generated", {"instrument": instrument}, conn=conn)
    finally:
        if owns_conn:
            _release_connection(conn)


def update_sahyog_status(case_id: int, status: str, officer_id: int | None, conn=None) -> None:
    """Manual, not synced from a real SAHYOG API — none exists to sync
    against (see the plan's SAHYOG research). Says so on the screen, not
    just in this docstring."""
    if status not in SAHYOG_STATUSES:
        raise ValueError(f"status must be one of {SAHYOG_STATUSES}, got {status!r}")
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE cases SET sahyog_status = %s WHERE id = %s", (status, case_id))
        conn.commit()
        log_case_event(case_id, officer_id, "sahyog_status_changed", {"status": status}, conn=conn)
    finally:
        if owns_conn:
            _release_connection(conn)


def set_case_intake(case_id: int, ncrp_ack_number: str | None, state: str | None, conn=None) -> None:
    """Complaint metadata arriving with a SAHYOG/NCRP push (no officer yet)."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE cases SET ncrp_ack_number = %s, state = %s WHERE id = %s",
                        (ncrp_ack_number, state, case_id))
        conn.commit()
        log_case_event(case_id, None, "sahyog_intake", {"ncrp_ack_number": ncrp_ack_number, "state": state},
                       conn=conn)
    finally:
        if owns_conn:
            _release_connection(conn)


def mark_sahyog_submitted(case_id: int, sahyog_ref: str, payload: dict, officer_id: int | None,
                          status: str = "submitted", conn=None) -> None:
    """`status` is what the hub reports — a resubmitted (idempotent) request
    keeps the status it already reached rather than going back to submitted."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE cases SET sahyog_status = %s, sahyog_ref = %s WHERE id = %s",
                        (status if status in SAHYOG_STATUSES else "submitted", sahyog_ref, case_id))
        conn.commit()
        log_case_event(case_id, officer_id, "sahyog_submitted",
                       {"sahyog_ref": sahyog_ref, "request_id": payload["request_id"],
                        "provision_code": payload["legal_basis"]["provision_code"],
                        "intermediary_id": payload["target"]["intermediary_id"]}, conn=conn)
    finally:
        if owns_conn:
            _release_connection(conn)


def record_sahyog_event(event: dict, conn=None) -> int | None:
    """Applies one hub callback: status update + timeline entry, in one
    transaction. Returns the case id, or None when the event was already
    applied (hubs retry; event_id is the de-dupe key) or the ref is unknown."""
    status = event["type"].lower()
    if status not in SAHYOG_STATUSES:
        raise ValueError(f"Unknown SAHYOG event type {event['type']!r}")
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM cases WHERE sahyog_ref = %s", (event["sahyog_ref"],))
            row = cur.fetchone()
            if not row:
                return None
            case_id = row[0]
            cur.execute("SELECT 1 FROM case_events WHERE case_id = %s AND action = 'sahyog_callback' "
                        "AND detail->>'event_id' = %s", (case_id, event["event_id"]))
            if cur.fetchone():
                return None
            cur.execute("UPDATE cases SET sahyog_status = %s WHERE id = %s", (status, case_id))
            cur.execute("INSERT INTO case_events (case_id, officer_id, action, detail) VALUES (%s, NULL, "
                        "'sahyog_callback', %s)", (case_id, json.dumps(event)))
        conn.commit()
        return case_id
    finally:
        if owns_conn:
            _release_connection(conn)


def log_case_event(case_id: int, officer_id: int | None, action: str,
                   detail: dict | None = None, conn=None) -> None:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO case_events (case_id, officer_id, action, detail) VALUES (%s, %s, %s, %s)",
                (case_id, officer_id, action, json.dumps(detail or {})),
            )
        conn.commit()
    finally:
        if owns_conn:
            _release_connection(conn)


def list_case_events(case_id: int, conn=None) -> list[dict]:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM case_events WHERE case_id = %s ORDER BY created_at ASC", (case_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        if owns_conn:
            _release_connection(conn)


def add_upi_hop(case_id: int, hop: dict, officer_id: int | None, conn=None) -> int:
    """Appends one hand-entered UPI/bank leg to a case's money trail.
    `hop_order` is assigned here as "however many hops already exist, plus
    one" -- hops are disclosed and entered in chain order in practice, so
    this needs no separate reordering UI; correcting a mistake is delete
    and re-add, the same pattern the rest of this store uses for edits."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM upi_hops WHERE case_id = %s", (case_id,))
            next_order = cur.fetchone()[0] + 1
            cur.execute(
                """
                INSERT INTO upi_hops
                    (case_id, hop_order, payer_vpa, payer_bank, payee_vpa, payee_bank,
                     amount, utr, transferred_at, source, note, officer_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (case_id, next_order, hop.get("payer_vpa"), hop.get("payer_bank"),
                 hop.get("payee_vpa"), hop.get("payee_bank"), hop.get("amount"), hop.get("utr"),
                 hop.get("transferred_at"), hop.get("source"), hop.get("note"), officer_id),
            )
            hop_id = cur.fetchone()[0]
        conn.commit()
        log_case_event(case_id, officer_id, "upi_hop_added", {"hop_id": hop_id, "hop_order": next_order}, conn=conn)
        return hop_id
    finally:
        if owns_conn:
            _release_connection(conn)


def list_upi_hops(case_id: int, conn=None) -> list[dict]:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM upi_hops WHERE case_id = %s ORDER BY hop_order ASC", (case_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        if owns_conn:
            _release_connection(conn)


def delete_upi_hop(case_id: int, hop_id: int, officer_id: int | None, conn=None) -> None:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM upi_hops WHERE id = %s AND case_id = %s", (hop_id, case_id))
        conn.commit()
        log_case_event(case_id, officer_id, "upi_hop_removed", {"hop_id": hop_id}, conn=conn)
    finally:
        if owns_conn:
            _release_connection(conn)


def create_officer(username: str, password_hash: str, role: str, display_name: str, conn=None) -> int:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO officers (username, password_hash, role, display_name)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (username, password_hash, role, display_name),
            )
            officer_id = cur.fetchone()[0]
        conn.commit()
        return officer_id
    finally:
        if owns_conn:
            _release_connection(conn)


def get_officer_by_username(username: str, conn=None) -> dict | None:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM officers WHERE username = %s", (username,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        if owns_conn:
            _release_connection(conn)


def log_action(officer_id: int | None, action: str, target: str | None = None,
               details: dict | None = None, conn=None) -> None:
    """Best-effort audit trail — every authenticated mutation gets a row here.
    This is what upgrades "we have a login" to "we can say who did what,"
    which is the part of gap #14 that actually matters for a court-facing
    evidence pack, not just having a password on the door."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_log (officer_id, action, target, details)
                VALUES (%s, %s, %s, %s)
                """,
                (officer_id, action, target, json.dumps(details or {})),
            )
        conn.commit()
    finally:
        if owns_conn:
            _release_connection(conn)
