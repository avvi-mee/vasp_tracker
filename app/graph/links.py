"""Cross-case linking. NCRP's Suspect Repository links complaints by phone,
email, bank account and URL — not by wallet. Two complaints from different
states whose money reached the same exchange deposit address were paid to the
same KYC'd account, so one disclosure notice answers both FIRs.

Pure functions only; the storage and the join live in app/data/case_store.py.
"""

# Strongest first. A deposit address maps to one exchange customer; a shared
# seed is the same wallet reported twice; a shared intermediate hop is a lead
# (it may be a mule, or just a busy service nobody has labelled yet).
STRENGTH_ORDER = ("same_beneficiary", "same_wallet", "shared_intermediary")


def case_link_keys(trace_result) -> list[tuple[str, str]]:
    """(address, role) pairs worth matching across cases. The labelled
    terminal is left out: an exchange hot wallet would link every case that
    ever touched that exchange, which is noise, not intelligence."""
    path = list(trace_result.path or [])
    keys = [(trace_result.seed_address, "seed")]
    end = len(path) - 1 if trace_result.label else len(path)
    keys += [(addr, "path") for addr in path[1:end]]
    keys += [(d.address, "deposit") for d in confirmed_deposits(trace_result)]
    return list(dict.fromkeys(keys))


def confirmed_deposits(trace_result) -> list:
    """Every confirmed exchange deposit address on the trail — the primary
    verdict's and any side branch's. A split payment can land in two
    accounts at the same exchange; both are the same kind of lead."""
    found = [getattr(trace_result, "deposit", None)]
    found += [c.deposit for c in (getattr(trace_result, "candidates", None) or [])]
    by_address = {d.address: d for d in found if d and d.is_deposit_address}
    return list(by_address.values())


def exchange_clusters(trace_result) -> list[dict]:
    """Deposit addresses on this trail grouped by the exchange hot wallet they
    sweep into. Each group is one exchange cluster: addresses the same
    exchange controls. Across cases the same grouping is done in SQL
    (case_store.list_exchange_clusters) from the `sink` stored per deposit."""
    labels = {c.path[-1]: c.label for c in (getattr(trace_result, "candidates", None) or []) if c.path}
    if trace_result.path:
        labels.setdefault(trace_result.path[-1], trace_result.label)
    groups: dict[str, dict] = {}
    for d in confirmed_deposits(trace_result):
        g = groups.setdefault(d.vasp_address, {"hot_wallet": d.vasp_address, "label": labels.get(d.vasp_address),
                                               "deposit_addresses": []})
        g["deposit_addresses"].append(d.address)
    return sorted(groups.values(), key=lambda g: -len(g["deposit_addresses"]))


def _strength(my_role: str, their_role: str) -> str:
    roles = {my_role, their_role}
    if "deposit" in roles:
        return "same_beneficiary"
    if roles == {"seed"}:
        return "same_wallet"
    return "shared_intermediary"


def group_linked_rows(rows: list[dict]) -> list[dict]:
    """Collapse the join (one row per shared address) into one entry per
    linked case, strongest link first, then newest."""
    by_case: dict[int, dict] = {}
    for r in rows:
        entry = by_case.setdefault(r["case_id"], {
            **{k: r.get(k) for k in ("case_id", "seed_address", "chain", "label", "ncrp_ack_number",
                                     "cctns_fir_number", "status", "created_at")},
            "shared": [], "strength": STRENGTH_ORDER[-1],
        })
        entry["shared"].append({"address": r["address"], "my_role": r["my_role"], "their_role": r["their_role"]})
        s = _strength(r["my_role"], r["their_role"])
        if STRENGTH_ORDER.index(s) < STRENGTH_ORDER.index(entry["strength"]):
            entry["strength"] = s
    newest_first = sorted(by_case.values(), key=lambda e: str(e["created_at"] or ""), reverse=True)
    return sorted(newest_first, key=lambda e: STRENGTH_ORDER.index(e["strength"]))  # stable
