"""Token-transfer parsing -- the path that makes USDT visible.

A tracer that reads only native transfers looks at an empty wallet while the
fraud proceeds sit next to it in USDT. These tests pin the two things that
silently break that: the token's own decimal scale, and the asset identity
used to compare values across assets.

Run: python -m pytest tests/test_token_transfers.py -v
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api_clients.etherscan import fetch_transactions as fetch_evm
from app.api_clients.tronscan import fetch_transactions as fetch_tron
from app.assets import amount, asset_key, dominant_asset

USDT_ERC20 = "0xdAC17F958D2ee523a2206206994597C13D831ec7"

ERC20_ROW = {
    "hash": "0xtoken", "blockNumber": "200", "timeStamp": "1700000500",
    "from": "0xAAA", "to": "0xBBB", "value": "50000000000",  # 50,000 USDT at 6 decimals
    "tokenSymbol": "USDT", "tokenDecimal": "6", "contractAddress": USDT_ERC20,
}
NATIVE_ROW = {
    "hash": "0xnative", "blockNumber": "100", "timeStamp": "1700000000",
    "from": "0xAAA", "to": "0xCCC", "value": "100000000000000000",  # 0.1 ETH
}


def _resp(rows):
    r = MagicMock()
    r.json.return_value = {"status": "1", "message": "OK", "result": rows}
    r.raise_for_status.return_value = None
    return r


def _tx(symbol, contract, whole, decimals):
    return {"tx_hash": "0x1", "from_addr": "0xa", "to_addr": "0xb", "value_wei": whole * 10**decimals,
            "asset_symbol": symbol, "asset_contract": contract, "decimals": decimals}


def test_worthless_token_flood_cannot_steer_the_trace():
    """REVIEW.md defect 7: send a wallet a million units of a junk token and
    decimal-unit ranking followed the junk instead of the real ETH."""
    txs = [_tx("ETH", "", 2, 18), _tx("FREE", "0xjunk", 1_000_000, 18)]
    assert dominant_asset(txs) == ("ETH", "")


def test_fake_usdt_reusing_the_symbol_loses_to_the_real_contract():
    txs = [_tx("USDT", USDT_ERC20.lower(), 5_000, 6), _tx("USDT", "0xfake", 9_000_000, 6)]
    assert dominant_asset(txs) == ("USDT", USDT_ERC20.lower())


def test_unlisted_token_still_followed_when_nothing_trusted_moved():
    txs = [_tx("XYZ", "0xnew", 100, 18)]
    assert dominant_asset(txs) == ("XYZ", "0xnew")


@patch("app.api_clients.etherscan.requests.get")
def test_erc20_transfer_keeps_its_own_decimal_scale(mock_get):
    """USDT is 6 decimals. Reading it as 18 makes 50,000 USDT look like dust."""
    mock_get.side_effect = lambda *a, **kw: _resp(
        [ERC20_ROW] if kw["params"]["action"] == "tokentx" else []
    )
    txs = fetch_evm("0xaaa", api_key="fake")

    assert len(txs) == 1
    assert txs[0]["asset_symbol"] == "USDT"
    assert txs[0]["decimals"] == 6
    assert txs[0]["asset_contract"] == USDT_ERC20.lower()
    assert amount(txs[0]) == 50_000.0


@patch("app.api_clients.etherscan.requests.get")
def test_dominant_asset_is_the_token_not_the_native_dust(mock_get):
    """The whole point: 50,000 USDT outranks 0.1 ETH, even though the raw
    integer for 0.1 ETH is larger."""
    def route(*a, **kw):
        action = kw["params"]["action"]
        return _resp({"txlist": [NATIVE_ROW], "tokentx": [ERC20_ROW]}.get(action, []))
    mock_get.side_effect = route

    txs = fetch_evm("0xaaa", api_key="fake")
    assert len(txs) == 2
    assert txs[0]["value_wei"] > txs[1]["value_wei"]   # raw integers say ETH wins
    assert dominant_asset(txs) == ("USDT", USDT_ERC20.lower())  # decimals say otherwise


@patch("app.api_clients.etherscan.requests.get")
def test_failed_transactions_are_dropped(mock_get):
    """A reverted tx moved nothing; counting it inflates sweep.py's ratios."""
    failed = {**NATIVE_ROW, "isError": "1"}
    mock_get.side_effect = lambda *a, **kw: _resp(
        [failed] if kw["params"]["action"] == "txlist" else []
    )
    assert fetch_evm("0xaaa", api_key="fake") == []


