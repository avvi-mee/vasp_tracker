"""Smoke test for chain auto-detection — uses the same real addresses
we've already verified elsewhere in this project, not made-up examples.
Run: python -m pytest tests/test_chain_detect.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.chain_detect import detect_chain


def test_detects_evm_address_as_ethereum():
    chain, note = detect_chain("0xF835A0247b0063C04EF22006eBe57c5F11977Cc4")  # the DAO hack contract
    assert chain == "Ethereum"
    assert "Polygon" in note  # honestly notes the EVM ambiguity


def test_detects_tron_address():
    chain, note = detect_chain("TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9")  # real Binance Tron wallet
    assert chain == "Tron"


def test_detects_solana_address():
    chain, note = detect_chain("FxteHmLwG9nk1eL4pjNve3Eub2goGkkz6g6TbvdmW46a")  # real Bitfinex Solana wallet
    assert chain == "Solana"


def test_detects_bitcoin_legacy_address():
    chain, note = detect_chain("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")  # Bitcoin genesis address
    assert chain == "Bitcoin — coming soon"


def test_detects_bitcoin_bech32_address():
    chain, note = detect_chain("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
    assert chain == "Bitcoin — coming soon"


def test_unrecognized_format_returns_none():
    chain, note = detect_chain("not-a-real-address")
    assert chain is None


def test_empty_input_returns_none_quietly():
    chain, note = detect_chain("")
    assert chain is None
    assert note == ""
