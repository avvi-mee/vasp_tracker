"""Chainalysis sanctions data — the two interfaces that are actually free.

Every Chainalysis product an investigator would recognise — Reactor, KYT,
Rapid, Wallet Scan, Storyline — is behind an enterprise contract. Two things
are not, and both are wired up here:

  1. THE ON-CHAIN ORACLE. A smart contract exposing
     `isSanctioned(address) -> bool`, readable by anyone with an `eth_call`.
     No key, no account, no agreement. EVM chains only.

  2. THE SANCTIONS SCREENING API. One HTTP endpoint, free, but it needs a key
     you request from Chainalysis. Covers *every* chain — Bitcoin, Tron and
     Solana included — and returns the designation itself rather than a bare
     boolean.

Together they are the only real Chainalysis data this project can honestly
claim to consult, and they complement each other exactly where it matters:
the oracle needs nothing but works on three of our six chains; the API needs
a key but works on all six.

Why either earns its place next to the OFAC SDN list already vendored in
app/data/ofac_sanctions.py: that list is a nightly snapshot of Treasury's XML
sitting in the repo, so it is exactly as fresh as the last `git pull` in that
directory, and it is OFAC-only. These are maintained by Chainalysis, read at
query time, and cover US, EU and UN designations. Independent sources
agreeing is worth more in an evidence pack than any one of them alone — and
where they disagree, that is itself worth showing an officer rather than
quietly resolving.

THE NONE CONTRACT, which every function here obeys:

    None   we did not get an answer — unsupported chain, no API key, network
           failure, or a response shape we do not recognise
    []     we asked and nothing was listed
    [...]  we asked and these were listed

None is never collapsed into False anywhere in this module, and callers must
not collapse it either. "We could not check" and "we checked and it was
clean" are different claims, and in a tool whose output is attached to a s.63
BSA certificate, letting the first read as the second is the quiet kind of
overstatement that discredits everything else on the page. The same
distinction is made for explorer risk flags in
app/data/chain_native_labels.py.
"""
import os
from concurrent.futures import ThreadPoolExecutor

import requests

from app.addresses import normalize_address as _normalize
from app.cache import cached_fetch

# --------------------------------------------------------------------------
# 1. On-chain sanctions oracle — free, no key, no signup.
#    Verified live against every chain in _CHAINS below.
# --------------------------------------------------------------------------

# keccak256("isSanctioned(address)")[:4]. Constant, so there is no reason to
# pull in a full ABI encoder for one call with one address argument.
_SELECTOR = "0xdf592f7d"

# Chainalysis deploys the same contract address across most EVM chains; Base
# is the exception. Documented at go.chainalysis.com/chainalysis-oracle-docs.html
_ORACLE_DEFAULT = "0x40C57923924B5c5c5455c48D93317139ADDaC8fb"
_ORACLE_BASE = "0x3A91A31cB3dC49b4db9Ce721F50a9D076c8D739B"

# currency code (app/chains.py) -> (public RPC, oracle contract).
# publicnode.com needs no key and no account, which keeps this integration
# free end to end — override per chain with e.g. ETH_RPC_URL if you'd rather
# point at your own node.
_CHAINS = {
    "ETH": ("https://ethereum-rpc.publicnode.com", _ORACLE_DEFAULT),
    "MATIC": ("https://polygon-bor-rpc.publicnode.com", _ORACLE_DEFAULT),
    "BNB": ("https://bsc-rpc.publicnode.com", _ORACLE_DEFAULT),
}

_TIMEOUT = 8  # short on purpose: corroboration is optional, a slow trace is not


def _collate(addresses: list[str], verdicts: list) -> list[str] | None:
    """Fold per-address verdicts into one answer for the trail, without
    letting a partial failure masquerade as a clean result.

    Screening a 12-hop trail means 12 independent lookups, and any one of
    them can come back None. Simply filtering for truthy verdicts — which is
    what this did first — reports "consulted, nothing listed" when one
    address was never actually checked. That is the precise None-collapse the
    module docstring forbids, reintroduced by a list comprehension.

    So:
      - any hit at all  -> report the hits. A positive finding stands on its
                           own; the addresses we failed to reach could only
                           add to it.
      - no hits, but at least one lookup failed -> None. We cannot say this
                           trail is clear when part of it went unexamined.
      - every lookup answered, none listed -> [] and we can say so.
    """
    hits = [a for a, verdict in zip(addresses, verdicts) if verdict]
    if hits:
        return hits
    if any(verdict is None for verdict in verdicts):
        return None
    return []


def supports(currency: str) -> bool:
    """Whether the oracle is deployed on this chain at all."""
    return (currency or "").upper() in _CHAINS


def _rpc_url(currency: str, configured: str) -> str:
    return os.environ.get(f"{currency.upper()}_RPC_URL") or configured


