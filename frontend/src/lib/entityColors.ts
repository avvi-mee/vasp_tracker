// One color/label mapping shared by the verdict card, the investigation
// graph, the exposure wheel, and the transactions table — so the same
// category always reads the same way everywhere, and a new view never
// silently disagrees with an existing one about what a category means.

// Literal hex, not var(--color-…), and that is not an oversight: Cytoscape
// renders the investigation graph to a <canvas> and parses colours itself,
// so a CSS custom property never resolves there — it silently falls back to
// the default grey. That is exactly why the graph rendered as uniform grey
// dots with no hierarchy while every other view was correctly coloured.
// These values mirror the tokens in globals.css; keep the two in step.
export const ENTITY_COLOR: Record<string, string> = {
  exchange: "#1b2a4a", // --color-navy
  "exchange cluster": "#1b2a4a",
  custodian: "#3f5c8a",
  issuer: "#4a6b85",
  defi: "#5a7a5c",
  organization: "#6b6f8a",
  service: "#7a7490",
  gambling: "#8a6a3c",
  mixer: "#8c3420", // --color-risk-high-fg
  mixing_service: "#8c3420",
  coinjoin: "#8c3420",
  market: "#5c1a1a", // darknet market — distinct from mixer, still unambiguously high-risk
  illicit: "#6d1b1b",
  sanctioned: "#8c3420",
  user: "#8c661f", // --color-gold
  unattributed: "#7c86a0", // --color-unattributed
  unknown: "#7c86a0",
};

/** Palette values the canvas graph needs alongside the entity colours —
 * same reason: no var() in Cytoscape. */
export const GRAPH_PALETTE = {
  ink: "#14181f",
  inkSoft: "#5b6477",
  wire: "#c3c9d6",
  paper: "#ffffff",
  gold: "#8c661f",
  danger: "#8c3420",
} as const;

// Plain-language names for an LEA officer, not a blockchain analyst — the
// raw category string (e.g. "mixing_service") is available one click
// deeper, never the primary thing on screen.
const PLAIN_LABEL: Record<string, string> = {
  exchange: "currency exchange",
  "exchange cluster": "currency exchange",
  custodian: "custody provider",
  issuer: "token issuer",
  defi: "decentralised exchange",
  organization: "organisation",
  service: "named service",
  gambling: "gambling service",
  mixer: "mixer / tumbler",
  mixing_service: "mixer / tumbler",
  coinjoin: "mixer / tumbler",
  market: "darknet market",
  illicit: "known illicit address",
  sanctioned: "sanctioned address",
  user: "individual wallet",
  unattributed: "unattributed address",
  unknown: "unattributed address",
};

/** Which categories an officer can actually serve a disclosure request on.
 * The whole point of the tool is reaching one of these — everything else is
 * a waypoint, and the UI should say which is which rather than colouring
 * them all the same. */
const ACTIONABLE = new Set(["exchange", "exchange cluster", "custodian"]);

export function entityColor(category: string | null | undefined): string {
  return ENTITY_COLOR[category ?? "unknown"] ?? ENTITY_COLOR.unknown;
}

export function entityPlainLabel(category: string | null | undefined): string {
  if (!category) return "unattributed address";
  return PLAIN_LABEL[category] ?? category;
}

export function isActionable(category: string | null | undefined): boolean {
  return ACTIONABLE.has((category ?? "").toLowerCase());
}

/** Risk tier a category implies on sight, for colour-grading a node or row
 * before any per-address assessment is available. */
export function categoryRisk(category: string | null | undefined): "high" | "medium" | "low" | "none" {
  const c = (category ?? "").toLowerCase();
  if (["mixer", "mixing_service", "coinjoin", "market", "illicit", "sanctioned"].includes(c)) return "high";
  if (["gambling"].includes(c)) return "medium";
  if (ACTIONABLE.has(c)) return "none";
  return "low";
}
