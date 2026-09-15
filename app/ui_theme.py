"""Visual theme for the Streamlit UI.

Shares its palette and typography with the project's HTML dossier so the
pitch deck, the written docs and the running app all read as one product.
Components are built as inline-styled HTML because Streamlit's own class
names change between versions — targeting them is fragile, our own markup
is not.
"""

NAVY = "#1B2A4A"
GOLD = "#8C661F"
INK = "#14181F"
INK_SOFT = "#4B5568"
WIRE = "#D3D7E0"
PAPER_RAISED = "#FFFFFF"
LEDGER_SOFT = "#EAEEF6"

RISK_STYLES = {
    "high":   {"fg": "#8C3420", "bg": "#FDECEB", "label": "HIGH RISK"},
    "medium": {"fg": "#8C661F", "bg": "#FBF3E4", "label": "MEDIUM RISK"},
    "low":    {"fg": "#4B5568", "bg": "#F1F3F7", "label": "LOW RISK"},
    "none":   {"fg": "#256B47", "bg": "#EAF5EF", "label": "NO RISK FLAG"},
}

ENTITY_STYLES = {
    "exchange":         {"fg": NAVY, "bg": LEDGER_SOFT},
    "exchange cluster": {"fg": NAVY, "bg": LEDGER_SOFT},
    "mixer":            {"fg": "#8C3420", "bg": "#FDECEB"},
    "user":             {"fg": GOLD, "bg": "#FBF3E4"},
    "unknown":          {"fg": INK_SOFT, "bg": "#F1F3F7"},
}

GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stTextInput, .stButton {{
    font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}}
code, pre {{ font-family: 'IBM Plex Mono', monospace !important; }}

/* Tighten Streamlit's default top padding — the branded header replaces it */
.block-container {{ padding-top: 2.2rem !important; max-width: 1200px; }}

