import type { Candidate, DepositEvidence, RiskAssessment, Typology } from "@/lib/api";
import { categoryRisk, entityColor, entityPlainLabel, isActionable } from "@/lib/entityColors";
import { Address, Badge, Card, EmptyState, riskStyle } from "@/components/ui";

export { SectionTitle } from "@/components/ui";

/** The one-line answer to the problem statement's actual question, sized
 * like an answer. Previously this was a grid of four equal tiles, so
 * "Reached: unattributed address" carried the same visual weight as
 * "Case ID: not saved". */
export function Answer({
  label,
  entityType,
  hopCount,
  confidence,
  source,
  maxHops,
  chain,
}: {
  label: string | null;
  entityType: string;
  hopCount: number;
  confidence: number;
  source: string | null;
  maxHops: number;
  chain: string;
}) {
  const resolved = Boolean(label);
  const color = entityColor(entityType);
  return (
    <div
      className="rounded-xl border bg-paper-raised p-4 sm:p-5"
      style={{ boxShadow: "var(--shadow-card)", borderColor: resolved ? color : "var(--color-wire-strong)" }}
    >
      <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-ink-faint">
        Nearest attributable entity
      </div>
      {resolved ? (
        <>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-2xl font-bold leading-tight" style={{ color }}>
              {label}
            </span>
            <Badge tone="accent">{entityPlainLabel(entityType)}</Badge>
            {isActionable(entityType) && (
              <Badge tone="none" title="A disclosure request can be served on this entity">
                disclosure target
              </Badge>
            )}
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-soft">
            <span>
              <b className="text-ink">{hopCount}</b> hop{hopCount === 1 ? "" : "s"} from the subject wallet
            </span>
            <span>
              attribution confidence <b className="text-ink">{(confidence * 100).toFixed(0)}%</b>
            </span>
            {source && (
              <span>
                source <span className="font-mono text-ink">{source}</span>
              </span>
            )}
          </div>
        </>
      ) : (
        <>
          <div className="mt-1 text-2xl font-bold leading-tight text-unattributed">
            No named entity within {maxHops} hops
          </div>
          <p className="mt-2 max-w-2xl text-xs leading-relaxed text-ink-soft">
            The money is still moving between wallets nobody has labelled. That is a real finding, not an
            error — it means no exchange has been reached yet on {chain}, so there is no VASP to serve a
            request on <em>from this trail</em>. The behavioural findings below still apply, and they do
            not need a label. Widening the hop limit or tracing a downstream address are the next moves.
          </p>
        </>
      )}
    </div>
  );
}

/** Risk, with the thing that was missing: which question it answers.
 * "HIGH RISK" alone invites the reasonable objection "based on what?" */
