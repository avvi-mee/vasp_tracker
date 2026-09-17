import type { Candidate, DepositEvidence, RiskAssessment } from "@/lib/api";

const RISK_STYLES: Record<string, { fg: string; bg: string; label: string }> = {
  high: { fg: "var(--color-risk-high-fg)", bg: "var(--color-risk-high-bg)", label: "HIGH RISK" },
  medium: { fg: "var(--color-risk-medium-fg)", bg: "var(--color-risk-medium-bg)", label: "MEDIUM RISK" },
  low: { fg: "var(--color-risk-low-fg)", bg: "var(--color-risk-low-bg)", label: "LOW RISK" },
  none: { fg: "var(--color-risk-none-fg)", bg: "var(--color-risk-none-bg)", label: "NO RISK FLAG" },
};

const ENTITY_COLOR: Record<string, string> = {
  exchange: "var(--color-navy)",
  "exchange cluster": "var(--color-navy)",
  mixer: "var(--color-risk-high-fg)",
  user: "var(--color-gold)",
  unknown: "var(--color-ink-soft)",
};

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mt-6 mb-2 text-xs font-semibold uppercase tracking-wide text-ink-soft">
      {children}
    </h3>
  );
}

export function StatTile({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-lg border border-wire bg-paper-raised px-4 py-3">
      <div className="text-[11px] uppercase tracking-wide text-ink-soft">{label}</div>
      <div className="font-mono text-lg font-semibold" style={{ color: color ?? "var(--color-ink)" }}>
        {value}
      </div>
    </div>
  );
}

export function RiskBadge({ risk }: { risk: RiskAssessment }) {
  const style = RISK_STYLES[risk.risk_level] ?? RISK_STYLES.none;
  return (
    <div
      className="inline-flex flex-col gap-0.5 rounded-md px-3 py-2 text-sm"
      style={{ color: style.fg, background: style.bg }}
    >
      <span className="font-semibold">{style.label}</span>
      {risk.risk_reason && <span className="text-xs opacity-90">{risk.risk_reason}</span>}
    </div>
  );
}

export function PathFlow({
  path,
  entityType,
  label,
}: {
  path: string[];
  entityType: string;
  label: string | null;
}) {
  const color = ENTITY_COLOR[entityType] ?? ENTITY_COLOR.unknown;
  return (
    <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
      {path.map((addr, i) => (
        <span key={`${addr}-${i}`} className="flex items-center gap-2">
          <span className="rounded border border-wire bg-ledger-soft px-2 py-1">{addr}</span>
          {i < path.length - 1 && <span className="text-ink-soft">&rarr;</span>}
        </span>
      ))}
      {label && (
        <span
          className="ml-1 rounded px-2 py-1 font-sans font-semibold"
          style={{ color, background: "var(--color-ledger-soft)" }}
        >
          {label} ({entityType})
        </span>
      )}
    </div>
  );
}

export function DepositCallout({ deposit }: { deposit: DepositEvidence }) {
  return (
    <div className="rounded-lg border border-wire bg-ledger-soft p-4 text-sm">
      <div className="mb-2 font-mono font-semibold">{deposit.address}</div>
      <div className="grid grid-cols-2 gap-2 text-xs text-ink-soft sm:grid-cols-4">
        <div>Confidence: <b className="text-ink">{(deposit.confidence * 100).toFixed(0)}%</b></div>
        <div>Forwarded: <b className="text-ink">{(deposit.forwarded_ratio * 100).toFixed(0)}%</b></div>
        <div>Funders: <b className="text-ink">{deposit.distinct_funders}</b></div>
        <div>Sweeps: <b className="text-ink">{deposit.sweep_count}</b></div>
      </div>
      {deposit.caveats?.length > 0 && (
        <ul className="mt-2 list-disc pl-4 text-xs text-ink-soft">
          {deposit.caveats.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** The ranked-candidate view — this is the screen that the old single-path
 * greedy walk couldn't produce at all. Showing every material split, not
 * just the top one, is the whole point of the Phase A BFS rewrite. */
export function CandidateList({ candidates }: { candidates: Candidate[] }) {
  if (candidates.length <= 1) return null;
  return (
    <div className="flex flex-col gap-2">
      {candidates.map((c, i) => (
        <div
          key={i}
          className="flex items-center justify-between rounded-md border border-wire bg-paper-raised px-3 py-2 text-sm"
        >
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs text-ink-soft">#{i + 1}</span>
            <span className="font-semibold" style={{ color: ENTITY_COLOR[c.entity_type] ?? ENTITY_COLOR.unknown }}>
              {c.label ?? "Unresolved"}
            </span>
            <span className="text-xs text-ink-soft">
              {c.entity_type} · {c.hop_count} hop{c.hop_count === 1 ? "" : "s"}
              {c.merged_path_count > 1 && ` · ${c.merged_path_count} converging paths`}
            </span>
          </div>
          <div className="font-mono text-xs font-semibold text-ink">
            {(c.value_share * 100).toFixed(1)}% of value
          </div>
        </div>
      ))}
    </div>
  );
}

export function FieldRow({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4 border-b border-wire/60 py-1.5 text-sm">
      <span className="text-ink-soft">{label}</span>
      <span className={mono ? "font-mono text-right" : "text-right"}>{value}</span>
    </div>
  );
}
