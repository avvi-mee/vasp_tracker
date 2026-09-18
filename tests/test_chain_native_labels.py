"""Explorer-published entity tags — harvesting, categorising, and the two
places they must NOT win: over a curated label, and over the truth about what
they are worth.

The bug these exist to prevent: app/api_clients/tronscan.py fetched a response
containing `to_address_tag: {"to_address_tag": "Binance-Hot 7"}` on 18
transfers of a real scam address and parsed straight past it, so the tool
reported "unattributed — hop limit reached" about a wallet whose nearest VASP
was named, one hop away, in data already in memory.

Run: python -m pytest tests/test_chain_native_labels.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx

from app.api_clients.tronscan import _clean_tag, _native, _risk_of, _trc20
from app.data.chain_native_labels import CONFIDENCE, categorize, harvest, harvest_risk_flags, is_junk
from app.data.indian_vasps import CONFIDENCE_SCORE
from app.graph.trace import trace_to_nearest_entity


# --- parsing the two shapes Tronscan actually returns (captured live) -------

def test_trc20_tag_is_a_dict_whose_name_key_may_be_missing():
    assert _clean_tag({"to_address_tag_logo": "", "to_address_tag": "Binance-Hot 7"}) == "Binance-Hot 7"
    assert _clean_tag({"from_address_tag_logo": ""}) is None  # logo only, no name


def test_native_tag_is_a_plain_string_or_null():
    assert _clean_tag("USDT Token") == "USDT Token"
    assert _clean_tag(None) is None


def test_tag_removed_placeholder_is_not_a_label():
    """Live responses carry "(移除标签)" — Chinese for "tag removed" — in the
    field where a name belongs. Treating it as an entity name would put
    Chinese boilerplate in a police report."""
    assert _clean_tag("(移除标签)") is None
    assert is_junk("(移除标签)")
    assert is_junk("  ")
    assert not is_junk("Bybit")


def test_trc20_rows_carry_their_tags_and_risk_flags_through():
    rows = [{
        "transaction_id": "0xabc", "from_address": "TFrom", "to_address": "TTo",
        "quant": "1000000", "block": 1, "block_ts": 1700000000000,
        "tokenInfo": {"tokenAbbr": "USDT", "tokenDecimal": 6, "tokenId": "TR7N"},
        "from_address_tag": {"from_address_tag": "Bybit", "from_address_tag_logo": ""},
        "to_address_tag": {"to_address_tag_logo": ""},
    }]
    tx = _trc20(rows, {"TFrom": {"risk": True}, "TTo": {"risk": False}})[0]
    assert tx["from_label"] == "Bybit"
    assert tx["to_label"] is None
    assert tx["from_risk"] is True
    assert tx["to_risk"] is False
    assert tx["timestamp"] == 1700000000  # still normalized out of milliseconds


def test_native_rows_carry_their_tags_through():
    rows = [{"hash": "0xabc", "ownerAddress": "TOwner", "toAddress": "TDest", "amount": 5,
             "block": 1, "timestamp": 1700000000000,
             "ownerAddressTag": None, "toAddressTag": "Binance-Hot 7"}]
    tx = _native(rows, {})[0]
    assert tx["to_label"] == "Binance-Hot 7"
    assert tx["from_label"] is None


def test_unassessed_risk_is_none_not_false():
    """"Tronscan did not assess this address" and "Tronscan assessed it and
    found nothing" are different claims. A police tool must not turn silence
    into a clean bill of health."""
    assert _risk_of({}, "TUnknown") is None
    assert _risk_of({"TA": {"risk": False}}, "TA") is False
    assert _risk_of({"TA": {"risk": True}}, "TA") is True


# --- categorising a tag ----------------------------------------------------

def test_exchange_names_are_recognised_including_numbered_hot_wallets():
    for tag in ("Binance-Hot 7", "OKX Hot Wallet 8", "Bybit", "Gate", "MXC", "Kraken 4"):
        assert categorize(tag) == "exchange", tag


def test_custodians_are_not_called_exchanges():
    assert categorize("Cobo Custody") == "custodian"


def test_an_unrecognised_name_is_not_guessed_into_an_exchange():
    """Claiming an unknown tag is an exchange would invent evidence — and
    would also wrongly trigger deposit-address analysis downstream."""
    assert categorize("Nile Testnet Faucet") == "service"


# --- harvesting into the shared lookup shape -------------------------------

def _tx(frm, to, from_label=None, to_label=None, **extra):
    return {"from_addr": frm, "to_addr": to, "from_label": from_label,
            "to_label": to_label, **extra}


def test_harvest_produces_the_same_record_shape_the_curated_loaders_do():
    labels = harvest([_tx("TSeed", "TDep", to_label="Binance-Hot 7")], "trx")
    record = labels[("TRX", "TDep")]
    assert set(record) == {"label", "category", "source", "confidence", "is_cluster_definer"}
    assert record["label"] == "Binance-Hot 7"
    assert record["category"] == "exchange"
    assert record["source"] == "Tronscan address tag"
    assert record["is_cluster_definer"] is False


def test_an_explorer_tag_is_rated_below_every_curated_tier():
    """Provenance has to survive into the number, or the certificate lies
    about how well corroborated the attribution is."""
    assert CONFIDENCE < min(CONFIDENCE_SCORE.values())


def test_token_contracts_are_not_harvested_as_entities():
    """The USDT contract is tagged "USDT Token" and is on the path of almost
    every Tron trace. Treating it as an entity would end traces at a contract
    instead of at a VASP."""
    assert harvest([_tx("TUsdt", "TSeed", from_label="USDT Token")], "TRX") == {}


def test_junk_tags_never_survive_harvesting_either():
    """Cleaning belongs in the client, but this is the shared choke point —
    a future chain client that forgets to clean must not poison the lookup."""
    assert harvest([_tx("TA", "TB", to_label="(移除标签)")], "TRX") == {}


def test_risk_flags_are_only_collected_when_actually_flagged():
    txs = [_tx("TA", "TB", from_risk=True, to_risk=False),
           _tx("TC", "TD")]  # no risk keys at all
    assert harvest_risk_flags(txs) == {"TA": True}


# --- the whole point: the trace now resolves --------------------------------

def test_a_trace_resolves_from_tags_found_in_its_own_fetched_transactions():
    """End to end, with no curated label available at all — exactly the real
    scam-address case, reduced to a fixture."""
    txs = [{"tx_hash": "0x1", "from_addr": "TSeed", "to_addr": "TDep", "value_wei": 1_000_000,
            "timestamp": 100, "decimals": 6, "asset_symbol": "USDT", "asset_contract": "TR7N",
            "block_number": 1, "from_label": None, "to_label": "Binance-Hot 7"}]

    result = trace_to_nearest_entity(
        "TSeed", "TRX", lambda a: txs if a == "TSeed" else [],
        labels_lookup={}, mixers_lookup={}, max_hops=4)

    assert result.label == "Binance-Hot 7"
    assert result.entity_type == "exchange"
    assert result.hop_count == 1
    assert result.source == "Tronscan address tag"
    assert result.confidence > 0  # not the falsy 0.0 that rendered as "—"


def test_a_curated_label_still_beats_an_explorer_tag_on_the_same_address():
    txs = [{"tx_hash": "0x1", "from_addr": "TSeed", "to_addr": "TDep", "value_wei": 1_000_000,
            "timestamp": 100, "decimals": 6, "asset_symbol": "USDT", "asset_contract": "TR7N",
            "block_number": 1, "from_label": None, "to_label": "Binance-Hot 7"}]
    curated = {("TRX", "TDep"): {"label": "WazirX (curated)", "category": "exchange",
                                 "source": "VASP Trace Indian VASP dataset", "confidence": 0.9,
                                 "is_cluster_definer": True}}

    result = trace_to_nearest_entity(
        "TSeed", "TRX", lambda a: txs if a == "TSeed" else [],
        labels_lookup=curated, mixers_lookup={}, max_hops=4)

    assert result.label == "WazirX (curated)"


def test_explorer_risk_flags_reach_the_trace_result():
    txs = [{"tx_hash": "0x1", "from_addr": "TSeed", "to_addr": "TDep", "value_wei": 1_000_000,
            "timestamp": 100, "decimals": 6, "asset_symbol": "USDT", "asset_contract": "TR7N",
            "block_number": 1, "to_risk": True}]

    result = trace_to_nearest_entity(
        "TSeed", "TRX", lambda a: txs if a == "TSeed" else [],
        labels_lookup={}, mixers_lookup={}, max_hops=2)

    assert result.explorer_flagged == ["TDep"]
    assert isinstance(result.graph, nx.DiGraph)
