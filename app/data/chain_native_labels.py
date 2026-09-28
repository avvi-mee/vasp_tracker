"""Entity labels the block explorer itself already published, harvested out
of the transaction responses this project was already fetching.

Why this exists: a real Tron scam address
(TNnrfcBk7WXJtKFHC76m7V8oAP9V98k5P5, from an actual case) returned
"unattributed — hop limit reached with no match" from this tool, while the
same Tronscan API response we fetched to produce that answer contained, in
plain text, `to_address_tag: {"to_address_tag": "Binance-Hot 7"}` on 18
separate transfers. The nearest VASP was one hop away, named, in data we had
in memory and parsed past. GraphSense TagPacks (app/data/tagpacks.py) is a
static, community-curated dataset that simply does not cover most live
addresses; the explorer's own tags do, because the explorer watches the chain.

These are a weaker class of evidence than our own curated datasets and are
recorded as such:

  Indian VASP dataset   0.75-0.95, checksum-validated, per-address provenance
  GraphSense TagPacks   community-curated, versioned, citable
  explorer tags (here)  0.60, third-party convenience label, unversioned

So they are never cluster-definers, never override a curated label (the
caller layers them *under* the curated lookup), and the Coverage &
Methodology page must state that a match sourced here is a lead to verify,
not a finished attribution. Tronscan's tags are displayed publicly without
the reuse restriction Etherscan places on its nametags; check per explorer
before harvesting a new chain this way.
"""
from app.addresses import normalize_address

# Placeholders explorers return where a real name would go. "(移除标签)" is
# literally "tag removed" and appears in live Tronscan responses. Lives here,
# not in the Tron client, so every future tag-harvesting client shares it.
JUNK_TAGS = {"(移除标签)", "(remove tag)", "-", "--", "null", "none", "unknown", "n/a"}

SOURCE = "Tronscan address tag"
# Deliberately below the Indian dataset's weakest tier (0.75, "single-source"):
# an explorer tag is uncorroborated and can go stale without notice.
CONFIDENCE = 0.60

# Substring -> category, checked in order, case-insensitively against the tag
# text. Names are the ones that actually appear in live Tronscan responses
# for Indian fraud addresses, plus the majors they route through.
CATEGORY_KEYWORDS: tuple[tuple[tuple[str, ...], str], ...] = (
    # Checked first: these are contracts and infrastructure, not entities to
    # attribute. They are dropped entirely below rather than labeled, so a
    # trace walks past the USDT contract instead of "reaching" it.
    (("token", "contract", "trc20", "trc10"), "token_contract"),
    # Before the exchange names: "upbit hack" / "Poloniex hack" name the
    # victim exchange, but the address belongs to the thief.
    (("phish", "scam", "fake", "hack", "exploit", "fraud", "ransom", "stolen", "heist"), "illicit"),
    (("tornado", "mixer", "mixing", "tumbler", "blender"), "mixer"),
    (("bridge",), "bridge"),
    (("binance", "okx", "okex", "huobi", "htx", "bybit", "gate", "mexc", "mxc",
      "kucoin", "poloniex", "bitfinex", "kraken", "coinbase", "bitget", "bitmart",
      "whitebit", "coinex", "crypto.com", "upbit", "bithumb", "bitkub", "bitstamp",
      "gemini", "bitrue", "lbank", "phemex", "bingx", "probit", "latoken",
      "digifinex", "xt.com", "wazirx", "coindcx", "zebpay", "bitso", "paxful"),
     "exchange"),
    (("cobo", "ceffu", "fireblocks", "bitgo", "copper", "custody", "custodian"), "custodian"),
    (("tether", "circle", "paxos", "treasury"), "issuer"),
    (("justlend", "justswap", "sunswap", "sun.io", "just ", "swap", "dex"), "defi"),
    (("foundation", "dao", "labs"), "organization"),
    (("casino", "bet", "dice", "lottery", "gambl"), "gambling"),
)

