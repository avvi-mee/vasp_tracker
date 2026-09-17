"""In-memory TTL fetch cache — no network needed.
Run: python -m pytest tests/test_cache.py -v
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.cache import cached_fetch, clear_cache


def test_second_call_within_ttl_does_not_refetch():
    clear_cache()
    calls = []

    def fetch():
        calls.append(1)
        return [{"tx_hash": "t1"}]

    first = cached_fetch(("ETH", "0xaaa"), fetch)
    second = cached_fetch(("ETH", "0xaaa"), fetch)

    assert first == second == [{"tx_hash": "t1"}]
    assert len(calls) == 1  # the second call was served from cache, not refetched


def test_different_keys_are_not_shared():
    clear_cache()
    calls = []

    def fetch_a():
        calls.append("a")
        return [{"tx_hash": "a"}]

    def fetch_b():
        calls.append("b")
        return [{"tx_hash": "b"}]

    cached_fetch(("ETH", "0xaaa"), fetch_a)
    cached_fetch(("ETH", "0xbbb"), fetch_b)

    assert calls == ["a", "b"]


def test_expired_entry_is_refetched(monkeypatch):
    clear_cache()
    import app.cache as cache_module

    calls = []

    def fetch():
        calls.append(1)
        return [{"tx_hash": str(len(calls))}]

    # Freeze "now" for the first call, then jump it forward past the TTL.
    t = [1000.0]
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: t[0])

    cached_fetch(("ETH", "0xaaa"), fetch)
    t[0] += cache_module._TTL_SECONDS + 1
    cached_fetch(("ETH", "0xaaa"), fetch)

    assert len(calls) == 2
