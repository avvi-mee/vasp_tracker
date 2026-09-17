"""Create an officer account directly against the database — no HTTP endpoint
exposes account creation for the first (bootstrap) admin, on purpose: an
open "create the first admin" API route is one the internet finds. Once that
first admin exists, further accounts go through an authenticated endpoint.

Usage:
    python scripts/create_officer.py --username admin --role admin --display-name "Nodal Admin"
    (prompts for a password if --password is omitted)
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.auth import hash_password
from app.data.case_store import create_officer, get_connection, init_db

VALID_ROLES = ("officer", "supervisor", "admin")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--role", default="officer", choices=VALID_ROLES)
    parser.add_argument("--password", help="omit to be prompted (not echoed)")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    conn = get_connection()
    try:
        init_db(conn=conn)
        officer_id = create_officer(
            username=args.username, password_hash=hash_password(password),
            role=args.role, display_name=args.display_name, conn=conn,
        )
    finally:
        conn.close()

    print(f"Created officer #{officer_id} — {args.username} ({args.role})")


if __name__ == "__main__":
    main()
