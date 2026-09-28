"""Fill the SIH template using its own text boxes and paragraph styles.
Only change vs template: bullet body text is smaller (heads/titles/fonts untouched)."""
import copy, re
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_THEME_COLOR, MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

TPL = r"C:\Users\Avvi\Downloads\SIH2026-IDEA-Presentation-Format.pptx"
OUT = r"C:\Users\Avvi\Downloads\VASP-Trace-SIH2026-Idea-v2.pptx"
GREY = RGBColor(0x40, 0x40, 0x40)

prs = Presentation(TPL)
S = prs.slides

# ---- prototypes taken straight from the template ----
def tb8(slide):
    return next(sh for sh in slide.shapes if sh.name == "TextBox 8")

HEAD_P = copy.deepcopy(tb8(S[1]).text_frame.paragraphs[0]._p)   # ❖ 32pt bold underline tx2
BUL_P = copy.deepcopy(tb8(S[2]).text_frame.paragraphs[0]._p)    # • Arial 28pt justified
BOX_SP = copy.deepcopy(tb8(S[2])._element)                      # template body text box

# drop the instructions slide (7) — template says delete before upload
sldIdLst = prs.slides._sldIdLst
prs.part.drop_rel(sldIdLst[-1].rId)
sldIdLst.remove(sldIdLst[-1])

INLINE = re.compile(r"(\*\*.+?\*\*|\[[^\]]+\]\([^)]+\))")


def _fill(p_el, text, size=None, bold=None, color=None, italic=False):
    """Replace runs of cloned paragraph with `text`, reusing the first run's rPr."""
    runs = p_el.findall(qn("a:r"))
    proto = copy.deepcopy(runs[0].find(qn("a:rPr")))
    for r in runs:
        p_el.remove(r)
    for br in p_el.findall(qn("a:br")):
        p_el.remove(br)
    end = p_el.find(qn("a:endParaRPr"))
    links = []
    for part in INLINE.split(text):
        if not part:
            continue
        b, link = bold, None
        if part.startswith("**"):
            part, b = part[2:-2], True
        m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", part)
        if m:
            part, link = m.group(1), m.group(2)
        r = etree.SubElement(p_el, qn("a:r"))
        rpr = copy.deepcopy(proto)
        if size:
            rpr.set("sz", str(int(size * 100)))
        if b is not None:
            rpr.set("b", "1" if b else "0")
        if italic:
            rpr.set("i", "1")
        r.append(rpr)
        t = etree.SubElement(r, qn("a:t"))
        t.text = part
        if part != part.strip():
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        if color is not None:
            for f in rpr.findall(qn("a:solidFill")):
                rpr.remove(f)
            sf = etree.Element(qn("a:solidFill"))
            etree.SubElement(sf, qn("a:srgbClr")).set("val", str(color))
            rpr.insert(0, sf)
        if link:
            links.append((r, link))
        if end is not None:
            end.addprevious(r)
    return links


