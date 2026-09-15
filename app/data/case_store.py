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
"""


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


def save_case(chain: str, trace_result, risk_assessment, conn=None) -> int:
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
                     compliance_status, compliance_detail, risk_flag, risk_level, risk_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    trace_result.seed_address, chain, trace_result.entity_type, trace_result.label,
                    trace_result.confidence, trace_result.hop_count, json.dumps(trace_result.path),
                    risk_assessment.compliance_status, risk_assessment.compliance_detail,
                    risk_assessment.risk_flag, risk_assessment.risk_level, risk_assessment.risk_reason,
                ),
            )
            case_id = cur.fetchone()[0]
        conn.commit()
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
