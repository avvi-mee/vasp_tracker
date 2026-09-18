"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  addToWatchlist,
  checkWatchlistEntry,
  getWatchlist,
  removeFromWatchlist,
  updateWatchlistStatus,
  type WatchlistEntry,
} from "@/lib/api";
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

export default function AlertsPage() {
  return <AuthGuard>{(officer) => <AlertsContent officer={officer} />}</AuthGuard>;
}

function AlertsContent({ officer }: { officer: Officer }) {
  const [entries, setEntries] = useState<WatchlistEntry[]>([]);
  const [newAddress, setNewAddress] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);

  function reload() {
    getWatchlist()
      .then(setEntries)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load watchlist"));
  }

  useEffect(reload, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newAddress.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await addToWatchlist(newAddress.trim());
      setNewAddress("");
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add address");
    } finally {
      setAdding(false);
    }
  }

  async function withBusy(id: number, fn: () => Promise<unknown>) {
    setBusyId(id);
    setError(null);
    try {
      await fn();
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  const openAlerts = entries.filter((e) => e.alert_status === "open");
  const rest = entries.filter((e) => e.alert_status !== "open");

  return (
    <AppShell officer={officer} title="Alerts" subtitle="Watchlist addresses and what changed on them">
      <p className="mb-4 max-w-2xl text-xs text-ink-soft">
        Addresses under recurring watch. &quot;Check now&quot; re-runs a real trace — there&apos;s no
        scheduler yet, so nothing re-checks itself automatically. An alert opens only when risk
        actually worsens or the attributed entity changes since the last check, never on a routine
        &quot;still fine&quot; result.
      </p>

      <form onSubmit={handleAdd} className="mb-6 flex gap-2">
        <input
          value={newAddress}
          onChange={(e) => setNewAddress(e.target.value)}
          placeholder="Add an address to the watchlist"
          className="flex-1 rounded-md border border-wire bg-paper-raised px-3 py-2 font-mono text-sm outline-none focus:border-navy"
        />
        <button
          type="submit"
          disabled={adding}
          className="rounded-md bg-navy px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {adding ? "Adding…" : "Add to watchlist"}
        </button>
      </form>

      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>
      )}

      {openAlerts.length > 0 && (
        <section className="mb-6">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-red-800">
            Open alerts ({openAlerts.length})
          </h3>
          <div className="flex flex-col gap-2">
            {openAlerts.map((e) => (
              <WatchRow key={e.id} entry={e} busy={busyId === e.id} onAction={(fn) => withBusy(e.id, fn)} highlighted />
            ))}
          </div>
        </section>
      )}

      <section>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">
          All watched addresses ({rest.length})
        </h3>
        <div className="flex flex-col gap-2">
          {rest.map((e) => (
            <WatchRow key={e.id} entry={e} busy={busyId === e.id} onAction={(fn) => withBusy(e.id, fn)} />
          ))}
          {entries.length === 0 && <div className="text-xs text-ink-soft">Nothing on the watchlist yet.</div>}
        </div>
      </section>
    </AppShell>
  );
}

function WatchRow({
  entry,
  busy,
  onAction,
  highlighted,
}: {
  entry: WatchlistEntry;
  busy: boolean;
  onAction: (fn: () => Promise<unknown>) => void;
  highlighted?: boolean;
}) {
  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-3 rounded-md border px-3 py-2 text-xs ${
        highlighted ? "border-red-200 bg-red-50" : "border-wire bg-paper-raised"
      }`}
    >
      <div className="min-w-0">
        <div className="font-mono">
          {entry.address.slice(0, 10)}…{entry.address.slice(-6)} · {entry.chain}
        </div>
        <div className="flex items-center gap-2">
          <span style={{ color: entityColor(entry.last_entity_type) }}>
            {entry.last_checked_at ? entry.last_label ?? entityPlainLabel(entry.last_entity_type) : "not yet checked"}
          </span>
          <span className="font-semibold" style={{ color: RISK_COLOR[entry.last_risk_level] }}>
            {entry.last_risk_level}
          </span>
          {entry.alert_reason && <span className="text-red-800">— {entry.alert_reason}</span>}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Link href={`/?address=${encodeURIComponent(entry.address)}`} className="text-navy underline">
          Investigate
        </Link>
        <button
          disabled={busy}
          onClick={() => onAction(() => checkWatchlistEntry(entry.id))}
          className="rounded bg-ledger-soft px-2 py-1 font-semibold text-ink disabled:opacity-50"
        >
          {busy ? "Checking…" : "Check now"}
        </button>
        {entry.alert_status === "open" && (
          <button
            disabled={busy}
            onClick={() => onAction(() => updateWatchlistStatus(entry.id, "acknowledged"))}
            className="rounded bg-navy px-2 py-1 font-semibold text-white disabled:opacity-50"
          >
            Acknowledge
          </button>
        )}
        <button
          disabled={busy}
          onClick={() => onAction(() => removeFromWatchlist(entry.id))}
          className="text-ink-soft hover:text-red-800"
        >
          Remove
        </button>
      </div>
    </div>
  );
}
