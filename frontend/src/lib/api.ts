// Hand-written client for the FastAPI service (app/api/main.py) — the API
// surface is five endpoints today, small enough that generating a typed
// client from /openapi.json isn't earning its keep yet. Revisit
// (openapi-typescript + openapi-fetch, per the plan) once it grows.

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

class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const getChains = () => request<Record<string, ChainInfo>>("/v1/chains");

export const getCoverage = () => request<Record<string, number>>("/v1/coverage");

export const traceWallet = (body: TraceRequest) =>
  request<TraceResponse>("/v1/trace", { method: "POST", body: JSON.stringify(body) });

/** Fetches the s.63 evidence zip and triggers a browser download — the
 * sandbox blocks a plain <a href> to a POST endpoint, so this does the
 * fetch-as-blob dance itself. */
export async function downloadCertificate(body: TraceRequest): Promise<void> {
  const res = await fetch(`${API_URL}/v1/certificate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(err.detail ?? `${res.status} ${res.statusText}`);
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
