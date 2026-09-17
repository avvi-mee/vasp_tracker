"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clearSession, getOfficer, getToken, type Officer } from "@/lib/auth";

/** Every screen behind login goes through this — checked client-side since
 * there's no server session to check against (the JWT lives in
 * localStorage). Redirects to /login with nothing rendered rather than a
 * flash of protected content, if there's no valid-looking session. */
export function AuthGuard({ children }: { children: (officer: Officer) => React.ReactNode }) {
  const router = useRouter();
  const [officer, setOfficer] = useState<Officer | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token = getToken();
    const stored = getOfficer();
    if (!token || !stored) {
      router.replace("/login");
      return;
    }
    setOfficer(stored);
    setChecked(true);
  }, [router]);

  if (!checked || !officer) return null;
  return <>{children(officer)}</>;
}

export function OfficerBar({ officer }: { officer: Officer }) {
  const router = useRouter();
  return (
    <div className="mb-4 flex items-center justify-between text-xs text-ink-soft">
      <span>
        Signed in as <b className="text-ink">{officer.display_name}</b> ·{" "}
        {officer.role === "officer" ? "Investigating Officer" : officer.role === "supervisor" ? "Reviewing Officer" : "Nodal Admin"}
      </span>
      <button
        onClick={() => {
          clearSession();
          router.replace("/login");
        }}
        className="rounded px-2 py-1 hover:bg-ledger-soft"
      >
        Sign out
      </button>
    </div>
  );
}
