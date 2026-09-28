"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type Case, type LinkCluster, getCases, getCoverage, getLinkClusters } from "@/lib/api";
import type { Officer } from "@/lib/auth";
import { entityColor, entityPlainLabel } from "@/lib/entityColors";
import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/AppShell";

export default function DashboardPage() {
  return <AuthGuard>{(officer) => <DashboardContent officer={officer} />}</AuthGuard>;
}

function DashboardContent({ officer }: { officer: Officer }) {
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [coverage, setCoverage] = useState<Record<string, number>>({});
  const [quickAddress, setQuickAddress] = useState("");
  const [clusters, setClusters] = useState<LinkCluster[]>([]);

  useEffect(() => {
    getCases().then(setCases).catch(() => {});
    getCoverage().then(setCoverage).catch(() => {});
    getLinkClusters().then(setClusters).catch(() => {});
  }, []);

  const stats = useMemo(
    () => ({
      total: cases.length,
      high: cases.filter((c) => c.risk_level === "high").length,
      medium: cases.filter((c) => c.risk_level === "medium").length,
      entities: new Set(cases.map((c) => c.label).filter(Boolean)).size,
      chains: new Set(cases.map((c) => c.chain)).size,
      pendingSahyog: cases.filter((c) => c.sahyog_status && c.sahyog_status !== "fulfilled").length,
    }),
    [cases]
  );

  function goToAddress(e: React.FormEvent) {
    e.preventDefault();
    if (!quickAddress.trim()) return;
    router.push(`/?address=${encodeURIComponent(quickAddress.trim())}`);
  }

  return (
    <AppShell officer={officer} title="Dashboard" subtitle="Your caseload, newest first">
<form onSubmit={goToAddress} className="mb-6 flex gap-2">
        <input
          value={quickAddress}
          onChange={(e) => setQuickAddress(e.target.value)}
          placeholder="Quick lookup — paste an address to jump into Investigate"
          className="flex-1 rounded-md border border-wire bg-paper-raised px-3 py-2 font-mono text-sm outline-none focus:border-navy"
        />
        <button type="submit" className="rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white">
          Investigate
        </button>
      </form>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Tile label="Total cases" value={String(stats.total)} />
        <Tile label="High risk" value={String(stats.high)} color="var(--color-risk-high-fg)" />
        <Tile label="Medium risk" value={String(stats.medium)} color="var(--color-risk-medium-fg)" />
        <Tile label="Entities identified" value={String(stats.entities)} />
        <Tile label="Chains covered" value={String(stats.chains)} />
        <Tile label="SAHYOG in progress" value={String(stats.pendingSahyog)} />
      </div>

      <section className="mb-6">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">
          Linked complaints — addresses shared across cases
        </h3>
        <p className="mb-2 text-xs text-ink-soft">
          A shared exchange deposit address means the same KYC&apos;d account received money from separate
          complaints: one notice can answer all of them.
        </p>
        <div className="flex flex-col gap-2">
          {clusters.map((cl) => (
            <div
              key={`${cl.chain}:${cl.address}`}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-wire bg-paper-raised px-3 py-2 text-xs"
            >
              <span className="font-mono">
                {cl.address.slice(0, 10)}…{cl.address.slice(-6)} · {cl.chain}
              </span>
              <span className={cl.roles.includes("deposit") ? "font-semibold text-navy" : "text-ink-soft"}>
                {cl.roles.includes("deposit") ? "Same beneficiary" : "Shared hop"} · {cl.case_count} cases
              </span>
              <span className="flex gap-2">
                {cl.case_ids.map((id) => (
                  <Link key={id} href={`/cases/${id}`} className="text-navy underline">
                    #{id}
                  </Link>
                ))}
              </span>
            </div>
          ))}
          {clusters.length === 0 && (
            <div className="text-xs text-ink-soft">No address is shared by two cases yet.</div>
          )}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">Recent cases</h3>
          <div className="flex flex-col gap-2">
            {cases.slice(0, 8).map((c) => (
              <Link
                key={c.id}
                href={`/cases/${c.id}`}
                className="flex items-center justify-between rounded-md border border-wire bg-paper-raised px-3 py-2 text-xs hover:bg-ledger-soft"
              >
                <span className="font-mono">
                  #{c.id} {c.seed_address.slice(0, 8)}…
                </span>
                <span style={{ color: entityColor(c.entity_type) }}>{c.label ?? entityPlainLabel(c.entity_type)}</span>
              </Link>
            ))}
            {cases.length === 0 && <div className="text-xs text-ink-soft">No cases yet — run a trace to start one.</div>}
          </div>
        </section>

        <section>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">
            Indian VASP dataset coverage
          </h3>
          <p className="mb-2 text-xs text-ink-soft">
            GraphSense carries almost none of these addresses — this dataset is ours. See{" "}
            <Link href="/coverage" className="text-navy underline">
              Coverage &amp; Methodology
            </Link>{" "}
            for the full picture.
          </p>
          <div className="flex flex-col gap-1">
            {Object.entries(coverage)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 8)
              .map(([name, count]) => (
                <div key={name} className="flex items-center justify-between text-xs">
                  <span>{name}</span>
                  <span className="font-mono">{count}</span>
                </div>
              ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function Tile({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border border-wire bg-paper-raised px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wide text-ink-soft">{label}</div>
      <div className="font-mono text-base font-semibold" style={{ color: color ?? "var(--color-ink)" }}>
        {value}
      </div>
    </div>
  );
}
