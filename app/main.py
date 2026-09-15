"""VASP Trace — Streamlit UI. Run with: streamlit run app/main.py"""
import json
import streamlit as st
from dotenv import load_dotenv

from app.api_clients.etherscan import fetch_transactions as fetch_evm, ETH_CHAIN_ID, POLYGON_CHAIN_ID
from app.api_clients.tronscan import fetch_transactions as fetch_tron
from app.data.tagpacks import load_labels
from app.data.known_mixers import KNOWN_MIXERS
from app.graph.trace import trace_to_nearest_entity
from app.graph.risk import assess
from app.data.case_store import init_db, save_case, list_cases
from app.sahyog.gateway import build_disclosure_request, submit_disclosure_request

load_dotenv()
st.set_page_config(page_title="VASP Trace", page_icon="🔗", layout="wide")

# Chain adapter registry — enabled chains carry a currency code + fetch function
# with the same normalized-transaction interface (see api_clients/*.py).
CHAINS = {
    "Ethereum": {"enabled": True, "currency": "ETH",
                 "fetch": lambda a: fetch_evm(a, chainid=ETH_CHAIN_ID, asset_type="ETH")},
    "Polygon": {"enabled": True, "currency": "MATIC",
                "fetch": lambda a: fetch_evm(a, chainid=POLYGON_CHAIN_ID, asset_type="MATIC")},
    "Tron": {"enabled": True, "currency": "TRX", "fetch": lambda a: fetch_tron(a)},
    "Bitcoin — coming soon": {"enabled": False},
    "BNB Chain — coming soon": {"enabled": False},
    "Solana — coming soon": {"enabled": False},
}


@st.cache_resource(show_spinner="Loading GraphSense TagPack labels (first run only)...")
def get_labels():
    return load_labels()


def render_lookup():
    st.title("VASP Trace")
    st.caption("Automated attribution of unknown wallets to nearest VASPs — SIH26182")

    col1, col2 = st.columns([3, 1])
    address = col1.text_input("Wallet address", placeholder="0xF835A0247b0063C04EF22006eBe57c5F11977Cc4")
    chain = col2.selectbox("Chain", list(CHAINS.keys()))

    if st.button("Trace", type="primary"):
        chain_cfg = CHAINS[chain]
        if not chain_cfg["enabled"]:
            st.warning(f"{chain} isn't wired up in this build yet — the API-client pattern "
                       f"extends cleanly to it (see the roadmap), just not built yet. "
                       f"Try Ethereum, Polygon, or Tron.")
            return
        if not address:
            st.error("Enter an address first.")
            return

        labels = get_labels()
        with st.spinner("Tracing across the chain..."):
            try:
                result = trace_to_nearest_entity(
                    seed_address=address, currency=chain_cfg["currency"],
                    fetch_transactions_fn=chain_cfg["fetch"],
                    labels_lookup=labels, mixers_lookup=KNOWN_MIXERS, max_hops=4,
                )
            except Exception as exc:
                st.error(f"Trace failed: {exc}")
                return

        risk = assess(result)
        st.session_state["last_result"] = result
        st.session_state["last_risk"] = risk
        st.session_state["last_chain"] = chain_cfg["currency"]

        try:
            init_db()
            case_id = save_case(chain_cfg["currency"], result, risk)
            st.session_state["last_case_id"] = case_id
        except Exception as exc:
            st.session_state["last_case_id"] = None
            st.info(f"Not saved to case history — database unreachable ({exc}). "
                    f"Set DATABASE_URL in .env to enable this.")

    if "last_result" in st.session_state:
        _render_verdict(st.session_state["last_result"], st.session_state["last_risk"],
                         st.session_state.get("last_chain", "ETH"))


def _truncate(addr: str) -> str:
    return addr if len(addr) <= 14 else f"{addr[:8]}…{addr[-4:]}"


