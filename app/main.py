"""VASP Trace — Streamlit UI. Run with: streamlit run app/main.py"""
import json
import streamlit as st
from dotenv import load_dotenv

from app.api_clients.etherscan import fetch_transactions as fetch_evm, ETH_CHAIN_ID, POLYGON_CHAIN_ID
from app.api_clients.tronscan import fetch_transactions as fetch_tron
from app.api_clients.solana import fetch_transactions as fetch_solana
from app.data.tagpacks import load_labels
from app.data.known_mixers import KNOWN_MIXERS
from app.graph.trace import trace_to_nearest_entity
from app.graph.risk import assess
from app.data.case_store import init_db, save_case, list_cases
from app.sahyog.gateway import build_disclosure_request, submit_disclosure_request
from app.graph.chain_detect import detect_chain
from app import ui_theme as ui

load_dotenv()
st.set_page_config(page_title="VASP Trace — SIH26182", page_icon="🔗", layout="wide")
st.markdown(ui.GLOBAL_CSS, unsafe_allow_html=True)

# Chain adapter registry — enabled chains carry a currency code + fetch function
# with the same normalized-transaction interface (see api_clients/*.py).
CHAINS = {
    "Ethereum": {"enabled": True, "currency": "ETH",
                 "fetch": lambda a: fetch_evm(a, chainid=ETH_CHAIN_ID, asset_type="ETH")},
    "Polygon": {"enabled": True, "currency": "MATIC",
                "fetch": lambda a: fetch_evm(a, chainid=POLYGON_CHAIN_ID, asset_type="MATIC")},
    "Tron": {"enabled": True, "currency": "TRX", "fetch": lambda a: fetch_tron(a)},
    "Solana": {"enabled": True, "currency": "SOL", "fetch": lambda a: fetch_solana(a)},
    "Bitcoin — coming soon": {"enabled": False},
    "BNB Chain — coming soon": {"enabled": False},
}

DEMO_ADDRESSES = {
    "— pick a verified example —": "",
    "2-hop trace → FixedFloat (the core scenario)": "0x392704a6048178a264cf6615547cfeac23867605",
    "1-hop trace → Binance": "0x8aa878f06c34fbe1e9d9c6d2ce3f118b4f7c1c65",
    "Mixer (Tornado Cash, OFAC-sanctioned)": "0x8589427373D6D84E98730D7795D8f6f8731FDA16",
    "OFAC SDN-listed address": "0x8576acc5c05d6ce88f4e49bf65bdf0c62f91353c",
    "Honest 'Unknown' (The DAO hack contract)": "0xF835A0247b0063C04EF22006eBe57c5F11977Cc4",
}


@st.cache_resource(show_spinner="Loading GraphSense TagPack labels (first run only)...")
def get_labels():
    return load_labels()


