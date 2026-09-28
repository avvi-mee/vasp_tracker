# A: SAHYOG / I4C research notes (SIH26182)

**Status, 2026-09-27: BLOCKED, and Q1–Q5 are unanswered.** WebFetch was refused on the first two calls (https://indiankanoon.org/doc/7614885/ and https://sahyog.mha.gov.in/). The refusal came from Claude Code's auto-mode safety check. It said the check was triggered by earlier conversation content, not by the fetch itself. It also said it "will keep firing for the rest of this conversation" and told me not to rework the action to get around it. So **0 fetches succeeded**. I did not try other routes (curl, PowerShell, browser automation), because they would be workarounds. Q6 is a design question and needs no web sources, so it is done below. **To finish Q1–Q5, re-run this brief outside auto mode (default permission mode) or in a fresh session.** The leads in "Could not verify" should make the re-run cheaper.

Labels: (a) official source · (b) reputable media · (c) inference.

## Findings

### Q1: Karnataka HC, X Corp v Union of India (24 Sep 2025)
- **Not extracted.** The fetch of https://indiankanoon.org/doc/7614885/ was blocked on 2026-09-27. This pass verified none of the following: legal basis (s.79(3)(b), IT Rules 2021 provisions), who may issue notices, how many agencies or intermediaries are onboarded, the workflow and timelines, any use beyond takedown, or the outcome and reasoning.
- Carried over from the brief (verified earlier by the caller, not re-checked here) (a): the judgment is at that URL, is dated 24 Sep 2025, and is by Justice M. Nagaprasanna.

### Q2: Other official SAHYOG material
- **Not reached.** The fetch of https://sahyog.mha.gov.in/ was blocked. I did not locate or read the user manual, FAQ, "Contact Details of the Authorized Officers" document or login page.
- Carried over from the brief (a), https://sahyog.mha.gov.in/: the portal exists "To automate the process of sending notices to intermediaries by the Appropriate Government or its agency under IT Act, 2000 to facilitate the removal or disabling of access to any information, data or communication link being used to commit an unlawful act". It brings "all Authorized Agencies of the country and all the intermediaries on one platform". The landing page says nothing about crypto, VASPs, data-disclosure requests or APIs.

### Q3: Are VASPs on SAHYOG? Do data-disclosure requests flow through it?
- **No evidence either way, because no fetches worked.** The Bitget press release (said to be from about 23 Jun 2025, claiming 45+ exchanges onboarded to SAHYOG for BNSS s.94 requests) was **not located**. I have not seen it and cannot say whether it exists or what it says.
- The only verified description of SAHYOG (the landing-page text above) covers takedown and disabling access under the IT Act. It does not mention data disclosure. (a)
- (c) Until a primary source says otherwise, treat "VASP data requests go through SAHYOG" as unconfirmed.

### Q4: Related I4C systems (NCRP, 1930 + CFCFRMS, Suspect Registry, Samanvaya/JMIS, CFMC, Cyber Commandos)
- **Not verified.** No page from i4c.mha.gov.in, cybercrime.gov.in, mha.gov.in or PIB was fetched. Recalled dates for the re-run to check are under "Could not verify".

### Q5: Central-government crypto initiatives
- **Nothing to report.** No pages were fetched.

## Proposed SAHYOG integration contract (c: inference, our design)

This does **not** describe any real SAHYOG interface, and I found no public SAHYOG API. The design assumes SAHYOG or an I4C gateway would expose one. If they don't, the same signed payload can ship as an export file that the officer uploads by hand.

**Who does what**
- **Initiator: an authorised officer of a requesting agency.** This follows the verified "Authorized Agencies" framing. The tool drafts the request. The officer reviews it, picks the legal provision, signs and submits. The tool never sends a request on its own, and never sends one straight to a VASP.
- **Hub: SAHYOG.** It routes the request to the VASP's registered account and relays status back.
- **Responder: the VASP,** through its SAHYOG account.
- **Tool:** receives status callbacks, stores the encrypted responses and keeps the audit trail.

**Endpoints (hub-side ones are hypothetical)**

| Side | Method | Path | Purpose |
|---|---|---|---|
| hub | GET | `/v1/intermediaries?category=VASP` | Directory of `intermediary_id`, legal name and supported request types. Maps a trace's attribution label to an ID that can be routed. |
| hub | POST | `/v1/vasp-requests` | Submit a request. The `Idempotency-Key` header equals `request_id`. Returns `202 {sahyog_ref, status}`. |
| hub | GET | `/v1/vasp-requests/{sahyog_ref}` | Status and response metadata. Fallback if callbacks fail. |
| tool | POST | `/v1/sahyog/events` | Signed status callback from the hub. |

Request types:
- `DISCLOSURE`
- `FREEZE`
- `RELEASE`: unfreeze, referencing the FREEZE via `related_ref`. A freeze with no release path is a trap.
- `PRESERVE`: optional.

Takedown is SAHYOG's own verified function and is out of scope for the tool.

**Request payload (example)**
```json
{
  "request_id": "<uuid-v4, also the idempotency key>",
  "request_type": "DISCLOSURE",
  "related_ref": null,
  "case": {"case_id": "<internal>", "ncrp_ack_no": "<optional>", "fir_no": "<optional>",
           "police_station": "<...>", "district": "<...>", "state": "<...>"},
  "requesting_agency": {"agency_id": "<hub-issued code>",
    "officer": {"officer_id": "<...>", "name": "<...>", "designation": "<...>", "phone": "<...>", "email": "<...>"}},
  "legal_basis": {"provision_code": "<officer picks from a hub-maintained list>", "order_ref": "<...>", "order_date": "2026-09-27"},
  "target": {"intermediary_id": "<from directory>", "name": "<...>"},
  "subjects": [{
    "chain": "tron", "asset": "USDT", "address": "<T...>", "role": "deposit_address",
    "tx_hashes": ["<...>"], "amount": "12500.00", "first_seen": "<ISO-8601>", "last_seen": "<ISO-8601>",
    "attribution": {"label": "<VASP label>", "confidence": 0.92, "method": "direct_deposit", "hops": 2}
  }],
  "time_window": {"from": "<ISO-8601>", "to": "<ISO-8601>"},
  "data_requested": ["KYC", "LOGIN_IP_DEVICE", "DEPOSIT_WITHDRAWAL_HISTORY", "LINKED_BANK_UPI"],
  "freeze": {"scope": "account", "amount_cap": null},
  "urgency": "NORMAL",
  "respond_by": "<ISO-8601>",
  "evidence": {"trace_run_id": "<...>", "snapshot": {"chain": "tron", "block_height": "<n>"},
               "tool_version": "<...>", "bundle_sha256": "<...>"},
  "iat": "<ISO-8601>", "nonce": "<random>"
}
```

**Status callback**
```json
{"event_id": "<uuid>", "sahyog_ref": "<...>", "request_id": "<...>",
 "type": "ACKNOWLEDGED | CLARIFICATION_SOUGHT | RESPONDED | ACTIONED | REJECTED | OVERDUE | WITHDRAWN",
 "at": "<ISO-8601>", "note": "<...>", "response": {"jwe": "<encrypted to requesting agency>", "sha256": "<...>"}}
```

**Security**
- **Mutual TLS in both directions** (tool to hub, and hub callbacks to tool). Certificates come from a government-trusted CA, and access tokens are bound to the client certificate (OAuth 2.0 mTLS, RFC 8705).
- **Two signatures.**
  - The officer signs the canonical payload (JWS, RFC 7515, over RFC 8785 JCS) with a personal signing credential. Which credentials count (DSC, eSign) is the hub's call.
  - The tool's deployment key signs the evidence bundle, to prove where it came from.
- **Officer identity** comes from the hub's or agency's identity provider (OIDC), with claims `officer_id`, `agency_id`, jurisdiction and roles. The **hub, not the tool,** decides who may submit which request type. The tool stores no officer passwords.
- **Replay protection:**
  - idempotency key, `iat` within ±5 minutes, and a nonce;
  - callbacks are signature-checked and deduplicated by `event_id`;
  - retries use exponential backoff.
- **Response data** (KYC, bank links) is encrypted to the requesting agency (JWE, RFC 7516). The tool stores only the ciphertext and a hash, decrypts only inside an officer session, and keeps it for a configurable period.
- **Data minimisation:** send only the addresses and tx hashes the request needs, never the whole graph.

**Audit**
- **Append-only, hash-chained log.** Each entry is `{seq, at_utc, actor, action, object, payload_sha256, prev_hash}`, and the head hash is signed daily.
- **Each request pins** the `trace_run_id`, the chain snapshot (block height), the tool version, the heuristics and the confidence. That lets anyone reproduce later the exact attribution the VASP was shown.
- **Reads are logged,** meaning views and exports of responses, not just writes.
- **Due-by timers are per provision and configurable,** because the real statutory timelines could not be verified.

## Could not verify
- Everything in Q1–Q5 above: legal basis and workflow from the judgment, SAHYOG manual/FAQ/officer-contact document/login page, VASP onboarding, the Bitget release, all I4C system details, any crypto initiative.
- **Leads for the re-run.** These are recalled from background knowledge and not checked. **Do not cite them.**
  - X Corp v UoI: widely reported as a **dismissal** of X's petition. Check the paragraphs on Shreya Singhal, s.69A vs s.79, and Article 19 rights for a foreign company.
  - Instruments reportedly at issue in that case, to check against the judgment text:
    - a MeitY Office Memorandum of 31 Oct 2023;
    - an MHA notification, recalled as March 2024, designating I4C to issue s.79(3)(b) notices.
  - I4C inaugurated about 10 Jan 2020.
  - NCRP (cybercrime.gov.in) opened to all cybercrime types about 30 Aug 2019.
  - CFCFRMS launched in 2021. The helpline is now 1930 (earlier 155260).
  - I4C's first Foundation Day, about 10 Sep 2024: recalled launches of Suspect Registry, CFMC, the Samanvaya platform and Cyber Commandos. Check PIB.
  - IT Rules 2021, Rule 3(1)(j): recalled as requiring intermediaries to give information or assistance to lawfully authorised agencies, with a 72-hour limit. It may be a legal hook for disclosure requests. Verify the text.
  - VASPs as PMLA reporting entities registered with FIU-IND (recalled notification: March 2023). A possible source for the VASP directory.
  - Bitget, about 23 Jun 2025: **no recollection at all.** Locate it on Bitget's own newsroom or blog, or drop the claim.

## Implications for the team's tool
- **Don't claim a SAHYOG API integration.** The only verified fact is that SAHYOG automates IT Act notices to intermediaries for takedown and disabling access. Pitch the tool as **"SAHYOG-ready"**: it produces a signed, machine-readable request packet and evidence bundle that an authorised officer files. Wire up an API only if MHA/I4C publishes one.
- **The officer picks the legal provision** from a configurable list. Never hard-code or auto-select s.79(3)(b) or BNSS sections. Takedown may rest on a different legal basis than disclosure or freeze, and that is exactly the part that is unverified.
- **Attribution output must be good enough to file.** For each subject that means chain, asset, address, tx hashes, amount, timestamps, hops, confidence and method, which is what a VASP needs to find the account. Block `FREEZE` on low-confidence attributions.
- **Keep the VASP directory (label to routable intermediary ID) as admin-editable data,** because SAHYOG's onboarded list could not be verified.
- **Pin reproducibility at request time.** Record block height and tool version, and put the SHA-256 of the evidence pack the tool already generates (commit 247b117, "PDF evidence pack") into the request.
- **Ship `RELEASE` alongside `FREEZE`, and track per-request status and overdue timers.** A freeze with no release path or tracking is a liability.
- **Accept NCRP acknowledgement numbers and FIR numbers as optional case keys** (c), so every request traces back to a complaint.
- **Re-run this research outside auto mode before any slide or README cites SAHYOG/I4C facts.**