def box(slide, x, y, w, md, size=12, h=0.5, space=3):
    """Clone the template's body text box and fill it with lines.
    '## head' = template ❖ heading (32pt as-is) · '- ' bullet · '  - ' sub-bullet
    '1. ' numbered · '_x_' italic note · plain = no bullet."""
    sp = copy.deepcopy(BOX_SP)
    slide.shapes._spTree.append(sp)
    shape = slide.shapes[-1]
    shape.left, shape.top, shape.width, shape.height = Inches(x), Inches(y), Inches(w), Inches(h)
    txBody = sp.find(qn("p:txBody"))
    for p in txBody.findall(qn("a:p")):
        txBody.remove(p)
    pending = []
    for line in md.strip("\n").split("\n"):
        if line.startswith("## "):
            p = copy.deepcopy(HEAD_P)
            txBody.append(p)
            _fill(p, line[3:])
            continue
        p = copy.deepcopy(BUL_P)
        txBody.append(p)
        pPr = p.find(qn("a:pPr"))
        sa = etree.SubElement(pPr, qn("a:spcAft"))
        etree.SubElement(sa, qn("a:spcPts")).set("val", str(space * 100))
        # spcAft must precede buFont in schema order
        pPr.remove(sa); pPr.find(qn("a:buFont")).addprevious(sa)
        txt, kw = line, {}
        if line.startswith("  - "):
            txt = line[4:]
            pPr.set("marL", str(int(Inches(0.45)))); pPr.set("indent", str(-int(Inches(0.18))))
            pPr.find(qn("a:buChar")).set("char", "–")
            kw["size"] = size - 1
        elif line.startswith("- "):
            txt = line[2:]
            pPr.set("marL", str(int(Inches(0.22)))); pPr.set("indent", str(-int(Inches(0.22))))
        elif re.match(r"\d+\. ", line):
            txt = line.split(". ", 1)[1]
            pPr.set("marL", str(int(Inches(0.28)))); pPr.set("indent", str(-int(Inches(0.28))))
            bc = pPr.find(qn("a:buChar"))
            an = etree.Element(qn("a:buAutoNum")); an.set("type", "arabicPeriod")
            bc.addprevious(an); pPr.remove(bc)
        else:
            italic = line.startswith("_") and line.endswith("_")
            if italic:
                txt = line[1:-1]
                kw.update(italic=True, color=GREY, size=size - 1)
            pPr.set("marL", "0"); pPr.set("indent", "0")
            for tag in ("a:buFont", "a:buChar"):
                e = pPr.find(qn(tag))
                if e is not None:
                    if tag == "a:buChar":
                        e.addprevious(etree.Element(qn("a:buNone")))
                    pPr.remove(e)
        kw.setdefault("size", size)
        pending += _fill(p, txt, **kw)
    # hyperlinks need relationships → do them through python-pptx
    for r_el, url in pending:
        rId = slide.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
        rpr = r_el.find(qn("a:rPr"))
        rpr.set("u", "sng")
        sf = rpr.find(qn("a:solidFill"))
        if sf is not None:
            rpr.remove(sf)
        sf = etree.Element(qn("a:solidFill")); etree.SubElement(sf, qn("a:srgbClr")).set("val", "0563C1")
        rpr.insert(0, sf)
        hl = etree.SubElement(rpr, qn("a:hlinkClick")); hl.set(qn("r:id"), rId)
    return shape


def placeholder(slide, x, y, w, h, label, body, size=10):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.adjustments[0] = 0.06
    sh.fill.solid(); sh.fill.fore_color.rgb = RGBColor(0xF7, 0xF9, 0xFC)
    sh.line.color.rgb = RGBColor(0x7F, 0x8C, 0x9D); sh.line.width = Pt(1.25)
    sh.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    sh.shadow.inherit = False
    tf = sh.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for side in ("left", "right", "top", "bottom"):
        setattr(tf, f"margin_{side}", Inches(0.08))
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = label
    r.font.name, r.font.size, r.font.bold = "Arial", Pt(size + 2), True
    r.font.color.theme_color = MSO_THEME_COLOR.TEXT_2
    for line in body.strip().split("\n"):
        q = tf.add_paragraph(); q.alignment = PP_ALIGN.CENTER; q.space_before = Pt(2)
        r = q.add_run(); r.text = line
        r.font.name, r.font.size = "Arial", Pt(size)
        r.font.color.rgb = GREY
    return sh


def table(slide, x, y, w, rows, colw, size=10, rowh=0.25, first_bold=True):
    shp = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(rowh * len(rows)))
    t = shp.table
    for i, cw in enumerate(colw):
        t.columns[i].width = Inches(cw)
    for ri, row in enumerate(rows):
        t.rows[ri].height = Inches(rowh)
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci)
            cell.margin_left = cell.margin_right = Inches(0.05)
            cell.margin_top = cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            p = cell.text_frame.paragraphs[0]
            r = p.add_run(); r.text = val
            r.font.name, r.font.size = "Arial", Pt(size)
            if ri == 0:
                cell.fill.fore_color.theme_color = MSO_THEME_COLOR.TEXT_2
                r.font.bold = True; r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                cell.fill.fore_color.rgb = RGBColor(0xEE, 0xF3, 0xF9) if ri % 2 else RGBColor(255, 255, 255)
                r.font.bold = first_bold and ci == 0
                r.font.color.rgb = RGBColor(0, 0, 0)
    return shp


def clear_body(slide):
    sp = tb8(slide)._element
    sp.getparent().remove(sp)


def set_title(slide, text):
    """Keep the template title run (36pt bold); only swap its text."""
    title = next(sh for sh in slide.shapes if sh.name == "Title 1")
    p = title.text_frame.paragraphs[0]._p
    runs = p.findall(qn("a:r"))
    for r in runs[:-1]:
        p.remove(r)
    for br in p.findall(qn("a:br")):
        p.remove(br)
    runs[-1].find(qn("a:t")).text = text


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


