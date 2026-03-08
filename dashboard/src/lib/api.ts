// ─── API Client ──────────────────────────────────────────────────────────────
// Typed fetch wrappers for the AgentLedger backend API.
// In development mode these fall through to mock data; swap BASE_URL for prod.

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

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
  if (token) headers["Authorization"] = `Bearer ${token}`;

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

// ─── Spend & Analytics ───────────────────────────────────────────────────────

export interface SpendSummary {
  mtdSpend: number;
  lastMonthSpend: number;
  changePercent: number;
  activeModels: number;
  activeTeams: number;
  totalRequests: number;
}

export interface DailySpendPoint {
  date: string;
  total: number;
  openai: number;
  anthropic: number;
  google: number;
}

export function fetchSummary() {
  return request<SpendSummary>("/analytics/summary");
}

export function fetchDailySpend(days = 30) {
  return request<DailySpendPoint[]>("/analytics/daily-spend", { params: { days } });
}

export function fetchTopModels(limit = 8) {
  return request<{ model: string; provider: string; spend: number; tokens: number; requests: number }[]>(
    "/analytics/top-models",
    { params: { limit } },
  );
}

export function fetchTopTeams(limit = 6) {
  return request<{ team: string; spend: number; models: number; members: number }[]>(
    "/analytics/top-teams",
    { params: { limit } },
  );
}

// ─── Explorer ────────────────────────────────────────────────────────────────

export interface ExplorerFilters {
  startDate?: string;
  endDate?: string;
  provider?: string;
  model?: string;
  team?: string;
  project?: string;
  environment?: string;
  page?: number;
  pageSize?: number;
}

export function fetchExplorerEvents(filters: ExplorerFilters = {}) {
  return request<{
    events: {
      id: string;
      timestamp: string;
      provider: string;
      model: string;
      team: string;
      project: string;
      environment: string;
      inputTokens: number;
      outputTokens: number;
      cost: number;
    }[];
    total: number;
    page: number;
    pageSize: number;
  }>("/events", { params: filters as Record<string, string> });
}

// ─── Alerts ──────────────────────────────────────────────────────────────────

export interface CreateAlertPayload {
  name: string;
  scope: "team" | "project" | "model";
  scopeValue: string;
  threshold: number;
  period: "daily" | "weekly" | "monthly";
  channels: string[];
}

export function fetchAlerts() {
  return request<{ id: string; name: string; scope: string; scopeValue: string; threshold: number; currentSpend: number; period: string; status: string; channels: string[]; createdAt: string }[]>("/alerts");
}

export function createAlert(payload: CreateAlertPayload) {
  return request<{ id: string }>("/alerts", { method: "POST", body: payload });
}

export function deleteAlert(id: string) {
  return request<void>(`/alerts/${id}`, { method: "DELETE" });
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export function fetchDepartmentCosts(month?: string) {
  return request<{ department: string; team: string; spend: number; tokens: number; requests: number; avgCostPerRequest: number }[]>(
    "/reports/department-costs",
    { params: { month } },
  );
}

export function fetchInvoiceReconciliation() {
  return request<{
    tracked: number;
    invoices: { provider: string; invoiceAmount: number; trackedAmount: number; delta: number }[];
  }>("/reports/invoice-reconciliation");
}

// ─── Settings ────────────────────────────────────────────────────────────────

export function fetchApiKeys() {
  return request<{ id: string; name: string; prefix: string; createdAt: string; lastUsed: string | null; status: string }[]>("/settings/api-keys");
}

export function createApiKey(name: string) {
  return request<{ id: string; key: string }>("/settings/api-keys", { method: "POST", body: { name } });
}

export function revokeApiKey(id: string) {
  return request<void>(`/settings/api-keys/${id}/revoke`, { method: "POST" });
}

export function fetchTeamMembers() {
  return request<{ id: string; name: string; email: string; role: string; team: string }[]>("/settings/team-members");
}

export function updateNotificationPrefs(prefs: { email: boolean; slackWebhook: string | null }) {
  return request<void>("/settings/notifications", { method: "PUT", body: prefs });
}
