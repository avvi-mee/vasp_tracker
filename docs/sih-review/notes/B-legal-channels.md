# B: Legal channels, status: BLOCKED, nothing verified (2026-09-27)

## What happened
- I sent the first 5 WebFetch calls in parallel: two indiankanoon.org searches (BNSS s.106 and s.107), the CERT-In Directions PDF of 28 Apr 2022, circle.com/legal/usdc-terms and tether.to/en/legal/.
- All 5 were refused by Claude Code's auto-mode safety check. The message said the refusal "reacts to earlier conversation content, not to the action itself", "will keep firing for the rest of this conversation", and that the action should not be retried or reworked.
- So I did not retry. I also did not use curl or browser tools to get around the block.
- **Result: I verified no facts. There is no sourced Findings section and no sourced routing table.**
- **Fix:** run this brief again outside auto mode (default permission mode) or in a fresh session.

## Leads for the rerun: from memory, NOT verified, do not cite
Every item below needs a fetched source before anyone uses it.

**Q1 (statutes and cases)**
- BNSS s.94 is probably the old CrPC s.91 (summons to produce documents; BNSS adds electronic communications).
- BNSS s.106 is probably the old CrPC s.102 (police power to seize property).
- BNSS s.107 is new: attachment, forfeiture or restoration of proceeds of crime, on a police application to a Magistrate. Check whether it needs a Magistrate's order, a show-cause notice first, and whether an ex parte interim order is allowed.
- BNSS s.112 is probably the old CrPC s.166A (letter of request for investigation outside India).
- Case lead: Kerala High Court, *Headstar Global Pvt Ltd v State of Kerala* (2025), on freezing bank accounts under s.106 vs s.107. Check the name, date and holding. Then use indiankanoon's own search for other High Court rulings (Delhi, Bombay, Madras) and any Supreme Court ruling.
- PMLA sections to check: s.5 (provisional attachment, 180 days), s.17 (search and seizure; freezing under s.17(1A)), s.50 (summons), s.12 and s.12A (reporting-entity records and access to them).
- IT Act sections to check: s.69 (interception and decryption), s.69A (blocking; was it used against offshore exchange URLs in 2023-24?), s.79 (intermediary safe harbour), and IT Rules 2021 r.3(1)(j) (information to authorised agencies within 72 hours).
- CERT-In Directions of 28 Apr 2022 under s.70B(6): check whether they require VASPs, exchanges and custodian wallet providers to keep KYC and transaction records for 5 years.

**Q2 (practical channels)**
- For each exchange, try its privacy policy, then its help centre's own search for "law enforcement".
- Circle: circle.com/legal/usdc-terms, the section on blocked addresses.
- Tether: the tether.to legal pages, and tether.io news for T3 Financial Crime Unit freeze totals.

**Q3 (MLAT)**
- MHA IS-II Division, "Comprehensive Guidelines for investigation abroad and issue of Letters Rogatory" (possibly Dec 2019). Find the current URL on mha.gov.in.

**Q4 (WazirX, Coinbase)**
- WazirX (Zettai Pte Ltd), Singapore scheme of arrangement: possibly court approval around Oct 2025, then relaunch. Check the dates and whether it is operating and registered in 2026.
- Coinbase: FIU-IND registration, possibly around Mar 2025.

**Q6 (tax)**
- Possible catch: the Income-tax Act 2025 may have replaced the 1961 Act from 1 Apr 2026. If so, s.115BBH and s.194S may have new numbers.
- Esya Centre study on TDS (2023): check its figures on users and volume moving offshore.

## Implications for the tool (design only; none of this relies on the unverified leads)
- Keep legal instruments as data, not code. Each route record should hold: act, section, a note on which older section it replaced, source URL, and a verified_on date. Sections get renumbered (CrPC became BNSS on 1 Jul 2024), and a hard-coded "s.91 CrPC" in a certificate template will go out of date.
- Leave a route's instrument field empty until a fetched source backs it. The UI should show "unverified" rather than a guess.
