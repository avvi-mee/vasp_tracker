"""HTTP client for a SAHYOG hub speaking the contract in
docs/sahyog-openapi.yaml (RESEARCH.md A.4). That contract is PROPOSED, not
an official I4C API — no public SAHYOG API exists. Today the only server that
speaks it is mock_sahyog/app.py; pointing SAHYOG_BASE_URL at a real endpoint
is the whole integration step.

Messages between the hub and VASP-Trace are signed with HMAC-SHA256 over the
raw body (header X-Sahyog-Signature). HMAC stands in for what a real hub
would use — mutual TLS plus JWS-signed payloads — and says so in the UI.
"""
import hashlib
import hmac
import os

import requests

SIGNATURE_HEADER = "X-Sahyog-Signature"
DEFAULT_BASE_URL = "http://localhost:8100"


def shared_secret() -> str | None:
    return os.environ.get("SAHYOG_SHARED_SECRET") or None


def sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify(body: bytes, signature: str | None, secret: str | None) -> bool:
    # No secret configured means nothing can be verified — reject, never
    # fall open.
    if not secret or not signature:
        return False
    return hmac.compare_digest(sign(body, secret), signature)


class SahyogClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10):
        self.base_url = (base_url or os.environ.get("SAHYOG_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, **params) -> dict | list:
        r = requests.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_vasps(self) -> list[dict]:
        return self._get("/v1/intermediaries", category="VASP")

    def submit(self, payload: dict) -> dict:
        """202 {sahyog_ref, status}. request_id is the idempotency key, so a
        retried submit of the same draft returns the same sahyog_ref."""
        r = requests.post(f"{self.base_url}/v1/vasp-requests", json=payload, timeout=self.timeout,
                          headers={"Idempotency-Key": payload["request_id"]})
        r.raise_for_status()
        return r.json()

    def status(self, sahyog_ref: str) -> dict:
        return self._get(f"/v1/vasp-requests/{sahyog_ref}")
