// One color/label mapping shared by the verdict card, the investigation
// graph, the exposure wheel, and the transactions table — so the same
// category always reads the same way everywhere, and a new view never
// silently disagrees with an existing one about what a category means.

export const ENTITY_COLOR: Record<string, string> = {
  exchange: "var(--color-navy)",
  "exchange cluster": "var(--color-navy)",
  mixer: "var(--color-risk-high-fg)",
  market: "#5c1a1a", // darknet market — distinct from mixer, still unambiguously high-risk
  sanctioned: "#8c3420",
  user: "var(--color-gold)",
  unknown: "var(--color-ink-soft)",
};

// Plain-language names for an LEA officer, not a blockchain analyst — the
// raw category string (e.g. "mixing_service") is available one click
// deeper, never the primary thing on screen.
const PLAIN_LABEL: Record<string, string> = {
  exchange: "currency exchange",
  "exchange cluster": "currency exchange",
  mixer: "mixer / tumbler",
  mixing_service: "mixer / tumbler",
  coinjoin: "mixer / tumbler",
  market: "darknet market",
  sanctioned: "sanctioned address",
  user: "individual wallet",
  unknown: "unattributed address",
};

export function entityColor(category: string | null | undefined): string {
  return ENTITY_COLOR[category ?? "unknown"] ?? ENTITY_COLOR.unknown;
}

export function entityPlainLabel(category: string | null | undefined): string {
  if (!category) return "unattributed address";
  return PLAIN_LABEL[category] ?? category;
}
