import type { ExposureCategory } from "@/lib/api";
import { entityColor, entityPlainLabel } from "@/lib/entityColors";

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
  if (leftCategories.length === 0 && rightCategories.length === 0) return null;
  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
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
      leftTitle="Direct exposure" leftSubtitle="Immediate counterparty" leftCategories={direct}
      rightTitle="Indirect exposure" rightSubtitle="Reached through intermediary hops" rightCategories={indirect}
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
      leftTitle="Receiving exposure" leftSubtitle="Who sent funds to this address" leftCategories={receiving}
      rightTitle="Sending exposure" rightSubtitle="Where this address sent funds" rightCategories={sending}
    />
  );
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
  return (
    <div className="flex items-center gap-4">
      <Donut categories={categories} />
      <div className="min-w-0 flex-1">
        <div className="text-xs font-semibold uppercase tracking-wide text-ink-soft">{title}</div>
        <div className="mb-2 text-[11px] text-ink-soft">{subtitle}</div>
        {categories.length === 0 && <div className="text-xs text-ink-soft">None found</div>}
        <div className="flex flex-col gap-1">
          {categories.map((c, i) => (
            <div key={i} className="flex items-center justify-between gap-2 text-xs">
              <span className="flex min-w-0 items-center gap-1.5">
                <span
                  className="inline-block h-2 w-2 shrink-0 rounded-full"
                  style={{ background: entityColor(c.category) }}
                />
                <span className="truncate">{entityPlainLabel(c.category)}</span>
              </span>
              <span className="shrink-0 font-mono">{(c.value_share * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Donut({ categories }: { categories: ExposureCategory[] }) {
  const total = categories.reduce((sum, c) => sum + c.value_share, 0) || 1;
  let cumulative = 0;
  const stops = categories.map((c) => {
    const start = (cumulative / total) * 360;
    cumulative += c.value_share;
    const end = (cumulative / total) * 360;
    return `${entityColor(c.category)} ${start}deg ${end}deg`;
  });
  const gradient = stops.length > 0 ? `conic-gradient(${stops.join(", ")})` : "var(--color-wire)";

  return (
    <div className="relative h-24 w-24 shrink-0 rounded-full" style={{ background: gradient }}>
      <div className="absolute inset-3 rounded-full bg-paper-raised" />
    </div>
  );
}
