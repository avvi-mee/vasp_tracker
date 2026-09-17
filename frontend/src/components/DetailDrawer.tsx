"use client";

import type { Candidate, Edge } from "@/lib/api";
import { entityColor, entityPlainLabel } from "@/lib/entityColors";
import type { GraphSelection } from "@/components/InvestigationGraph";

/** One consistent "inspect anything" interaction — clicking a graph node,
 * a graph edge, or a transactions-table row all land here, mirroring the
 * Reactor pattern of a dedicated detail view separate from the graph. */
export function DetailDrawer({
  selection,
  candidates,
  onClose,
}: {
  selection: GraphSelection | null;
  candidates: Candidate[];
  onClose: () => void;
}) {
  if (!selection) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/20" onClick={onClose}>
      <div
        className="h-full w-full max-w-sm overflow-y-auto bg-paper-raised p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} className="mb-4 text-xs text-ink-soft hover:text-ink">
          Close ✕
        </button>
        {selection.kind === "node" ? (
          <NodeDetail address={selection.address} candidates={candidates} />
        ) : (
          <EdgeDetail edge={selection.edge} />
        )}
      </div>
    </div>
  );
}

function NodeDetail({ address, candidates }: { address: string; candidates: Candidate[] }) {
  const matches = candidates.filter((c) => c.path.includes(address));
  const terminal = candidates.find((c) => c.path[c.path.length - 1] === address);

  return (
    <div>
      <div className="mb-3 break-all font-mono text-xs text-ink-soft">{address}</div>
      {terminal ? (
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
        </>
      ) : (
        <div className="text-sm text-ink-soft">
          Intermediate address — not itself attributed to a named entity.
        </div>
      )}
      <div className="mt-4 text-[11px] font-semibold uppercase tracking-wide text-ink-soft">
        Appears in {matches.length} traced path{matches.length === 1 ? "" : "s"}
      </div>
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