def render_lookup():
    st.markdown(ui.header(), unsafe_allow_html=True)

    def _on_address_change():
        detected, _ = detect_chain(st.session_state.get("address_input", ""))
        if detected:
            st.session_state["chain_select"] = detected

    def _on_demo_pick():
        picked = DEMO_ADDRESSES.get(st.session_state.get("demo_pick", ""), "")
        if picked:
            st.session_state["address_input"] = picked
            detected, _ = detect_chain(picked)
            if detected:
                st.session_state["chain_select"] = detected

    if "chain_select" not in st.session_state:
        st.session_state["chain_select"] = "Ethereum"

    address = st.text_input(
        "Wallet address", placeholder="Paste any wallet address — the chain is detected automatically",
        key="address_input", on_change=_on_address_change, label_visibility="collapsed",
    )

    c1, c2 = st.columns([1, 2])
    with c1:
        traced = st.button("Trace wallet", type="primary", use_container_width=True)
    with c2:
        st.selectbox("Demo", list(DEMO_ADDRESSES.keys()), key="demo_pick",
                     on_change=_on_demo_pick, label_visibility="collapsed")

    detected, detect_note = detect_chain(address) if address else (None, "")
    if address and detected:
        st.markdown(
            f"<div style='font-size:13px;color:{ui.INK_SOFT};margin:2px 0 10px 0'>"
            f"Detected chain: <b style='color:{ui.NAVY}'>{detected}</b> — {detect_note}</div>",
            unsafe_allow_html=True)
    elif address:
        st.markdown(
            f"<div style='font-size:13px;color:{ui.GOLD};margin:2px 0 10px 0'>"
            f"Address format not recognised — set the chain manually below.</div>",
            unsafe_allow_html=True)

    with st.expander("Override detected chain"):
        chain = st.selectbox("Chain", list(CHAINS.keys()), key="chain_select")

    if traced:
        chain_cfg = CHAINS[chain]
        if not chain_cfg["enabled"]:
            st.warning(f"{chain} isn't wired up in this build yet — the adapter pattern extends "
                       f"cleanly to it, it just isn't built. Try Ethereum, Polygon, Tron, or Solana.")
            return
        if not address:
            st.error("Enter a wallet address first.")
            return

        labels = get_labels()
        with st.spinner("Tracing across the chain…"):
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
            st.session_state["last_case_id"] = save_case(chain_cfg["currency"], result, risk)
        except Exception as exc:
            st.session_state["last_case_id"] = None
            st.info(f"Not saved to case history — database unreachable ({exc}).")

    if "last_result" in st.session_state:
        _render_verdict(st.session_state["last_result"], st.session_state["last_risk"],
                        st.session_state.get("last_chain", "ETH"),
                        st.session_state.get("last_case_id"))


def _render_verdict(result, risk, chain, case_id):
    st.markdown(ui.section_title("Verdict"), unsafe_allow_html=True)

    entity_style = ui.ENTITY_STYLES.get(result.entity_type, ui.ENTITY_STYLES["unknown"])
    t1, t2, t3, t4 = st.columns(4)
    t1.markdown(ui.stat_tile("Entity type", result.entity_type, entity_style["fg"]), unsafe_allow_html=True)
    t2.markdown(ui.stat_tile("Confidence", f"{result.confidence:.0%}" if result.confidence else "—"),
                unsafe_allow_html=True)
    t3.markdown(ui.stat_tile("Hops traced", str(result.hop_count)), unsafe_allow_html=True)
    t4.markdown(ui.stat_tile("Case ID", f"#{case_id}" if case_id else "not saved"), unsafe_allow_html=True)

    st.markdown(ui.risk_badge(risk.risk_level, risk.risk_reason), unsafe_allow_html=True)

    st.markdown(ui.section_title("Traced path"), unsafe_allow_html=True)
    st.markdown(ui.path_flow(result.path, result.entity_type, result.label), unsafe_allow_html=True)

    st.markdown(ui.section_title("Evidence"), unsafe_allow_html=True)
    rows = [
        ui.field_row("Seed address", result.seed_address, mono=True),
        ui.field_row("Chain", chain),
        ui.field_row("Attributed entity", result.label or "<i>None — unattributed</i>"),
        ui.field_row("Compliance status", f"<code>{risk.compliance_status}</code> — {risk.compliance_detail}"),
    ]
    if result.source:
        rows.append(ui.field_row("Label source", result.source, mono=True))
    if result.reason:
        rows.append(ui.field_row("Trace outcome", result.reason))
    st.markdown("".join(rows), unsafe_allow_html=True)

    st.markdown(ui.section_title("SAHYOG disclosure request"), unsafe_allow_html=True)
    st.caption("Drafts a correctly-formatted disclosure/freeze request. Does not transmit anywhere — "
               "SAHYOG API access is government-internal and pending I4C provisioning.")
    note = st.text_input("Analyst note (optional)", key="analyst_note")
    if st.button("Generate SAHYOG-ready report"):
        request = build_disclosure_request(chain, result, risk, analyst_note=note)
        response = submit_disclosure_request(request)
        st.download_button("⬇ Download report (JSON)", data=json.dumps(request, indent=2),
                           file_name=f"vasp-trace-report-{result.seed_address[:10]}.json",
                           type="primary")
        st.caption(f"{response['status']} — {response['detail']}")
        with st.expander("View full report"):
            st.json(request)