# ======================= SLIDE 1 =======================
s = S[0]
for sh in s.shapes:
    if sh.name == "TextBox 9":
        paras = sh.text_frame.paragraphs
        vals = ["Problem Statement ID – SIH26182",
                "Problem Statement Title – Automated Blockchain Intelligence & VASP Attribution Engine integrated with the SAHYOG Portal",
                "Theme – [FILL]",
                "PS Category – Software",
                "Team ID – [FILL]",
                "Team Name – [FILL]"]
        for para, v in zip(paras[1:], vals):
            para.runs[0].text = v
            para.line_spacing = 1.5
        paras[0]._p.getparent().remove(paras[0]._p)   # template's blank spacer line
        sh.top = Inches(1.95)
    elif sh.name == "Subtitle 3":
        sh.text_frame.paragraphs[1].runs[0].text = "VASP-Trace"
notes(s, "Organisation: Ministry of Home Affairs (MHA) / Indian Cyber Crime Coordination Centre (I4C).\n"
         "Tagline: VASP-Trace — from a suspect wallet to the exchange deposit account behind it, with the evidence and the right legal notice ready.\n"
         "Fill Theme (exact text from the SIH portal), Team ID and Team Name, and put your team name in the oval on slides 2–6, before exporting to PDF.")

# ======================= SLIDE 2 — IDEA =======================
s = S[1]
clear_body(s)
next(sh for sh in s.shapes if sh.name == "Title 1").text_frame.paragraphs[0].runs[-1].text = "VASP-Trace"

box(s, 0.3, 1.2, 6.25, """
## Proposed Solution
**VASP-Trace — Automated VASP Attribution & SAHYOG Request Engine :** an India-first blockchain-intelligence engine for cyber cells and I4C. An officer pastes a suspect wallet from an NCRP complaint (or SAHYOG pushes it); VASP-Trace follows the money on-chain, names the **nearest exchange / custodial VASP** and the **deposit address** behind one KYC'd account, and drafts the **legal request**.
1. **Detect chain** — Tron, Ethereum, Polygon, BNB Chain, Solana, Bitcoin.
2. **Trace** — branches carrying ≥10% of value, up to 12 hops, one asset at a time.
3. **Attribute** — Indian-VASP dataset (112 addresses) → GraphSense (500,115 labels) → explorer tags.
4. **Pin the deposit address** — sweep test (Victor, FC 2020): ≥90% forwarded to one hot wallet.
5. **Judge risk** — sanctions (OFAC + Chainalysis oracle), mixers, FIU-IND status + 5 laundering typologies.
6. **Act** — legal instrument, SAHYOG-shaped request, **BSA 2023 s.63 certificate**.
7. **Track** — case file: NCRP ack no., CCTNS FIR, UPI/bank trail, watchlist alerts.
""", size=11, space=2)

placeholder(s, 0.35, 5.35, 6.15, 1.5, "[DIAGRAM D1 — Solution flow]",
            "Complaint (NCRP / SAHYOG) → Wallet → Trace → Attribute (VASP + deposit address) → Risk → Act (BNSS notice + s.63) → Track\n+ screenshot of the verdict card", size=9)

table(s, 6.75, 1.3, 6.3, [
    ["Pain point in the PS", "How VASP-Trace addresses it"],
    ["Wallet unhosted / VASP unknown", "Nearest named VASP + the deposit address it can answer about"],
    ["Many intermediate wallets", "Ranked multi-hop search; reports every dropped branch"],
    ["Manual tracing takes days", "Verdict in ~3 s on live data + plain-language summary"],
    ["Wrong party / instrument", "Routes by FIU-IND status and request type"],
    ["Evidence must stand in court", "BSA s.63 certificate with reproducible SHA-256"],
], colw=[2.3, 4.0], size=10, rowh=0.27)

box(s, 6.7, 3.0, 6.35, """
## Innovation & uniqueness
1. **Deposit-address output** — one address = one KYC'd account = one answerable notice ✅
2. **Cross-case linking** — same deposit address across states' NCRP complaints = same beneficiary 🛠
3. **India-native legal layer** — BSA s.63 ✅ · NCRP / CCTNS / UPI ✅ · BNSS s.94 / s.106 / s.107 routing 🛠
4. **Honest by design** — "unattributed" ≠ "clean"; every label carries its source ✅
5. **Bridges & swaps decoded**, trace continues on the other chain 🛠
""", size=11, space=2)

