"use client";

import { useMemo } from "react";
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

/** The screen that actually justifies moving off Streamlit: every address
 * and transaction the ranked-candidate search explored, not just the single
 * winning path — Reactor's core interaction (expand, explore, follow a
 * branch) over data this project already computes server-side. */
export function InvestigationGraph({ seedAddress, candidates, edges, activeAsset, onSelect }: Props) {
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
      const short = `${id.slice(0, 6)}…${id.slice(-4)}`;
      return {
        data: {
          id,
          label: info?.label ? `${info.label}\n${short}` : short,
          isSeed,
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
          width: (n: NodeSingular) => (n.data("isSeed") ? 30 : 18),
          height: (n: NodeSingular) => (n.data("isSeed") ? 30 : 18),
          "border-width": (n: NodeSingular) => (n.data("isSeed") ? 3 : 0),
          "border-color": "var(--color-gold)",
        },
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
        },
      },
    ],
    []
  );

  return (
    <CytoscapeComponent
      elements={elements}
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      stylesheet={stylesheet as any}
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      layout={{ name: "breadthfirst", directed: true, roots: [seedAddress], spacingFactor: 1.3, padding: 20 } as any}
      style={{ width: "100%", height: "420px" }}
      className="rounded-lg border border-wire bg-paper-raised"
      cy={(cy: Core) => {
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
  );
}
