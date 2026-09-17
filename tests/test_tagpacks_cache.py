"""TagPack disk cache -- parsing the real vendored dataset took 69s measured
live; this pins the fingerprint-based cache that fixes it, using a tiny
synthetic dataset instead of the real 500K-tag one (fast, deterministic).
Run: python -m pytest tests/test_tagpacks_cache.py -v
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml as yaml_module

from app.data.tagpacks import load_labels

TAGPACK_V1 = """
label: Test Exchange
currency: ETH
category: exchange
source: unit-test
tags:
  - address: "0xaaa"
"""

TAGPACK_V2 = """
label: Test Exchange
currency: ETH
category: exchange
source: unit-test
tags:
  - address: "0xaaa"
  - address: "0xbbb"
"""


def _write(tmp_path, content):
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir(exist_ok=True)
    (packs_dir / "test.yaml").write_text(content, encoding="utf-8")
    return packs_dir


def test_cache_file_is_created_and_reused(tmp_path, monkeypatch):
    packs_dir = _write(tmp_path, TAGPACK_V1)

    calls = []
    real_load = yaml_module.load

    def counting_load(*a, **kw):
        calls.append(1)
        return real_load(*a, **kw)

    monkeypatch.setattr(yaml_module, "load", counting_load)

    first = load_labels(packs_dir)
    assert ("ETH", "0xaaa") in first
    assert len(calls) == 1  # cold: parsed once
    assert (packs_dir.parent / ".labels_cache.pkl").exists()

    second = load_labels(packs_dir)
    assert second == first
    assert len(calls) == 1  # warm: served from cache, not re-parsed


def test_changing_the_dataset_invalidates_the_cache(tmp_path):
    packs_dir = _write(tmp_path, TAGPACK_V1)
    first = load_labels(packs_dir)
    assert ("ETH", "0xbbb") not in first

    time.sleep(0.05)  # ensure a strictly later mtime on filesystems with coarse resolution
    _write(tmp_path, TAGPACK_V2)

    second = load_labels(packs_dir)
    assert ("ETH", "0xbbb") in second  # new tag picked up -- cache was rebuilt, not stale


def test_use_cache_false_bypasses_the_cache_entirely(tmp_path):
    packs_dir = _write(tmp_path, TAGPACK_V1)
    load_labels(packs_dir, use_cache=True)
    cache_file = packs_dir.parent / ".labels_cache.pkl"
    assert cache_file.exists()

    # Corrupt the cache; use_cache=False must not even look at it.
    cache_file.write_bytes(b"not a valid pickle")
    result = load_labels(packs_dir, use_cache=False)
    assert ("ETH", "0xaaa") in result
