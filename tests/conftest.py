"""Keeps the whole suite offline.

Every test in this directory mocks its own HTTP, which held as long as the
only network calls lived in app/api_clients/* and each test file patched the
client it exercised. Two later additions broke that assumption by calling out
from inside the shared /v1/trace path rather than from a chain client:

  app/prices.py                    CoinGecko, for rupee display
  app/api_clients/chainalysis.py   the sanctions oracle over a public RPC,
                                   and the Sanctions Screening API

Both fail soft, so nothing goes red when they reach the internet — the suite
just quietly gets slower, flaky on a train, and dependent on two third
parties having a good day. Worse, it would then be asserting against live
sanctions data that can change under it.

So they are switched off here for every test, centrally, rather than left for
each new test file to remember. A test that actually wants to exercise either
one patches it directly (see test_prices.py and test_chainalysis*.py), which
still works: those patch the module's own `requests`, not this.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app.api_clients import chainalysis
from app.cache import clear_cache


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    # app/prices.py checks this on every call and returns {} — the same
    # behaviour the UI already handles when the feed is unreachable.
    monkeypatch.setenv("DISABLE_PRICE_FEED", "1")

    # The oracle has no such switch, so cut it at the chain map: an empty map
    # means supports() is False for every currency, is_sanctioned() returns
    # None before building a request, and screen_addresses() returns None —
    # i.e. exactly the "not consulted" state, which is the honest default for
    # a test run and is itself covered by test_chainalysis_oracle.py.
    monkeypatch.setattr(chainalysis, "_CHAINS", {})

    # And the Screening API is gated on a key, so removing it makes every
    # call a no-op. This matters more than it looks: app/api/main.py calls
    # load_dotenv() at import, so a developer with a real CHAINALYSIS_API_KEY
    # in their .env would otherwise have the whole suite screening live
    # against Chainalysis — burning their quota and asserting against
    # sanctions data that can change underneath the tests.
    monkeypatch.delenv("CHAINALYSIS_API_KEY", raising=False)

    # cached_fetch is process-global and now holds oracle verdicts as well as
    # transaction lists; without this, one test's fixture can answer another's
    # lookup.
    clear_cache()
    yield
    clear_cache()


def pytest_configure(config):
    config.addinivalue_line("markers", "live: hits a real third-party API; excluded from the default run")
