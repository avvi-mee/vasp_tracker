"use client";

import { useMemo, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import type { Core, ElementDefinition, EventObject, NodeSingular, EdgeSingular } from "cytoscape";
import type { Candidate, Edge } from "@/lib/api";
import { ENTITY_COLOR, GRAPH_PALETTE, entityColor, entityPlainLabel } from "@/lib/entityColors";
import { Button } from "@/components/ui";

export type GraphSelection =
  | { kind: "node"; address: string }
  | { kind: "edge"; edge: Edge };

interface Props {
  seedAddress: string;
  candidates: Candidate[];
  edges: Edge[];
  activeAsset: string | null;
  flagged?: string[];
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
 * branch) over data this project already computes server-side.
 *
 * Colours here are literal hex from entityColors.ts, never CSS custom
 * properties: Cytoscape draws to a canvas and parses colour strings itself,
 * so `var(--color-navy)` silently failed and every node fell back to the
 * same default grey. That, plus 7-8px type, is why this read as a field of
 * identical unlabelled dots. */
export function InvestigationGraph({ seedAddress, candidates, edges, activeAsset, flagged = [], onSelect }: Props) {
  const cyRef = useRef<Core | null>(null);
  const [search, setSearch] = useState("");
  const [searchError, setSearchError] = useState(false);

  const legend = useMemo(() => {
    const present = new Set(candidates.map((c) => c.entity_type ?? "unknown"));
    return Array.from(present).filter((c) => c in ENTITY_COLOR || true);
  }, [candidates]);

  const elements = useMemo<ElementDefinition[]>(() => {
    const terminalInfo = new Map<string, { entityType: string; label: string | null }>();
    for (const c of candidates) {
      const terminal = c.path[c.path.length - 1];
      terminalInfo.set(terminal, { entityType: c.entity_type, label: c.label });
    }
    const flaggedSet = new Set(flagged);

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
          // The name is the point. An officer scanning this graph is looking
          // for "Binance", not for the first six characters of a hex string.
          label: isSeed ? `SUBJECT\n${short}` : info?.label ? `${info.label}\n${short}` : short,
          isSeed,
          isLabeled,
          isFlagged: flaggedSet.has(id),
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
  }, [seedAddress, candidates, edges, activeAsset, flagged]);

  const stylesheet = useMemo(
    () => [
      {
        selector: "node",
        style: {
          label: "data(label)",
          "font-size": 11,
          "font-weight": (n: NodeSingular) => (n.data("isLabeled") || n.data("isSeed") ? 700 : 400),
          "text-wrap": "wrap" as const,
          "text-valign": "bottom" as const,
          "text-margin-y": 7,
          "text-background-color": GRAPH_PALETTE.paper,
          "text-background-opacity": 0.82,
          "text-background-padding": 2,
          "text-background-shape": "roundrectangle" as const,
          color: GRAPH_PALETTE.ink,
          "background-color": (n: NodeSingular) => entityColor(n.data("entityType")),
          // Attributed entities read as bigger and visually distinct from
          // plain intermediate hops — a seed gets the biggest, gold-ringed
          // treatment; a labeled terminal is next; an unlabeled hop is a
          // small plain dot, matching the hierarchy a real Reactor graph uses.
          width: (n: NodeSingular) => (n.data("isSeed") ? 40 : n.data("isLabeled") ? 30 : 16),
          height: (n: NodeSingular) => (n.data("isSeed") ? 40 : n.data("isLabeled") ? 30 : 16),
          "border-width": (n: NodeSingular) =>
            n.data("isSeed") ? 4 : n.data("isFlagged") ? 3 : n.data("isLabeled") ? 2 : 1,
          "border-color": (n: NodeSingular) =>
            n.data("isSeed")
              ? GRAPH_PALETTE.gold
              : n.data("isFlagged")
                ? GRAPH_PALETTE.danger
                : GRAPH_PALETTE.ink,
        },
      },
      {
        selector: "node.search-match",
        style: { "border-width": 5, "border-color": GRAPH_PALETTE.gold },
      },
      {
        selector: "edge",
        style: {
          width: (e: EdgeSingular) => Math.max(1.5, Math.min(10, Math.log10((e.data("amount") || 0) + 1) * 2.5)),
          "line-color": GRAPH_PALETTE.wire,
          "target-arrow-color": GRAPH_PALETTE.wire,
          "target-arrow-shape": "triangle" as const,
          "curve-style": "bezier" as const,
          opacity: (e: EdgeSingular) => (e.data("dimmed") ? 0.12 : 0.95),
          label: "data(displayLabel)",
          "font-size": 10,
          color: GRAPH_PALETTE.inkSoft,
          "text-background-color": GRAPH_PALETTE.paper,
          "text-background-opacity": 0.9,
          "text-background-padding": 2,
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
    const needle = search.trim().toLowerCase();
    const match = cy
      .nodes()
      .filter((n) => n.id().toLowerCase().includes(needle) || String(n.data("label")).toLowerCase().includes(needle));
    if (match.length === 0) {
      setSearchError(true);
      return;
    }
    setSearchError(false);
    match.addClass("search-match");
    cy.animate({ fit: { eles: match, padding: 60 }, duration: 300 });
  }

  if (edges.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-wire-strong bg-ledger-soft/50 px-4 py-10 text-center">
        <div className="text-sm font-semibold text-ink-soft">No transaction graph to draw</div>
        <p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-ink-soft">
          This wallet made no outgoing transfers the trace could follow, so there are no edges. It may be a
          receive-only address, or its funds may have moved in an asset this chain adapter does not read yet.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <form onSubmit={runSearch} className="flex min-w-0 flex-1 gap-2">
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSearchError(false);
            }}
            placeholder="Find an address or entity in this graph"
            className={`min-w-0 flex-1 rounded-md border bg-paper-raised px-2.5 py-1.5 font-mono text-xs outline-none focus:border-navy ${
              searchError ? "border-red-400" : "border-wire"
            }`}
          />
          <Button type="submit" tone="ghost" className="shrink-0 !py-1.5 !text-xs">
            Find
          </Button>
        </form>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-ink-soft">
          <LegendDot color={GRAPH_PALETTE.gold} ring>
            subject
          </LegendDot>
          {legend.map((c) => (
            <LegendDot key={c} color={entityColor(c)}>
              {entityPlainLabel(c)}
            </LegendDot>
          ))}
        </div>
      </div>
      <CytoscapeComponent
        elements={elements}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        stylesheet={stylesheet as any}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        layout={{ name: "breadthfirst", directed: true, roots: [seedAddress], spacingFactor: 1.5, padding: 30 } as any}
        // Flexes with the viewport instead of a fixed 420px that left a
        // phone with a letterbox and a large monitor with wasted space.
        style={{ width: "100%", height: "clamp(320px, 55vh, 620px)" }}
        className="rounded-xl border border-wire bg-paper-raised"
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
      <p className="mt-1.5 text-[11px] text-ink-faint">
        Node size is attribution, not value: the subject is largest, named entities next, unlabelled hops
        smallest. Edge thickness is the amount moved. Click any node or edge for the underlying record.
      </p>
    </div>
  );
}

function LegendDot({ color, ring, children }: { color: string; ring?: boolean; children: React.ReactNode }) {
  return (
    <span className="flex items-center gap-1">
      <span
        className="inline-block h-2.5 w-2.5 rounded-full"
        style={{ background: color, boxShadow: ring ? `0 0 0 2px ${GRAPH_PALETTE.gold}66` : undefined }}
      />
      {children}
    </span>
  );
}
