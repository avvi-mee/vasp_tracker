"use client";

import { useEffect, useState } from "react";
import { type ChainInfo, getChains, getCoverage } from "@/lib/api";
import type { Officer } from "@/lib/auth";
import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/AppShell";

const CHAIN_SOURCES: Record<string, { source: string; note: string }> = {
  Ethereum: { source: "Etherscan API V2", note: "Native + ERC-20 + internal transactions." },
  Polygon: { source: "Etherscan API V2", note: "Native + ERC-20 + internal transactions." },
  Tron: { source: "Tronscan API", note: "Native TRX + TRC20 (primarily USDT)." },
  Solana: { source: "Helius parsed-transaction API", note: "Native SOL + SPL tokens (USDC/USDT-SPL)." },
  Bitcoin: { source: "Blockchair API", note: "Dominant-output following. No common-input-ownership clustering yet." },
  "BNB Chain": { source: "NodeReal MegaNode", note: "Native BNB only — BEP-20 tokens not yet added." },
};

export default function CoveragePage() {
  return <AuthGuard>{(officer) => <CoverageContent officer={officer} />}</AuthGuard>;
}

function CoverageContent({ officer }: { officer: Officer }) {
  const [chains, setChains] = useState<Record<string, ChainInfo>>({});
  const [coverage, setCoverage] = useState<Record<string, number>>({});

  useEffect(() => {
    getChains().then(setChains).catch(() => {});
    getCoverage().then(setCoverage).catch(() => {});
  }, []);

  return (
    <AppShell officer={officer} title="Coverage & methodology" subtitle="What this tool can see, how well, and where it stops">
<p className="mb-6 max-w-2xl text-sm text-ink-soft">
        Every heuristic this tool uses states its own confidence and limits — on this page, not just
        in a docstring. That&apos;s a deliberate choice: the most-cited criticism of commercial blockchain
        analytics tooling in real court proceedings is the absence of a published methodology or
        error rate. Publishing ours costs little and answers the one objection that has actually
        mattered.
      </p>

      <Section title="Chain data sources">
        <div className="overflow-x-auto rounded-md border border-wire">
          <table className="w-full text-left text-xs">
            <thead className="bg-ledger-soft text-ink-soft">
              <tr>
                <th className="px-2 py-1.5 font-medium">Chain</th>
                <th className="px-2 py-1.5 font-medium">Status</th>
                <th className="px-2 py-1.5 font-medium">Source</th>
                <th className="px-2 py-1.5 font-medium">Coverage note</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(chains).map(([name, cfg]) => (
                <tr key={name} className="border-t border-wire/60">
                  <td className="px-2 py-1.5 font-semibold">{name}</td>
                  <td className="px-2 py-1.5">
                    <span style={{ color: cfg.enabled ? "var(--color-risk-none-fg)" : "var(--color-ink-soft)" }}>
                      {cfg.enabled ? "Live" : "Not wired up"}
                    </span>
                  </td>
                  <td className="px-2 py-1.5">{CHAIN_SOURCES[name]?.source ?? "—"}</td>
                  <td className="px-2 py-1.5 text-ink-soft">{CHAIN_SOURCES[name]?.note ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Indian VASP dataset">
        <p className="mb-2 text-xs text-ink-soft">
          GraphSense — the open labelling dataset everything else here leans on — is effectively blind
          to Indian exchanges (measured: WazirX 0 addresses, CoinDCX 0, ZebPay 0 before this dataset).
          Every address below was checksum-validated before being accepted; 158 of 270 candidate rows
          from the upstream source failed that check and were discarded rather than shipped.
        </p>
        <div className="flex flex-col gap-1">
          {Object.entries(coverage)
            .sort((a, b) => b[1] - a[1])
            .map(([name, count]) => (
              <div key={name} className="flex items-center justify-between text-xs">
                <span>{name}</span>
                <span className="font-mono">{count} address(es)</span>
              </div>
            ))}
        </div>
      </Section>

      <Section title="Sanctions screening — two sources, and where each one stops">
        <p className="mb-2 text-xs leading-relaxed text-ink-soft">
          A trail is screened against two independent sanctions sources. They are reported
          separately rather than merged, because they fail in different ways and an officer is
          entitled to know which one actually answered.
        </p>
        <div className="overflow-x-auto rounded-md border border-wire">
          <table className="w-full text-left text-xs">
            <thead className="bg-ledger-soft text-ink-soft">
              <tr>
                <th className="px-2 py-1.5 font-medium">Source</th>
                <th className="px-2 py-1.5 font-medium">Lists</th>
                <th className="px-2 py-1.5 font-medium">Chains</th>
                <th className="px-2 py-1.5 font-medium">Freshness</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-wire">
                <td className="px-2 py-1.5 text-ink-soft">Vendored OFAC SDN snapshot</td>
                <td className="px-2 py-1.5 text-ink-soft">US Treasury SDN only</td>
                <td className="px-2 py-1.5 text-ink-soft">Ethereum, Polygon, Bitcoin, Tron, Solana, BNB Chain</td>
                <td className="px-2 py-1.5 text-ink-soft">As current as this build&apos;s copy of the list. Works offline; can be stale.</td>
              </tr>
              <tr className="border-t border-wire">
                <td className="px-2 py-1.5 text-ink-soft">Chainalysis on-chain sanctions oracle</td>
                <td className="px-2 py-1.5 text-ink-soft">US, EU and UN designations</td>
                <td className="px-2 py-1.5 text-ink-soft">Ethereum, Polygon, BNB Chain (EVM only)</td>
                <td className="px-2 py-1.5 text-ink-soft">Read live from chain at query time. Unavailable if the RPC is down.</td>
              </tr>
              <tr className="border-t border-wire">
                <td className="px-2 py-1.5 text-ink-soft">Chainalysis Sanctions Screening API</td>
                <td className="px-2 py-1.5 text-ink-soft">US, EU and UN designations, with the designation text</td>
                <td className="px-2 py-1.5 text-ink-soft">All six — including Bitcoin, Tron and Solana</td>
                <td className="px-2 py-1.5 text-ink-soft">Read at query time. Requires an API key; reports &ldquo;not consulted&rdquo; without one.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-ink-soft">
          The oracle is Chainalysis&apos;s own <code>isSanctioned(address)</code> contract, queried
          directly over a public RPC — free, no API key, no vendor agreement. The Screening API is
          the other half of what Chainalysis gives away: it needs a key, but it reaches the three
          chains the oracle cannot. Everything else Chainalysis sells (Reactor, KYT, Rapid, Wallet
          Scan) is licensed and is not used here.
        </p>
        <p className="mt-2 text-xs leading-relaxed text-ink-soft">
          Each source reports its own result, and a source that could not answer says so rather
          than staying silent. <strong>A trail with no hit from a source that was never consulted
          has not been cleared by it</strong> — it was never shown to it, and the two are not the
          same claim. This also applies when only part of a trail could be screened: a partial
          result is reported as not consulted, never as a clean pass.
        </p>
      </Section>

      <Section title="Where a label comes from, and what it is worth">
        <p className="mb-2 text-xs leading-relaxed text-ink-soft">
          Attribution draws on three sources of different quality, and the verdict always names which
          one it used. They are consulted in this order; a stronger source always wins on collision.
        </p>
        <div className="overflow-x-auto rounded-md border border-wire">
          <table className="w-full min-w-[560px] text-left text-xs">
            <thead className="bg-ledger-soft text-ink-soft">
              <tr>
                <th className="px-2 py-1.5 font-medium">Source</th>
                <th className="px-2 py-1.5 font-medium">Confidence</th>
                <th className="px-2 py-1.5 font-medium">What it means</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-wire">
                <td className="px-2 py-1.5">VASP Trace Indian VASP dataset</td>
                <td className="px-2 py-1.5 font-mono">0.75 &ndash; 0.95</td>
                <td className="px-2 py-1.5">
                  Checksum-validated, per-address provenance recorded (operator-confirmed, confirmed,
                  or single-source).
                </td>
              </tr>
              <tr className="border-t border-wire">
                <td className="px-2 py-1.5">GraphSense TagPacks</td>
                <td className="px-2 py-1.5 font-mono">0.40 &ndash; 0.95</td>
                <td className="px-2 py-1.5">
                  Community-curated, versioned and citable, but stale on live addresses. Each pack states
                  how its labels were obtained: authority data 0.95, forensic 0.90, service or ledger data
                  0.85, web crawl 0.60, untrusted transaction 0.40 (unstated: 0.70).
                </td>
              </tr>
              <tr className="border-t border-wire">
                <td className="px-2 py-1.5">Block explorer address tags</td>
                <td className="px-2 py-1.5 font-mono">0.60</td>
                <td className="px-2 py-1.5">
                  A third-party convenience label, unversioned, withdrawable without notice. Harvested
                  from the explorer&apos;s own transaction responses because the curated sets simply do
                  not cover most live addresses. Treat a match sourced here as a lead to verify with the
                  exchange, not a finished attribution.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-ink-soft">
          Attribution confidence = distance score &times; (label confidence &divide; 0.95). The distance
          score is 0.90 &minus; 0.15 per hop (+0.05 for a cluster-defining label), kept between 0.30 and
          0.95. So a 0.60 explorer tag one hop away scores 0.47, while a 0.95 operator-confirmed address
          at the same distance scores 0.75.
        </p>
        <p className="mt-2 text-xs leading-relaxed text-ink-soft">
          Explorers also publish a per-address risk flag with no stated reasoning. It is used only as
          corroboration — it can raise an unattributed trail from low to medium and is recorded as such,
          and it never produces a verdict on its own.
        </p>
      </Section>

      <Section title="Laundering typologies — thresholds, stated so they can be argued with">
        <p className="mb-2 text-xs leading-relaxed text-ink-soft">
          Behavioural detection answers a different question from attribution: not &ldquo;where did the
          money go&rdquo; but &ldquo;how does this wallet behave&rdquo;. It needs no label, which is why a
          scam wallet can be flagged before anyone has named a single address on its trail. Every
          pattern below has innocent explanations — a payroll wallet fans out, an OTC desk funnels in, a
          merchant sweeps — so a match raises a question and sets priority. It does not prove anything.
        </p>
        <div className="overflow-x-auto rounded-md border border-wire">
          <table className="w-full min-w-[560px] text-left text-xs">
            <thead className="bg-ledger-soft text-ink-soft">
              <tr>
                <th className="px-2 py-1.5 font-medium">Pattern</th>
                <th className="px-2 py-1.5 font-medium">Fires when</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Many-to-one funnel", "5+ distinct funders and 3 or fewer destinations. High severity at 15+ funders."],
                ["Rapid layering", "Median hold under 60 min across 3+ sweeps, with 80%+ of received value forwarded on. High severity under 10 min across 10+ sweeps."],
                ["Fan-out / smurfing", "8+ destinations whose amounts vary by under 35% of the mean, inside a 7-day window. High severity at 20+ destinations."],
                ["Peel chain", "3+ consecutive hops each forwarding 70–99% of what arrived, never rising."],
                ["Round-amount structuring", "The same round figure (multiple of 100, at least 100) sent 4+ times."],
              ].map(([name, rule]) => (
                <tr key={name} className="border-t border-wire">
                  <td className="px-2 py-1.5 whitespace-nowrap">{name}</td>
                  <td className="px-2 py-1.5">{rule}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-ink-soft">
          These thresholds are judgement calls, not measured error rates, and this tool publishes no
          false-positive rate because it has not been validated against a labelled corpus. Saying so is
          the point: the criticism that has actually held up against commercial blockchain analytics in
          court is the absence of a published methodology, and an unpublished threshold cannot be
          cross-examined.
        </p>
      </Section>

      <Section title="Deposit-address detection (sweep.py)">
        <p className="text-xs text-ink-soft">
          Implements the deposit-address heuristic from Victor, Financial Cryptography 2020: an
          address that receives from many distinct counterparties and forwards the large majority of
          it onward to one exchange is scored as that exchange&apos;s deposit address, not just &quot;funds
          reached the exchange&quot;. Every score comes with its own caveats surfaced alongside it — e.g.
          when history may be truncated, when a meaningful share went to other destinations, or when
          the address sat on funds far longer than a sweep account usually would. A single high
          destination-share is deliberately never enough on its own to confirm a deposit address —
          that would misname an ordinary personal wallet as an exchange account, which is the false
          positive that actually costs an investigation credibility.
        </p>
      </Section>

      <Section title="Ranked-candidate trace — known limits, stated plainly">
        <p className="text-xs text-ink-soft">
          The trace ranks every material split at each hop rather than following one path, but it
          still bounds how many branches it follows (a materiality floor plus a total-branch cap) to
          keep a single trace from making an unbounded number of real API calls. When that cap drops a
          branch, it&apos;s recorded as an explicit caveat on the result, not silently absorbed — and worth
          knowing plainly: because the cap is value-based, a deliberately small split (structuring,
          done specifically to stay under a size threshold) is exactly the kind of path it could still
          miss. Exposure percentages (direct vs. indirect) are not a single pie and are not required
          to sum to 100% — a path exposed to more than one category counts toward each one.
        </p>
      </Section>
    </AppShell>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">{title}</h3>
      {children}
    </section>
  );
}
