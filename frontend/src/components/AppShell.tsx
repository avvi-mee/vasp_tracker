"use client";

// The header + OfficerBar + NavBar block was copy-pasted into six page
// files. One shell instead, so a change to navigation happens once.
//
// Left sidebar rather than the old row of tabs: the row already wrapped at
// five items on a laptop, and Wallet Scan and cross-chain tracing are still
// to come. It collapses to a top bar with a drawer below the sm breakpoint,
// where a fixed sidebar would eat a third of the screen.

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearSession, type Officer } from "@/lib/auth";

const LINKS = [
  { href: "/dashboard", label: "Dashboard", hint: "Caseload at a glance" },
  { href: "/", label: "Investigate", hint: "Trace a wallet" },
  { href: "/cases", label: "Cases", hint: "Saved investigations" },
  { href: "/alerts", label: "Alerts", hint: "Watchlist activity" },
  { href: "/coverage", label: "Coverage", hint: "What this tool can and cannot see" },
];

const ROLE_TITLE: Record<string, string> = {
  officer: "Investigating Officer",
  supervisor: "Reviewing Officer",
  admin: "Nodal Admin",
};

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function AppShell({
  officer,
  title,
  subtitle,
  actions,
  children,
}: {
  officer: Officer;
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  function signOut() {
    clearSession();
    router.replace("/login");
  }

  return (
    <div className="flex min-h-screen w-full flex-col sm:flex-row">
      {/* Sidebar — sticky on desktop, a disclosure below sm. */}
      <aside className="shrink-0 border-b border-wire bg-paper-raised sm:sticky sm:top-0 sm:h-screen sm:w-56 sm:border-b-0 sm:border-r">
        <div className="flex items-center justify-between gap-2 px-4 py-3 sm:block">
          <Link href="/" className="block min-w-0">
            <div className="text-base font-bold leading-tight text-navy">VASP Trace</div>
            <div className="font-mono text-[10px] text-ink-faint">SIH26182 · MHA / I4C</div>
          </Link>
          <button
            onClick={() => setMenuOpen((o) => !o)}
            aria-expanded={menuOpen}
            aria-label="Toggle navigation"
            className="rounded border border-wire px-2 py-1 text-xs text-ink-soft sm:hidden"
          >
            Menu
          </button>
        </div>

        <nav className={`${menuOpen ? "block" : "hidden"} border-t border-wire px-2 pb-3 pt-2 sm:block sm:border-t-0`}>
          {LINKS.map((l) => {
            const active = isActive(pathname, l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setMenuOpen(false)}
                className={`mb-0.5 block rounded-md px-3 py-2 text-sm transition-colors ${
                  active ? "bg-navy font-semibold text-white" : "text-ink-soft hover:bg-ledger-soft hover:text-ink"
                }`}
              >
                {l.label}
                <span className={`block text-[10px] leading-tight ${active ? "text-white/70" : "text-ink-faint"}`}>
                  {l.hint}
                </span>
              </Link>
            );
          })}
        </nav>

        <div className={`${menuOpen ? "block" : "hidden"} border-t border-wire px-4 py-3 sm:block sm:absolute sm:bottom-0 sm:w-56`}>
          <div className="truncate text-xs font-semibold text-ink">{officer.display_name}</div>
          <div className="text-[10px] text-ink-faint">{ROLE_TITLE[officer.role] ?? officer.role}</div>
          <button onClick={signOut} className="mt-1.5 text-[11px] text-ink-soft underline hover:text-ink">
            Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
          <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-xl font-bold leading-tight text-ink">{title}</h1>
              {subtitle && <p className="mt-0.5 text-sm text-ink-soft">{subtitle}</p>}
            </div>
            {actions}
          </header>
          {children}
        </div>
      </main>
    </div>
  );
}
