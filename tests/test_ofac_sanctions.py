"""OFAC SDN ingestion — reads the real vendored list (no network), so this
also catches the repo going missing/empty rather than a live network flake.
Run: python -m pytest tests/test_ofac_sanctions.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.known_illicit import check_illicit
from app.data.ofac_sanctions import load_ofac_addresses

OFAC_ONLY_ADDRESS = "0x038989cbb1710c72b9920dc4fa529158f463e72c"  # not in the hand-curated list
HAND_CURATED_AND_OFAC_ADDRESS = "0x098b716b8aaf21512996dc57eb0615e2383e2f96"  # Ronin exploiter — in both


def test_ofac_list_loads_hundreds_of_addresses():
    loaded = load_ofac_addresses()
    assert len(loaded) > 500  # ETH+BTC+TRX+SOL+BSC combined, not the old 2-address list


def test_check_illicit_catches_an_ofac_only_address():
    hit = check_illicit(OFAC_ONLY_ADDRESS)
    assert hit is not None
    assert "OFAC" in hit["label"]


def test_hand_curated_label_wins_on_collision():
    hit = check_illicit(HAND_CURATED_AND_OFAC_ADDRESS)
    assert hit["label"] == "Ronin Bridge Exploiter (Lazarus Group)"


def test_unlisted_address_is_not_flagged():
    assert check_illicit("0x0000000000000000000000000000000000dEaD") is None