box(s, 6.7, 5.5, 6.35, """
**Proof it works** (live run, 27 Sep 2026): Indian-case Tron wallet → **Binance-Hot 7** in **3.0 s** · deposit score **0.95**, **15** funders → 1 wallet · behaviour risk **HIGH** · **257** tests pass · evidence pack in **1.7 s**
_✅ working · 🛠 in build_
""", size=11, space=2)

notes(s, "Open with the one-case story: a complaint lists one Tron wallet, and today an officer clicks through explorers for days. Show that the output is a deposit address plus a notice, not just a graph. Say clearly which items are working and which are in build.\n\n"
         "Detail if asked: trace keeps USDT from being lost behind dust; Indian-VASP dataset = 112 checksum-validated addresses (CoinDCX, WazirX, CoinSwitch); explorer tags e.g. Tronscan 'Binance-Hot 7'; sweep test = forwards ≥90% onward, to one hot wallet, from many funders, within minutes; typologies = funnel, rapid layering, fan-out smurfing, peel chain, round-amount structuring; s.63 pack = Part A + Part B + SHA-256 hash report; NCRP's Suspect Repository covers phones, emails, accounts and URLs but not wallets; freeze section depends on the state's High Court position (Courts split in 2026); bridge decoding via THORChain memo, LI.FI / LayerZero status APIs.")

# ======================= SLIDE 3 — TECHNICAL APPROACH =======================
s = S[2]
clear_body(s)

box(s, 0.3, 1.2, 6.25, """
## Technology Stack
- **Frontend :** Next.js 16, React 19, TypeScript, Tailwind CSS 4, Cytoscape.js + dagre
- **Backend :** Python 3.13, FastAPI (19 REST endpoints), NetworkX, PyJWT, fpdf2
- **Database :** PostgreSQL (Supabase) — cases, officers, audit log, UPI hops, watchlist
- **Chain APIs** (free tiers, no nodes) : Tronscan · Etherscan V2 · NodeReal · Helius · Blockstream Esplora 🛠
- **Intelligence :** Indian-VASP dataset, GraphSense TagPacks, OFAC SDN list, Chainalysis oracle, CoinGecko (₹)
- **Security :** PBKDF2-SHA256, JWT sessions, officer audit log; supervisor approval 🛠
- **Testing :** pytest — 257 tests, all network mocked
- **Scale :** Redis, worker queue, self-hosted indexers at I4C/NCFL
""", size=11, space=3)

box(s, 6.7, 1.2, 6.35, """
## Methodology
1. **Input** — wallet pasted by officer ✅ or from NCRP/SAHYOG intake 🛠
2. **Fetch** — native + token + internal transfers, cached 60 s
3. **Search** — BFS: ≥10% materiality, ≤3 branches/hop, 12 hops, 60-lookup budget
4. **Label** — Indian VASP → GraphSense → explorer tags; source kept
5. **Deposit test** — sweep score (forward 0.35 · one dest 0.30 · funders 0.20 · speed 0.15) ≥ 0.60
6. **Risk** — 6 trail rules + 5 behaviour typologies; worse wins
7. **Evidence** — canonical JSON → SHA-256 → BSA s.63 PDFs
8. **Route & request** — FIU-IND status → SAHYOG-shaped request → tracking
9. **Monitor** — watchlist re-trace → alert on risk / entity change
""", size=12, space=3)

placeholder(s, 0.35, 4.45, 3.2, 2.4, "[LOGO ROW]",
            "Next.js · React · TypeScript · Tailwind · Python · FastAPI · PostgreSQL · Supabase · Tron · Ethereum · Polygon · BNB Chain · Solana · Bitcoin", size=8)
placeholder(s, 3.7, 4.45, 9.35, 2.4, "[DIAGRAM D2 — System architecture]  (solid = working · dashed = in build 🛠)",
            "Officer (laptop / phone) → Next.js console → FastAPI (Auth · Trace · Cases · Evidence · Watchlist · SAHYOG adapter 🛠) → Engine (trace · deposit detector · risk · summary · bridge decoder 🛠 · cross-case linker 🛠)\n"
            "Data: PostgreSQL · label store · sanctions (OFAC, Chainalysis) · VASP directory 🛠   |   APIs: Tronscan · Etherscan V2 · NodeReal · Helius · Esplora · CoinGecko · LI.FI / LayerZero / THORChain 🛠\n"
            "Outbound: request → SAHYOG → VASP; s.63 certificate → court", size=9)

