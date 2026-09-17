"use client";

import { useMemo, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import type { Core, ElementDefinition, EventObject, NodeSingular, EdgeSingular } from "cytoscape";
import type { Candidate, Edge } from "@/lib/api";
import { entityColor } from "@/lib/entityColors";

export type GraphSelection =
  | { kind: "node"; address: string }
  | { kind: "edge"; edge: Edge };

interface Props {
  seedAddress: string;
  candidates: Candidate[];
  edges: Edge[];
  activeAsset: string | null;
  onSelect: (selection: GraphSelection) => void;
}

function formatAmount(n: number): string {
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (n >= 1) return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return n.toLocaleString(undefined, { maximumFractionDigits: 6 });
}

/** The screen that actually justifies moving off Streamlit: every address
 * and transaction the ranked-candidate search explored, not just the single
 * winning path — Reactor's core interaction (expand, explore, follow a
 * branch) over data this project already computes server-side. Node sizing
 * and edge value labels are deliberately borrowed from a real Reactor
 * screenshot: attributed entities read as bigger and visually distinct from
 * plain intermediate hops, and an edge's amount is legible on the graph
 * itself, not hidden behind a click. */
export function InvestigationGraph({ seedAddress, candidates, edges, activeAsset, onSelect }: Props) {
  const cyRef = useRef<Core | null>(null);
  const [search, setSearch] = useState("");
  const [searchError, setSearchError] = useState(false);

  const elements = useMemo<ElementDefinition[]>(() => {
    const terminalInfo = new Map<string, { entityType: string; label: string | null }>();
    for (const c of candidates) {
      const terminal = c.path[c.path.length - 1];
      terminalInfo.set(terminal, { entityType: c.entity_type, label: c.label });
    }

    const nodeIds = new Set<string>([seedAddress]);
    edges.forEach((e) => {
      nodeIds.add(e.from);
      nodeIds.add(e.to);
    });

    const nodes: ElementDefinition[] = Array.from(nodeIds).map((id) => {
      const info = terminalInfo.get(id);
      const isSeed = id === seedAddress;
      const isLabeled = Boolean(info?.label);
      const short = `${id.slice(0, 6)}…${id.slice(-4)}`;
      return {
        data: {
          id,
          label: info?.label ? `${info.label}\n${short}` : short,
          isSeed,
          isLabeled,
          entityType: info?.entityType ?? "unknown",
        },
      };
    });

    const edgeEls: ElementDefinition[] = edges.map((e, i) => ({
      data: {
        id: `e${i}`,
        source: e.from,
        target: e.to,
        amount: e.amount ?? 0,
        asset: e.asset ?? "",
        displayLabel: e.amount != null ? `${formatAmount(e.amount)} ${e.asset ?? ""}`.trim() : "",
        dimmed: activeAsset != null && e.asset !== activeAsset,
      },
    }));

    return [...nodes, ...edgeEls];
  }, [seedAddress, candidates, edges, activeAsset]);

  const stylesheet = useMemo(
    () => [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "font-size": 8,
          "text-wrap": "wrap" as const,
          "text-valign": "bottom" as const,
          "text-margin-y": 6,
          color: "var(--color-ink)",
          "background-color": (n: NodeSingular) => entityColor(n.data("entityType")),
          // Attributed entities read as bigger and visually distinct from
          // plain intermediate hops — a seed gets the biggest, gold-ringed
          // treatment; a labeled terminal is next; an unlabeled hop is a
          // small plain dot, matching the hierarchy a real Reactor graph uses.
          width: (n: NodeSingular) => (n.data("isSeed") ? 32 : n.data("isLabeled") ? 24 : 13),
          height: (n: NodeSingular) => (n.data("isSeed") ? 32 : n.data("isLabeled") ? 24 : 13),
          "border-width": (n: NodeSingular) => (n.data("isSeed") ? 3 : n.data("isLabeled") ? 2 : 0),
          "border-color": (n: NodeSingular) => (n.data("isSeed") ? "var(--color-gold)" : "var(--color-ink)"),
        },
      },
      {
        selector: "node.search-match",
        style: { "border-width": 3, "border-color": "var(--color-gold)" },
      },
      {
        selector: "edge",
        style: {
          width: (e: EdgeSingular) => Math.max(1, Math.min(9, Math.log10((e.data("amount") || 0) + 1) * 2.5)),
          "line-color": "var(--color-wire)",
          "target-arrow-color": "var(--color-wire)",
          "target-arrow-shape": "triangle" as const,
          "curve-style": "bezier" as const,
          opacity: (e: EdgeSingular) => (e.data("dimmed") ? 0.15 : 0.9),
          label: "data(displayLabel)",
          "font-size": 7,
          color: "var(--color-ink-soft)",
          "text-background-color": "var(--color-paper-raised)",
          "text-background-opacity": 0.85,
          "text-background-padding": 1,
          "text-rotation": "autorotate" as const,
        },
      },
    ],
    []
  );

  function runSearch(e: React.FormEvent) {
    e.preventDefault();
    const cy = cyRef.current;
    if (!cy || !search.trim()) return;
    cy.nodes().removeClass("search-match");
    const match = cy.nodes().filter((n) => n.id().toLowerCase().includes(search.trim().toLowerCase()));
    if (match.length === 0) {
      setSearchError(true);
      return;
    }
    setSearchError(false);
    match.addClass("search-match");
    cy.animate({ fit: { eles: match, padding: 60 }, duration: 300 });
  }

  return (
    <div>
      <form onSubmit={runSearch} className="mb-2 flex gap-2">
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setSearchError(false);
          }}
          placeholder="Find an address in this graph"
          className={`flex-1 rounded-md border bg-paper-raised px-2 py-1 font-mono text-xs outline-none focus:border-navy ${
            searchError ? "border-red-300" : "border-wire"
          }`}
        />
        <button type="submit" className="rounded-md bg-ledger-soft px-3 py-1 text-xs font-semibold text-ink-soft">
          Find
        </button>
      </form>
      <CytoscapeComponent
        elements={elements}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        stylesheet={stylesheet as any}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        layout={{ name: "breadthfirst", directed: true, roots: [seedAddress], spacingFactor: 1.3, padding: 20 } as any}
        style={{ width: "100%", height: "420px" }}
        className="rounded-lg border border-wire bg-paper-raised"
        cy={(cy: Core) => {
          cyRef.current = cy;
          cy.removeAllListeners();
          cy.on("tap", "node", (evt: EventObject) => {
            onSelect({ kind: "node", address: evt.target.id() });
          });
          cy.on("tap", "edge", (evt: EventObject) => {
            const idx = Number(String(evt.target.id()).slice(1));
            const edge = edges[idx];
            if (edge) onSelect({ kind: "edge", edge });
          });
        }}
      />
    </div>
  );
}