def _render_path_flow(result) -> None:
    """A linear flow diagram of the hop path — our trace is always a single
    chain, never a branching graph, so this honestly represents the data
    (a heavier graph-viz library would be overkill for a straight line)."""
    end_style = {
        "exchange": ("#e8f1fb", "#1b2a4a"), "exchange cluster": ("#e8f1fb", "#1b2a4a"),
        "mixer": ("#fdeceb", "#8c3420"), "unknown": ("#f1f1f1", "#555"),
    }.get(result.entity_type, ("#f1f1f1", "#555"))

    chips = []
    for i, addr in enumerate(result.path):
        is_last = i == len(result.path) - 1
        bg, fg = end_style if is_last else ("#fff", "#333")
        border = fg if is_last else "#ccc"
        label_html = f"<div style='font-size:11px;color:{fg};margin-top:2px'>{result.label}</div>" \
            if is_last and result.label else ""
        chips.append(
            f"<div style='display:flex;flex-direction:column;align-items:center;min-width:120px'>"
            f"<div title='{addr}' style='background:{bg};color:{fg};border:1.5px solid {border};"
            f"border-radius:8px;padding:8px 10px;font-family:monospace;font-size:12px;text-align:center'>"
            f"{_truncate(addr)}</div>{label_html}</div>"
        )
        if not is_last:
            chips.append("<div style='align-self:center;color:#999;font-size:18px;padding:0 4px'>→</div>")

    st.markdown(
        f"<div style='display:flex;flex-wrap:wrap;align-items:flex-start;gap:4px;padding:8px 0'>"
        f"{''.join(chips)}</div>",
        unsafe_allow_html=True,
    )


def _render_verdict(result, risk, chain):
    st.divider()
    st.subheader("Verdict")

    c1, c2, c3 = st.columns(3)
    c1.metric("Entity type", result.entity_type)
    c2.metric("Confidence", f"{result.confidence:.0%}" if result.confidence else "—")
    c3.metric("Hops", result.hop_count)

    st.write(f"**Label:** {result.label or '_(none — Unknown/Unattributed)_'}")
    st.write("**Traced path:**")
    _render_path_flow(result)
    if result.source:
        st.caption(f"Source: {result.source}")
    if result.reason:
        st.caption(f"Reason: {result.reason}")

    if risk.risk_flag:
        st.error(f"⚠ RISK FLAGGED — {risk.risk_reason}")
    else:
        st.success("No risk flag raised.")
    st.write(f"**Compliance status:** `{risk.compliance_status}` — {risk.compliance_detail}")

    st.divider()
    st.subheader("SAHYOG-ready report")
    st.caption("Drafts a correctly-formatted disclosure/freeze request. Does NOT submit anywhere live — "
              "SAHYOG API access is government-internal and pending I4C provisioning.")
    note = st.text_input("Analyst note (optional)", key="analyst_note")
    if st.button("Generate SAHYOG-ready report"):
        request = build_disclosure_request(chain, result, risk, analyst_note=note)
        response = submit_disclosure_request(request)
        st.json(request)
        st.info(f"{response['status']}: {response['detail']}")
        st.download_button("Download report (JSON)", data=json.dumps(request, indent=2),
                           file_name=f"vasp-trace-report-{result.seed_address[:10]}.json")


def render_dashboard():
    st.title("Case Dashboard")
    st.caption("Every trace run through this app, saved automatically.")
    try:
        init_db()
        cases = list_cases(limit=100)
    except Exception as exc:
        st.warning(f"Case database unreachable — set DATABASE_URL in .env. ({exc})")
        return

    if not cases:
        st.info("No cases yet — run a trace on the Lookup page.")
        return

    import pandas as pd
    df = pd.DataFrame(cases)[["id", "created_at", "seed_address", "entity_type", "label",
                              "confidence", "compliance_status", "risk_flag"]]
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(cases)} case(s) shown (most recent first, limit 100).")


page = st.sidebar.radio("View", ["Lookup", "Case Dashboard"])
if page == "Lookup":
    render_lookup()
else:
    render_dashboard()
