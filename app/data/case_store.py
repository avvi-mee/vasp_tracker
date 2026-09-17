"""Case storage — Postgres (Supabase), chosen over SQLite because the app
deploys to Streamlit Community Cloud, whose filesystem is ephemeral and
would silently drop a local SQLite file on every restart.

Needs DATABASE_URL in .env (Supabase: Project Settings -> Database ->
Connection string -> URI). Uses plain psycopg2, not the full supabase-py
SDK — we only need basic CRUD on one table, not auth/storage/realtime.
"""
import os
import json
import psycopg2
import psycopg2.extras

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
ALTER TABLE cases ADD COLUMN IF NOT EXISTS sahyog_instrument TEXT;   -- 's94_bnss' | 's107_bnss' | 'pmla_s5' | 's63_bsa'
ALTER TABLE cases ADD COLUMN IF NOT EXISTS sahyog_draft JSONB;

CREATE TABLE IF NOT EXISTS case_events (
    id SERIAL PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id),
    officer_id INTEGER REFERENCES officers(id),
    action TEXT NOT NULL,   -- 'trace_saved' | 'status_changed' | 'sahyog_draft_generated' | 'sahyog_status_changed' | 'certificate_downloaded'
    detail JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

SAHYOG_STATUSES = ("draft", "ready_for_submission", "submitted", "acknowledged", "fulfilled")
CASE_STATUSES = ("open", "pending", "closed")


def get_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Set DATABASE_URL in your .env file — see .env.example.")
    return psycopg2.connect(url)


def init_db(conn=None) -> None:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    finally:
        if owns_conn:
            conn.close()


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
        conn.commit()
        if officer_id is not None:
            log_case_event(case_id, officer_id, "trace_saved", conn=conn)
        return case_id
    finally:
        if owns_conn:
            conn.close()


def list_cases(limit: int = 50, conn=None) -> list[dict]:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM cases ORDER BY created_at DESC LIMIT %s", (limit,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        if owns_conn:
            conn.close()


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
            conn.close()


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
            conn.close()


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
            conn.close()


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
            conn.close()


def save_sahyog_draft(case_id: int, instrument: str, draft: dict, officer_id: int | None, conn=None) -> None:
    """First disclosure-request draft on a case, or a regenerated one —
    always resets status to 'draft', since a new draft supersedes whatever
    submission state the previous one was in."""
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE cases SET sahyog_status = 'draft', sahyog_instrument = %s, sahyog_draft = %s WHERE id = %s",
                (instrument, json.dumps(draft), case_id),
            )
        conn.commit()
        log_case_event(case_id, officer_id, "sahyog_draft_generated", {"instrument": instrument}, conn=conn)
    finally:
        if owns_conn:
            conn.close()


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
            conn.close()


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
            conn.close()


def list_case_events(case_id: int, conn=None) -> list[dict]:
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM case_events WHERE case_id = %s ORDER BY created_at ASC", (case_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        if owns_conn:
            conn.close()


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
            conn.close()


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
            conn.close()


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
            conn.close()
