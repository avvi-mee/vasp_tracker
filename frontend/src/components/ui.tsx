// Shared primitives. Every page was hand-rolling
// `rounded-md border border-wire bg-paper-raised px-3 py-2` inline, which is
// how five screens drift into looking like five products. One file rather
// than a directory of eight two-line files — they are small, they change
// together, and nothing imports them individually.

import type { ReactNode } from "react";

type RiskLevel = "none" | "low" | "medium" | "high" | "critical" | "unknown";

export const RISK_STYLE: Record<RiskLevel, { fg: string; bg: string; line: string; label: string }> = {
  critical: { fg: "var(--color-risk-critical-fg)", bg: "var(--color-risk-critical-bg)", line: "var(--color-risk-critical-line)", label: "CRITICAL" },
  high: { fg: "var(--color-risk-high-fg)", bg: "var(--color-risk-high-bg)", line: "var(--color-risk-high-line)", label: "HIGH RISK" },
  medium: { fg: "var(--color-risk-medium-fg)", bg: "var(--color-risk-medium-bg)", line: "var(--color-risk-medium-line)", label: "MEDIUM RISK" },
  low: { fg: "var(--color-risk-low-fg)", bg: "var(--color-risk-low-bg)", line: "var(--color-risk-low-line)", label: "LOW RISK" },
  none: { fg: "var(--color-risk-none-fg)", bg: "var(--color-risk-none-bg)", line: "var(--color-risk-none-line)", label: "NO RISK FLAG" },
  unknown: { fg: "var(--color-unattributed)", bg: "var(--color-unattributed-bg)", line: "var(--color-unattributed)", label: "NOT ASSESSED" },
};

export function riskStyle(level: string | null | undefined) {
  return RISK_STYLE[(level ?? "unknown") as RiskLevel] ?? RISK_STYLE.unknown;
}

export function Card({
  title,
  subtitle,
  action,
  children,
  className = "",
  padded = true,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <section
      className={`rounded-xl border border-wire bg-paper-raised ${className}`}
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      {(title || action) && (
        <header className="flex flex-wrap items-start justify-between gap-2 border-b border-wire px-4 py-3">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-soft">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={padded ? "p-4" : ""}>{children}</div>
    </section>
  );
}

export function SectionTitle({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="mt-8 mb-3 flex flex-wrap items-baseline justify-between gap-2">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-ink-soft">{children}</h3>
      {hint && <span className="text-[11px] text-ink-faint">{hint}</span>}
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
  title,
}: {
  children: ReactNode;
  tone?: RiskLevel | "neutral" | "accent";
  title?: string;
}) {
  const style =
    tone === "neutral"
      ? { color: "var(--color-ink-soft)", background: "var(--color-ledger-soft)", borderColor: "var(--color-wire)" }
      : tone === "accent"
        ? { color: "var(--color-navy)", background: "var(--color-ledger-soft)", borderColor: "var(--color-wire-strong)" }
        : { color: riskStyle(tone).fg, background: riskStyle(tone).bg, borderColor: riskStyle(tone).line };
  return (
    <span
      title={title}
      className="inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold"
      style={style}
    >
      {children}
    </span>
  );
}

const BUTTON_TONES = {
  primary: "bg-navy text-white hover:bg-navy-soft",
  accent: "bg-gold text-white hover:opacity-90",
  ghost: "border border-wire bg-paper-raised text-ink hover:bg-ledger-soft",
} as const;

export function Button({
  children,
  tone = "primary",
  type = "button",
  disabled,
  onClick,
  className = "",
}: {
  children: ReactNode;
  tone?: keyof typeof BUTTON_TONES;
  type?: "button" | "submit";
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-md px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_TONES[tone]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Input({
  value,
  onChange,
  placeholder,
  mono,
  className = "",
  ariaLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  mono?: boolean;
  className?: string;
  ariaLabel?: string;
}) {
  return (
    <input
      value={value}
      aria-label={ariaLabel ?? placeholder}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`min-w-0 rounded-md border border-wire bg-paper-raised px-3 py-2 text-sm outline-none transition-colors focus:border-navy ${mono ? "font-mono" : ""} ${className}`}
    />
  );
}

/** A stat that says what it means when it has nothing to show. `value`
 * being 0 is a value — the Investigate page used `confidence ? x : "—"`,
 * so a real 0% confidence rendered as an em dash and looked like a bug. */
export function Stat({
  label,
  value,
  hint,
  color,
  tone,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  color?: string;
  tone?: RiskLevel;
}) {
  const accent = tone ? riskStyle(tone) : null;
  return (
    <div
      className="rounded-lg border border-wire bg-paper-raised px-3 py-2.5"
      style={{ boxShadow: "var(--shadow-card)", borderLeft: accent ? `3px solid ${accent.line}` : undefined }}
    >
      <div className="text-[10px] font-semibold uppercase tracking-[0.07em] text-ink-faint">{label}</div>
      <div
        className="mt-0.5 truncate font-mono text-base font-semibold leading-tight"
        style={{ color: color ?? accent?.fg ?? "var(--color-ink)" }}
        title={typeof value === "string" ? value : undefined}
      >
        {value}
      </div>
      {hint && <div className="mt-0.5 text-[11px] leading-snug text-ink-soft">{hint}</div>}
    </div>
  );
}

/** Empty states explain why there is nothing and what to do next. A blank
 * tile trains an officer to distrust the whole screen. */
export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-wire-strong bg-ledger-soft/50 px-4 py-6 text-center">
      <div className="text-sm font-semibold text-ink-soft">{title}</div>
      {children && <p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-ink-soft">{children}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <div className={`vt-skeleton ${className}`} />;
}

/** Tables of transactions and cases are wider than a phone. Each gets its
 * own scroll container so the page body never scrolls sideways. */
export function TableScroll({ children }: { children: ReactNode }) {
  return <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">{children}</div>;
}

export function Tabs<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: ReactNode }[];
}) {
  return (
    <div className="inline-flex rounded-md border border-wire bg-ledger-soft p-0.5" role="tablist">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={value === o.value}
          onClick={() => onChange(o.value)}
          className={`rounded px-3 py-1.5 text-xs font-semibold transition-colors ${
            value === o.value ? "bg-paper-raised text-navy shadow-sm" : "text-ink-soft hover:text-ink"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Copy-to-clipboard address. An officer transcribing a 42-character hex
 * string by hand into a disclosure request is a typo waiting to happen. */
export function Address({ value, className = "" }: { value: string; className?: string }) {
  return (
    <button
      onClick={() => navigator.clipboard?.writeText(value)}
      title={`${value} — click to copy`}
      className={`rounded border border-wire bg-ledger-soft px-1.5 py-0.5 font-mono text-[11px] transition-colors hover:border-navy ${className}`}
    >
      {value}
    </button>
  );
}
