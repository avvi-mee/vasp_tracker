"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getOfficer, getToken, type Officer } from "@/lib/auth";

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
