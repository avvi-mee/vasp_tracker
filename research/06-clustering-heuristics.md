# Wallet-Clustering Heuristics: Common-Input-Ownership and Deposit-Address Sweep

Research note for SIH26182 (automated attribution of unknown crypto wallets to nearest VASPs).
Covers the two foundational clustering heuristics used to group individual on-chain addresses
into "entities" (a wallet, a person, or a VASP) before those entities can be attributed to a
known service.

---

## 1. Common-Input-Ownership Heuristic (UTXO chains: Bitcoin)

### Plain-language explanation

Bitcoin (and other UTXO-model chains) transactions can spend multiple "coins" (UTXOs) at once.
A transaction lists every address whose UTXOs it is spending as **inputs**, and where the money
goes as **outputs**. To spend a UTXO, whoever builds the transaction must produce a valid
signature from the private key that controls it.

The heuristic says: **if two or more addresses appear as inputs to the same transaction, they
are controlled by the same person or wallet.** This is because building that transaction
required signing with *every one* of those addresses' private keys at once — something only
the key-holder(s) can normally do together. Apply this rule transitively across many
transactions (if A and B co-sign one transaction, and B and C co-sign another, then A, B, and C
are all merged into one cluster) and you can collapse millions of pseudonymous addresses into a
much smaller number of "entities."

This is often called the **multi-input heuristic**, **co-spend heuristic**, or
**common-input-ownership heuristic (CIOH)**.

### Why it works (assumption) and failure modes

**Underlying assumption:** a rational actor does not hand their private key to a stranger. If a
single transaction needs signatures from addresses A, B, and C, the simplest explanation is that
one wallet (or one person) holds all three keys — not that three separate parties agreed to
jointly build and sign one transaction.

**Known failure modes / false positives:**
- **CoinJoin and similar joint-transaction protocols** are built specifically to defeat this
  heuristic: multiple independent parties contribute inputs to one transaction, so the "same
  signer" assumption becomes false by construction.
- **PayJoin / P2EP**, where the *receiver* also contributes an input to what looks like a normal
  two-party payment, making a CoinJoin-style transaction indistinguishable from an ordinary one.
- **Exchange/custodial batching**, where a service combines many customers' UTXOs into one
  outgoing transaction (e.g., batched withdrawals), incorrectly merging unrelated customers into
  the exchange's own cluster.
- **Multisig wallets**, where several distinct co-signers legitimately share control of the same
  addresses — correct in that narrow sense, but can over-merge if some of those signers are also
  independently active elsewhere.
- **Mining-pool payout transactions** with very large numbers of inputs/outputs, which can
  balloon a cluster with unrelated participants.

Even the original paper notes this heuristic is a *heuristic*, not a proof: it can be defeated by
deliberate multi-party protocols, and industry follow-up work (e.g. Gong et al., cited in later
literature) has measured non-trivial error rates for the plain multi-input rule alone, which is
why production tools pair it with additional heuristics (e.g. the change-address / one-time
change heuristic) and manual review rather than relying on it alone.

### Pseudocode

```text
# Input: list of transactions, each tx.inputs = [address, address, ...]
# Output: a partition of addresses into clusters (entities)

function commonInputOwnershipClustering(transactions):
    uf = new UnionFind()              # every address starts in its own singleton cluster

    for tx in transactions:
        inputAddrs = distinct(tx.inputs)
        if length(inputAddrs) < 2:
            continue                  # single-input tx gives no new linkage

        anchor = inputAddrs[0]
        for addr in inputAddrs[1:]:
            uf.union(anchor, addr)    # merge addr into anchor's cluster

    return uf.allClusters()           # each cluster = addresses believed co-owned
```

### Citation

