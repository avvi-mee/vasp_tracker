# D - Methods research (PARTIAL: web access was blocked partway through)

Date: 2026-09-27. Notes file: D:\VASP-Trace\docs\sih-review\notes\D-methods.md (same text as this report).

**Status.** 5 fetches worked. The next 3 WebFetch calls were refused by Claude Code's auto-mode safety check: the arXiv PDF of 2107.05749, the list of links on the TRON resource-model page, and the arXiv abstract of 2205.13882. The refusal message said it was reacting to earlier conversation content, that it "will keep firing for the rest of this conversation", and that the action should not be reworked to get around it. So I stopped fetching and did not use curl or the browser instead. **To finish this research, re-run the brief outside auto mode (the default permission mode) or in a fresh session.** Fetches used: 8 of 35.

Legend: **[V]** = checked against a page I fetched in this session. **[T]** = checked by the team (cited, not fetched again). **[U]** = NOT checked. It comes from background knowledge or is my own design inference. Don't cite it as fact until someone fetches the source.

## Clustering heuristics

**Citation correction [V].** https://arxiv.org/abs/2107.05749 is *not* "How to Peel a Million". It is Moser & Narayanan, "Resurrecting Address Clustering in Bitcoin", Financial Cryptography 2022. Its abstract says the authors:
- build a ground-truth set of Bitcoin transactions whose change output is known;
- develop a change-output predictor with a low false-positive rate;
- detect and prevent "cluster collapse";
- measure the effect on applications.

The correct ID for Kappos, Yousaf, Stutz, Rollet, Haslhofer & Meiklejohn, "How to Peel a Million: Validating and Expanding Bitcoin Clusters", is **arXiv 2205.13882**, submitted 27 May 2022 [V, arXiv search]. What the paper says is **not** checked, because the abstract fetch was blocked. That covers its peel-chain definition, its validation data and its precision numbers.