notes(s, "Stress \"no blockchain nodes, free public APIs, works today\". Point out that every threshold is published on the tool's Coverage page, so a defence lawyer can argue with a number, not a black box.\n\n"
         "Detail if asked: Backend also psycopg2 + OpenAPI; chains per API — Tronscan (Tron TRX + TRC-20 USDT), Etherscan API V2 (Ethereum, Polygon), NodeReal MegaNode (BNB Chain), Helius (Solana), Blockstream Esplora (Bitcoin, replacing Blockchair). GraphSense TagPacks are MIT-licensed; OFAC list from 0xB10C, nightly; Chainalysis oracle is on-chain and free. Search also caps ≤8 active branches and reports every dropped branch. Evidence record has no clock so the hash is reproducible (Part A / Part B / hash report).")

# ======================= SLIDE 4 — FEASIBILITY =======================
s = S[3]
clear_body(s)

box(s, 0.3, 1.2, 4.6, """
## Feasibility
- **Technical :** live data on 6 chains, free APIs, no nodes; Tron trace 3.0 s, ETH 3-hop 34.3 s; 257 tests
- **Legal :** VDA SPs are PMLA reporting entities since 7 Mar 2023; FIU-IND guidelines (8 Jan 2026) flag unhosted-wallet transfers as high-risk
- **Operational :** fits NCRP → case → VASP request → status
- **Economic :** open data + free tiers; no per-seat licence
""", size=12, space=3)

box(s, 0.3, 3.8, 4.6, """
## Use cases
1. Cyber cell: wallet → deposit address + BNSS s.94 notice
2. I4C: many complaints → one deposit address → one notice 🛠
3. Freeze while funds sit at an exchange or in USDT 🛠
4. FIU-IND / ED: flows to offshore platforms on notice lists
5. Court: s.63 certificate hash re-derivable by defence
""", size=11, space=2)

table(s, 5.1, 1.3, 7.95, [
    ["Challenge / risk", "Strategy to overcome it"],
    ["Heuristics are probabilistic — only the VASP knows the owner", "Evidence-graded confidence; \"unattributed\" never shown as \"clean\""],
    ["Label coverage — GraphSense: 30 Tron labels in 500,115; no WazirX / CoinDCX / ZebPay", "Persist explorer tags with provenance; VASP directory from FIU-IND lists & orders"],
    ["Offshore VASPs — FIU-IND notices to 49 entities (9 · 25 · 15)", "Registration-aware routing: s.94 · LE portal · LoR / MLAT · USDT issuer freeze"],
    ["Freezing law unsettled — AP HC: s.107; Karnataka & Bombay HCs: s.106", "Both drafts generated; the officer chooses, nothing auto-filed"],
    ["Cross-chain hops & mixers", "Bridge decoders (THORChain, LI.FI, LayerZero) 🛠"],
    ["Free-tier limits — Etherscan 3 calls/s; Blockchair HTTP 430", "Rate limiter + cache now; self-hosted indexers at NCFL"],
    ["SAHYOG has no public API", "Adapter + mock + published OpenAPI contract 🛠"],
], colw=[3.9, 4.05], size=10, rowh=0.42, first_bold=False)

box(s, 5.05, 4.85, 8.0, """
## Supporting facts
- India ranks **#1** in the Chainalysis 2025 Global Crypto Adoption Index
- **50** VDA SPs registered with FIU-IND (~Oct 2025, MoF via CoinGeek)
- **>₹3.5 lakh crore** of Indian VDA trading moved offshore after 1% TDS (Esya Centre, via KoinX)
- FinCEN: Huione Group laundered **>US$4 bn** (2021–25); on FIU-IND's Oct 2025 notice list
""", size=11, space=1)

