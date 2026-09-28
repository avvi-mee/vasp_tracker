"""Rupee conversion is decision support, so its failure mode matters more
than its happy path: a missing rate must produce no number at all, never a
zero and never a stale-but-unlabelled one presented as current.

Run: python -m pytest tests/test_prices.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch

import pytest
import requests

from app import prices

_PAYLOAD = {"ethereum": {"inr": 265403}, "tether": {"inr": 95.77}, "bitcoin": {"inr": 8307750}}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    # conftest.py sets DISABLE_PRICE_FEED suite-wide so no other test reaches
    # CoinGecko. This file patches requests.get itself, so it needs the real
    # code path — and it also has a test that the switch works, which sets
    # the variable back deliberately.
    monkeypatch.delenv("DISABLE_PRICE_FEED", raising=False)
    prices.clear_cache()
    yield
    prices.clear_cache()


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_rates_and_conversion():
    with patch.object(prices.requests, "get", return_value=_Resp(_PAYLOAD)):
        assert prices.inr_rate("ETH") == 265403
        assert prices.to_inr(0.42, "ETH") == pytest.approx(111469.26)


def test_symbol_lookup_is_case_insensitive():
    with patch.object(prices.requests, "get", return_value=_Resp(_PAYLOAD)):
        assert prices.inr_rate("eth") == prices.inr_rate("ETH")


def test_unmapped_symbol_is_none_not_zero():
    """A random BEP-20 has no CoinGecko id. Returning 0.0 here would render
    as 'Rs 0' next to a real balance, which reads as 'worthless' rather than
    'unknown' — the exact opposite of what the tool knows."""
    with patch.object(prices.requests, "get", return_value=_Resp(_PAYLOAD)):
        assert prices.inr_rate("SCAMCOIN") is None
        assert prices.to_inr(1_000_000, "SCAMCOIN") is None


def test_cold_start_failure_yields_empty_table():
    with patch.object(prices.requests, "get", side_effect=requests.ConnectionError("down")):
        assert prices.rates() == {}
        assert prices.inr_rate("ETH") is None


def test_stale_table_survives_a_later_outage():
    with patch.object(prices.requests, "get", return_value=_Resp(_PAYLOAD)):
        assert prices.inr_rate("ETH") == 265403
    prices._cache = (prices._cache[0] - prices._TTL_SECONDS - 1, prices._cache[1])  # force expiry
    with patch.object(prices.requests, "get", side_effect=requests.ConnectionError("down")):
        # An hour-old rate still answers "thousands or crores?", which is the
        # question being asked. Only a cold start shows nothing.
        assert prices.inr_rate("ETH") == 265403


def test_one_batched_call_covers_every_asset():
    with patch.object(prices.requests, "get", return_value=_Resp(_PAYLOAD)) as get:
        prices.rates(); prices.rates(); prices.inr_rate("BTC")
    get.assert_called_once()
    assert get.call_args.kwargs["params"]["vs_currencies"] == "inr"


def test_feed_can_be_disabled_for_offline_demos():
    with patch.dict("os.environ", {"DISABLE_PRICE_FEED": "1"}):
        with patch.object(prices.requests, "get") as get:
            assert prices.rates() == {}
            get.assert_not_called()


def test_prices_stay_out_of_the_certified_record():
    """The evidence pack's SHA-256 must stay reproducible, so nothing that
    changes purely because time passed may enter build_record()."""
    import inspect
    from app.evidence import certificate
    assert "prices" not in inspect.getsource(certificate)