export function RiskBadge({ risk }: { risk: RiskAssessment }) {
  const style = riskStyle(risk.risk_level);
  const basisText =
    risk.basis === "behaviour"
      ? "from this wallet's own transaction behaviour"
      : "from where the funds ended up";
  return (
    <div
      className="rounded-lg border px-4 py-3"
      style={{ color: style.fg, background: style.bg, borderColor: style.line }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-bold tracking-wide">{style.label}</span>
        <span className="text-[11px] opacity-80">· {basisText}</span>
      </div>
      {risk.risk_reason && <p className="mt-1 text-xs leading-relaxed opacity-95">{risk.risk_reason}</p>}
    </div>
  );
}

const SEVERITY_ORDER = ["high", "medium", "low"] as const;

/** Laundering typologies — the part of the problem statement that had no
 * implementation, and the reason a scam wallet can now be called high-risk
 * without waiting for someone to label it. */
export function TypologyPanel({ typologies }: { typologies: Typology[] }) {
  if (typologies.length === 0) {
    return (
      <EmptyState title="No laundering typology matched">
        This wallet&apos;s transactions do not fit funnelling, layering, smurfing, peeling or round-amount
        structuring at the thresholds this tool uses. Absence of a pattern is not evidence of innocence —
        a wallet with few transactions has too little history to show one.
      </EmptyState>
    );
  }
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {[...typologies]
        .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity))
        .map((t) => {
          const style = riskStyle(t.severity);
          return (
            <div
              key={t.name}
              className="rounded-lg border bg-paper-raised p-4"
              style={{ borderColor: style.line, borderLeftWidth: 4, boxShadow: "var(--shadow-card)" }}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h4 className="text-sm font-semibold" style={{ color: style.fg }}>
                  {t.title}
                </h4>
                <div className="flex shrink-0 gap-1.5">
                  <Badge tone={t.severity}>{t.severity}</Badge>
                  <Badge tone="neutral">{(t.confidence * 100).toFixed(0)}% fit</Badge>
                </div>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-ink-soft">{t.explanation}</p>
              <dl className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-wire pt-2 text-[11px]">
                {Object.entries(t.stats).map(([k, v]) => (
                  <div key={k} className="flex gap-1">
                    <dt className="text-ink-faint">{k.replace(/_/g, " ")}</dt>
                    <dd className="font-mono font-semibold text-ink">
                      {Array.isArray(v) ? v.join(", ") : String(v)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          );
        })}
    </div>
  );
}

/** What to do next, in the officer's own vocabulary. The recommendation is
 * already computed server-side (app/sahyog/gateway.py); it was buried in a
 * JSON blob nothing rendered. */
export function NextStep({ draft }: { draft: Record<string, unknown> }) {
  const rec = draft?.recommended_instrument as { label?: string; reason?: string } | undefined;
  if (!rec?.label) return null;
  return (
    <Card title="Recommended legal instrument" subtitle="Computed from the attribution and the entity's FIU-IND status">
      <div className="text-sm font-semibold text-navy">{rec.label}</div>
      <p className="mt-1 text-xs leading-relaxed text-ink-soft">{rec.reason}</p>
      <p className="mt-2 border-t border-wire pt-2 text-[11px] leading-relaxed text-ink-faint">
        A suggestion, not legal advice, and nothing here is submitted anywhere automatically. SAHYOG&apos;s
        crypto-VASP workflow is manual and portal-based; the draft below is for a nodal officer to review,
        sign and submit themselves.
      </p>
    </Card>
  );
}

export function PathFlow({
  path,
  entityType,
  label,
  flagged = [],
}: {
  path: string[];
  entityType: string;
  label: string | null;
  flagged?: string[];
}) {
  const color = entityColor(entityType);
  const flaggedSet = new Set(flagged);
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {path.map((addr, i) => {
        const isLast = i === path.length - 1;
        const isFlagged = flaggedSet.has(addr);
        return (
          <span key={`${addr}-${i}`} className="flex items-center gap-1.5">
            <span className="flex flex-col items-start">
              <span className="text-[9px] uppercase tracking-wide text-ink-faint">
                {i === 0 ? "subject" : `hop ${i}`}
              </span>
              <span
                className="rounded border px-1.5 py-0.5 font-mono text-[11px]"
                style={{
                  borderColor: isLast && label ? color : isFlagged ? "var(--color-risk-high-line)" : "var(--color-wire)",
                  background: isFlagged ? "var(--color-risk-high-bg)" : "var(--color-ledger-soft)",
                  color: isLast && label ? color : "var(--color-ink)",
                  fontWeight: isLast && label ? 600 : 400,
                }}
                title={isFlagged ? "The block explorer flags this address as risky" : undefined}
              >
                {addr}
              </span>
            </span>
            {!isLast && <span className="mt-3 text-ink-faint">&rarr;</span>}
          </span>
        );
      })}
      {label && (
        <span
          className="mt-3 ml-1 rounded px-2 py-1 text-xs font-semibold"
          style={{ color, background: "var(--color-ledger-soft)" }}
        >
          {label}
        </span>
      )}
    </div>
  );
}

function humanizeSeconds(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 90) return `${seconds}s`;
  if (seconds < 5400) return `${Math.round(seconds / 60)} min`;
  if (seconds < 172800) return `${Math.round(seconds / 3600)} hr`;
  return `${Math.round(seconds / 86400)} days`;
}

/** The single most operationally useful output this tool produces: not
 * "the money reached Binance" but "the money reached THIS account at
 * Binance, and India's Travel Rule has no de minimis threshold, so the
 * KYC record already exists". */
