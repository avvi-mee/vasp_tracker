"""Section 63 BSA evidence certificate generation.

A trace report is worthless in court unless it is admissible. Under section 63
of the Bharatiya Sakshya Adhiniyam, 2023 (in force 1 July 2024, successor to
s.65B of the Evidence Act), electronic records offered as secondary evidence
must be accompanied by the certificate in the Schedule to the Act — and
s.63(4) requires it "at each instance where it is being submitted for
admission". No foreign forensics tool emits this form.

Two things the statute settles, which shape this module:

1. The Schedule is split into PART A (filled by the party) and PART B (filled
   by an expert). Both are signed; s.63(4) requires the signature of the
   person in charge of the device *and* an expert. Part B's signature block
   additionally carries a designation.

2. Both parts require the hash value of the record and the algorithm used,
   chosen from SHA1 / SHA256 / MD5 / Other. We emit SHA-256: BPR&D's SOP on
   digital evidence describes MD5 and SHA-1 as less secure and being phased
   out. The Schedule also requires the hash report to be *enclosed*, which is
   what render_hash_report() produces.

What gets certified is this tool's own output file — not the blockchain. The
s.63(2) recitals ("lawful control", "regularly fed in the ordinary course of
activities") describe the computer that produced the record, and nobody has
lawful control over a public ledger. So the trace findings are frozen into a
canonical JSON record, that file is hashed, and the certificate attests to
that file.

Nothing here is signed or auto-affirmed. Every statement of personal
knowledge is left blank for the human who must swear to it. A tool that
pre-fills a solemn affirmation is forging one.

Sources: Gazette of India Extraordinary Pt. II s.1 No. 53, 25 Dec 2023
(Act 47 of 2023); BPR&D SOP on digital evidence; Pune Bar Association v.
Union of India, WP(C) 599/2026 (SC, 22 May 2026) on who may sign Part B.
"""
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime, timezone, timedelta

from fpdf import FPDF
from fpdf.enums import XPos, YPos

TOOL_NAME = "VASP Trace"
TOOL_VERSION = "1.0"
IST = timezone(timedelta(hours=5, minutes=30), "IST")

# Single source of truth for the three form filenames -- Part A's own text
# names the hash report enclosure by filename, and this project already
# shipped one drift bug (the text said .txt after the file itself became
# .pdf) from that name being duplicated by hand in two places.
PART_A_FILENAME = "CERTIFICATE-PART-A.pdf"
PART_B_FILENAME = "CERTIFICATE-PART-B.pdf"
HASH_REPORT_FILENAME = "HASH-REPORT.pdf"

# The Schedule's algorithm tickboxes, in the order the form lists them.
HASH_ALGORITHMS = ("SHA1", "SHA256", "MD5", "Other")
ALGORITHM_USED = "SHA256"


@dataclass
class EvidencePack:
    record_json: str        # the electronic record being certified, verbatim
    record_sha256: str      # its hash — the value that goes on the certificate
    record_filename: str
    generated_at_ist: str
    case_reference: str


def _jsonable(value):
    """Dataclasses (TraceResult, RiskAssessment, DepositEvidence) and the
    networkx graph need coercing before they will serialize."""
    if is_dataclass(value) and not isinstance(value, type):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _screening_provenance(result) -> dict:
    """What each sanctions source contributed to this trail.

    `vendored_ofac_sdn` is always consulted — it is a file in the repo, so it
    works offline and cannot be "unreachable", only stale. The Chainalysis
    on-chain oracle is read live and is EVM-only, so it has a third state
    beyond hit/clean: not_consulted.
    """
    oracle = getattr(result, "oracle_sanctioned", None)
    api = getattr(result, "api_sanctioned", None)
    return {
        "vendored_ofac_sdn": {
            "consulted": True,
            "note": "Local snapshot of Treasury's SDN list; as current as this build's copy.",
        },
        "chainalysis_onchain_oracle": {
            "consulted": oracle is not None,
            "method": "isSanctioned(address) — US/EU/UN designations, read live from chain",
            "addresses_listed": sorted(oracle) if oracle else [],
            "note": ("Consulted." if oracle is not None else
                     "Not consulted — no oracle deployment on this chain, the endpoint was "
                     "unreachable, or part of the trail could not be screened. Absence of a "
                     "hit here is NOT evidence of absence."),
        },
        "chainalysis_screening_api": {
            "consulted": api is not None,
            "method": "Chainalysis Sanctions Screening API — all chains, requires an API key",
            "addresses_listed": sorted(api) if api else [],
            "note": ("Consulted." if api is not None else
                     "Not consulted — no API key configured in this deployment, or part of "
                     "the trail could not be screened. Absence of a hit here is NOT evidence "
                     "of absence."),
        },
    }


