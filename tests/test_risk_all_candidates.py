"""Risk must read every material branch, not only the primary path.

The bug (REVIEW.md defect 6): 60% of the funds reached Binance and 40% went
into a mixer. The primary path was Binance, so risk said "none".

Run: python -m pytest tests/test_risk_all_candidates.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

from app.graph.risk import assess
from app.graph.trace import Candidate, TraceResult

SANCTIONED = "0x098b716b8aaf21512996dc57eb0615e2383e2f96"  # Ronin exploiter — curated + OFAC


def _cand(path, entity_type, label, share):
    return Candidate(path=path, hop_count=len(path) - 1, entity_type=entity_type, label=label,
                     confidence=0.8, source="t", reason=None, asset=None, deposit=None, value_share=share)


def _result(side):
    primary = _cand(["0xseed", "0xbin"], "exchange", "Binance: Hot Wallet 20", 1 - side.value_share)
    return TraceResult(seed_address="0xseed", path=primary.path, graph=nx.DiGraph(), hop_count=1,
                       entity_type="exchange", label=primary.label, confidence=0.8,
                       candidates=[primary, side])


def test_material_branch_into_a_mixer_is_high_risk():
    risk = assess(_result(_cand(["0xseed", "0xmix"], "mixing_service", "Tornado Cash", 0.40)))
    assert risk.risk_level == "high"
    assert "40%" in risk.risk_reason
    assert "Tornado Cash" in risk.risk_reason


def test_dust_branch_into_a_mixer_does_not_escalate():
    risk = assess(_result(_cand(["0xseed", "0xmix"], "mixing_service", "Tornado Cash", 0.05)))
    assert risk.risk_level == "none"


def test_sanctioned_address_on_a_side_branch_is_high_risk():
    risk = assess(_result(_cand(["0xseed", SANCTIONED], "unknown", None, 0.30)))
    assert risk.risk_level == "high"
