"""One plain-language paragraph explaining what a trace found.

Chainalysis's newest headline product, Rapid, exists because reading a graph
is a skill and most people who need the answer do not have it. A station-house
officer with a wallet address from an NCRP complaint should not have to
interpret exposure donuts and hop counts to learn whether there is anything
here worth an FIR.

Everything below is already computed elsewhere in this module's siblings —
trace.py found the entity, risk.py judged it, typology.py measured the
behaviour, sweep.py spotted the deposit address. This file adds no analysis
whatsoever. It only says out loud what those four already concluded.

Deterministic template, not a language model, and that is the whole design:

  - Every clause is emitted from a field that exists, so there is nothing for
    a model to invent. A tool whose output is attached to a s.63 BSA
    certificate cannot have a component that is usually right.
  - Same input, same sentence. A defence expert re-running the trace gets the
    text they are contesting, verbatim.
  - No API key, no per-request cost, no dependency that can be down at 2am.

The tone rule, applied throughout: never assert more than the underlying
field supports. "No entity matched" is not "clean", "not consulted" is not
"no hit", and a pruned branch gets said out loud rather than quietly dropped.
"""

_LEVEL_WORDS = {
    "high": "HIGH risk",
    "medium": "MEDIUM risk",
    "low": "LOW risk",
    "none": "no risk flag",
}


def _short(address: str) -> str:
    return f"{address[:10]}…{address[-6:]}" if len(address) > 20 else address


def _subject_sentence(result, chain: str) -> str:
    subject = getattr(result, "subject_entity", None)
    who = f"{chain} wallet {_short(result.seed_address)}" if chain else f"wallet {_short(result.seed_address)}"
    if subject and subject.get("label"):
        # Matters more than it looks: if the officer pasted an exchange's own
        # hot wallet, every behavioural finding below describes that exchange
        # doing its job, and risk.py has already declined to escalate on it.
        category = subject.get("category")
        named = f"{subject['label']} ({category})" if category else subject["label"]
        return f"The {who} is itself a known entity — {named}."
    return f"Subject: {who}."


def _destination_sentence(result) -> str:
    asset = (result.asset or ("funds", ""))[0] or "funds"
    if not result.label:
        return (f"Following the {asset} out of this wallet reached no named entity within "
                f"{result.max_hops or result.hop_count} hops. That is an unattributed trail, "
                f"not a clean one — it means no dataset this build carries has a name for where "
                f"the money stopped.")
    hops = "the wallet itself" if result.hop_count == 0 else (
        "1 hop" if result.hop_count == 1 else f"{result.hop_count} hops")
    confidence = f"{result.confidence:.0%}" if result.confidence is not None else "unstated"
    source = f", per {result.source}" if result.source else ""
    return (f"Following the {asset} reaches {result.label} "
            f"({result.entity_type or 'uncategorised'}) at {hops}, "
            f"attributed with {confidence} confidence{source}.")


def _risk_sentence(risk) -> str:
    level = _LEVEL_WORDS.get(risk.risk_level, risk.risk_level)
    basis = ("how this wallet itself behaves" if getattr(risk, "basis", "trail") == "behaviour"
             else "where the funds ended up")
    reason = f" {risk.risk_reason}" if risk.risk_reason else ""
    return f"Assessed {level}, on {basis}.{reason}"


def _behaviour_sentence(typologies) -> str:
    typologies = list(typologies or ())
    if not typologies:
        return ("No laundering typology matched this wallet's own transaction pattern. "
                "The detectors only cover five patterns, so this is silence from them, "
                "not a finding of good behaviour.")
    named = ", ".join(t.title.lower() for t in typologies)
    verb = "pattern matched" if len(typologies) == 1 else "patterns matched"
    return (f"{len(typologies)} laundering {verb} the wallet's own activity: {named}. "
            f"{typologies[0].explanation}")


def _screening_sentence(result) -> str:
    """Three sanctions sources, and this sentence has to be straight about
    which of them actually answered. The local OFAC snapshot always does. The
    two Chainalysis interfaces each have their own reason to be silent — the
    oracle is EVM-only, the API needs a key — and silence from either is not
    a clean result.
    """
    oracle = getattr(result, "oracle_sanctioned", None)
    api = getattr(result, "api_sanctioned", None)

    listed = sorted(set(oracle or ()) | set(api or ()))
    if listed:
        which = " and ".join(filter(None, [
            "the on-chain oracle" if oracle else "",
            "the Screening API" if api else "",
        ]))
        return (f"Chainalysis sanctions data ({which}) lists "
                f"{len(listed)} address{'' if len(listed) == 1 else 'es'} on this trail: "
                f"{', '.join(_short(a) for a in listed)}.")

    consulted = [name for name, value in
                 (("on-chain oracle", oracle), ("Screening API", api)) if value is not None]
    if not consulted:
        return ("Neither Chainalysis source was consulted — the on-chain oracle has no "
                "deployment on this chain and no Screening API key is configured. Only the "
                "local OFAC SDN snapshot screened this trail, so this is narrower coverage "
                "than it looks.")
    missing = [name for name, value in
               (("on-chain oracle", oracle), ("Screening API", api)) if value is None]
    sentence = (f"Screened against the local OFAC SDN snapshot and Chainalysis "
                f"({', '.join(consulted)}); nothing on this trail is listed.")
    if missing:
        sentence += f" The Chainalysis {', '.join(missing)} did not answer for this trail."
    return sentence


def _deposit_sentence(result) -> str:
    deposit = getattr(result, "deposit", None)
    if not deposit:
        return ""
    if not deposit.is_deposit_address:
        # The evidence object exists whenever the check ran — ran is not passed.
        return ("The hop before the exchange was checked and did not match a deposit-address "
                "pattern, so the request should name the exchange wallet and the transaction "
                "hashes rather than a single customer account.")
    return ("At least one hop behaves like an exchange deposit address rather than an "
            "independent party, so the exchange behind it — not the address holder — is who "
            "a disclosure request should name.")


def _caveat_sentence(result) -> str:
    caveats = list(getattr(result, "caveats", None) or ())
    if not caveats:
        return ""
    return "Limits on this search: " + " ".join(caveats)


def summarise(result, risk, typologies=(), chain: str = "") -> str:
    """The whole finding as one paragraph, in the order an officer needs it:
    who, where the money went, how bad, why, what was screened, what was
    missed."""
    parts = [
        _subject_sentence(result, chain),
        _destination_sentence(result),
        _risk_sentence(risk),
        _behaviour_sentence(typologies),
        _screening_sentence(result),
        _deposit_sentence(result),
        _caveat_sentence(result),
    ]
    return " ".join(p for p in parts if p)