notes(s, "Admit the limits before a judge raises them. The honest list (label coverage, freeze-law split, offshore VASPs) is the most credible slide in the deck.\n\n"
         "Detail if asked: PMLA notification S.O. 1072(E), 7 Mar 2023 — VASPs must keep KYC and answer lawful requests. Operational fit adds NCRP acknowledgement and CCTNS FIR fields. Offshore notice waves: Dec 2023: 9 · Oct 2025: 25 · Sep 2026: 15. VASP directory built from the Lok Sabha registrant list (Dec 2023: CoinDCX, WazirX, CoinSwitch, ZebPay…), FIU-IND penalty orders and the 3 notice waves. Routing: registered Indian VASP → BNSS s.94; registered offshore → its law-enforcement portal; unregistered → letter of request / MLAT + FIU-IND intimation; USDT still on-chain → issuer freeze. Freeze split: AP HC 31 Mar 2026 (Magistrate's order, s.107) vs Karnataka HC 10 Aug 2026 and Bombay HC 30 Jul 2026 (police freeze, s.106). Self-hosted indexers also stop suspect addresses leaking to third-party explorers. Esya: >₹3.5 lakh crore Jul 2022–Oct 2023, >90% share. FinCEN May 2025: Huione >US$4 bn Aug 2021–Jan 2025 incl. scam proceeds.")

# ======================= SLIDE 5 — IMPACT =======================
s = S[4]
clear_body(s)

box(s, 0.3, 1.2, 6.25, """
## Impact
- **Cyber-cell officers :** named VASP + deposit address in seconds, readable summary, ready notice
- **I4C :** complaints linked across states via shared deposit addresses 🛠 — mule networks surfaced
- **VASPs :** precise requests (deposit address + tx hashes) — faster KYC answers
- **Courts :** s.63 certificate with reproducible SHA-256 and published thresholds
- **Victims :** faster freezes while funds are still at the exchange or in USDT
""", size=13, space=4)

placeholder(s, 0.35, 5.05, 6.15, 1.8, "[DIAGRAM D3 — Benefits tree]",
            "\"Benefits of the solution\" → Social · Economic · Legal & Governance · Technological · Environmental (1 icon each)", size=10)

box(s, 6.7, 1.2, 6.35, """
## Benefits
- **Social :** exposes scam collection wallets (live case: 15 payers → 1 wallet → exchange); better recovery; deters mule networks
- **Economic :** no per-seat licence — reaches every district; capability stays in India
- **Legal & governance :** native BNSS / BSA outputs; FIU-IND status at point of action; full audit log
- **Technological :** indigenous, API-first, open data; self-hostable; SAHYOG / NCRP contract
- **Environmental :** hosted APIs, no energy-heavy nodes; paperless evidence packs
""", size=13, space=4)

notes(s, "Don't quote percentage improvements. Say: \"Measured today: 3 seconds from wallet to named exchange on a real case. The manual path the PS describes takes days.\"\n\n"
         "Detail if asked: scams covered — investment, task and 'digital arrest'; recovered proceeds return to victims; data sovereignty with production indexers at I4C.")

# ======================= SLIDE 6 — RESEARCH =======================
s = S[5]
clear_body(s)

box(s, 0.3, 1.2, 12.7, "## Comparison with existing systems")
table(s, 0.35, 1.85, 12.7, [
    ["Feature", "VASP-Trace", "Chainalysis Reactor", "TRM Forensics", "GraphSense (OSS)", "Manual explorers"],
    ["Multi-chain tracing", "✅ 6 chains", "✅", "✅", "✅ (BTC-focused)", "❌ one chain at a time"],
    ["Tron USDT focus", "✅", "✅", "✅", "❌ (30 Tron labels)", "✅ view only"],
    ["Deposit-address identification", "✅", "✅", "✅", "❌", "❌"],
    ["Indian VASP labels (CoinDCX, WazirX …)", "✅ curated", "?", "?", "❌", "partial tags"],
    ["FIU-IND registration-aware routing", "🛠", "❌", "❌", "❌", "❌"],
    ["BNSS notice + BSA s.63 certificate", "✅ s.63 · 🛠 routing", "❌", "❌", "❌", "❌"],
    ["SAHYOG request / NCRP + UPI fields", "🛠 / ✅", "❌", "❌", "❌", "❌"],
    ["Cross-case linking via deposit addresses", "🛠", "?", "?", "❌", "❌"],
    ["Bridge / cross-chain decoding", "🛠", "✅", "✅", "❌", "❌"],
    ["Published thresholds (no black box)", "✅", "❌", "❌", "✅", "—"],
    ["Self-hosted, data in India", "✅", "❌ SaaS", "❌ SaaS", "✅", "—"],
    ["Licence cost", "Free / open data", "Commercial", "Commercial", "Free", "Free"],
], colw=[3.5, 1.85, 1.85, 1.65, 1.8, 2.05], size=9, rowh=0.2)

