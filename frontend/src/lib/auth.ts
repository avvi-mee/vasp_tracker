// Session storage for the officer login — kept in localStorage (not an
// httpOnly cookie), a disclosed, deliberate simplification for a
// same-origin-mismatched dev setup (:3000 calling :8000). Revisit before any
// real deployment. See the plan's Auth section for the reasoning.

const TOKEN_KEY = "vasp_trace_token";
const OFFICER_KEY = "vasp_trace_officer";

export interface Officer {
  id: number;
  username: string;
  role: string;
  display_name: string;
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getOfficer(): Officer | null {
  try {
    const raw = localStorage.getItem(OFFICER_KEY);
    return raw ? (JSON.parse(raw) as Officer) : null;
  } catch {
    return null;
  }
}

export function setSession(token: string, officer: Officer): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(OFFICER_KEY, JSON.stringify(officer));
  } catch {
    // localStorage unavailable (private browsing, etc.) — session just won't survive a reload.
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(OFFICER_KEY);
  } catch {
    // nothing to clear if we couldn't read it either
  }
}
