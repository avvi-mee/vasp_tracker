// Hand-written client for the FastAPI service (app/api/main.py) — the API
// surface is small enough that generating a typed client from /openapi.json
// isn't earning its keep yet. Revisit (openapi-typescript + openapi-fetch,
// per the plan) once it grows.

import { clearSession, getToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface TraceRequest {
  address: string;
  chain?: string;
  case_reference?: string;
  analyst_note?: string;
}

export interface DepositEvidence {
  address: string;
  vasp_address: string;
  is_deposit_address: boolean;
  confidence: number;
  forwarded_ratio: number;
  destination_share: number;
  distinct_funders: number;
  sweep_count: number;
  median_hold_seconds: number | null;
  asset: string;
  caveats: string[];
}

export interface Candidate {
  path: string[];
  hop_count: number;
  entity_type: string;
  label: string | null;
  confidence: number;
  source: string | null;
  reason: string | null;
  asset: [string, string] | null;
  deposit: DepositEvidence | null;
  value_share: number;
  merged_path_count: number;
}

export interface Edge {
  from: string;
  to: string;
  tx_hash: string | null;
  value_wei: number | string | null;
  amount: number | null;
  asset: string | null;
  timestamp: number | null;
  block_number: number | null;
}

export interface ExposureCategory {
  category: string;
  label: string | null;
  value_share: number;
}

export interface ExposureBreakdown {
  direct: ExposureCategory[];
  indirect: ExposureCategory[];
}

export interface SeedExposure {
  receiving: ExposureCategory[];
  sending: ExposureCategory[];
}

export interface TraceResultJson {
  seed_address: string;
  path: string[];
  hop_count: number;
  entity_type: string;
  label: string | null;
  confidence: number;
  source: string | null;
  reason: string | null;
  asset: [string, string] | null;
  deposit: DepositEvidence | null;
  candidates: Candidate[];
  edges: Edge[];
  caveats: string[];
  exposure: ExposureBreakdown;
  seed_exposure: SeedExposure;
}

export interface RiskAssessment {
  compliance_status: string;
  compliance_detail: string;
  risk_flag: boolean;
  risk_level: "none" | "low" | "medium" | "high";
  risk_reason: string | null;
}

export interface TraceResponse {
  chain: string;
  case_id: number | null;
  trace: TraceResultJson;
  risk: RiskAssessment;
  sahyog_draft: Record<string, unknown>;
}

export interface ChainInfo {
  enabled: boolean;
  currency: string | null;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeaders() },
    ...init,
  });
  if (res.status === 401) clearSession(); // stale/expired token — next page load sends them to /login
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail ?? `${res.status} ${res.statusText}`, res.status);
  }
  return res.json() as Promise<T>;
}

export interface LoginResponse {
  token: string;
  officer: { id: number; username: string; role: string; display_name: string };
}

export const login = (username: string, password: string) =>
  request<LoginResponse>("/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });

export const getChains = () => request<Record<string, ChainInfo>>("/v1/chains");

export const getCoverage = () => request<Record<string, number>>("/v1/coverage");

export const traceWallet = (body: TraceRequest) =>
  request<TraceResponse>("/v1/trace", { method: "POST", body: JSON.stringify(body) });

export interface Case {
  id: number;
  seed_address: string;
  chain: string;
  entity_type: string | null;
  label: string | null;
  confidence: number | null;
  hop_count: number | null;
  path: string[] | null;
  compliance_status: string | null;
  compliance_detail: string | null;
  risk_flag: boolean;
  risk_level: "none" | "low" | "medium" | "high";
  risk_reason: string | null;
  status: "open" | "pending" | "closed";
  tags: string[];
  officer_id: number | null;
  ncrp_ack_number: string | null;
  cctns_fir_number: string | null;
  sahyog_status: "draft" | "ready_for_submission" | "submitted" | "acknowledged" | "fulfilled" | null;
  sahyog_instrument: string | null;
  sahyog_draft: Record<string, unknown> | null;
  created_at: string;
}

export interface CaseEvent {
  id: number;
  officer_id: number | null;
  action: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface CaseDetail extends Case {
  events: CaseEvent[];
}

export const getCases = (limit = 200) => request<Case[]>(`/v1/cases?limit=${limit}`);

export const getCase = (id: number) => request<CaseDetail>(`/v1/cases/${id}`);

export const updateCase = (
  id: number,
  patch: Partial<Pick<Case, "status" | "tags" | "ncrp_ack_number" | "cctns_fir_number">>
) => request<CaseDetail>(`/v1/cases/${id}`, { method: "PATCH", body: JSON.stringify(patch) });

export const generateSahyogDraft = (id: number) =>
  request<CaseDetail>(`/v1/cases/${id}/sahyog`, { method: "POST" });

export const updateSahyogStatus = (id: number, status: string) =>
  request<CaseDetail>(`/v1/cases/${id}/sahyog`, { method: "PATCH", body: JSON.stringify({ status }) });

export interface WatchlistEntry {
  id: number;
  address: string;
  chain: string;
  added_by_officer_id: number | null;
  added_at: string;
  last_checked_at: string | null;
  last_entity_type: string | null;
  last_label: string | null;
  last_risk_level: "none" | "low" | "medium" | "high";
  alert_status: "clear" | "open" | "acknowledged";
  alert_reason: string | null;
}

export const getWatchlist = () => request<WatchlistEntry[]>("/v1/watchlist");

export const addToWatchlist = (address: string, chain?: string) =>
  request<WatchlistEntry>("/v1/watchlist", { method: "POST", body: JSON.stringify({ address, chain }) });

export const checkWatchlistEntry = (id: number) =>
  request<WatchlistEntry>(`/v1/watchlist/${id}/check`, { method: "POST" });

export const updateWatchlistStatus = (id: number, status: string) =>
  request<WatchlistEntry>(`/v1/watchlist/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });

export const removeFromWatchlist = (id: number) =>
  request<{ status: string }>(`/v1/watchlist/${id}`, { method: "DELETE" });

/** Fetches the s.63 evidence zip and triggers a browser download — the
 * sandbox blocks a plain <a href> to a POST endpoint, so this does the
 * fetch-as-blob dance itself. */
export async function downloadCertificate(body: TraceRequest): Promise<void> {
  const res = await fetch(`${API_URL}/v1/certificate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (res.status === 401) clearSession();
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(err.detail ?? `${res.status} ${res.statusText}`, res.status);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? "evidence.zip";

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
