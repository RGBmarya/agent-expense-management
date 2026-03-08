// ─── API Client ──────────────────────────────────────────────────────────────
// Typed fetch wrappers for the AgentLedger backend API.
// In development mode these fall through to mock data; swap BASE_URL for prod.

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, params, ...init } = options;

  let url = `${BASE_URL}${path}`;
  if (params) {
    const search = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) search.set(k, String(v));
    }
    const qs = search.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };

  const token = typeof window !== "undefined" ? localStorage.getItem("al_token") : null;
  if (token) headers["X-API-Key"] = token;

  const res = await fetch(url, {
    ...init,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, text);
  }

  return res.json() as Promise<T>;
}

// ─── Dashboard Overview ─────────────────────────────────────────────────────

export interface BreakdownItem {
  key: string;
  total_cost_usd: number;
  request_count: number;
}

export interface TrendPoint {
  date: string;
  total_cost_usd: number;
  request_count: number;
}

export interface OverviewResponse {
  mtd_spend_usd: number;
  previous_mtd_spend_usd: number;
  trend_30d: TrendPoint[];
  top_providers: BreakdownItem[];
  top_models: BreakdownItem[];
  top_teams: BreakdownItem[];
}

export function fetchOverview() {
  return request<OverviewResponse>("/dashboard/overview");
}

// ─── Explorer ────────────────────────────────────────────────────────────────

export interface ExplorerFilters {
  start_date?: string;
  end_date?: string;
  provider?: string;
  model?: string;
  team?: string;
  project?: string;
  environment?: string;
  limit?: number;
  offset?: number;
}

export interface ExploreRow {
  provider: string;
  model: string;
  team: string | null;
  project: string | null;
  environment: string | null;
  total_cost_usd: number;
  request_count: number;
}

export interface ExploreResponse {
  rows: ExploreRow[];
  total: number;
}

export function fetchExplorerEvents(filters: ExplorerFilters = {}) {
  return request<ExploreResponse>("/dashboard/explore", {
    params: filters as Record<string, string>,
  });
}

// ─── Spend Over Time ────────────────────────────────────────────────────────

export interface SpendTimeseriesPoint {
  period_start: string;
  total_cost_usd: number;
  request_count: number;
}

export function fetchSpendOverTime(params: {
  start_date?: string;
  end_date?: string;
  granularity?: "hourly" | "daily" | "monthly";
  provider?: string;
  model?: string;
  team?: string;
} = {}) {
  return request<{ data: SpendTimeseriesPoint[]; granularity: string }>(
    "/dashboard/spend-over-time",
    { params: params as Record<string, string> },
  );
}

// ─── Alerts ──────────────────────────────────────────────────────────────────

export interface CreateAlertPayload {
  scope: "org" | "provider" | "team" | "project" | "model";
  scope_value: string;
  threshold_usd: number;
  period: "hourly" | "daily" | "monthly";
  notify_channels?: Record<string, unknown>;
  predictive?: boolean;
}

export interface BudgetAlertResponse {
  id: string;
  org_id: string;
  scope: string;
  scope_value: string;
  period: string;
  threshold_usd: number;
  notify_channels: Record<string, unknown> | null;
  predictive: boolean;
  last_triggered_at: string | null;
}

export function fetchAlerts() {
  return request<BudgetAlertResponse[]>("/alerts");
}

export function createAlert(payload: CreateAlertPayload) {
  return request<BudgetAlertResponse>("/alerts", { method: "POST", body: payload });
}

export function deleteAlert(id: string) {
  return request<void>(`/alerts/${id}`, { method: "DELETE" });
}

export function checkAlerts() {
  return request<{ results: { alert_id: string; scope: string; scope_value: string; threshold_usd: number; current_spend_usd: number; pct_used: number; triggered: boolean }[] }>("/alerts/check");
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export function fetchMonthlyReport(month: string) {
  return request<{
    rows: { month: string; team: string; project: string; provider: string; total_cost_usd: number; request_count: number }[];
    grand_total_usd: number;
  }>("/reports/monthly", { params: { month } });
}

export function fetchInvoiceReconciliation(month: string, lineItems: { provider: string; invoice_amount_usd: number }[]) {
  return request<{
    month: string;
    rows: { provider: string; tracked_usd: number; invoice_usd: number; difference_usd: number; pct_difference: number }[];
  }>("/reports/invoice-reconciliation", { method: "POST", body: { month, line_items: lineItems } });
}

export function exportCsvUrl(params: ExplorerFilters = {}): string {
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) search.set(k, String(v));
  }
  const qs = search.toString();
  return `${BASE_URL}/reports/export${qs ? `?${qs}` : ""}`;
}

// ─── Auth / API Keys ────────────────────────────────────────────────────────

export function fetchApiKeys() {
  return request<{ keys: { id: string; label: string; created_at: string; revoked_at: string | null }[] }>("/auth/keys");
}

export function createApiKey(label: string) {
  return request<{ id: string; raw_key: string; label: string; created_at: string }>("/auth/keys", { method: "POST", body: { label } });
}

export function revokeApiKey(id: string) {
  return request<void>(`/auth/keys/${id}`, { method: "DELETE" });
}