def build_record(chain: str, result, risk, case_reference: str = "",
                 analyst_note: str = "", typologies=()) -> dict:
    """Freeze the trace findings into the structure that will be hashed.

    Deliberately excludes anything that changes between runs of the same
    trace — no wall-clock timestamp, no case id — because the hash has to be
    reproducible. A defence expert re-running the trace must be able to
    arrive at the same digest; a clock reading in the payload would guarantee
    they never do. Run time is recorded on the certificate instead.
    """
    hops = []
    for src, dst, edge in result.graph.edges(data=True):
        hops.append({
            "from_address": src,
            "to_address": dst,
            "transaction_hash": edge.get("tx_hash"),
            "value_raw": str(edge.get("value_wei")),  # str: these exceed float precision
        })

    record = {
        "record_type": "blockchain_wallet_attribution_report",
        "produced_by": {"tool": TOOL_NAME, "version": TOOL_VERSION},
        "case_reference": case_reference,
        "subject": {"seed_address": result.seed_address, "chain": chain},
        "attribution": {
            "entity_type": result.entity_type,
            "entity_label": result.label,
            "hops_traversed": result.hop_count,
            "confidence": result.confidence,
            "label_source": result.source,
            "outcome_note": result.reason,
        },
        "traced_path": result.path,
        "transactions_relied_upon": hops,
        "risk_assessment": {
            "risk_level": risk.risk_level,
            "risk_reason": risk.risk_reason,
            # Which question the level answers: what the funds reached
            # ("trail") or how the subject wallet behaves ("behaviour").
            "basis": getattr(risk, "basis", "trail"),
            "compliance_status": risk.compliance_status,
            "compliance_detail": risk.compliance_detail,
        },
        "analyst_note": analyst_note,
        # Which sanctions sources were actually consulted for this trail, and
        # what each said. In the record rather than only in risk_reason's prose
        # because "the oracle was not reachable" and "the oracle said clean"
        # are different claims, and a certificate that cannot tell them apart
        # is asserting coverage it does not have.
        #
        # Safe for the reproducible-hash rule above: unlike a clock reading or
        # a price, a sanctions verdict does not change merely because time
        # passed. If it differs on a re-run, the finding genuinely differs and
        # the digest ought to say so.
        "sanctions_screening": _screening_provenance(result),
    }
    if getattr(result, "deposit", None):
        record["deposit_address_finding"] = _jsonable(result.deposit)
    if typologies:
        # A risk level reached on behaviour must carry the behaviour into the
        # certified record. Otherwise the certificate asserts a conclusion
        # whose entire basis sits outside the evidence it certifies — and the
        # arithmetic (funder counts, hold times, split variance) is precisely
        # what a defence expert is entitled to re-derive and contest.
        record["behavioural_findings"] = [
            {"pattern": t.name, "title": t.title, "severity": t.severity,
             "confidence": t.confidence, "basis": t.explanation,
             "measurements": _jsonable(t.stats), "evidence": list(t.evidence)}
            for t in typologies
        ]
    return _jsonable(record)


def canonical_json(record: dict) -> str:
    """Byte-for-byte reproducible serialization. sort_keys and fixed
    separators mean two independent runs over identical findings produce an
    identical file, and therefore an identical hash. Without this the
    certificate's hash would not survive re-derivation."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_evidence_pack(chain: str, result, risk, case_reference: str = "",
                        analyst_note: str = "", typologies=()) -> EvidencePack:
    record = build_record(chain, result, risk, case_reference, analyst_note, typologies)
    record_json = canonical_json(record)
    short = result.seed_address[:10]
    return EvidencePack(
        record_json=record_json,
        record_sha256=sha256_hex(record_json),
        record_filename=f"trace-record-{short}.json",
        generated_at_ist=datetime.now(IST).strftime("%d/%m/%Y %H:%M"),
        case_reference=case_reference,
    )


def _tickboxes(options, selected) -> str:
    return "   ".join(f"[{'X' if o == selected else ' '}] {o}" for o in options)


def _blank(width: int = 44) -> str:
    return "_" * width


_SOURCE_TICKBOXES = ("Computer / Storage Media", "DVR", "Mobile", "Flash Drive",
                     "CD/DVD", "Server", "Cloud", "Other")


def _header(pack: EvidencePack, part: str, filled_by: str) -> str:
    date, time = pack.generated_at_ist.split(" ")
    return f"""\
{'=' * 78}
                              CERTIFICATE
                          [See section 63(4)(c)]
        Bharatiya Sakshya Adhiniyam, 2023 — Schedule to the Act
{'=' * 78}

                      PART {part} — To be filled by the {filled_by}