export function DepositCallout({ deposit }: { deposit: DepositEvidence }) {
  return (
    <Card
      title="Deposit address identified"
      subtitle="The hop before the exchange maps to one KYC'd account — name this address in the disclosure request, not the exchange's hot wallet"
      action={<Badge tone={deposit.confidence >= 0.8 ? "none" : "medium"}>{(deposit.confidence * 100).toFixed(0)}% confidence</Badge>}
    >
      <Address value={deposit.address} className="text-xs" />
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          ["Forwarded onward", `${(deposit.forwarded_ratio * 100).toFixed(0)}%`],
          ["To this one VASP", `${(deposit.destination_share * 100).toFixed(0)}%`],
          ["Distinct funders", String(deposit.distinct_funders)],
          ["Median hold", humanizeSeconds(deposit.median_hold_seconds)],
        ].map(([k, v]) => (
          <div key={k} className="rounded-md bg-ledger-soft px-2.5 py-2">
            <div className="text-[10px] uppercase tracking-wide text-ink-faint">{k}</div>
            <div className="font-mono text-sm font-semibold text-ink">{v}</div>
          </div>
        ))}
      </div>
      {deposit.caveats?.length > 0 && (
        <ul className="mt-3 list-disc space-y-0.5 border-t border-wire pl-5 pt-2 text-[11px] text-ink-soft">
          {deposit.caveats.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/** Ranked candidates. Eight rows all reading "Unresolved · 4 hops" is noise
 * pretending to be a ranking, which is exactly what the screenshots showed —
 * so unresolved terminals collapse into one summarising row. */
export function CandidateList({ candidates }: { candidates: Candidate[] }) {
  const named = candidates.filter((c) => c.label);
  const unresolved = candidates.filter((c) => !c.label);
  const unresolvedShare = unresolved.reduce((sum, c) => sum + c.value_share, 0);

  if (candidates.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      {named.map((c, i) => {
        const tone = categoryRisk(c.entity_type);
        return (
          <div
            key={`${c.label}-${i}`}
            className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5 rounded-lg border border-wire bg-paper-raised px-3 py-2.5"
            style={{ borderLeft: `3px solid ${entityColor(c.entity_type)}` }}
          >
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <span className="font-mono text-[11px] text-ink-faint">#{i + 1}</span>
              <span className="font-semibold text-sm" style={{ color: entityColor(c.entity_type) }}>
                {c.label}
              </span>
              <Badge tone={tone === "none" ? "none" : tone}>{entityPlainLabel(c.entity_type)}</Badge>
              <span className="text-[11px] text-ink-soft">
                {c.hop_count} hop{c.hop_count === 1 ? "" : "s"} · {(c.confidence * 100).toFixed(0)}% confidence
                {c.merged_path_count > 1 && ` · ${c.merged_path_count} converging paths`}
              </span>
            </div>
            <ValueBar share={c.value_share} color={entityColor(c.entity_type)} />
          </div>
        );
      })}

      {unresolved.length > 0 && (
        <div className="rounded-lg border border-dashed border-wire-strong bg-ledger-soft/50 px-3 py-2.5">
          <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
            <div className="min-w-0 text-sm">
              <span className="font-semibold text-unattributed">
                {unresolved.length} unresolved {unresolved.length === 1 ? "trail" : "trails"}
              </span>
              <span className="ml-2 text-[11px] text-ink-soft">
                {unresolved.length === 1
                  ? unresolved[0].reason ?? "no entity matched"
                  : "ended at addresses no dataset names — dead ends, hop limits, or the search budget"}
              </span>
            </div>
            <ValueBar share={unresolvedShare} color="var(--color-unattributed)" />
          </div>
        </div>
      )}
    </div>
  );
}

function ValueBar({ share, color }: { share: number; color: string }) {
  return (
    <div className="flex shrink-0 items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-ledger-soft sm:w-28">
        <div className="h-full rounded-full" style={{ width: `${Math.max(2, share * 100)}%`, background: color }} />
      </div>
      <span className="w-12 text-right font-mono text-[11px] font-semibold text-ink">
        {(share * 100).toFixed(1)}%
      </span>
    </div>
  );
}

export function FieldRow({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-wire py-2 text-sm last:border-b-0 sm:flex-row sm:justify-between sm:gap-4">
      <span className="shrink-0 text-xs text-ink-soft sm:text-sm">{label}</span>
      <span className={`min-w-0 ${mono ? "font-mono text-xs" : "text-sm"} sm:text-right`}>{value}</span>
    </div>
  );
}
