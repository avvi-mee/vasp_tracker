"""The Chainalysis sanctions oracle client, and how risk.py reads it.

Two things worth pinning down, both of which are easy to get quietly wrong:

  1. None is not False. A non-EVM chain has no oracle deployment and a free
     public RPC can have a bad minute — neither is evidence that an address
     is clean. If this collapses to False anywhere, the tool starts telling
     officers "not sanctioned" about chains it never asked about.

  2. A dead RPC must not fail a trace. The oracle is corroboration layered on
     top of a vendored OFAC snapshot that works offline; losing it should
     cost a line in the reason text, not the investigation.

Every test here mocks the HTTP call — same posture as the other client tests
in this directory, and the reason the suite still runs on a train.

Run: python -m pytest tests/test_chainalysis_oracle.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch

import networkx as nx
import pytest
import requests

from app.api_clients import chainalysis as oracle
from app.cache import clear_cache
from app.graph.risk import assess
from app.graph.trace import TraceResult

SANCTIONED = "0x7F367cC41522cE07553e823bf3be79A889DEbe1B"  # Blender.io, OFAC SDN
CLEAN = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"       # vitalik.eth

_TRUE = "0x" + "0" * 63 + "1"
_FALSE = "0x" + "0" * 64

# conftest.py blanks the chain map suite-wide so no other test can reach a
# real RPC. Captured at import, before any fixture runs, so this file can put
# it back — it is the one file whose whole job is exercising this client.
_REAL_CHAINS = dict(oracle._CHAINS)


@pytest.fixture(autouse=True)
def _restore_chain_map(monkeypatch):
    # Function-scoped autouse fixtures in a module run after those in
    # conftest, so this wins. Every test below still patches requests.post,
    # so restoring the map exposes the encoding and dispatch logic without
    # letting anything off the machine.
    monkeypatch.setattr(oracle, "_CHAINS", _REAL_CHAINS)
    # cached_fetch is process-global; one test's mocked verdict would
    # otherwise still be sitting there for the next one.
    clear_cache()
    yield
    clear_cache()


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _rpc(result):
    return patch.object(oracle.requests, "post", return_value=_Resp({"jsonrpc": "2.0", "id": 1, "result": result}))


def test_sanctioned_address_returns_true():
    with _rpc(_TRUE):
        assert oracle.is_sanctioned(SANCTIONED, "ETH") is True


def test_clean_address_returns_false_not_none():
    with _rpc(_FALSE):
        assert oracle.is_sanctioned(CLEAN, "ETH") is False


def test_unsupported_chain_returns_none_without_calling_out():
    """Bitcoin/Tron/Solana have no oracle. The distinction that matters: this
    is None ("didn't ask"), never False ("asked, it's clean")."""
    with patch.object(oracle.requests, "post") as post:
        for currency in ("BTC", "TRX", "SOL"):
            assert oracle.is_sanctioned(SANCTIONED, currency) is None
            assert oracle.screen_addresses([SANCTIONED], currency) is None
        post.assert_not_called()


def test_rpc_failure_is_none_not_false():
    with patch.object(oracle.requests, "post", side_effect=requests.ConnectionError("boom")):
        assert oracle.is_sanctioned(SANCTIONED, "ETH") is None


def test_malformed_rpc_reply_is_none():
    for bad in (None, "not-hex", {"unexpected": "shape"}):
        clear_cache()
        with _rpc(bad):
            assert oracle.is_sanctioned(SANCTIONED, "ETH") is None


def test_non_evm_address_on_evm_chain_is_not_asked_about():
    with patch.object(oracle.requests, "post") as post:
        assert oracle.is_sanctioned("TPvQPSaEM2mCrRCdQR3n8NcAGVCsSCRdaZ", "ETH") is None
        post.assert_not_called()


def test_call_is_well_formed():
    """The selector and the 32-byte left-padded argument are hand-built here
    rather than via an ABI encoder, so the encoding itself needs a test."""
    with _rpc(_TRUE) as post:
        oracle.is_sanctioned(SANCTIONED, "ETH")
    params = post.call_args.kwargs["json"]["params"][0]
    assert params["to"] == oracle._ORACLE_DEFAULT
    assert params["data"] == "0xdf592f7d" + "0" * 24 + SANCTIONED[2:].lower()
    assert len(params["data"]) == 10 + 64


def test_base_uses_its_own_oracle_address():
    """Chainalysis deploys the same address everywhere except Base. If these
    two constants ever collapse into one, Base screening silently hits a
    contract that isn't there."""
    assert oracle._ORACLE_BASE != oracle._ORACLE_DEFAULT


