# Demo Addresses — Publicly Documented Scam/Hack/Sanctioned Wallets

Purpose: a small set of crypto addresses safe to use as demo/test data for the
VASP-attribution pipeline (SIH26182). All three are already public knowledge —
reported by mainstream press, a national blockchain-forensics firm, or a
government sanctions body — so using them as demo input does not expose any
private individual's or unreported victim's data.

---

## 1. The DAO hack (2016) — attacker contract

- **Address:** `0xF835A0247b0063C04EF22006eBe57c5F11977Cc4`
  (secondary attacker contract also cited alongside it: `0xC0ee9dB1a9e07CA63E4fF0d5Fb6F86BF68d47B89`)
- **Chain:** Ethereum
- **Associated with:** The DAO reentrancy exploit, June 17–18, 2016 — attacker
  drained ~3.6M ETH (~$60M at the time) from The DAO smart contract via a
  recursive-call ("reentrancy") bug. This event triggered the Ethereum/Ethereum
  Classic chain split.
- **Source:** Analysis of the DAO exploit, Hacking Distributed (Phil Daian /
  Emin Gün Sirer et al.), June 18, 2016 — https://hackingdistributed.com/2016/06/18/analysis-of-the-dao-exploit/
  (contract also visible on Etherscan: https://etherscan.io/address/0xF835A0247b0063C04EF22006eBe57c5F11977Cc4,
  created June 17, 2016, matching the exploit timeline)
- **Why safe to use:** One of the most widely written-about incidents in
  crypto history; address has been public in technical writeups and press for
  nearly a decade; no victim PII involved, it identifies the attacker's
  contract, not a person.

---

## 2. Tornado Cash — OFAC-sanctioned mixer address

- **Address:** `0x8589427373D6D84E98730D7795D8f6f8731FDA16`
- **Chain:** Ethereum
- **Associated with:** Tornado Cash, the Ethereum mixing service OFAC added to
  its Specially Designated Nationals (SDN) list on August 8, 2022 for
  laundering funds tied to the Lazarus Group and other hacks. This specific
  address is Tornado Cash's donation address, labeled `Tornado.Cash: Donate`
  on Etherscan and shown as "Blocked" by stablecoin issuers (USDC/USDT)
  post-sanction. (Note: OFAC lifted the Tornado Cash sanctions in March 2025
  after litigation, but the address's historical designation and the
  hack-laundering association remain well documented.)
- **Source:** OFAC recent action, August 8, 2022 — https://ofac.treasury.gov/recent-actions/20220808 ;
  also Etherscan label: https://etherscan.io/address/0x8589427373D6D84E98730D7795D8f6f8731FDA16
- **Why safe to use:** A government sanctions designation is about as public
  and citable as data gets; the address identifies a protocol/service
  contract, not a private individual.

---

## 3. Ronin Bridge hack / Lazarus Group — OFAC-sanctioned exploiter address

- **Address:** `0x098B716B8Aaf21512996dC57EB0615e2383E2f96`
- **Chain:** Ethereum
- **Associated with:** The March 23, 2022 Ronin Network (Axie Infinity) bridge
  hack — ~173,600 ETH and 25.5M USDC (~$600–625M) stolen. Chainalysis linked
  the address to the exploit; the FBI and U.S. Treasury attributed the hack to
  North Korea's Lazarus Group, and OFAC added this address to the SDN list on
  April 14, 2022. Etherscan labels it "Ronin Bridge Exploiter."
- **Source:** Treasury updates Lazarus Group sanctions with digital currency
  address linked to Ronin Bridge hack, CyberScoop, April 14, 2022 —
  https://cyberscoop.com/ronin-bridge-hack-lazarus-group-north-korea-treasury-sanctions/ ;
  also Etherscan: https://etherscan.io/address/0x098b716b8aaf21512996dc57eb0615e2383e2f96
- **Why safe to use:** Publicly named in a U.S. Treasury/OFAC sanctions
  action and extensively covered by press (CyberScoop, Elliptic, TRM Labs,
  Bleeping Computer); identifies a state-linked threat actor's wallet, not an
  individual victim.

---

## Notes & confidence

- **Confidence: high** for all three addresses — each is corroborated by at
  least two independent, citable sources (an official government sanctions
  action or a canonical technical writeup, plus a public block-explorer label
  or press report). Addresses were cross-checked against Etherscan's public
  name-tag system, which independently confirms the same attribution reported
  in the press/OFAC sources above.
- All three examples are on **Ethereum**. A Bitcoin-chain example was
  investigated (2016 Bitfinex hack, DOJ's 2022 Lichtenstein/Morgan seizure —
  https://www.justice.gov/usao-dc/2016-bitfinex-hack) but no specific BTC
  address string could be verified from public sources in this research pass
  (DOJ materials describe "a list of ~2,000 addresses" without publishing the
  full list in the press coverage reviewed). If a Bitcoin-chain demo address
  is needed later, PlusToken (2019 Ponzi, tracked by Chainalysis) is a
  promising lead but likewise needs a source that quotes a specific address
  string rather than just the case narrative — worth a follow-up pass before
  relying on any specific PlusToken address.
- None of these addresses represent a private individual's unreported wallet;
  all three are already the subject of public sanctions actions, DOJ/Treasury
  statements, or widely cited forensics writeups, so they are appropriate to
  hard-code as demo/seed data in the project.
