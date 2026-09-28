"""Tiny in-memory TTL cache for chain-client fetches.

The same address is often fetched more than once within a short window in
normal use — a trace's own seed address vs. its receiving/sending exposure
re-fetch (app/api/main.py's _seed_exposure_json), a certificate regenerating
the same trace moments after /v1/trace already ran it, a watchlist re-check
right after adding an address. Each of those redundant fetches is a real
network round-trip against a rate-limited free-tier API for data already
fetched seconds ago.

A real distributed cache (Redis) is already a documented fast-follow for
scaling this beyond one process — this is the free, zero-dependency version
that helps today, not a replacement for it.
"""
import threading
import time
from typing import Callable, TypeVar

_TTL_SECONDS = 60
_lock = threading.Lock()
_cache: dict[tuple, tuple[float, object]] = {}
_T = TypeVar("_T")
# ponytail: no eviction/size cap — fine for a demo process that runs for a
# session, not for a server left running for days. Add an LRU cap or move to
# Redis before that's a real deployment concern.


def cached_fetch(key: tuple, fetch_fn: Callable[[], _T]) -> _T:
    """Generic in value type: chain clients cache tx lists, the Chainalysis
    oracle client caches a bool per address. Same TTL, same key discipline."""
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit is not None and now - hit[0] < _TTL_SECONDS:
            return hit[1]
    result = fetch_fn()
    with _lock:
        _cache[key] = (now, result)
    return result


def clear_cache() -> None:
    """For tests — avoids one test's cached fetch leaking into another's assertions."""
    with _lock:
        _cache.clear()
