"""Chainalysis Sanctions Screening API client.

This client is written against Chainalysis's published documentation and has
never seen a real 200 — no key has been provisioned yet. The endpoint is
confirmed reachable (403 {"message":"Invalid API Key"} without a key), but
the success-path shape is documentation, not observation. That is the same
caveat app/api_clients/bsctrace.py carries.

So these tests are not really about the happy path. They pin the behaviour
that makes shipping an unverified client defensible in the first place:
every payload the module does not positively recognise has to come back as
None — "not consulted" — never as an empty all-clear. If the documented
shape turns out to be wrong, the tool must degrade to saying it did not
check, not to saying the trail is clean.

Run: python -m pytest tests/test_chainalysis_api.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch

import pytest
import requests

from app.api_clients import chainalysis
from app.cache import clear_cache

SANCTIONED = "0x7F367cC41522cE07553e823bf3be79A889DEbe1B"
CLEAN = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

_HIT = {"identifications": [{
    "category": "sanctions",
    "name": "SDN: LAZARUS GROUP",
    "description": "Cyber-related designation.",
    "url": "https://home.treasury.gov/",
}]}
_NO_HIT = {"identifications": []}


@pytest.fixture(autouse=True)
def _with_key(monkeypatch):
    # conftest.py strips the key suite-wide so nothing reaches Chainalysis.
    # This file is the one that needs the configured path, and every test
    # below still patches requests.get.
    monkeypatch.setenv("CHAINALYSIS_API_KEY", "test-key")
    clear_cache()
    yield
    clear_cache()


class _Resp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _api(payload, status_code=200):
    return patch.object(chainalysis.requests, "get", return_value=_Resp(payload, status_code))


def test_sanctioned_address_returns_the_designation():
    with _api(_HIT):
        found = chainalysis.api_designations(SANCTIONED)
    assert len(found) == 1
    # The designation itself is the point — this is what the oracle's bare
    # bool cannot give an officer.
    assert found[0]["name"] == "SDN: LAZARUS GROUP"
    assert found[0]["url"].startswith("https://")


def test_clean_address_is_empty_list_not_none():
    with _api(_NO_HIT):
        assert chainalysis.api_designations(CLEAN) == []


def test_no_key_configured_is_not_consulted(monkeypatch):
    monkeypatch.delenv("CHAINALYSIS_API_KEY", raising=False)
    with patch.object(chainalysis.requests, "get") as get:
        assert chainalysis.api_available() is False
        assert chainalysis.api_designations(SANCTIONED) is None
        assert chainalysis.api_screen_addresses([SANCTIONED]) is None
        get.assert_not_called()


def test_auth_failure_is_none_not_clean():
    """A rejected key means we have no finding. Reporting [] here would tell
    an officer the trail was screened and cleared when it was never screened
    at all — the single worst thing this client could do."""
    for status in (400, 401, 403, 429, 500):
        clear_cache()
        with _api({"message": "Invalid API Key"}, status_code=status):
            assert chainalysis.api_designations(SANCTIONED) is None


def test_network_failure_is_none():
    with patch.object(chainalysis.requests, "get", side_effect=requests.ConnectionError("down")):
        assert chainalysis.api_designations(SANCTIONED) is None


def test_unrecognised_payload_shapes_are_none():
    """The whole safety argument for shipping this before it has ever seen a
    real 200. Anything that is not {"identifications": [...]} is treated as
    "we did not get an answer"."""
    for payload in (
        {},                                   # no identifications key
        {"identifications": None},
        {"identifications": "sanctioned"},    # not a list
        ["unexpected", "top-level", "list"],
        "plain string",
        ValueError("not json at all"),
    ):
        clear_cache()
        with _api(payload):
            assert chainalysis.api_designations(SANCTIONED) is None, payload


def test_unknown_category_still_counts_as_a_hit():
    """If Chainalysis renames the category, requiring an exact match would
    turn every hit into a miss — failing towards "clean", which is the wrong
    direction for a sanctions check to fail in."""
    with _api({"identifications": [{"category": "sanctions-list-v2", "name": "X"}]}):
        assert len(chainalysis.api_designations(SANCTIONED)) == 1


def test_request_carries_the_key_header_and_address():
    with _api(_NO_HIT) as get:
        chainalysis.api_designations(SANCTIONED)
    assert get.call_args.args[0].endswith(SANCTIONED.lower())
    assert get.call_args.kwargs["headers"]["X-API-Key"] == "test-key"


def test_screening_a_trail_returns_only_the_hits():
    def _verdict(url, headers, timeout):
        return _Resp(_HIT if url.endswith(SANCTIONED.lower()) else _NO_HIT)

    with patch.object(chainalysis.requests, "get", side_effect=_verdict):
        assert chainalysis.api_screen_addresses([SANCTIONED, CLEAN]) == [SANCTIONED.lower()]


def test_partial_failure_across_a_trail_is_none():
    def _verdict(url, headers, timeout):
        if url.endswith(CLEAN.lower()):
            raise requests.ConnectionError("one bad minute")
        return _Resp(_NO_HIT)

    with patch.object(chainalysis.requests, "get", side_effect=_verdict):
        assert chainalysis.api_screen_addresses([SANCTIONED, CLEAN]) is None


def test_api_covers_the_chains_the_oracle_cannot():
    """The reason this client exists at all: api_screen_addresses takes no
    currency, because unlike the on-chain oracle it is not EVM-only."""
    def _verdict(url, headers, timeout):
        return _Resp(_HIT)

    btc = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
    tron = "TPvQPSaEM2mCrRCdQR3n8NcAGVCsSCRdaZ"
    with patch.object(chainalysis.requests, "get", side_effect=_verdict):
        hits = chainalysis.api_screen_addresses([btc, tron])
    assert len(hits) == 2
    # And the oracle genuinely cannot answer for either.
    assert chainalysis.is_sanctioned(btc, "BTC") is None
    assert chainalysis.is_sanctioned(tron, "TRX") is None
