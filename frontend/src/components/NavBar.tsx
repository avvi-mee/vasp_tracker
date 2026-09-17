"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Investigate" },
  { href: "/cases", label: "Cases" },
];

export function NavBar() {
  const pathname = usePathname();
  return (
    <nav className="mb-4 flex gap-1 text-xs">
      {LINKS.map((l) => {
        const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            className={`rounded px-3 py-1.5 font-semibold ${active ? "bg-navy text-white" : "bg-ledger-soft text-ink-soft"}`}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