box(s, 0.3, 4.5, 12.7, "_Competitor columns from public product descriptions, not independently tested; '?' = not publicly documented._", size=10)

box(s, 0.3, 4.8, 3.6, """
**Government & legal**
- [SAHYOG portal (MHA)](https://sahyog.mha.gov.in/)
- [FIU-IND VDA guidelines, 8 Jan 2026](https://fiuindia.gov.in/pdfs/downloads/VDA08012026.pdf)
- [Lok Sabha: 28 VDA SPs, Dec 2023](https://inc42.com/buzz/coindcx-wazirx-28-vda-service-providers-registered-fiu-govt/)
- [25 offshore notices, Oct 2025](https://coingeek.com/indian-regulator-issues-notices-to-25-offshore-crypto-platforms/) · [15 notices, Sep 2026](https://www.business-standard.com/markets/cryptocurrency/fiu-issues-notice-to-15-crypto-service-providers-asks-to-take-down-urls-126090900585_1.html)
- [Karnataka HC, X Corp v. UoI, 2025](https://indiankanoon.org/doc/7614885/)
- BNSS freeze: [AP HC](https://indiankanoon.org/doc/195992643/) · [Karnataka HC](https://indiankanoon.org/doc/14622554/) · [Bombay HC](https://indiankanoon.org/doc/22370397/)
""", size=9, space=0)

box(s, 4.0, 4.8, 3.6, """
**Research papers**
- [Meiklejohn et al., IMC 2013](https://cseweb.ucsd.edu/~smeiklejohn/files/imc13.pdf)
- [Victor, Ethereum clustering, FC 2020](https://www.ifca.ai/fc20/preproceedings/31.pdf)
- [Kappos et al., Peel a Million, USENIX 2022](https://www.usenix.org/conference/usenixsecurity22/presentation/kappos)
- [Möser & Narayanan, FC 2022](https://arxiv.org/abs/2107.05749)
- [Wang et al., ZKP mixers, 2022](https://arxiv.org/abs/2201.09035)
""", size=9, space=0)

box(s, 7.7, 4.8, 2.6, """
**Data & ecosystem**
- [Chainalysis Adoption Index 2025](https://www.chainalysis.com/blog/2025-global-crypto-adoption-index/)
- [Chainalysis oracle](https://go.chainalysis.com/chainalysis-oracle-docs.html)
- [GraphSense TagPacks](https://github.com/graphsense/graphsense-tagpacks)
- [OFAC address lists](https://github.com/0xB10C/ofac-sanctioned-digital-currency-addresses)
- [THORChain memos](https://dev.thorchain.org/concepts/memos.html)
- [Tornado Cash delisting, 2025](https://home.treasury.gov/news/press-releases/sb0057)
""", size=9, space=0)

placeholder(s, 10.4, 4.85, 2.65, 2.0, "[DIAGRAM D4 — Research workflow]",
            "PS analysis → Legal review → Literature → Data-source survey → Prototype → Live tests → Gap review → Roadmap", size=8)

notes(s, "The table is honest. We show where incumbents are ahead (bridge decoding) and where we're ahead (Indian labels, Indian legal outputs, self-hosted).\n\n"
         "Likely jury questions (keep for Q&A):\n"
         "1. SAHYOG has no public API — what did you integrate? Its published role is automated notices under IT Act s.79(3)(b). We built a SAHYOG-shaped request pack, an adapter and a mock with a proposed OpenAPI contract, all labelled MOCK. Going live is configuration once I4C exposes an endpoint.\n"
         "2. False-positive rate? Not yet measured. Next step: evaluate against known exchange deposit addresses. Every attribution shows its evidence, and unattributed ≠ clean.\n"
         "3. Can you freeze USDT on Tron? Exchange route: s.94 for KYC, and a freeze per the state HC's position. Issuer route: USDT has a contract-level blacklist (addBlackList / isBlackListed).\n"
         "4. Which BNSS section? s.94 for disclosure. For freezing, the 2026 High Courts split (AP: s.107 with a Magistrate's order; Karnataka and Bombay: s.106 allowed). The tool drafts both and the officer chooses.\n"
         "5. Why not buy Chainalysis? We're complementary: Indian labels, Indian legal outputs, NCRP/UPI linkage, self-hosting, and a cost that reaches every district.")

prs.save(OUT)
print("saved", OUT)
