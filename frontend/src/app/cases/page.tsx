"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { type Case, getCases } from "@/lib/api";
import type { Officer } from "@/lib/auth";
import { entityColor, entityPlainLabel } from "@/lib/entityColors";
import { AuthGuard } from "@/components/AuthGuard";
import { AppShell } from "@/components/AppShell";

const RISK_COLOR: Record<string, string> = {
  high: "var(--color-risk-high-fg)",
  medium: "var(--color-risk-medium-fg)",
  low: "var(--color-risk-low-fg)",
  none: "var(--color-risk-none-fg)",
};

export default function CasesPage() {
  return <AuthGuard>{(officer) => <CasesContent officer={officer} />}</AuthGuard>;
}

function CasesContent({ officer }: { officer: Officer }) {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    getCases()
      .then(setCases)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load cases"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    return cases.filter((c) => {
      if (statusFilter && c.status !== statusFilter) return false;
      if (riskFilter && c.risk_level !== riskFilter) return false;
      if (search && !c.seed_address.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [cases, statusFilter, riskFilter, search]);

  return (
    <AppShell officer={officer} title="Cases" subtitle="Saved investigations and their disclosure status">

      <div className="mb-4 flex flex-wrap gap-2 text-xs">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search address"
          className="rounded-md border border-wire bg-paper-raised px-3 py-1.5 font-mono outline-none focus:border-navy"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-wire bg-paper-raised px-2 py-1.5"
        >
          <option value="">All statuses</option>
          <option value="open">Open</option>
          <option value="pending">Pending</option>
          <option value="closed">Closed</option>
        </select>
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="rounded-md border border-wire bg-paper-raised px-2 py-1.5"
        >
          <option value="">All risk levels</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="none">None</option>
        </select>
        <span className="flex items-center text-ink-soft">
          {filtered.length} of {cases.length} case(s)
        </span>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>
      )}
      {loading && <div className="text-sm text-ink-soft">Loading…</div>}

      {!loading && !error && (
        <div className="overflow-x-auto rounded-md border border-wire">
          <table className="w-full text-left text-xs">
            <thead className="bg-ledger-soft text-ink-soft">
              <tr>
                <th className="px-2 py-1.5 font-medium">Case</th>
                <th className="px-2 py-1.5 font-medium">Address</th>
                <th className="px-2 py-1.5 font-medium">Chain</th>
                <th className="px-2 py-1.5 font-medium">Reached</th>
                <th className="px-2 py-1.5 font-medium">Risk</th>
                <th className="px-2 py-1.5 font-medium">Status</th>
                <th className="px-2 py-1.5 font-medium">SAHYOG</th>
                <th className="px-2 py-1.5 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} className="border-t border-wire/60 hover:bg-ledger-soft">
                  <td className="px-2 py-1.5">
                    <Link href={`/cases/${c.id}`} className="font-semibold text-navy hover:underline">
                      #{c.id}
                    </Link>
                  </td>
                  <td className="px-2 py-1.5 font-mono">
                    {c.seed_address.slice(0, 8)}…{c.seed_address.slice(-4)}
                  </td>
                  <td className="px-2 py-1.5">{c.chain}</td>
                  <td className="px-2 py-1.5">
                    <span style={{ color: entityColor(c.entity_type) }}>{c.label ?? entityPlainLabel(c.entity_type)}</span>
                  </td>
                  <td className="px-2 py-1.5">
                    <span className="font-semibold" style={{ color: RISK_COLOR[c.risk_level] ?? RISK_COLOR.none }}>
                      {c.risk_level}
                    </span>
                  </td>
                  <td className="px-2 py-1.5 capitalize">{c.status}</td>
                  <td className="px-2 py-1.5">{c.sahyog_status ? c.sahyog_status.replaceAll("_", " ") : "—"}</td>
                  <td className="whitespace-nowrap px-2 py-1.5 text-ink-soft">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-2 py-4 text-center text-ink-soft">
                    No cases match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