@patch("app.api_clients.tronscan.requests.get")
def test_trc20_usdt_on_tron_is_parsed(mock_get):
    """The single most important case for Indian investigations."""
    row = {
        "transaction_id": "0xtrc", "from_address": "TFrom", "to_address": "TTo",
        "quant": "226000000000", "block_ts": 1700000000000, "block": 55,  # Tronscan gives ms, not s
        "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "tokenInfo": {"tokenAbbr": "USDT", "tokenDecimal": 6},
    }
    resp = MagicMock()
    resp.json.return_value = {"token_transfers": [row]}
    resp.raise_for_status.return_value = None
    mock_get.return_value = resp

    txs = fetch_tron("TFrom", api_key="fake", max_records=1)
    trc20 = [t for t in txs if t["transfer_type"] == "token"]

    assert len(trc20) == 1
    assert trc20[0]["asset_symbol"] == "USDT"
    assert amount(trc20[0]) == 226_000.0
    # Base58 Tron addresses must not be lowercased -- that corrupts them.
    assert trc20[0]["from_addr"] == "TFrom"
    # Tronscan gives milliseconds; every other chain client gives seconds.
    # Left unconverted this silently corrupts anything sorting/rendering by
    # time across chains -- live-verified against a real address (13-digit
    # values), not assumed.
    assert trc20[0]["timestamp"] == 1700000000


def test_asset_key_separates_same_symbol_on_different_contracts():
    """Fake tokens reuse real symbols freely, so symbol alone cannot identify
    an asset."""
    real = {"asset_symbol": "USDT", "asset_contract": USDT_ERC20.lower()}
    fake = {"asset_symbol": "USDT", "asset_contract": "0xdeadbeef"}
    assert asset_key(real) != asset_key(fake)


def test_sweep_ratios_are_measured_within_one_asset():
    """The bug this pins: summing value_wei across assets.

    A deposit address receives 50,000 USDT (6 decimals) and forwards all of it
    to the exchange, but also holds a dust amount of ETH (18 decimals) it never
    moves. Summed as raw integers, the unswept ETH dwarfs the swept USDT and
    the forwarding ratio collapses to near zero — hiding a textbook deposit
    address.
    """
    from app.graph.sweep import classify_deposit_address

    DEP = "0x1111111111111111111111111111111111111111"
    HOT = "0x2222222222222222222222222222222222222222"
    SRC = "0x3333333333333333333333333333333333333333"

    def usdt(frm, to, whole, ts):
        return {"tx_hash": f"0x{ts}", "block_number": 1, "timestamp": ts,
                "from_addr": frm, "to_addr": to, "value_wei": whole * 10**6,
                "asset_symbol": "USDT", "asset_contract": USDT_ERC20.lower(),
                "decimals": 6, "transfer_type": "token"}

    txs = [
        usdt(SRC, DEP, 30_000, 1_700_000_000),
        usdt("0x4444444444444444444444444444444444444444", DEP, 20_000, 1_700_000_050),
        usdt(DEP, HOT, 50_000, 1_700_000_200),
        # Dust ETH that never moves — 0.5 ETH is 5e17 base units, ten billion
        # times the integer magnitude of 50,000 USDT.
        {"tx_hash": "0xdust", "block_number": 1, "timestamp": 1_700_000_010,
         "from_addr": SRC, "to_addr": DEP, "value_wei": 5 * 10**17,
         "asset_symbol": "ETH", "asset_contract": "", "decimals": 18,
         "transfer_type": "native"},
    ]

    ev = classify_deposit_address(DEP, txs, HOT)

    assert ev.asset == "USDT"
    assert ev.forwarded_ratio == 1.0, "all 50,000 USDT was forwarded"
    assert ev.is_deposit_address
