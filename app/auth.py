"""Password hashing and session tokens for the officer login.

Password hashing uses stdlib `hashlib.pbkdf2_hmac` — no bcrypt/passlib
dependency needed at this scale. JWT is the one genuinely new dependency
(`pyjwt`); there's no equivalent in the standard library worth hand-rolling.
"""
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt

logger = logging.getLogger("vasp_trace.auth")

PBKDF2_ITERATIONS = 200_000
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 12

_JWT_SECRET = os.environ.get("JWT_SECRET")
if not _JWT_SECRET:
    # Boots the demo anyway rather than hard-failing — but every restart
    # invalidates existing sessions, and this is NOT safe for anything beyond
    # a single-machine demo. Set JWT_SECRET in .env before deploying anywhere.
    _JWT_SECRET = secrets.token_hex(32)
    logger.warning(
        "JWT_SECRET not set in .env — using a random one-time secret. "
        "Every officer will need to log in again after any server restart. "
        "Set JWT_SECRET before deploying this anywhere but a laptop demo."
    )


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    salt, _, digest_hex = stored_hash.partition("$")
    if not salt or not digest_hex:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return secrets.compare_digest(digest.hex(), digest_hex)


def create_token(officer_id: int, username: str, role: str, display_name: str) -> str:
    payload = {
        "sub": str(officer_id),
        "username": username,
        "role": role,
        "display_name": display_name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises jwt.PyJWTError (expired, malformed, bad signature) — callers
    turn that into a 401, not this module's job."""
    return jwt.decode(token, _JWT_SECRET, algorithms=[JWT_ALGORITHM])
