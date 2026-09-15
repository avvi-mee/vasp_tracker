"""Deposit-address / sweep detection.

Uses synthetic transaction lists on purpose: the point is to pin down the
decision boundary between "pass-through funnel" and "ordinary wallet", and a
live address can drift across that boundary between test runs.

Run: python -m pytest tests/test_sweep.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.sweep import classify_deposit_address, DEPOSIT_THRESHOLD
from app.graph.trace import trace_to_nearest_entity

DEPOSIT = "0x1111111111111111111111111111111111111111"
HOT_WALLET = "0x2222222222222222222222222222222222222222"
VICTIM_A = "0x3333333333333333333333333333333333333333"
VICTIM_B = "0x4444444444444444444444444444444444444444"
ELSEWHERE = "0x5555555555555555555555555555555555555555"

DAY = 86400


def tx(frm, to, value, ts, h="0xhash"):
    return {"tx_hash": h, "block_number": 1, "timestamp": ts,
            "from_addr": frm, "to_addr": to, "value_wei": value, "asset_type": "ETH"}


def test_classic_sweep_is_detected():
    """Two funders in, everything out to one exchange address, swept quickly."""
    txs = [
        tx(VICTIM_A, DEPOSIT, 10_000, 1_700_000_000),
        tx(VICTIM_B, DEPOSIT, 5_000, 1_700_000_100),
        tx(DEPOSIT, HOT_WALLET, 15_000, 1_700_000_400),
    ]
    ev = classify_deposit_address(DEPOSIT, txs, HOT_WALLET)

    assert ev.is_deposit_address
    assert ev.confidence >= DEPOSIT_THRESHOLD
    assert ev.forwarded_ratio == 1.0
    assert ev.destination_share == 1.0
    assert ev.distinct_funders == 2
    assert ev.sweep_count == 1
    assert ev.median_hold_seconds == 300  # swept 5 min after the last deposit


def test_ordinary_wallet_is_not_flagged():
    """Receives, spends most of it in several directions, keeps a balance.
    This is the false-positive case that matters — wrongly naming someone's
    personal wallet as an exchange deposit address sends police to the wrong
    door."""
    txs = [
        tx(VICTIM_A, DEPOSIT, 10_000, 1_700_000_000),
        tx(DEPOSIT, ELSEWHERE, 3_000, 1_700_100_000),
        tx(DEPOSIT, HOT_WALLET, 2_000, 1_700_200_000),
    ]
    ev = classify_deposit_address(DEPOSIT, txs, HOT_WALLET)

    assert not ev.is_deposit_address
    assert ev.forwarded_ratio == 0.2
    assert ev.destination_share == 0.4
    assert ev.caveats  # and it says why


def test_partial_forward_to_single_destination_is_borderline_not_confirmed():
    """Sends only to the exchange, but keeps most of the money. Single
    destination alone must not be enough to confirm."""
    txs = [
        tx(VICTIM_A, DEPOSIT, 10_000, 1_700_000_000),
        tx(DEPOSIT, HOT_WALLET, 1_000, 1_700_000_500),
    ]
    ev = classify_deposit_address(DEPOSIT, txs, HOT_WALLET)

    assert ev.destination_share == 1.0
    assert ev.forwarded_ratio == 0.1
    assert not ev.is_deposit_address


def test_base58_addresses_are_not_lowercased():
    """Tron addresses are case-sensitive — a lowercasing bug here would make
    every Tron deposit address silently fail to match."""
    tron_deposit = "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"
    tron_hot = "TWd4WrZ9wn84f5x1hZhL4DHvk738ns5jwb"
    txs = [
        tx(VICTIM_A, tron_deposit, 10_000, 1_700_000_000),
        tx(tron_deposit, tron_hot, 10_000, 1_700_000_300),
    ]
    ev = classify_deposit_address(tron_deposit, txs, tron_hot)

    assert ev.address == tron_deposit  # unchanged, not lowercased
    assert ev.vasp_address == tron_hot
    assert ev.forwarded_ratio == 1.0


def test_trace_attaches_deposit_evidence_at_the_hop_before_the_exchange():
    """End-to-end: the trace should hand back the deposit address, not just
    the exchange name."""
    labels = {("ETH", HOT_WALLET): {"label": "Binance: Hot Wallet",
                                     "category": "exchange", "source": "test",
                                     "is_cluster_definer": True}}
    ledger = {
        VICTIM_A: [tx(VICTIM_A, DEPOSIT, 10_000, 1_700_000_000)],
        DEPOSIT: [
            tx(VICTIM_A, DEPOSIT, 10_000, 1_700_000_000),
            tx(VICTIM_B, DEPOSIT, 5_000, 1_700_000_100),
            tx(DEPOSIT, HOT_WALLET, 15_000, 1_700_000_400),
        ],
    }
    result = trace_to_nearest_entity(
        seed_address=VICTIM_A, currency="ETH",
        fetch_transactions_fn=lambda a: ledger.get(a, []),
        labels_lookup=labels, mixers_lookup={}, max_hops=4,
    )

    assert result.entity_type == "exchange"
    assert result.label == "Binance: Hot Wallet"
    assert result.deposit is not None
    assert result.deposit.address == DEPOSIT
    assert result.deposit.is_deposit_address
    assert DEPOSIT in result.deposit.summary()


def test_no_deposit_evidence_when_exchange_is_the_seed_itself():
    """Hop 0 — there is no preceding address to analyse."""
    labels = {("ETH", HOT_WALLET): {"label": "Binance: Hot Wallet",
                                     "category": "exchange", "source": "test"}}
    result = trace_to_nearest_entity(
        seed_address=HOT_WALLET, currency="ETH",
        fetch_transactions_fn=lambda a: [],
        labels_lookup=labels, mixers_lookup={}, max_hops=4,
    )

    assert result.hop_count == 0
    assert result.deposit is None