def test_screen_addresses_returns_only_the_hits():
    def _verdict(url, json, timeout):
        sanctioned = SANCTIONED[2:].lower() in json["params"][0]["data"]
        return _Resp({"result": _TRUE if sanctioned else _FALSE})

    with patch.object(oracle.requests, "post", side_effect=_verdict):
        hits = oracle.screen_addresses([SANCTIONED, CLEAN], "ETH")
    assert hits == [SANCTIONED.lower()]


def test_screen_addresses_empty_trail_is_empty_not_none():
    assert oracle.screen_addresses([], "ETH") == []


def test_partial_failure_is_not_reported_as_a_clean_trail():
    """One flaky RPC call in a twelve-hop trail must not produce "consulted,
    nothing listed". Filtering for truthy verdicts did exactly that — the
    unanswered address just vanished from the list."""
    def _flaky(url, json, timeout):
        if CLEAN[2:].lower() in json["params"][0]["data"]:
            raise requests.ConnectionError("one bad minute")
        return _Resp({"result": _FALSE})

    with patch.object(oracle.requests, "post", side_effect=_flaky):
        assert oracle.screen_addresses([SANCTIONED, CLEAN], "ETH") is None


def test_a_hit_still_stands_when_another_lookup_failed():
    """A positive finding is valid on its own — the addresses we could not
    reach could only add to it, never retract it."""
    def _flaky(url, json, timeout):
        data = json["params"][0]["data"]
        if CLEAN[2:].lower() in data:
            raise requests.ConnectionError("one bad minute")
        return _Resp({"result": _TRUE})

    with patch.object(oracle.requests, "post", side_effect=_flaky):
        assert oracle.screen_addresses([SANCTIONED, CLEAN], "ETH") == [SANCTIONED.lower()]


def test_fully_answered_clean_trail_is_empty_list_not_none():
    with _rpc(_FALSE):
        assert oracle.screen_addresses([SANCTIONED, CLEAN], "ETH") == []


def _result(**kw):
    base = dict(seed_address="0xseed", path=["0xseed", CLEAN.lower()], graph=nx.DiGraph(),
                hop_count=1, entity_type="unknown", label=None, confidence=0.5)
    return TraceResult(**{**base, **kw})


def test_oracle_hit_alone_raises_the_trail_to_high():
    """The address is on no list this build vendors — only the live oracle
    knows about it. That still has to be HIGH."""
    result = _result(path=["0xseed", CLEAN.lower()], oracle_sanctioned=[CLEAN.lower()])
    risk = assess(result)
    assert risk.risk_level == "high"
    assert "Chainalysis" in risk.risk_reason


def test_oracle_silence_does_not_change_an_unattributed_verdict():
    """Not consulted (None) and consulted-and-clean ([]) must both leave the
    existing low-risk "unattributed trail" verdict exactly as it was."""
    for value in (None, []):
        risk = assess(_result(oracle_sanctioned=value))
        assert risk.risk_level == "low"
        assert "Chainalysis" not in (risk.risk_reason or "")


def test_both_sources_agreeing_is_stated_as_corroboration():
    ronin = "0x098b716b8aaf21512996dc57eb0615e2383e2f96"  # in KNOWN_ILLICIT
    risk = assess(_result(path=["0xseed", ronin], oracle_sanctioned=[ronin]))
    assert risk.risk_level == "high"
    assert "Ronin" in risk.risk_reason
    assert "Independently confirmed" in risk.risk_reason
