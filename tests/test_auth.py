"""Password hashing and session tokens — no network/DB needed.
Run: python -m pytest tests/test_auth.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import jwt as pyjwt

from app.auth import create_token, decode_token, hash_password, verify_password


def test_correct_password_verifies():
    stored = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", stored) is True


def test_wrong_password_is_rejected():
    stored = hash_password("correct horse battery staple")
    assert verify_password("wrong password", stored) is False


def test_two_hashes_of_the_same_password_differ():
    """Salted -- otherwise identical passwords produce identical hashes,
    which leaks who shares a password."""
    assert hash_password("same password") != hash_password("same password")


def test_malformed_stored_hash_is_rejected_not_crashed():
    assert verify_password("anything", "not-a-valid-hash") is False


def test_token_roundtrips_officer_identity():
    token = create_token(officer_id=7, username="inspector.rao", role="officer", display_name="Inspector Rao")
    payload = decode_token(token)
    assert payload["sub"] == "7"
    assert payload["username"] == "inspector.rao"
    assert payload["role"] == "officer"
    assert payload["display_name"] == "Inspector Rao"


def test_tampered_token_is_rejected():
    token = create_token(officer_id=7, username="inspector.rao", role="officer", display_name="Inspector Rao")
    tampered = token[:-4] + "abcd"
    with pytest.raises(pyjwt.PyJWTError):
        decode_token(tampered)
