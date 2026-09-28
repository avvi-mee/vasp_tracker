/**
 * Rupee formatting for on-chain amounts.
 *
 * The backend ships a rate table ({ ETH: 265403, USDT: 95.77, ... }) rather
 * than pre-converted figures, because every component here already holds the
 * amount it renders — see app/prices.py for why the table can also arrive
 * empty, and why an unknown rate must show nothing rather than zero.
 *
 * Lakh/crore, not millions. A figure an Indian investigating officer, a
 * magistrate or an FIU-IND analyst reads should not need converting from a
 * scale none of them work in.
 */

export type InrRates = Record<string, number>;

const LAKH = 100_000;
const CRORE = 10_000_000;

/** null when the asset has no known rate — callers render token units alone. */
export function toInr(amount: number | null | undefined, asset: string | null | undefined, rates: InrRates): number | null {
  if (amount == null || !asset) return null;
  const rate = rates[asset.toUpperCase()];
  return rate == null ? null : amount * rate;
}

/** Compact rupees: ₹8,42,050 · ₹47.9 L · ₹1.24 Cr */
export function formatInr(value: number): string {
  if (!Number.isFinite(value)) return "—";
  if (value >= CRORE) return `₹${trim(value / CRORE)} Cr`;
  if (value >= LAKH) return `₹${trim(value / LAKH)} L`;
  if (value < 1) return `₹${value.toFixed(2)}`;
  return `₹${Math.round(value).toLocaleString("en-IN")}`;
}

/** The whole conversion in one call: "" when the rate is unknown, so it can
 *  be dropped straight into JSX next to the token figure. */
export function inrLabel(amount: number | null | undefined, asset: string | null | undefined, rates: InrRates): string {
  const value = toInr(amount, asset, rates);
  return value == null ? "" : formatInr(value);
}

function trim(n: number): string {
  // 1.20 Cr reads as false precision; 1.2 Cr is the same number, honestly.
  return n.toFixed(2).replace(/\.?0+$/, "");
}
