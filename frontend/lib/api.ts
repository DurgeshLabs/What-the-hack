/**
 * Thin fetch wrapper for the FastAPI backend.
 * Response shapes follow docs/api/api-contracts.md.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type HealthResponse = Record<string, unknown>;

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface AlertCard {
  id: string;
  status: string;
  severity: string;
  title: string;
  summary: string;
  risk_score: number;
  risk_level: RiskLevel;
  predicted_attack_type: string | null;
  confidence_score: number;
  forecast_window_start: string;
  forecast_window_end: string;
  created_at: string;
  recommended_actions: string[];
  top_feature_contributors: { feature: string; contribution: number; value?: number }[];
}

export interface AlertListResponse {
  items: AlertCard[];
  next_cursor: string | null;
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (!(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} for ${path}`);
  }
  return (await response.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "analyst" | "viewer";
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_at: string;
  user: AuthUser;
}

/** POST /auth/login. The backend identifies users by email; 401 on bad credentials, 429 when rate-limited. */
export function login(email: string, password: string): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function saveSession(session: TokenResponse) { localStorage.setItem("wth_session", JSON.stringify(session)); }
export function getSession(): TokenResponse | null { const raw = typeof window === "undefined" ? null : localStorage.getItem("wth_session"); try { return raw ? JSON.parse(raw) as TokenResponse : null; } catch { return null; } }
export function clearSession() { if (typeof window !== "undefined") localStorage.removeItem("wth_session"); }
export function isUnauthorized(error: unknown) { return error instanceof Error && error.message.startsWith("401 "); }

export function refresh(refreshToken: string): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token: refreshToken }) });
}

export function logout(token: string): Promise<void> {
  return fetch(`${API_BASE_URL}/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).then(() => undefined);
}

export function listAlerts(token: string): Promise<AlertListResponse> {
  return request<AlertListResponse>("/alerts", {}, token);
}

export function getAlertDetail(token: string, id: string): Promise<AlertCard> {
  return request<AlertCard>(`/alerts/${id}`, {}, token);
}

export interface TrafficWindow {
  id: string;
  traffic_source_id: string;
  window_start: string;
  window_end: string;
  window_seconds: number;
  flow_count: number;
  packet_count: number;
  byte_count: number;
}

export interface TrafficWindowListResponse {
  items: TrafficWindow[];
  next_cursor: string | null;
}

/** Windows are paginated: pass the previous page's next_cursor as `after` to continue. */
export function listWindows(token: string, trafficSourceId: string, after?: string | null, limit = 200): Promise<TrafficWindowListResponse> {
  const params = new URLSearchParams({ traffic_source_id: trafficSourceId, limit: String(limit) });
  if (after) params.set("after", after);
  return request<TrafficWindowListResponse>(`/windows?${params.toString()}`, {}, token);
}

export interface Overview {
  traffic_source_id: string; window_count: number; model_ready: boolean;
  traffic: { timestamp: string; packets: number; bytes: number; flows: number }[];
  latest_features: Record<string, number> | null;
}
export interface Forecast {
  observed_until: string; peak_risk_level: RiskLevel; peak_risk_stage: string | null;
  risk_timeline: { step: number; risk_score: number; stage: string | null }[];
  top_feature_contributors: { feature: string; contribution: number; value?: number }[];
}

export function getOverview(token: string, sourceId: string): Promise<Overview> {
  return request<Overview>(`/analytics/overview?traffic_source_id=${encodeURIComponent(sourceId)}`, {}, token);
}

export function getForecast(token: string, sourceId: string): Promise<Forecast> {
  return request<Forecast>(`/analytics/forecast?traffic_source_id=${encodeURIComponent(sourceId)}`, {}, token);
}
export function saveForecast(token: string, sourceId: string): Promise<{alert_id: string; forecast: Forecast}> {
  return request(`/analytics/forecast?traffic_source_id=${encodeURIComponent(sourceId)}`, { method: "POST" }, token);
}
export interface IngestionJob { id: string; traffic_source_id: string; status: string; total_rows: number; accepted_rows: number; skipped_rows: number; error_message: string | null; }
export interface TrafficSource { id: string; name: string; source_type: "csv_replay" | "zeek_live"; description: string | null; is_active: boolean; created_at: string; updated_at: string; }
export function listTrafficSources(token: string): Promise<TrafficSource[]> {
  return request<TrafficSource[]>("/ingestion/sources", {}, token);
}
export function startReplay(token: string, file: File): Promise<IngestionJob> {
  const form = new FormData(); form.append("file", file);
  return request<IngestionJob>("/ingestion/upload", { method: "POST", body: form }, token);
}
export function getJobStatus(token: string, jobId: string): Promise<IngestionJob> {
  return request<IngestionJob>(`/ingestion/${jobId}/status`, {}, token);
}
