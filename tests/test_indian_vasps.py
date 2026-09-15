"""Indian VASP label dataset.

The dataset is the project's answer to its own biggest gap, so these tests
guard the things that would quietly break it: address corruption, chain
mis-registration, and losing to a stale GraphSense label on merge.

Run: python -m pytest tests/test_indian_vasps.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.indian_vasps import (
    load_indian_vasp_labels, merge_labels, coverage_summary, CONFIDENCE_SCORE,
)

# WazirX's own post-incident report names this as the drained multisig — the
# one address in the dataset the operator itself published.
WAZIRX_MULTISIG = "0x27fd43babfbe83a81d14665b1a6fb8030a60c9b4"
COINDCX_ETHERSCAN_TAGGED = "0x06051836ac6c5112b890f8b6ec78e33d1afeae7c"
# spellbook files this under "bitcoin"; the string is valid Tron Base58Check.
WAZIRX_TRON = "TPQqrAEnrWKTefTpgCNzXAGmJuvBqUrk1P"


def test_the_gap_this_dataset_exists_to_close_is_actually_closed():
    """GraphSense has zero WazirX and zero CoinDCX addresses. If this
    regresses, the tool is blind to India's two largest exchanges again."""
    coverage = coverage_summary()
    assert coverage.get("WazirX", 0) >= 10
    assert coverage.get("CoinDCX", 0) >= 50
    assert coverage.get("CoinSwitch", 0) >= 2


def test_wazirx_multisig_resolves_with_operator_confirmed_confidence():
    labels = load_indian_vasp_labels()
    record = labels[("ETH", WAZIRX_MULTISIG)]
    assert record["entity"] == "WazirX"
    assert record["category"] == "exchange"
    assert record["confidence"] == CONFIDENCE_SCORE["operator-confirmed"]
    assert record["corroboration"] == "operator-confirmed"


def test_single_source_labels_are_scored_lower_than_corroborated_ones():
    """Confidence has to reflect corroboration, or the certificate overstates
    what the evidence supports."""
    labels = load_indian_vasp_labels()
    assert (labels[("ETH", COINDCX_ETHERSCAN_TAGGED)]["confidence"]
            > CONFIDENCE_SCORE["single-source"])
    assert CONFIDENCE_SCORE["operator-confirmed"] > CONFIDENCE_SCORE["confirmed"]


def test_evm_addresses_resolve_on_every_evm_chain():
    """The same key controls the same address on Ethereum, Polygon and BNB."""
    labels = load_indian_vasp_labels()
    for currency in ("ETH", "MATIC", "BNB"):
        assert labels[(currency, WAZIRX_MULTISIG)]["entity"] == "WazirX"
    assert ("TRX", WAZIRX_MULTISIG) not in labels  # and not on non-EVM chains


def test_mislabelled_tron_address_registers_under_tron_not_bitcoin():
    """The upstream source filed two Tron addresses under bitcoin. Trusting
    that column would make them permanently unmatchable."""
    labels = load_indian_vasp_labels()
    assert ("TRX", WAZIRX_TRON) in labels
    assert ("BTC", WAZIRX_TRON) not in labels


def test_base58_addresses_keep_their_case():
    """Tron and Bitcoin addresses are case-sensitive. Lowercasing one on load
    corrupts it into an address that can never match."""
    labels = load_indian_vasp_labels()
    base58 = [addr for (cur, addr) in labels if cur in ("TRX", "BTC")]
    assert base58
    assert any(c.isupper() for addr in base58 for c in addr)
    assert WAZIRX_TRON in base58  # exact string, unmodified


def test_every_shipped_address_is_well_formed():
    """158 of 270 upstream rows were corrupt — truncations and sliced
    fragments. None of that may reach the shipped dataset."""
    for (currency, address) in load_indian_vasp_labels():
        assert address == address.strip()
        if address.startswith("0x"):
            assert len(address) == 42, f"malformed EVM address: {address}"
            assert address == address.lower()
            int(address, 16)  # raises if it is not hex
        elif address.startswith("bc1"):
            # bech32 — a different alphabet from base58: all-lowercase, and it
            # excludes 1/b/i/o rather than 0/O/I/l.
            assert 42 <= len(address) <= 62, f"suspicious length: {address}"
            assert address == address.lower()
            assert set(address[3:]) <= set("qpzry9x8gf2tvdw0s3jn54khce6mua7l")
        else:
            assert 25 <= len(address) <= 64, f"suspicious length: {address}"
            assert not (set(address) & set("0OIl")), f"not base58: {address}"


def test_indian_labels_win_over_graphsense_on_collision():
    stale = {("ETH", WAZIRX_MULTISIG): {"label": "Unknown", "category": "user",
                                         "source": "graphsense"}}
    merged = merge_labels(stale)
    assert merged[("ETH", WAZIRX_MULTISIG)]["entity"] == "WazirX"
    assert merged[("ETH", WAZIRX_MULTISIG)]["category"] == "exchange"


def test_merge_keeps_graphsense_labels_it_does_not_cover():
    binance = ("ETH", "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be")
    merged = merge_labels({binance: {"label": "Binance 1", "category": "exchange"}})
    assert merged[binance]["label"] == "Binance 1"
    assert merged[("ETH", WAZIRX_MULTISIG)]["entity"] == "WazirX"


def test_labels_match_the_graphsense_record_shape():
    """merge_labels only works if both sides produce the same shape — the
    trace code reads these fields without knowing which source they came
    from."""
    record = load_indian_vasp_labels()[("ETH", WAZIRX_MULTISIG)]
    assert {"label", "category", "source", "confidence", "is_cluster_definer"} <= set(record)
    assert isinstance(record["confidence"], float)
    assert isinstance(record["is_cluster_definer"], bool)


def test_missing_dataset_degrades_quietly():
    assert load_indian_vasp_labels(Path("no-such-file.csv")) == {}