def is_sanctioned(address: str, currency: str) -> bool | None:
    """True/False from the oracle, or None when we could not get an answer —
    unsupported chain, RPC down, malformed reply. Never raises: a trace must
    not fail because a free public RPC had a bad minute.
    """
    currency = (currency or "").upper()
    entry = _CHAINS.get(currency)
    if entry is None:
        return None

    address = _normalize(address)
    if not (address.startswith("0x") and len(address) == 42):
        return None  # not an EVM address; nothing the oracle could answer about

    def _call() -> bool | None:
        rpc_url, oracle = entry
        body = {
            "jsonrpc": "2.0", "id": 1, "method": "eth_call",
            # 32-byte left-padded address argument, no 0x on the padding.
            "params": [{"to": oracle, "data": _SELECTOR + address[2:].lower().rjust(64, "0")}, "latest"],
        }
        try:
            resp = requests.post(_rpc_url(currency, rpc_url), json=body, timeout=_TIMEOUT)
            resp.raise_for_status()
            result = resp.json().get("result")
        except (requests.RequestException, ValueError):
            return None
        # A bool returns as a 32-byte word: 0x00..00 or 0x00..01.
        if not isinstance(result, str) or not result.startswith("0x"):
            return None
        try:
            return int(result, 16) == 1
        except ValueError:
            return None

    return cached_fetch(("CHAINALYSIS_ORACLE", currency, address), _call)


def screen_addresses(addresses, currency: str) -> list[str] | None:
    """Screen a whole trail against the on-chain oracle.

    Returns the sanctioned addresses (sorted), or None when this chain has no
    oracle — so callers can tell "clean" from "not checked" without a second
    flag to keep in sync.

    Concurrent because a 12-hop trail would otherwise add a dozen sequential
    round-trips to every trace; same ThreadPoolExecutor pattern the Etherscan
    client already uses for its three parallel endpoints.
    """
    if not supports(currency):
        return None
    unique = sorted({_normalize(a) for a in addresses})
    if not unique:
        return []
    with ThreadPoolExecutor(max_workers=8) as pool:
        verdicts = list(pool.map(lambda a: is_sanctioned(a, currency), unique))
    return _collate(unique, verdicts)


# --------------------------------------------------------------------------
# 2. Sanctions Screening API — free, but needs a requested key.
#
#    NOT LIVE-VERIFIED. The endpoint is confirmed reachable (it answers
#    403 {"message":"Invalid API Key"} without a key), but no key has been
#    provisioned yet, so the success-path response shape below comes from
#    Chainalysis's published documentation and has never been checked against
#    a real 200. This is the same caveat app/api_clients/bsctrace.py carries,
#    and it is flagged here for the same reason.
#
#    The risk that caveat usually implies — silently misreading a response —
#    is closed off structurally rather than by hoping: _identifications()
#    returns None for ANY payload it does not positively recognise. An
#    unexpected shape therefore degrades to "not consulted", which the risk
#    engine, the certificate and the UI all already handle honestly. It
#    cannot produce a false hit, and it cannot produce a false all-clear.
# --------------------------------------------------------------------------

API_URL = "https://public.chainalysis.com/api/v1/address/{address}"

# The documented category for a sanctions designation. Matched
# case-insensitively, and an identification whose category we do not
# recognise is reported rather than dropped — see _is_sanctions_hit.
_SANCTIONS_CATEGORY = "sanctions"


def api_key() -> str | None:
    return os.environ.get("CHAINALYSIS_API_KEY") or None


def api_available() -> bool:
    """Whether a key is configured. Everything below is inert without one, so
    the module is safe to ship before the key request is granted."""
    return api_key() is not None


def _is_sanctions_hit(identification: dict) -> bool:
    """Treat an identification as a sanctions listing unless it clearly says
    otherwise.

    The free API is documented as returning sanctions designations only, so
    an entry appearing at all is the signal. Requiring category == "sanctions"
    would mean a category rename upstream silently turns every hit into a
    miss — failing towards "clean", which is the wrong direction for this
    particular check to fail in.
    """
    category = str(identification.get("category") or "").lower()
    return category in ("", _SANCTIONS_CATEGORY) or "sanction" in category


def _identifications(address: str) -> list[dict] | None:
    """Raw identifications for one address, or None if we got no usable answer."""
    key = api_key()
    if not key:
        return None

    address = _normalize(address)

    def _call() -> list[dict] | None:
        try:
            resp = requests.get(API_URL.format(address=address),
                                headers={"X-API-Key": key, "Accept": "application/json"},
                                timeout=_TIMEOUT)
        except requests.RequestException:
            return None
        # 400/401/403 mean the key is wrong or the address was rejected —
        # either way we have no finding, not a clean result.
        if resp.status_code != 200:
            return None
        try:
            payload = resp.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        found = payload.get("identifications")
        if not isinstance(found, list):
            return None  # a shape we do not recognise is not an all-clear
        return [i for i in found if isinstance(i, dict)]

    return cached_fetch(("CHAINALYSIS_API", address), _call)


def api_designations(address: str) -> list[dict] | None:
    """The sanctions designations the API reports for one address.

    Unlike the oracle's bare bool these carry `name`, `description` and a
    `url` to the designation itself, which is what makes them worth putting
    in front of an officer rather than just colouring a badge red.
    """
    found = _identifications(address)
    if found is None:
        return None
    return [i for i in found if _is_sanctions_hit(i)]


def api_screen_addresses(addresses) -> list[str] | None:
    """Screen a whole trail against the API. Chain-agnostic — this is the
    half of Chainalysis's free offering that reaches Bitcoin, Tron and Solana,
    where the oracle has no deployment.

    Returns None if no key is configured, so an unconfigured build reports
    "not consulted" rather than a misleading empty result.
    """
    if not api_available():
        return None
    unique = sorted({_normalize(a) for a in addresses})
    if not unique:
        return []
    # Gentler than the oracle's 8: this is a rate-limited free API key rather
    # than a public RPC, and its published limits are not documented. Raise it
    # once a real key exists to measure against.
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(api_designations, unique))
    return _collate(unique, results)
