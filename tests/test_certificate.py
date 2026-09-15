"""Section 63 BSA certificate generation.

The property that matters most is reproducibility: if the hash on the
certificate cannot be re-derived from the file, the certificate is worthless.

Run: python -m pytest tests/test_certificate.py -v
"""
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

from app.evidence.certificate import (
    build_evidence_pack, build_record, build_certificate_bundle, canonical_json,
    render_part_a, render_part_b, render_hash_report,
)
from app.graph.trace import TraceResult
from app.graph.risk import assess


def _result():
    g = nx.DiGraph()
    g.add_edge("0xaaa", "0xbbb", tx_hash="0xdeadbeef", value_wei=15_000_000_000_000_000_000)
    return TraceResult(
        seed_address="0xaaa", path=["0xaaa", "0xbbb"], graph=g, hop_count=1,
        entity_type="exchange", label="Binance 1", confidence=0.75,
        source="graphsense-tagpacks",
    )


def _pack(**kw):
    r = _result()
    return build_evidence_pack("ETH", r, assess(r), **kw)


def test_hash_is_reproducible_across_independent_runs():
    """Two separate builds over identical findings must agree — a defence
    expert re-running the trace has to reach the same digest."""
    assert _pack().record_sha256 == _pack().record_sha256


def test_certified_hash_actually_matches_the_certified_file():
    """The digest on the certificate must be the digest of the enclosed file.
    If these ever drift apart the whole exercise is theatre."""
    pack = _pack()
    recomputed = hashlib.sha256(pack.record_json.encode("utf-8")).hexdigest()
    assert pack.record_sha256 == recomputed
    assert len(pack.record_sha256) == 64


def test_record_carries_no_clock_reading():
    """A timestamp inside the payload would change the hash every run and
    make re-derivation impossible."""
    record = build_record("ETH", _result(), assess(_result()))
    blob = canonical_json(record)
    assert "generated_at" not in blob and "timestamp" not in blob


def test_canonical_json_is_order_independent():
    a = canonical_json({"z": 1, "a": {"y": 2, "b": 3}})
    b = canonical_json({"a": {"b": 3, "y": 2}, "z": 1})
    assert a == b


def test_record_preserves_large_values_without_float_rounding():
    """15 ETH in wei exceeds float precision — it must survive as a string."""
    record = build_record("ETH", _result(), assess(_result()))
    assert record["transactions_relied_upon"][0]["value_raw"] == "15000000000000000000"


def test_part_a_carries_the_s63_2_recitals_and_part_b_does_not():
    """The Schedule puts the lawful-control recital in Part A only."""
    pack = _pack()
    record = json.loads(pack.record_json)
    part_a, part_b = render_part_a(pack, record), render_part_b(pack, record)

    assert "lawful control" in part_a
    assert "lawful control" not in part_b
    assert "Owned" in part_a and "Owned" not in part_b


def test_both_parts_carry_the_hash_and_sha256_is_ticked():
    pack = _pack()
    record = json.loads(pack.record_json)
    for part in (render_part_a(pack, record), render_part_b(pack, record)):
        assert pack.record_sha256 in part
        assert "[X] SHA256" in part
        assert "[ ] MD5" in part and "[ ] SHA1" in part
        assert "[See section 63(4)(c)]" in part


def test_part_b_signature_block_asks_for_a_designation():
    """s.63(4) has the expert sign; the Schedule's Part B block differs from
    Part A's by carrying a designation."""
    pack = _pack()
    record = json.loads(pack.record_json)
    assert "(Name, designation and signature)" in render_part_b(pack, record)
    assert "(Name and signature)" in render_part_a(pack, record)


def test_nothing_is_pre_affirmed_on_the_operators_behalf():
    """The tool must never fill in a solemn affirmation. Name, parentage,
    address, place and signature stay blank for the human who swears to it."""
    pack = _pack()
    record = json.loads(pack.record_json)
    for part in (render_part_a(pack, record), render_part_b(pack, record)):
        assert "solemnly affirm" in part
        head = part.split("solemnly affirm")[0]
        assert "_____" in head          # name / parentage / address left blank
        assert "Place .. ____" in part  # place left blank


def test_blockchain_specifics_land_in_the_catch_all_field():
    """The Schedule has no address or ledger field, so they go under
    'any other relevant information'."""
    pack = _pack()
    record = json.loads(pack.record_json)
    part_a = render_part_a(pack, record)
    assert "Any other relevant information" in part_a
    assert "0xaaa" in part_a and "ETH" in part_a and "Binance 1" in part_a


def test_deposit_address_appears_on_the_certificate_when_found():
    from app.graph.sweep import DepositEvidence
    r = _result()
    r.deposit = DepositEvidence(
        address="0xbbb", vasp_address="0xccc", is_deposit_address=True,
        confidence=0.85, forwarded_ratio=1.0, destination_share=1.0,
        distinct_funders=2, sweep_count=1, median_hold_seconds=300,
    )
    pack = build_evidence_pack("ETH", r, assess(r))
    record = json.loads(pack.record_json)
    assert record["deposit_address_finding"]["is_deposit_address"] is True
    assert "Deposit address" in render_part_a(pack, record)


def test_hash_report_gives_verification_commands():
    report = render_hash_report(_pack())
    assert "certutil -hashfile" in report and "sha256sum" in report
    assert "SHA-256" in report


def test_hash_report_states_what_the_certificate_does_not_prove():
    """Overclaiming in a legal document is the failure mode to avoid."""
    flat = " ".join(render_hash_report(_pack()).split())  # prose is hard-wrapped
    assert "does not and cannot certify the blockchain itself" in flat
    assert "not that the attribution is correct" in flat


def test_bundle_contains_all_four_documents_and_verifies_end_to_end():
    pack, blob = build_certificate_bundle("ETH", _result(), assess(_result()),
                                          case_reference="FIR 123/2026")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = z.namelist()
        assert pack.record_filename in names
        assert {"CERTIFICATE-PART-A.txt", "CERTIFICATE-PART-B.txt",
                "HASH-REPORT.txt"} <= set(names)
        # the digest on the certificate matches the file actually shipped
        shipped = z.read(pack.record_filename)
        assert hashlib.sha256(shipped).hexdigest() == pack.record_sha256
        assert "FIR 123/2026" in z.read("CERTIFICATE-PART-A.txt").decode("utf-8")