Sarah Meiklejohn, Marjori Pomarole, Grant Jordan, Kirill Levchenko, Damon McCoy, Geoffrey M.
Voelker, Stefan Savage. **"A Fistful of Bitcoins: Characterizing Payments Among Men with No
Names."** Proceedings of the 2013 ACM Internet Measurement Conference (IMC '13), Barcelona,
Spain, pp. 127–140. DOI: [10.1145/2504730.2504747](https://doi.org/10.1145/2504730.2504747).
Author PDF: <https://cseweb.ucsd.edu/~smeiklejohn/files/imc13.pdf>

Confirmed by direct read of the paper's own PDF (converted to text and grepped). Exact
formalization, verbatim from Section 4.3, "Heuristic 1":

> "If two (or more) addresses are inputs to the same transaction, they are controlled by the
> same user; i.e., for any transaction *t*, all *pk* ∈ inputs(*t*) are controlled by the same
> user."
>
> "It is also quite safe: the sender in the transaction must know the private signing key
> belonging to each public key used as an input, so it is unlikely that the collection of public
> keys are controlled by multiple entities (as these entities would need to reveal their private
> keys to each other)."

Note: this exact idea (linking co-spent inputs) predates Meiklejohn et al. — the paper itself
says it "has already been used many times in previous work" — but this is the paper most
consistently cited as the canonical formalization and empirical validation of the heuristic
(it clustered ~12M keys into ~3.3M entities and won the ACM IMC Test-of-Time Award in 2024),
which is why it's treated as the primary reference. The CoinJoin failure mode is documented on
the [Bitcoin Wiki's Common-input-ownership heuristic page](https://en.bitcoin.it/wiki/Common-input-ownership_heuristic),
which states CoinJoin and PayJoin exist "specifically to break this heuristic."

---

## 2. Deposit-Address Sweep Pattern (account-based chains: Ethereum, BSC, Tron)

### Plain-language explanation

Account-based chains (Ethereum, BSC, Tron, and EVM-compatible chains generally) don't have
UTXOs, so the multi-input trick above doesn't apply. Instead, centralized exchanges (VASPs) use
a different, very common operational pattern:

1. When a customer wants to deposit funds, the exchange generates a **unique deposit address
   just for that customer** (so the exchange's backend can credit the right account without
   requiring users to enter a memo/reference for every deposit).
2. Funds sent to that address don't stay there — periodically (often within minutes to hours),
   the exchange's backend automatically **sweeps** (forwards) the balance from the deposit
   address into a small number of central **hot wallets**, usually leaving the deposit address
   near-empty afterward. Fees are typically paid out of the swept amount, so the forwarded
   amount is slightly less than what was received.
3. Because *every* customer's deposit address eventually forwards to the *same* small set of
   hot-wallet addresses, all addresses that forward to a given hot wallet within a plausible
   fee/time window can be clustered together as "deposit addresses belonging to Exchange X" —
   even without knowing anything about the depositing users themselves.

This is usually called **deposit address reuse (of the hot wallet)** or the **sweep / forwarding
heuristic**. It's the account-based-chain analogue of common-input-ownership: instead of
"co-signed together," the signal is "co-forwards to the same destination under matching
amount/time constraints."

### Why it works (assumption) and failure modes

**Underlying assumption:** deposit addresses are single-purpose and short-lived; nobody except
the exchange's sweep bot spends from them, and the sweep bot always forwards to one of a small,
stable set of hot wallets, on a fairly predictable cadence (to minimize idle-fund risk and gas
costs). If address D forwards ~100% of what it receives to known exchange hot wallet H within a
short delay, D is almost certainly a deposit address the exchange itself controls.

**Known failure modes / false positives:**
- **Pooled / shared deposit addresses with memo or tag-based identification.** Some
  services (and this is common on Tron, and on account systems like XRP/EOS) issue the *same*
  on-chain deposit address to many customers, distinguishing them only by an off-chain
  memo/tag/destination-tag. In that case the sweep pattern correctly identifies the address as
  exchange-controlled, but it does **not** separate individual depositors — treating "shared tag
  address" the same as "per-customer address" over-merges many unrelated users.
- **Irregular or batched sweeping.** Not every exchange sweeps promptly or 1:1. Some batch many
  deposit addresses' sweeps together, wait for a minimum balance threshold, or sweep on an
  irregular schedule — this weakens the tight amount/time-window assumption and causes false
  negatives (missed links) rather than false positives, but tuning the window too loosely to
  catch these cases increases false positives elsewhere.
- **Smart-contract forwarders.** Some exchanges (the paper cites Kraken's token deposits) use
  mass-deployed, near-identical smart contracts as deposit addresses that auto-forward with zero
  amount difference (the depositing EOA pays gas). These are easy to detect once one instance is
  known, but they look different from EOA-based sweeps and need separate handling.
  Different token types can also break the timing/amount assumptions used for the native-asset case.
- **Exchange-to-exchange transfers.** If one exchange's hot wallet happens to send funds through
  what looks like a forwarding pattern to another exchange's hot wallet, a naive implementation
  could incorrectly merge two unrelated VASPs into one cluster. Careful implementations
  explicitly exclude known exchange/hot-wallet addresses from being misclassified as "deposit
  addresses" of another exchange, and require a deposit address to forward to only a single
  downstream hot wallet.
- **Hot-wallet address rotation.** Exchanges occasionally rotate/replace their main hot wallet,
  which can split what should be one cluster into two, or (if not filtered) wrongly imply a
  relationship between the old and new custodian entity.
- **No ground truth.** Unlike Bitcoin clustering (where CoinJoin is an active, known defeat
  mechanism), the main practical limitation here is that the heuristic's precision hinges on
  already having a reliable seed list of known exchange hot-wallet addresses; unlabeled or newly
  created hot wallets won't be caught, and large unexpected clusters can form around addresses
  that are actually undocumented exchange wallets rather than errors.

### Pseudocode

```text
# Input: list of transfers (native-asset or token), each:
#   { from, to, amount, blockNumber, assetType }
# knownHotWallets: set of confirmed exchange hot/main wallet addresses
# amax: max allowed (received - forwarded) amount difference (fee slippage)
# tmax: max allowed block/time delay between receipt and forwarding
# Output: map of hotWallet -> set of addresses believed to be its deposit addresses

function depositSweepClustering(transfers, knownHotWallets, amax, tmax):
    incomingByAddr = groupBy(transfers, t -> t.to)
    outgoingByAddr = groupBy(transfers, t -> t.from)
    depositClusters = {}                       # hotWallet -> set(depositAddress)

    for addr, inList in incomingByAddr:
        if addr in knownHotWallets:
            continue                            # don't treat a hot wallet itself as a deposit addr
        outList = outgoingByAddr.get(addr, [])
        if outList is empty:
            continue                            # never forwarded anything, not a sweep pattern

        sweepTx = outList[0]                    # assume one dominant forwarding tx
        if sweepTx.to not in knownHotWallets:
            continue

        for inTx in inList:
            if inTx.assetType != sweepTx.assetType:
                continue
            amountDiff = inTx.amount - sweepTx.amount
            timeDiff   = sweepTx.blockNumber - inTx.blockNumber
            if 0 <= amountDiff <= amax and 0 <= timeDiff <= tmax:
                depositClusters[sweepTx.to].add(addr)   # addr = deposit address of this hot wallet

    return depositClusters
```

(This mirrors "Algorithm 1: Deposit address reuse heuristic" in the cited paper, simplified for
readability — the original also excludes known exchange and miner addresses from being
classified as depositing *users*, and separately builds a weakly-connected-components graph for
the exchange-entity side and the depositor side.)

### Citation

Friedhelm Victor. **"Address Clustering Heuristics for Ethereum."** In: *Financial Cryptography
and Data Security 2020 (FC 2020)*, Lecture Notes in Computer Science, vol. 12059, Springer,
pp. 617–633. DOI: [10.1007/978-3-030-51280-4_33](https://doi.org/10.1007/978-3-030-51280-4_33).
Preprint PDF: <https://www.ifca.ai/fc20/preproceedings/31.pdf> · Code:
<https://github.com/etherclust/etherclust>

Confirmed by direct read of the paper's own PDF (converted to text and grepped), Section 5.1,
"Deposit address reuse":

> "In order to sell Ether or other cryptoassets, a user has to send them to an exchange. To
> credit the assets to the correct account, exchanges typically create so-called deposit
> addresses, which will then forward received funds to a main address. As these deposit
> addresses are created per customer, multiple addresses that send funds to the same deposit
> address are highly likely to be controlled by the same entity... Their characteristic property
> is that they forward received amounts to a major exchange account. The forwarded amount is
> often slightly less than what was received, as the exchange has to pay for the transaction
> costs."

The paper reports this single heuristic was "responsible for most address clusters" found in
their study (13.1M forwarding traces identified across a 2019 Ethereum dataset, clustering
17.9% of all active addresses) — evidence it is the dominant real-world clustering signal for
account-based chains, ahead of the paper's other two heuristics (airdrop multi-participation,
transfer-authorization). Its own Discussion section (Section 7) is the source for the
"no ground truth / requires known hot-wallet seed list" limitation noted above.

---

## Notes & confidence

- **Sourcing method:** both citations were verified by downloading the authors' own PDF copies
  (UCSD author mirror for Meiklejohn et al.; IFCA preproceedings mirror for Victor), extracting
  text locally with `pdftotext`, and grepping for the exact heuristic definitions — not from
  memory or secondary paraphrase. Quotes above are verbatim from the papers.
- **Industry blog coverage was thin.** I looked for a Chainalysis/TRM Labs/Elliptic engineering
  writeup specifically on the sweep pattern; the pages found (e.g. TRM Labs' "Fundamentals of
  Cryptocurrency Transaction Tracing") mention deposit addresses and sweeps only at a marketing
  level with no technical depth on parameters or failure modes, so I relied on the peer-reviewed
  academic source instead, which is more rigorous and citable for a hackathon report anyway.
- **Confidence: high** that both heuristics are accurately and faithfully described, including
  their assumptions and the cited failure modes (CoinJoin/PayJoin for Heuristic 1; pooled/tag
  deposit addresses, irregular sweeping, smart-contract forwarders, and hot-wallet rotation for
  Heuristic 2) — these are drawn directly from the papers' own text or from a corroborating
  source (Bitcoin Wiki for the CoinJoin caveat).
- **Confidence: medium** on the exact numeric parameters shown in Victor (2020) (`amax` ≈
  0.01 ETH, `tmax` ≈ 3,200 blocks / ~13 hours) — these were empirically tuned on a specific 2019
  Ethereum dataset and should be treated as a starting point, not a universal constant; BSC and
  Tron will need their own tuning (different block times, different typical fee levels, and
  Tron's memo/tag-based deposit model in particular needs the "shared address" caveat applied
  more aggressively).
- **Pseudocode is illustrative, not production code** — simplified for a ~15–20 line budget per
  the task; a real implementation needs to handle multiple sweep transactions per deposit
  address, token vs. native-asset separation, and the exchange/miner exclusion lists the
  original algorithm applies.
- **Tooling pointer (not verified in depth, mentioned in Victor 2020's related-work section):**
  open-source implementations of the Bitcoin-side heuristics exist in **BlockSci** and
  **GraphSense**; may be worth evaluating for the UTXO side of this SIH project rather than
  reimplementing common-input-ownership from scratch.
