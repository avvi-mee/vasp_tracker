"use client";

import { useMemo, useState } from "react";
import type { Edge } from "@/lib/api";

type SortKey = "timestamp" | "amount";

/** The "Transaction and Transfer UI" pattern the Reactor research confirmed
 * by name — a dedicated view for real transaction-level detail, separate
 * from the graph-level view, over every edge the search explored. */
export function TransactionsTable({ edges, onSelect }: { edges: Edge[]; onSelect: (edge: Edge) => void }) {
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [assetFilter, setAssetFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const assets = useMemo(
    () => Array.from(new Set(edges.map((e) => e.asset).filter((a): a is string => Boolean(a)))),
    [edges]
  );

  const rows = useMemo(() => {
    const fromTs = dateFrom ? new Date(dateFrom).getTime() / 1000 : null;
    const toTs = dateTo ? new Date(dateTo).getTime() / 1000 + 86400 : null; // inclusive of the whole "to" day
    const filtered = edges.filter((e) => {
      if (assetFilter && e.asset !== assetFilter) return false;
      if (fromTs != null && (e.timestamp ?? 0) < fromTs) return false;
      if (toTs != null && (e.timestamp ?? 0) > toTs) return false;
      return true;
    });
    return [...filtered].sort((a, b) =>
      sortKey === "timestamp" ? (b.timestamp ?? 0) - (a.timestamp ?? 0) : (b.amount ?? 0) - (a.amount ?? 0)
    );
  }, [edges, assetFilter, sortKey, dateFrom, dateTo]);

  if (edges.length === 0) return <div className="text-xs text-ink-soft">No transactions to show.</div>;

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
        <SortButton active={sortKey === "timestamp"} onClick={() => setSortKey("timestamp")}>
          Newest first
        </SortButton>
        <SortButton active={sortKey === "amount"} onClick={() => setSortKey("amount")}>
          Largest first
        </SortButton>
        {assets.length > 1 && (
          <select
            value={assetFilter}
            onChange={(e) => setAssetFilter(e.target.value)}
            className="rounded border border-wire bg-paper-raised px-2 py-1"
          >
            <option value="">All assets</option>
            {assets.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        )}
        <label className="flex items-center gap-1 text-ink-soft">
          From
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded border border-wire bg-paper-raised px-1.5 py-1"
          />
        </label>
        <label className="flex items-center gap-1 text-ink-soft">
          To
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded border border-wire bg-paper-raised px-1.5 py-1"
          />
        </label>
        {(dateFrom || dateTo) && (
          <button
            onClick={() => {
              setDateFrom("");
              setDateTo("");
            }}
            className="text-navy underline"
          >
            Clear dates
          </button>
        )}
        <span className="text-ink-soft">{rows.length} transaction(s)</span>
      </div>
      <div className="overflow-x-auto rounded-xl border border-wire bg-paper-raised">
        <table className="w-full min-w-[640px] text-left text-xs">
          <thead className="bg-ledger-soft text-ink-soft">
            <tr>
              <th className="px-2 py-1.5 font-medium">Time</th>
              <th className="px-2 py-1.5 font-medium">From</th>
              <th className="px-2 py-1.5 font-medium">To</th>
              <th className="px-2 py-1.5 font-medium">Amount</th>
              <th className="px-2 py-1.5 font-medium">Tx hash</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e, i) => (
              <tr
                key={i}
                onClick={() => onSelect(e)}
                className="cursor-pointer border-t border-wire/60 font-mono hover:bg-ledger-soft"
              >
                <td className="whitespace-nowrap px-2 py-1.5">
                  {e.timestamp ? new Date(e.timestamp * 1000).toLocaleString() : "—"}
                </td>
                <td className="px-2 py-1.5">{e.from.slice(0, 8)}…{e.from.slice(-4)}</td>
                <td className="px-2 py-1.5">{e.to.slice(0, 8)}…{e.to.slice(-4)}</td>
                <td className="whitespace-nowrap px-2 py-1.5">
                  {e.amount != null ? e.amount.toLocaleString(undefined, { maximumFractionDigits: 6 }) : "—"}{" "}
                  {e.asset}
                </td>
                <td className="px-2 py-1.5">{e.tx_hash ? `${e.tx_hash.slice(0, 10)}…` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SortButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded px-2 py-1 font-medium ${active ? "bg-navy text-white" : "bg-ledger-soft text-ink-soft"}`}
    >
      {children}
    </button>
  );
}