I, {_blank(40)} (Name),
Son / daughter / spouse of {_blank(34)},
residing / employed at {_blank(38)},
do hereby solemnly affirm and sincerely state and submit as follows:—

That the electronic / digital record produced herewith was retrieved from:

   {_tickboxes(_SOURCE_TICKBOXES[:4], 'Computer / Storage Media')}
   {_tickboxes(_SOURCE_TICKBOXES[4:], None)}

   Other (specify): {_blank(30)}

Make & Model ......... {_blank(36)}
Colour ............... {_blank(36)}
Serial Number ........ {_blank(36)}
IMEI / UIN / UID / MAC / Cloud ID (as applicable):
                       {_blank(36)}
"""


def _other_relevant_information(pack: EvidencePack, record: dict) -> str:
    """The Schedule has no field for a blockchain address, transaction hash or
    block height — it predates this use. They go under the form's catch-all
    "any other relevant information (specify)" rather than being omitted."""
    subject = record["subject"]
    attribution = record["attribution"]
    lines = [
        f"Nature of record ....... Blockchain wallet attribution report",
        f"Produced by ............ {TOOL_NAME} v{TOOL_VERSION}",
        f"Subject wallet address . {subject['seed_address']}",
        f"Distributed ledger ..... {subject['chain']}",
        f"Attributed entity ...... {attribution['entity_label'] or 'not attributed'}"
        f" ({attribution['entity_type']})",
        f"Hops traversed ......... {attribution['hops_traversed']}",
        f"Transactions relied on . {len(record['transactions_relied_upon'])}"
        f" (listed in the enclosed record)",
        f"Record file ............ {pack.record_filename}",
    ]
    if pack.case_reference:
        lines.insert(0, f"Case reference ......... {pack.case_reference}")
    if record.get("deposit_address_finding", {}).get("is_deposit_address"):
        lines.append(f"Deposit address ........ "
                     f"{record['deposit_address_finding']['address']}")
    body = "\n".join(f"   {line}" for line in lines)
    return f"Any other relevant information (specify):\n\n{body}\n"


def _hash_clause(pack: EvidencePack) -> str:
    return f"""\
I state that the HASH value/s of the electronic / digital record/s is

   {pack.record_sha256}

obtained through the following algorithm:—

   {_tickboxes(HASH_ALGORITHMS, ALGORITHM_USED)}

   Other: {_blank(30)} (Legally acceptable standard)

(Hash report to be enclosed with the certificate — see {HASH_REPORT_FILENAME})
"""


def _signature_block(pack: EvidencePack, with_designation: bool) -> str:
    date, time = pack.generated_at_ist.split(" ")
    who = ("(Name, designation and signature)" if with_designation
           else "(Name and signature)")
    return f"""\

                                        {_blank(34)}
                                        {who}

Date ... {date} (DD/MM/YYYY)
Time ... {time} hours IST (24-hour format)
Place .. {_blank(34)}
"""


def render_part_a(pack: EvidencePack, record: dict) -> str:
    """Part A — the party. Carries the s.63(2) recitals, which Part B omits."""
    return (
        _header(pack, "A", "Party")
        + f"""
{_other_relevant_information(pack, record)}
That the computer or communication device referred to above was, at all
material times, regularly used to store or process information for the
purposes of activities regularly carried on over that period by a person
having lawful control over the use of that device; that information of the
kind contained in the electronic record was regularly fed into it in the
ordinary course of those activities; that throughout the material part of
that period the device was operating properly; and that any period in which
it was not operating properly was not such as to affect the electronic record
or the accuracy of its contents.

The said computer or communication device is

   {_tickboxes(('Owned', 'Maintained', 'Managed', 'Operated'), None)}

   by me (select as applicable).

{_hash_clause(pack)}"""
        + _signature_block(pack, with_designation=False)
    )


def render_part_b(pack: EvidencePack, record: dict) -> str:
    """Part B — the expert. Per Pune Bar Association v. Union of India (SC,
    22 May 2026) a person with special skill and expertise in computer science
    and cyber forensics may sign, not only an Examiner notified under s.79A of
    the IT Act — though that order expressly left the question of law open, so
    a notified Examiner remains the safer signatory."""
    return (
        _header(pack, "B", "Expert")
        + f"""
{_other_relevant_information(pack, record)}
{_hash_clause(pack)}"""
        + _signature_block(pack, with_designation=True)
    )


def render_hash_report(pack: EvidencePack) -> str:
    """The enclosure the Schedule requires alongside the certificate, and the
    instructions a defence expert needs to re-derive the digest independently.
    A hash nobody can reproduce proves nothing."""
    return f"""\
{'=' * 78}
HASH REPORT — enclosure to the certificate under section 63(4), BSA 2023
{'=' * 78}