**Common-input ownership [T]:** Meiklejohn et al. 2013 (IMC'13).
**Ethereum deposit-address reuse, airdrop multi-participation, self-authorization [T]:** Victor 2020 (FC 2020).

**BlockSci change heuristics [V].** Source: https://citp.github.io/BlockSci/reference/heuristics/change.html. This is the documentation for the BlockSci software, not the 2017 paper.

| Heuristic | Rule (quoted or condensed) | Caveat the docs give |
|---|---|---|
| Address reuse | An input address that also appears as an output marks that output as change | none |
| Address type | If all inputs are one type (e.g. P2PKH or P2SH), change is likely the same type | none |
| Optimal change | "an output that is smaller than any of the inputs it is likely the change" | With one input, every output qualifies |
| Power of ten | Round outputs (multiples of 10^digits) are treated as payments, not change | none |
| Client change behaviour | "If an output is the first to send value to an address, it is potentially the change" (a fresh address) | none |
| Locktime (dynamic) | A spent output whose spending transaction matches this transaction's locktime behaviour | Also returns unspent outputs |
| Peeling chain (dynamic) | Returns "the outputs that continue the peeling chain" | Also returns unspent outputs |
| Spent / None | Utility filters. None switches off change-based clustering | none |

**Failure modes.**
- The docs warn that the dynamic heuristics also return unspent outputs, so combine them with the Spent filter.
- Optimal change tells you nothing when a transaction has one input.
- Moser & Narayanan's abstract confirms that change-based clustering can suffer cluster collapse [V]. Their numbers are not checked, because the full-text fetch was blocked.

**Not checked [U]:**
- nVersion, BIP69 ordering and RBF as wallet fingerprints for finding change.
- Detecting CoinJoin (Wasabi/Whirlpool equal outputs) and PayJoin (BIP78).
- The heuristic list in the BlockSci paper itself (arXiv 1709.02489 was not fetched).

**Account chains: TRON activation [V].** Source: https://developers.tron.network/docs/account.
- An account is activated by "Send[ing] any amount of TRX or a TRC-10 token from an existing account to the new address, or call[ing] wallet/createaccount".
- The sender pays a 1 TRX account-creation fee. Another 0.1 TRX is burned if its bandwidth is insufficient.
- If a contract sends TRX or TRC-10 to an unactivated address, that activates it at an extra cost of 25,000 Energy.
- TRC-20 transfers are not listed as a way to activate an account.
- The page does not say the activator is stored in the account record. An "activated by" link has to be worked out from the address's first incoming TRX, TRC-10 or CreateAccount transaction.

Is activation used as an attribution signal in any documented method? **Not found**; the search was blocked. Ethereum gas funding ("who paid the first gas") as an attribution link: **not checked**.

## Deposit-address & sweep detection

- **[T] Victor 2020, deposit-address reuse.** Exchange deposit addresses forward funds to the exchange's hot wallet. Senders who reuse the same deposit address are linked to each other.
- **[V] TRON resources that matter for sweeps.** Source: https://developers.tron.network/docs/resource-model.
  - Bandwidth pays for transaction bytes; Energy pays for contract execution.
  - Each account gets 600 free Bandwidth per rolling 24 hours.
  - More resources come from staking (Stake 2.0, `freezebalancev2`).
  - If resources run short, "the network can burn TRX from the sender's balance". For Energy, `fee_limit` caps how much TRX is burned.
- **[U] Expected sweep pattern.** This is my inference from the two items above, not a published method. Receiving TRC-20 does not activate an address, and sending TRC-20 out needs Energy. So an exchange deposit address that receives USDT must be activated and given resources before it can sweep. Expected pattern:
  1. USDT comes in from unrelated senders.
  2. A recurring feeder address F sends TRX (activation or fee top-up) or delegates energy.
  3. The full USDT balance goes to a hot wallet H, probably shortly afterwards.
  4. The same F and H show up across many such addresses.

  Test this on addresses already labelled as exchange deposit addresses before giving it any weight.
- **Not checked:**
  - How DelegateResource works, and whether delegations can be seen through free APIs.
  - Energy-rental markets.
  - Published work on the ERC-20 pattern where ETH for gas is topped up before the token sweep.

## Mixer detection

Nothing was checked in this session. The leads below are background knowledge [U]; check them at the URLs given.

**Tornado Cash**
- Legal timeline to check:
  - OFAC designation: 8 Aug 2022.
  - Van Loon v. U.S. Dept. of the Treasury, 5th Cir., 26 Nov 2024: immutable smart contracts are not "property" under IEEPA.
  - Treasury took Tornado Cash off the SDN list on 21 Mar 2025 (check sb0057).
- Developer cases:
  - Alexey Pertsev was convicted in the Netherlands (May 2024).
  - In Roman Storm's US trial (Aug 2025), the jury convicted on one count of conspiracy to run an unlicensed money-transmitting business and could not agree on the others.
- Check at https://home.treasury.gov/news/press-releases/sb0057 and https://en.wikipedia.org/wiki/Tornado_Cash.

**Deposit-to-withdrawal linking**
- Wang et al. (arXiv 2201.09035) and Tutela (arXiv 2201.06811) propose heuristics roughly like:
  - the same address deposits and withdraws;
  - a unique gas price;
  - deposit and withdrawal addresses linked by direct transactions;
  - multi-denomination use.
- The exact lists and their accuracy are **not checked**.

**BTC mixers (dates not checked)**
- ChipMixer taken down by DOJ/Europol (Mar 2023).
- Sinbad designated by OFAC (Nov 2023).
- Samourai Wallet founders arrested (Apr 2024, SDNY).
- zkSNACKs stopped running the Wasabi coordinator (June 2024).

**CoinJoin shape detection** (many equal-value outputs; Whirlpool's fixed pool sizes): **not checked**. A likely source is Stutz et al., "Adoption and Actual Privacy of Decentralized CoinJoin Implementations in Bitcoin" (AFT 2022); its arXiv ID is not confirmed.

## Confidence scoring

Nothing was checked in this session.

**Leads [U]**
- Moser, Bohme & Breuker, "Towards Risk Scoring of Bitcoin Transactions" (FC 2014 workshops): poison and haircut taint.
- Anderson et al., "Bitcoin Redux" (WEIS 2018): FIFO (Clayton's case).
- Tironsakkul et al. (2019): TIHO.
- How Chainalysis, TRM and Elliptic describe exposure scoring: not fetched.
- Noisy-OR, Bayesian and Dempster-Shafer combination: no primary source specific to forensics has been checked.

**Design suggestion [U, not tested against any literature].** Keep an explicit list of evidence for each attribution: the signal, its source, its hop distance, and whether it is independent of the others. Combine only independent signals, using noisy-OR:

P = 1 - PRODUCT(1 - w_i * r_i * d^h_i)

- w_i is how strong the signal is.
- r_i is how reliable the label source is. For example, an exchange hot wallet confirmed on-chain beats a community tag.
- d is a per-hop decay, e.g. 0.7-0.8.
- h_i is the number of hops.

Show direct exposure (h = 0) and indirect exposure separately. Vendors reportedly do this too, but their wording is not checked.

## Laundering typologies

The FATF "Virtual Assets Red Flag Indicators of ML/TF" (Sept 2020) and the FATF targeted updates (2024-2026) were **not fetched**. The Source column shows what is and isn't checked. The rules are simple suggestions a small team could build, and are [U] unless marked otherwise.

| Typology | On-chain detection rule (small-team version) | Source |
|---|---|---|
| Peel chain | 4 or more transactions in a row, each with 1-2 inputs and 2 outputs: a small payment plus a large remainder that is spent next in the same shape. Account-model version: each hop sends 90% or more of what it received to a fresh address within hours | [V] BlockSci peeling-chain heuristic; Kappos et al. 2022 (ID checked, content not) |
| Fan-out (smurfing/structuring) | One address pays 10 or more fresh addresses within an hour, in near-equal amounts or amounts just under a threshold | FATF 2020 [U] |
| Fan-in (aggregation) | 10 or more unrelated senders pay one address, followed by a single quick outflow | [T] Victor 2020 (the exchange deposit pattern is the harmless version) |
| Layering / rapid pass-through | Funds come in and 95% or more go out within an hour, repeated over 3 or more hops, with nothing held | FATF 2020 [U] |
| Chain-hopping | The path reaches a labelled bridge, swap or instant exchange. Mark the trace as "continues on another chain" | FATF 2020 [U] |
| Mixer | Interaction with labelled mixer contracts. A BTC transaction with 5 or more equal-value outputs is a CoinJoin, so don't apply common-input clustering to it | [T] Meiklejohn 2013 for common-input ownership; mixer patterns [U] |
| Nested service | The address paying into an exchange deposit address is itself a service cluster that receives from many senders | [U] |
| OTC/P2P broker | Many distinct counterparties, round USDT amounts, quick movement in and out of several exchanges | [U] |
| Gambling | The direct counterparty is a labelled gambling address or contract | FATF 2020 [U] |
| Address poisoning | A tiny, zero-value or fake-token transfer arrives from an address whose first and last 4-6 characters match a recent real counterparty. Flag any later payment to that lookalike | Tsuchiya et al., "Blockchain Address Poisoning" (USENIX Security 2025) [U] |
| Round-tripping | Funds leave a cluster and come back to it within 5 hops | [U] |

## Could not verify

1. Everything behind the three blocked fetches:
   - the Moser & Narayanan full text;
   - the TRON delegation link list;
   - the Kappos et al. abstract and content.
2. Kappos et al.'s peel-chain definition, validation data and precision numbers (arXiv 2205.13882).
3. Earlier Bitcoin work:
   - the heuristic list in the BlockSci paper (arXiv 1709.02489);
   - wallet fingerprinting (nLockTime, nVersion, BIP69);
   - CoinJoin and PayJoin detection.
4. TRON and Ethereum account signals:
   - TRON DelegateResource and energy rental;
   - whether TRON activation is used anywhere as an attribution signal;
   - Ethereum gas funding as a documented heuristic.
5. Mixers:
   - the Tornado Cash legal timeline (sb0057, Van Loon, Wikipedia);
   - Wang et al. and Tutela;
   - ChipMixer, Sinbad, Samourai and Wasabi.
6. Scoring:
   - Moser/Bohme/Breuker 2014;
   - sources for FIFO, LIFO and TIHO;
   - how Chainalysis, TRM and Elliptic score exposure;
   - sources for noisy-OR and Dempster-Shafer.
7. FATF:
   - the Sept 2020 red flags;
   - the targeted updates for 2024, 2025 and 2026 (including whether a 2026 update exists).
8. The address-poisoning paper.

## Implications for the team's tool

- **Fix the citation now.** Kappos et al. is arXiv 2205.13882. arXiv 2107.05749 is Moser & Narayanan (FC 2022), a separate paper that is also worth citing for false positives from change heuristics and for cluster collapse.
- **Tron/USDT first, one call per address.** Store each address's activation transaction: its first incoming TRX or TRC-10 transfer, or the CreateAccount call. Whoever sent it paid the 1 TRX fee. Some addresses receive USDT and later sweep it to the same wallet. If one activator shows up across many of them, it is a cheap signal that the activator may be an exchange's fee wallet. No documented method uses this for attribution, so treat it as supporting evidence and never the only evidence until it has been tested on known exchange addresses.
- **Tron deposit/sweep detection** combines Victor 2020's deposit rule with the TRON resource facts: USDT comes in from unrelated senders, feeder F provides a TRX top-up or energy, and the full USDT balance goes out to H. Require F or H to carry an independent label before calling the address an "exchange deposit address".
- **BTC.** Use common-input ownership [T], plus only the BlockSci change rules with low false positives: address type, fresh address and power of ten, applied together. Skip transactions that look like CoinJoin. Cap, or raise an alert on, sudden growth in a cluster's size (cluster collapse).
- **Report confidence as evidence, not a black-box number.** List each signal with its source, hop count and whether it is independent. If you show a score, use noisy-OR over independent signals with hop decay, and show direct and indirect exposure separately.
- **Treat mixers as a stop condition.** Report "exposure to mixer" and stop the trace. Don't claim a deposit-to-withdrawal link unless a published heuristic (still to be checked) fires.
- **Finish the checking outside auto mode.** Priority URLs:
  - https://home.treasury.gov/news/press-releases/sb0057
  - the FATF red-flags page and the targeted-update pages
  - arXiv 2205.13882, 2201.09035 and 2201.06811
  - the TRON Stake 2.0 and delegation docs
