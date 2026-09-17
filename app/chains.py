"""Chain adapter registry — one definition shared by the Streamlit UI and the
FastAPI service, so enabling a chain (or wiring in a new one) doesn't mean
updating two dicts that can drift apart.
"""
from app.api_clients.etherscan import fetch_transactions as fetch_evm, ETH_CHAIN_ID, POLYGON_CHAIN_ID
from app.api_clients.tronscan import fetch_transactions as fetch_tron
from app.api_clients.solana import fetch_transactions as fetch_solana
from app.api_clients.blockchair import fetch_transactions as fetch_bitcoin
from app.api_clients.bsctrace import fetch_transactions as fetch_bnb

CHAINS = {
    "Ethereum": {"enabled": True, "currency": "ETH",
                 "fetch": lambda a: fetch_evm(a, chainid=ETH_CHAIN_ID, asset_type="ETH")},
    "Polygon": {"enabled": True, "currency": "MATIC",
                "fetch": lambda a: fetch_evm(a, chainid=POLYGON_CHAIN_ID, asset_type="MATIC")},
    "Tron": {"enabled": True, "currency": "TRX", "fetch": lambda a: fetch_tron(a)},
    "Solana": {"enabled": True, "currency": "SOL", "fetch": lambda a: fetch_solana(a)},
    # Blockchair's free tier is unauthenticated but rate-limited (~1440
    # req/day) — fine for a demo, not for volume; set BLOCKCHAIR_API_KEY to
    # raise the ceiling. No common-input-ownership clustering yet (research/06).
    "Bitcoin": {"enabled": True, "currency": "BTC", "fetch": lambda a: fetch_bitcoin(a)},
    # Enabled even without NODEREAL_API_KEY provisioned yet: fetch_bnb raises
    # a clear RuntimeError ("set NODEREAL_API_KEY...") that both main.py and
    # app/api/main.py already catch and surface — failing loud with an honest
    # message beats hiding a working adapter behind "coming soon".
    "BNB Chain": {"enabled": True, "currency": "BNB", "fetch": lambda a: fetch_bnb(a)},
}