File certified ....... {pack.record_filename}
Algorithm ............ SHA-256 (FIPS 180-4)
Digest (hexadecimal) . {pack.record_sha256}
Size ................. {len(pack.record_json.encode('utf-8'))} bytes
Generated ............ {pack.generated_at_ist} IST
Produced by .......... {TOOL_NAME} v{TOOL_VERSION}

VERIFICATION
{'-' * 78}
The digest above is of the enclosed file exactly as supplied, with no
normalisation applied on reading. To verify independently:

   Windows   certutil -hashfile {pack.record_filename} SHA256
   Linux     sha256sum {pack.record_filename}
   macOS     shasum -a 256 {pack.record_filename}

Any single-byte alteration to the file produces a different digest, and the
certificate then no longer attests to the file presented.

REPRODUCIBILITY
{'-' * 78}
The record is serialised as JSON with sorted keys and fixed separators, and
contains no clock reading or run-specific identifier. Re-running the trace
over the same blockchain data therefore reproduces this file byte-for-byte
and this digest. Note what that does and does not establish: it shows the
report was derived from the ledger data it cites, not that the attribution
is correct.

SCOPE
{'-' * 78}
This certifies the integrity of the analysis report produced by the tool. It
does not and cannot certify the blockchain itself, which is a public
distributed ledger under no party's lawful control. Attribution of an address
to a service provider rests on published address labels and the transaction
graph, both recorded in the certified file; identification of the account
holder behind that address remains a matter for the service provider to
disclose.
"""


# fpdf2's core Courier font (no embedded TTF, no new font-file asset to ship)
# can't encode a handful of Unicode punctuation this module's own text uses —
# confirmed live: rendering crashed with FPDFUnicodeEncodingException on
# U+2014, the em dash used throughout the certificate prose. Transliterated
# to their plain-ASCII equivalents, which change nothing legally: a hyphen
# instead of an em dash affects typography, not the sworn statement's meaning.
_PDF_CHAR_REPLACEMENTS = {
    "—": "-", "–": "-",              # em dash, en dash
    "‘": "'", "’": "'",              # curly single quotes
    "“": '"', "”": '"',              # curly double quotes
    "…": "...",                           # ellipsis
}


def _pdf_safe(text: str) -> str:
    for src, dst in _PDF_CHAR_REPLACEMENTS.items():
        text = text.replace(src, dst)
    # Belt and braces: any character still outside Courier's reach becomes
    # "?" rather than throwing and producing no certificate at all — the
    # known substitutions above are the only ones this module has ever
    # needed, but a future edit adding a new character must not silently
    # break evidence generation for every trace.
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _text_to_pdf(text: str) -> bytes:
    """Renders plain text as a paginated PDF, Courier throughout so the
    form's own fixed-width layout (tickboxes, blank-line rules, the '=' / '-'
    separators) survives unchanged rather than being rebuilt in PDF markup.
    The render_part_a/b/hash_report functions below are untouched — this
    only changes the file format they're written into, not their content,
    so nothing about what the certificate says (or the s.63 reasoning behind
    it) changes along with this.
    """
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_font("Courier", size=9)
    for line in _pdf_safe(text).split("\n"):
        # Confirmed live: multi_cell's own default leaves the cursor at the
        # right edge of whatever it just rendered rather than the left
        # margin, so the following line's available width shrank to almost
        # nothing and fpdf2 raised "not enough horizontal space to render a
        # single character" on its very first character. Explicit reset.
        pdf.multi_cell(0, 4.2, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())


def build_certificate_bundle(chain: str, result, risk, case_reference: str = "",
                             analyst_note: str = "", typologies=()) -> tuple[EvidencePack, bytes]:
    """Returns the pack plus a zip: the certified record, both certificate
    parts, and the hash report. The record itself stays JSON, not PDF —
    canonical_json()'s reproducibility, and the hash computed over it, is
    the whole basis for the certificate; converting the certified file to a
    different format would mean the hash no longer describes what's enclosed.
    Everything meant to be printed, read and signed by hand is PDF."""
    pack = build_evidence_pack(chain, result, risk, case_reference, analyst_note, typologies)
    record = json.loads(pack.record_json)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(pack.record_filename, pack.record_json)
        bundle.writestr(PART_A_FILENAME, _text_to_pdf(render_part_a(pack, record)))
        bundle.writestr(PART_B_FILENAME, _text_to_pdf(render_part_b(pack, record)))
        bundle.writestr(HASH_REPORT_FILENAME, _text_to_pdf(render_hash_report(pack)))
    return pack, buffer.getvalue()