# Not attributions — a token contract is not a party to a transaction in the
# sense a disclosure request cares about.
NON_ENTITY_CATEGORIES = {"token_contract"}


def is_junk(tag: str | None) -> bool:
    return not tag or not tag.strip() or tag.strip().lower() in JUNK_TAGS


def categorize(tag: str) -> str:
    """Map an explorer tag to the same category vocabulary risk.py and
    exposure.py already speak. Falls back to "service": we know the address
    belongs to *something* named, which is genuinely more than nothing, but
    claiming it is an exchange would be inventing evidence."""
    lowered = tag.lower()
    for keywords, category in CATEGORY_KEYWORDS:
        if any(k in lowered for k in keywords):
            return category
    return "service"


def entity_category(rec: dict) -> str:
    """The category of a label record from any source. GraphSense leaves
    `category` empty on 81,815 labels — ransomware, sextortion, hacks,
    "defi fraud" — and marks them with `abuse` instead; defaulting those to
    "exchange" turned ransomware wallets into disclosure targets."""
    if rec.get("category"):
        return rec["category"]
    if rec.get("abuse"):
        return "illicit"
    return categorize(rec.get("label") or "")


def harvest(txs: list[dict], currency: str) -> dict[tuple[str, str], dict]:
    """Pull {(currency, address): label_record} out of normalized transactions.

    Same shape as app/data/tagpacks.load_labels() and
    app/data/indian_vasps.load_indian_vasp_labels(), so the existing
    lookup_address() path consumes it with no change to the search algorithm.
    Chain clients that publish no tags simply contribute nothing.
    """
    currency = currency.upper()
    labels: dict[tuple[str, str], dict] = {}
    for tx in txs:
        for addr_field, label_field in (("from_addr", "from_label"), ("to_addr", "to_label")):
            tag = tx.get(label_field)
            if is_junk(tag):
                continue
            tag = tag.strip()
            category = categorize(tag)
            if category in NON_ENTITY_CATEGORIES:
                continue
            key = (currency, normalize_address(tx[addr_field]))
            labels.setdefault(key, {
                "label": tag,
                "category": category,
                "source": SOURCE,
                "confidence": CONFIDENCE,
                "is_cluster_definer": False,
            })
    return labels


def harvest_risk_flags(txs: list[dict]) -> dict[str, bool]:
    """Addresses the explorer itself flags as risky. Corroboration only — it
    is an unexplained third-party boolean, so it may raise attention but must
    never be the sole basis for a verdict (see app/graph/risk.py)."""
    flags: dict[str, bool] = {}
    for tx in txs:
        for addr_field, risk_field in (("from_addr", "from_risk"), ("to_addr", "to_risk")):
            risk = tx.get(risk_field)
            if risk:  # None (not assessed) and False (assessed clean) both skipped
                flags[normalize_address(tx[addr_field])] = True
    return flags


def demo() -> None:
    txs = [
        {"from_addr": "TSeed", "to_addr": "TDep", "from_label": None,
         "to_label": "Binance-Hot 7", "to_risk": True},
        {"from_addr": "TUsdt", "to_addr": "TSeed", "from_label": "USDT Token", "to_label": None},
        {"from_addr": "TBad", "to_addr": "TSeed", "from_label": "(移除标签)", "to_label": None},
    ]
    labels = harvest(txs, "trx")
    assert labels[("TRX", "TDep")]["label"] == "Binance-Hot 7"
    assert labels[("TRX", "TDep")]["category"] == "exchange"
    assert labels[("TRX", "TDep")]["confidence"] < 0.75  # below the Indian dataset's weakest tier
    assert ("TRX", "TUsdt") not in labels, "token contracts are not entities"
    assert ("TRX", "TBad") not in labels, "cleaning happens in the client, but junk must not survive"
    assert harvest_risk_flags(txs) == {"TDep": True}
    assert categorize("Cobo Custody") == "custodian"
    assert categorize("Nile Testnet Faucet") == "service"
    print("chain_native_labels self-check OK")


if __name__ == "__main__":
    demo()