def render_dashboard():
    st.markdown(ui.header(), unsafe_allow_html=True)
    st.markdown(ui.section_title("Case dashboard"), unsafe_allow_html=True)

    try:
        init_db()
        cases = list_cases(limit=200)
    except Exception as exc:
        st.warning(f"Case database unreachable — set DATABASE_URL in .env. ({exc})")
        return
    if not cases:
        st.info("No cases yet — run a trace on the Lookup page.")
        return

    import pandas as pd
    df = pd.DataFrame(cases)

    m = st.columns(5)
    m[0].markdown(ui.stat_tile("Total cases", str(len(df))), unsafe_allow_html=True)
    m[1].markdown(ui.stat_tile("High risk", str(int((df["risk_level"] == "high").sum())),
                               ui.RISK_STYLES["high"]["fg"]), unsafe_allow_html=True)
    m[2].markdown(ui.stat_tile("Medium risk", str(int((df["risk_level"] == "medium").sum())),
                               ui.RISK_STYLES["medium"]["fg"]), unsafe_allow_html=True)
    m[3].markdown(ui.stat_tile("Entities identified", str(df["label"].dropna().nunique())),
                  unsafe_allow_html=True)
    m[4].markdown(ui.stat_tile("Chains covered", str(df["chain"].nunique())), unsafe_allow_html=True)

    st.markdown(ui.section_title("Filter"), unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([2, 2, 2, 3])
    chain_filter = f1.multiselect("Chain", sorted(df["chain"].unique()))
    entity_filter = f2.multiselect("Entity type", sorted(df["entity_type"].dropna().unique()))
    risk_filter = f3.multiselect("Risk level", ["high", "medium", "low", "none"])
    search = f4.text_input("Search address", placeholder="0x… or T…")

    filtered = df.copy()
    if chain_filter:
        filtered = filtered[filtered["chain"].isin(chain_filter)]
    if risk_filter:
        filtered = filtered[filtered["risk_level"].isin(risk_filter)]
    if entity_filter:
        filtered = filtered[filtered["entity_type"].isin(entity_filter)]
    if search:
        filtered = filtered[filtered["seed_address"].str.contains(search, case=False, na=False)]

    if not filtered.empty:
        st.bar_chart(filtered["entity_type"].value_counts(), use_container_width=True, height=220)

    st.dataframe(
        filtered[["id", "created_at", "chain", "seed_address", "entity_type", "label",
                  "confidence", "compliance_status", "risk_level"]],
        use_container_width=True, hide_index=True,
    )
    st.caption(f"{len(filtered)} of {len(df)} case(s) — most recent first, limit 200.")


with st.sidebar:
    st.markdown(f"<div style='font-weight:700;font-size:16px;color:{ui.INK};margin-bottom:2px'>"
                f"VASP Trace</div>"
                f"<div style='font-size:11px;color:{ui.INK_SOFT};font-family:\"IBM Plex Mono\",monospace;"
                f"margin-bottom:16px'>SIH26182 · MHA / I4C</div>", unsafe_allow_html=True)
    page = st.radio("View", ["Lookup", "Case Dashboard"], label_visibility="collapsed")
    st.markdown(f"<div style='margin-top:24px;font-size:11px;color:{ui.INK_SOFT};line-height:1.7'>"
                f"<b>Live chains</b><br>Ethereum · Polygon · Tron · Solana</div>",
                unsafe_allow_html=True)

if page == "Lookup":
    render_lookup()
else:
    render_dashboard()
