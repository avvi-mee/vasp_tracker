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
