"""Direct vs. indirect exposure — no network calls.
Run: python -m pytest tests/test_exposure.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.exposure import compute_exposure
from app.graph.trace import Candidate


class _FakeResult:
    def __init__(self, candidates):
        self.candidates = candidates


def test_direct_exposure_is_the_immediate_hop():
    """Seed -> labeled exchange in one hop: exposure is direct, not indirect."""
    labels = {("ETH", "0xexch"): {"label": "Test Exchange", "category": "exchange"}}
    candidates = [Candidate(["0xseed", "0xexch"], 1, "exchange", "Test Exchange",
                            0.9, "test", None, None, None, 1.0)]
    result = _FakeResult(candidates)

    exposure = compute_exposure(result, "ETH", labels, mixers_lookup={})

    assert len(exposure.direct) == 1
    assert exposure.direct[0].category == "exchange"
    assert exposure.direct[0].value_share == 1.0
    assert exposure.indirect == []


def test_indirect_exposure_is_anything_beyond_hop_one():
    """Seed -> unlabeled -> labeled exchange: exposure is indirect."""
    labels = {("ETH", "0xexch"): {"label": "Test Exchange", "category": "exchange"}}
    candidates = [Candidate(["0xseed", "0xmiddle", "0xexch"], 2, "exchange", "Test Exchange",
                            0.9, "test", None, None, None, 1.0)]
    result = _FakeResult(candidates)

    exposure = compute_exposure(result, "ETH", labels, mixers_lookup={})

    assert exposure.direct == []
    assert len(exposure.indirect) == 1
    assert exposure.indirect[0].category == "exchange"


def test_one_path_can_expose_to_more_than_one_category():
    """Passes through a mixer at hop 1, then reaches a labeled exchange at
    hop 2 -- exposed to BOTH, direct AND indirect, from the same candidate.
    Percentages are not a single pie and don't need to sum to 100%."""
    labels = {("ETH", "0xexch"): {"label": "Test Exchange", "category": "exchange"}}
    mixers = {("ETH", "0xmixer"): "Test Mixer"}
    candidates = [Candidate(["0xseed", "0xmixer", "0xexch"], 2, "exchange", "Test Exchange",
                            0.9, "test", None, None, None, 1.0)]
    result = _FakeResult(candidates)

    exposure = compute_exposure(result, "ETH", labels, mixers_lookup=mixers)

    assert exposure.direct[0].category == "mixer"
    assert exposure.direct[0].value_share == 1.0
    assert exposure.indirect[0].category == "exchange"
    assert exposure.indirect[0].value_share == 1.0


def test_shared_history_sums_value_share_across_candidates():
    """Two candidates both pass through the same hop-1 exchange before
    diverging -- that exchange's direct exposure is the sum of both shares."""
    labels = {("ETH", "0xexch"): {"label": "Test Exchange", "category": "exchange"}}
    candidates = [
        Candidate(["0xseed", "0xexch", "0xa"], 2, "unknown", None, 0.0, None,
                 "dead end", None, None, 0.6),
        Candidate(["0xseed", "0xexch", "0xb"], 2, "unknown", None, 0.0, None,
                 "dead end", None, None, 0.4),
    ]
    result = _FakeResult(candidates)

    exposure = compute_exposure(result, "ETH", labels, mixers_lookup={})

    assert len(exposure.direct) == 1
    assert exposure.direct[0].value_share == 1.0  # 0.6 + 0.4


def test_graphsense_category_names_fold_into_the_same_buckets_as_risk_py():
    """A GraphSense "mixing_service"/"market" label must show up in the wheel
    under the same "mixer"/"market" bucket risk.py itself uses -- otherwise
    the wheel and the verdict could disagree about what happened."""
    labels = {("ETH", "0xblender"): {"label": "Blender.io", "category": "mixing_service"}}
    candidates = [Candidate(["0xseed", "0xblender"], 1, "mixing_service", "Blender.io",
                            0.9, "test", None, None, None, 1.0)]
    result = _FakeResult(candidates)

    exposure = compute_exposure(result, "ETH", labels, mixers_lookup={})

    assert exposure.direct[0].category == "mixer"