/* Primary button in the project's navy rather than Streamlit red */
.stButton > button[kind="primary"] {{
    background: {NAVY}; border: 1px solid {NAVY}; font-weight: 600;
    letter-spacing: .01em; border-radius: 8px;
}}
.stButton > button[kind="primary"]:hover {{ background: #24375e; border-color: #24375e; }}

/* The address field is the hero input — give it presence */
.stTextInput input {{
    font-family: 'IBM Plex Mono', monospace; font-size: 15px;
    border-radius: 8px; border: 1.5px solid {WIRE};
}}
.stTextInput input:focus {{ border-color: {NAVY}; box-shadow: 0 0 0 2px rgba(27,42,74,.12); }}
</style>
"""


def header() -> str:
    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            border-bottom:2px solid {NAVY};padding:0 0 14px 0;margin-bottom:22px;">
  <div>
    <div style="font-size:26px;font-weight:700;color:{INK};letter-spacing:-.01em;line-height:1.1">
      VASP&nbsp;Trace
    </div>
    <div style="font-size:13px;color:{INK_SOFT};margin-top:3px">
      Automated attribution of unknown wallets to their nearest Virtual Asset Service Provider
    </div>
  </div>
  <div style="text-align:right;font-family:'IBM Plex Mono',monospace;font-size:11px;color:{INK_SOFT};
              line-height:1.7">
    <div style="color:{GOLD};font-weight:600">SIH26182</div>
    <div>MHA · I4C</div>
  </div>
</div>
"""


def risk_badge(level: str, reason: str | None) -> str:
    s = RISK_STYLES.get(level, RISK_STYLES["none"])
    reason_html = (
        f"<div style='font-size:13px;color:{s['fg']};opacity:.92;margin-top:6px;line-height:1.5'>{reason}</div>"
        if reason else ""
    )
    return f"""
<div style="background:{s['bg']};border-left:4px solid {s['fg']};border-radius:6px;
            padding:14px 16px;margin:4px 0 18px 0;">
  <div style="font-family:'IBM Plex Mono',monospace;font-size:13px;font-weight:600;
              letter-spacing:.08em;color:{s['fg']}">{s['label']}</div>
  {reason_html}
</div>
"""


def stat_tile(label: str, value: str, accent: str = NAVY) -> str:
    return f"""
<div style="background:{PAPER_RAISED};border:1px solid {WIRE};border-radius:10px;
            padding:14px 16px;height:100%">
  <div style="font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.09em;
              text-transform:uppercase;color:{INK_SOFT}">{label}</div>
  <div style="font-size:24px;font-weight:700;color:{accent};margin-top:4px;line-height:1.2">{value}</div>
</div>
"""


def _truncate(addr: str) -> str:
    return addr if len(addr) <= 16 else f"{addr[:8]}…{addr[-6:]}"


def path_flow(path: list[str], entity_type: str, label: str | None) -> str:
    """Linear hop diagram. The trace is always a single chain of hops, never a
    branching graph — this represents that honestly; a graph-viz library would
    be decoration, not information."""
    end = ENTITY_STYLES.get(entity_type, ENTITY_STYLES["unknown"])
    chips = []
    for i, addr in enumerate(path):
        is_last = i == len(path) - 1
        fg, bg, border = (end["fg"], end["bg"], end["fg"]) if is_last else (INK, PAPER_RAISED, WIRE)
        caption = (f"<div style='font-size:11px;color:{fg};margin-top:4px;font-weight:600;"
                   f"max-width:150px;text-align:center'>{label}</div>") if is_last and label else (
                  f"<div style='font-size:10px;color:{INK_SOFT};margin-top:4px'>"
                  f"{'seed' if i == 0 else f'hop {i}'}</div>")
        chips.append(
            f"<div style='display:flex;flex-direction:column;align-items:center;min-width:130px'>"
            f"<div title='{addr}' style='background:{bg};color:{fg};border:1.5px solid {border};"
            f"border-radius:8px;padding:9px 11px;font-family:\"IBM Plex Mono\",monospace;"
            f"font-size:12px;font-weight:{600 if is_last else 400};text-align:center;width:100%'>"
            f"{_truncate(addr)}</div>{caption}</div>"
        )
        if not is_last:
            chips.append(f"<div style='align-self:flex-start;margin-top:12px;color:{GOLD};"
                         f"font-size:17px;padding:0 6px'>→</div>")
    return (f"<div style='display:flex;flex-wrap:wrap;align-items:flex-start;gap:2px;"
            f"padding:10px 0 4px 0'>{''.join(chips)}</div>")


def field_row(label: str, value: str, mono: bool = False) -> str:
    font = "'IBM Plex Mono',monospace" if mono else "inherit"
    return f"""
<div style="display:flex;gap:14px;padding:7px 0;border-top:1px solid {WIRE};font-size:13.5px">
  <div style="flex:0 0 170px;color:{INK_SOFT};font-family:'IBM Plex Mono',monospace;
              font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding-top:2px">{label}</div>
  <div style="flex:1;color:{INK};font-family:{font};word-break:break-word">{value}</div>
</div>
"""


def deposit_callout(dep) -> str:
    """The deposit address is the single most actionable thing on the page —
    it is what goes in the disclosure request — so it gets its own block
    rather than a row in the evidence table."""
    confirmed = dep.is_deposit_address
    fg, bg = (NAVY, LEDGER_SOFT) if confirmed else (INK_SOFT, "#F1F3F7")
    heading = ("Deposit address identified" if confirmed
               else "No deposit address confirmed")
    points = dep.signals if confirmed else dep.caveats
    bullets = "".join(
        f"<li style='margin:3px 0'>{p}</li>" for p in points[:4]
    )
    note = (f"<div style='font-size:12.5px;color:{INK_SOFT};margin-top:10px;line-height:1.55'>"
            f"This address maps to a single customer account at the VASP. Name "
            f"<i>this</i> address in the disclosure request — naming the exchange "
            f"alone identifies millions of users.</div>") if confirmed else ""
    return f"""
<div style="background:{bg};border:1.5px solid {fg};border-radius:10px;padding:16px 18px;margin:4px 0 18px 0">
  <div style="display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:600;
                letter-spacing:.07em;text-transform:uppercase;color:{fg}">{heading}</div>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:{INK_SOFT}">
      confidence {dep.confidence:.0%}</div>
  </div>
  <div style="font-family:'IBM Plex Mono',monospace;font-size:15px;font-weight:600;color:{fg};
              margin:10px 0 4px 0;word-break:break-all">{dep.address}</div>
  <ul style="margin:8px 0 0 0;padding-left:18px;font-size:12.5px;color:{INK};line-height:1.5">
    {bullets}
  </ul>
  {note}
</div>
"""


def section_title(text: str) -> str:
    return (f"<div style='font-size:15px;font-weight:700;color:{INK};margin:22px 0 10px 0;"
            f"padding-bottom:6px;border-bottom:1px solid {WIRE}'>{text}</div>")
