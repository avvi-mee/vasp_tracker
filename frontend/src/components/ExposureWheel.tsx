import type { ExposureCategory } from "@/lib/api";
import { categoryRisk, entityColor, entityPlainLabel } from "@/lib/entityColors";

/** Shares can overlap (one path/side can be exposed to more than one
 * category) and are not required to sum to 100% — see app/graph/exposure.py. */
export function ExposurePair({
  leftTitle,
  leftSubtitle,
  leftCategories,
  rightTitle,
  rightSubtitle,
  rightCategories,
}: {
  leftTitle: string;
  leftSubtitle: string;
  leftCategories: ExposureCategory[];
  rightTitle: string;
  rightSubtitle: string;
  rightCategories: ExposureCategory[];
}) {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
      <ExposureColumn title={leftTitle} subtitle={leftSubtitle} categories={leftCategories} />
      <ExposureColumn title={rightTitle} subtitle={rightSubtitle} categories={rightCategories} />
    </div>
  );
}

/** Direct vs. indirect exposure — Chainalysis's own stated distinction
 * (direct = the seed's immediate counterparty; indirect = anything reached
 * through intermediary hops, regardless of distance), built from that
 * concept rather than copied from any screenshot — the real chart's exact
 * geometry is not publicly documented anywhere we could verify. */
export function ExposureWheel({ direct, indirect }: { direct: ExposureCategory[]; indirect: ExposureCategory[] }) {
  return (
    <ExposurePair
      leftTitle="Direct" leftSubtitle="Immediate counterparty" leftCategories={direct}
      rightTitle="Indirect" rightSubtitle="Through intermediary hops" rightCategories={indirect}
    />
  );
}

/** Receiving vs. sending exposure for the seed address itself — a
 * complementary cut from direct/indirect: transfer direction at the seed,
 * not hop distance. Confirmed from a real Reactor screenshot as a distinct,
 * named pair of wheels alongside the direct/indirect ones. */
export function SeedExposureWheel({ receiving, sending }: { receiving: ExposureCategory[]; sending: ExposureCategory[] }) {
  return (
    <ExposurePair
      leftTitle="Receiving" leftSubtitle="Who sent funds here" leftCategories={receiving}
      rightTitle="Sending" rightSubtitle="Where funds went" rightCategories={sending}
    />
  );
}

/** The riskiest category present, so the headline number says something
 * about severity rather than just being the biggest slice. */
function headline(categories: ExposureCategory[]): ExposureCategory | null {
  if (categories.length === 0) return null;
  const rank = { high: 0, medium: 1, low: 2, none: 3 };
  return [...categories].sort(
    (a, b) => rank[categoryRisk(a.category)] - rank[categoryRisk(b.category)] || b.value_share - a.value_share
  )[0];
}

function ExposureColumn({
  title,
  subtitle,
  categories,
}: {
  title: string;
  subtitle: string;
  categories: ExposureCategory[];
}) {
  const top = headline(categories);
  return (
    <div className="flex items-start gap-3">
      <Donut categories={categories} centre={top ? `${(top.value_share * 100).toFixed(0)}%` : "—"} />
      <div className="min-w-0 flex-1">
        <div className="text-xs font-semibold uppercase tracking-wide text-ink">{title}</div>
        <div className="mb-2 text-[11px] leading-tight text-ink-faint">{subtitle}</div>
        {categories.length === 0 ? (
          <div className="text-[11px] leading-relaxed text-ink-soft">
            Nothing to categorise on this side — no transfers in this direction, or none in the traced asset.
          </div>
        ) : (
          <ul className="flex flex-col gap-1">
            {categories.map((c, i) => (
              <li key={i} className="flex items-center justify-between gap-2 text-[11px]">
                <span className="flex min-w-0 items-center gap-1.5">
                  <span
                    className="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
                    style={{ background: entityColor(c.category) }}
                  />
                  <span className="truncate" title={c.label ?? entityPlainLabel(c.category)}>
                    {entityPlainLabel(c.category)}
                    {c.label && <span className="text-ink-faint"> · {c.label}</span>}
                  </span>
                </span>
                <span className="shrink-0 font-mono font-semibold">{(c.value_share * 100).toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/** A donut that is legible when one category holds 100%.
 *
 * The old version drew a conic-gradient ring and nothing else, so an
 * all-unattributed breakdown rendered as a flat pale-grey circle on a white
 * card — which read as "no data" when it actually meant "100% of this money
 * went somewhere nobody can name", the single most important thing on the
 * screen. Now: a visible slate for unattributed, a hairline separating
 * slices, and the headline share printed in the hole. */
function Donut({ categories, centre }: { categories: ExposureCategory[]; centre: string }) {
  const total = categories.reduce((sum, c) => sum + c.value_share, 0) || 1;
  // Prefix sums rather than a mutable accumulator: React's lint rule rejects
  // reassigning a captured variable during render, and there are at most a
  // handful of categories, so the quadratic walk costs nothing.
  const stops = categories.map((c, i) => {
    const before = categories.slice(0, i).reduce((sum, x) => sum + x.value_share, 0);
    const start = (before / total) * 360;
    const end = ((before + c.value_share) / total) * 360;
    return `${entityColor(c.category)} ${start}deg ${end}deg`;
  });
  const gradient =
    stops.length > 0
      ? `conic-gradient(${stops.join(", ")})`
      : "repeating-conic-gradient(var(--color-ledger-soft) 0deg 12deg, var(--color-wire) 12deg 24deg)";

  return (
    <div
      className="relative h-20 w-20 shrink-0 rounded-full ring-1 ring-inset"
      style={{ background: gradient, ["--tw-ring-color" as string]: "rgb(0 0 0 / 0.08)" }}
      aria-hidden
    >
      <div className="absolute inset-[22%] flex items-center justify-center rounded-full bg-paper-raised">
        <span className="font-mono text-[11px] font-semibold text-ink">{centre}</span>
      </div>
    </div>
  );
}
