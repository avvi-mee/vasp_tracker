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
  /** Hops to follow. Server default is 12; it was pinned at 4, which is
   * shorter than most real laundering chains. */
  max_hops?: number;
}

/** A behavioural pattern found in the subject wallet's own transactions —
 * see app/graph/typology.py. These are what let the tool say something is
 * suspicious with no label at all. */
export interface Typology {
  name: string;
  title: string;
  severity: "low" | "medium" | "high";
  confidence: number;
  explanation: string;
  stats: Record<string, number | string | number[]>;
  evidence: string[];
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
  /** Only set on WalletActivity edges below -- "in" (paid the subject) or
   * "out" (subject paid them). Edges on the traced path don't need it: the
   * subject is always the source there, by construction of the search. */
  direction?: "in" | "out";
}

/** Every direct counterparty of the subject address itself, both
 * directions — who funded it, and where it sent funds — separate from
 * `edges` above (the ranked-candidate search's forward path only). This is
 * what answers "where did the money come from": the trace graph alone only
 * ever walks forward from the seed, so a wallet funded by 30 people showed
 * up with nothing pointing at it. Capped per direction so the graph stays
 * legible; `*_total` says how much was left out when it was.
 */
export interface WalletActivity {
  edges: Edge[];
  incoming_shown: number;
  incoming_total: number;
  outgoing_shown: number;
  outgoing_total: number;
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
  typologies: Typology[];
  explorer_flagged: string[];
  /** Addresses on a followed path that the Chainalysis on-chain sanctions
   *  oracle lists. null means the oracle was NOT consulted — non-EVM chain,
   *  or the endpoint was unreachable — which is not the same as clean, and
   *  must not be rendered as though it were. */
  oracle_sanctioned: string[] | null;
  /** Same, from Chainalysis's Sanctions Screening API. Separate field
   *  because the two sources have different reach — the oracle is EVM-only,
   *  this one covers every chain but needs an API key — so which of them
   *  answered is itself information. null = not consulted. */
  api_sanctioned: string[] | null;
  max_hops: number;
  wallet_activity: WalletActivity;
  /** { ASSET_SYMBOL: rupees per whole unit }. Empty when the price feed is
   *  unreachable; the UI then shows token units alone. See app/prices.py. */
  inr_rates: Record<string, number>;
  /** The whole finding restated as one paragraph, generated from the fields
   *  above by a deterministic template (app/graph/summary.py) — not a model,
   *  so it can never assert something the rest of this object does not. */
  summary: string;
}

export interface RiskAssessment {
  compliance_status: string;
  compliance_detail: string;
  risk_flag: boolean;
  risk_level: "none" | "low" | "medium" | "high";
  risk_reason: string | null;
  /** Which question drove risk_level: what the money reached ("trail") or
   * how the wallet itself behaves ("behaviour"). */
  basis: "trail" | "behaviour";
  typologies: string[];
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

/** One hand-entered leg of a UPI/bank money trail. There is no API that
 * produces this — UPI and bank ledgers are private, held by banks and
 * NPCI, and only ever reach this tool because an officer already obtained
 * a hop through a bank disclosure or an NCRP complaint. Every field is
 * nullable: a disclosure rarely arrives complete. */
export interface UpiHop {
  id: number;
  case_id: number;
  hop_order: number;
  payer_vpa: string | null;
  payer_bank: string | null;
  payee_vpa: string | null;
  payee_bank: string | null;
  amount: number | null;
  utr: string | null;
  transferred_at: string | null;
  source: string | null;
  note: string | null;
  officer_id: number | null;
  created_at: string;
}

export interface UpiHopInput {
  payer_vpa?: string;
  payer_bank?: string;
  payee_vpa?: string;
  payee_bank?: string;
  amount?: number;
  utr?: string;
  transferred_at?: string;
  source?: string;
  note?: string;
}

export interface CaseDetail extends Case {
  events: CaseEvent[];
  upi_hops: UpiHop[];
}

export const getCases = (limit = 200) => request<Case[]>(`/v1/cases?limit=${limit}`);

export const getCase = (id: number) => request<CaseDetail>(`/v1/cases/${id}`);

export const updateCase = (
  id: number,
  patch: Partial<Pick<Case, "status" | "tags" | "ncrp_ack_number" | "cctns_fir_number">>
) => request<CaseDetail>(`/v1/cases/${id}`, { method: "PATCH", body: JSON.stringify(patch) });

export type LinkStrength = "same_beneficiary" | "same_wallet" | "shared_intermediary";

export interface LinkedCase {
  case_id: number;
  seed_address: string;
  chain: string;
  label: string | null;
  ncrp_ack_number: string | null;
  cctns_fir_number: string | null;
  status: string;
  created_at: string;
  strength: LinkStrength;
  shared: { address: string; my_role: string; their_role: string }[];
}

export interface LinkCluster {
  chain: string;
  address: string;
  roles: string[];
  case_count: number;
  case_ids: number[];
}

export const getLinkedCases = (id: number) => request<LinkedCase[]>(`/v1/cases/${id}/linked`);

export const getLinkClusters = (limit = 20) => request<LinkCluster[]>(`/v1/links?limit=${limit}`);

export type SahyogRequestType = "disclosure" | "freeze";

/** What the backend's recommend_instrument() returns inside a draft. */
export interface RecommendedInstrument {
  instrument: string;
  label: string;
  reason: string;
  request_type?: SahyogRequestType;
  state?: string | null;
  channel?: string;
  legal_basis?: string;
  options?: { instrument: string; label: string; when: string }[];
}

export const generateSahyogDraft = (id: number, requestType: SahyogRequestType = "disclosure", state?: string) =>
  request<CaseDetail>(`/v1/cases/${id}/sahyog`, {
    method: "POST",
    body: JSON.stringify({ request_type: requestType, state: state || null }),
  });

export const updateSahyogStatus = (id: number, status: string) =>
  request<CaseDetail>(`/v1/cases/${id}/sahyog`, { method: "PATCH", body: JSON.stringify({ status }) });

export const addUpiHop = (caseId: number, hop: UpiHopInput) =>
  request<CaseDetail>(`/v1/cases/${caseId}/upi-hops`, { method: "POST", body: JSON.stringify(hop) });

export const removeUpiHop = (caseId: number, hopId: number) =>
  request<CaseDetail>(`/v1/cases/${caseId}/upi-hops/${hopId}`, { method: "DELETE" });

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

/** Whether unattended re-checking is actually running. The Alerts page shows
 *  this rather than assuming: a list that looks live but is only refreshed by
 *  hand is worse than one that says so. */
export interface WatchlistMonitor {
  enabled: boolean;
  interval_minutes: number;
  /** Unix seconds, null until the first sweep completes. */
  last_sweep_at: number | null;
  last_sweep_checked: number;
  last_sweep_errors: number;
}

export const getWatchlistMonitor = () => request<WatchlistMonitor>("/v1/watchlist/monitor");

export const checkAllWatchlist = () =>
  request<WatchlistMonitor>("/v1/watchlist/check-all", { method: "POST" });

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
