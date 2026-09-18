"use client";

import { useState } from "react";
import { addToWatchlist, type Candidate, type Edge } from "@/lib/api";
import { entityColor, entityPlainLabel } from "@/lib/entityColors";
import type { GraphSelection } from "@/components/InvestigationGraph";

/** One consistent "inspect anything" interaction — clicking a graph node,
 * a graph edge, or a transactions-table row all land here, mirroring the
 * Reactor pattern of a dedicated detail view separate from the graph. */
export function DetailDrawer({
  selection,
  candidates,
  edges,
  chain,
  onClose,
}: {
  selection: GraphSelection | null;
  candidates: Candidate[];
  edges: Edge[];
  chain: string;
  onClose: () => void;
}) {
  if (!selection) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/20" onClick={onClose}>
      <div
        className="h-full w-full overflow-y-auto bg-paper-raised p-4 shadow-xl sm:max-w-md sm:p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} className="mb-4 text-xs text-ink-soft hover:text-ink">
          Close ✕
        </button>
        {selection.kind === "node" ? (
          <NodeDetail address={selection.address} candidates={candidates} edges={edges} chain={chain} />
        ) : (
          <EdgeDetail edge={selection.edge} />
        )}
      </div>
    </div>
  );
}

type Tab = "overview" | "transfers" | "counterparties";

function NodeDetail({
  address,
  candidates,
  edges,
  chain,
}: {
  address: string;
  candidates: Candidate[];
  edges: Edge[];
  chain: string;
}) {
  const [tab, setTab] = useState<Tab>("overview");
  const [watching, setWatching] = useState(false);
  const [watchError, setWatchError] = useState<string | null>(null);

  const matches = candidates.filter((c) => c.path.includes(address));
  const terminal = candidates.find((c) => c.path[c.path.length - 1] === address);
  const ownEdges = edges.filter((e) => e.from === address || e.to === address);
  const counterparties = Array.from(
    new Set(ownEdges.map((e) => (e.from === address ? e.to : e.from)))
  );

  async function handleWatch() {
    setWatching(true);
    setWatchError(null);
    try {
      await addToWatchlist(address, chain);
    } catch (err) {
      setWatchError(err instanceof Error ? err.message : "Failed to add to watchlist");
    } finally {
      setWatching(false);
    }
  }

  return (
    <div>
      <div className="mb-2 break-all font-mono text-xs text-ink-soft">{address}</div>
      <button
        onClick={handleWatch}
        disabled={watching}
        className="mb-3 rounded bg-ledger-soft px-2 py-1 text-[11px] font-semibold text-ink disabled:opacity-50"
      >
        {watching ? "Adding…" : "☆ Watch this address"}
      </button>
      {watchError && <div className="mb-3 text-[11px] text-red-800">{watchError}</div>}

      <div className="mb-3 flex gap-1 text-[11px]">
        <TabButton active={tab === "overview"} onClick={() => setTab("overview")}>
          Overview
        </TabButton>
        <TabButton active={tab === "transfers"} onClick={() => setTab("transfers")}>
          Transfers ({ownEdges.length})
        </TabButton>
        <TabButton active={tab === "counterparties"} onClick={() => setTab("counterparties")}>
          Counterparties ({counterparties.length})
        </TabButton>
      </div>

      {tab === "overview" &&
        (terminal ? (
          <>
            <div className="mb-1 text-lg font-semibold" style={{ color: entityColor(terminal.entity_type) }}>
              {terminal.label ?? "Unresolved"}
            </div>
            <div className="mb-3 text-xs text-ink-soft">{entityPlainLabel(terminal.entity_type)}</div>
            <Field label="Value share of this path" value={`${(terminal.value_share * 100).toFixed(1)}%`} />
            <Field label="Hops from seed" value={String(terminal.hop_count)} />
            {terminal.merged_path_count > 1 && (
              <Field label="Converging paths" value={String(terminal.merged_path_count)} />
            )}
            <div className="mt-4 text-[11px] font-semibold uppercase tracking-wide text-ink-soft">
              Appears in {matches.length} traced path{matches.length === 1 ? "" : "s"}
            </div>
          </>
        ) : (
          <div className="text-sm text-ink-soft">Intermediate address — not itself attributed to a named entity.</div>
        ))}

      {tab === "transfers" && (
        <div className="flex flex-col gap-2">
          {ownEdges.map((e, i) => (
            <div key={i} className="rounded border border-wire bg-ledger-soft px-2 py-1.5 text-[11px]">
              <div>
                {e.from === address ? "→ " : "← "}
                {(e.from === address ? e.to : e.from).slice(0, 10)}…
              </div>
              <div className="text-ink-soft">
                {e.amount} {e.asset} {e.timestamp ? `· ${new Date(e.timestamp * 1000).toLocaleDateString()}` : ""}
              </div>
            </div>
          ))}
          {ownEdges.length === 0 && <div className="text-xs text-ink-soft">No transfers in the explored graph.</div>}
        </div>
      )}

      {tab === "counterparties" && (
        <div className="flex flex-col gap-1">
          {counterparties.map((addr) => (
            <div key={addr} className="break-all rounded border border-wire bg-ledger-soft px-2 py-1 font-mono text-[11px]">
              {addr}
            </div>
          ))}
          {counterparties.length === 0 && <div className="text-xs text-ink-soft">None in the explored graph.</div>}
        </div>
      )}
    </div>
  );
}

function EdgeDetail({ edge }: { edge: Edge }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-soft">Transaction</div>
      <Field label="From" value={edge.from} mono />
      <Field label="To" value={edge.to} mono />
      <Field label="Amount" value={`${edge.amount ?? "—"} ${edge.asset ?? ""}`} />
      <Field label="Time" value={edge.timestamp ? new Date(edge.timestamp * 1000).toLocaleString() : "—"} />
      <Field label="Block" value={edge.block_number != null ? String(edge.block_number) : "—"} />
      <Field label="Tx hash" value={edge.tx_hash ?? "—"} mono />
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-[11px] text-ink-soft">{label}</div>
      <div className={mono ? "break-all font-mono text-xs" : "text-sm"}>{value}</div>
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`rounded px-2 py-1 font-semibold ${active ? "bg-navy text-white" : "bg-ledger-soft text-ink-soft"}`}
    >
      {children}
    </button>
  );
}
