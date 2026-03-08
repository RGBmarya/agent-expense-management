// ─── Types ────────────────────────────────────────────────────────────────────

export interface DailySpend {
  date: string;
  total: number;
  openai: number;
  anthropic: number;
  google: number;
}

export interface ModelSpend {
  model: string;
  provider: string;
  spend: number;
  tokens: number;
  requests: number;
}

export interface TeamSpend {
  team: string;
  spend: number;
  models: number;
  members: number;
}

export interface ActivityEvent {
  id: string;
  timestamp: string;
  type: "request" | "alert" | "config" | "budget";
  description: string;
  team: string;
  cost: number;
}

export interface ExplorerEvent {
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
}

export interface BudgetAlert {
  id: string;
  name: string;
  scope: "team" | "project" | "model";
  scopeValue: string;
  threshold: number;
  currentSpend: number;
  period: "daily" | "weekly" | "monthly";
  status: "ok" | "warning" | "exceeded";
  channels: string[];
  createdAt: string;
}

export interface AlertHistoryEntry {
  id: string;
  alertName: string;
  triggeredAt: string;
  level: "warning" | "exceeded";
  message: string;
  acknowledged: boolean;
}

export interface DepartmentCost {
  department: string;
  team: string;
  spend: number;
  tokens: number;
  requests: number;
  avgCostPerRequest: number;
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  createdAt: string;
  lastUsed: string | null;
  status: "active" | "revoked";
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: "admin" | "member" | "viewer";
  team: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function dateStr(daysAgo: number): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return d.toISOString().split("T")[0];
}

function ts(daysAgo: number, hour: number = 12): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  d.setHours(hour, Math.floor(Math.random() * 60), 0, 0);
  return d.toISOString();
}

// ─── Daily Spend (30 days) ────────────────────────────────────────────────────

export const dailySpendData: DailySpend[] = Array.from({ length: 30 }, (_, i) => {
  const day = 29 - i;
  const base = 800 + Math.sin(i * 0.3) * 200;
  const openai = base * (0.45 + Math.random() * 0.1);
  const anthropic = base * (0.30 + Math.random() * 0.08);
  const google = base * (0.15 + Math.random() * 0.05);
  return {
    date: dateStr(day),
    total: Math.round((openai + anthropic + google) * 100) / 100,
    openai: Math.round(openai * 100) / 100,
    anthropic: Math.round(anthropic * 100) / 100,
    google: Math.round(google * 100) / 100,
  };
});

// ─── Top Models ───────────────────────────────────────────────────────────────

export const topModels: ModelSpend[] = [
  { model: "gpt-4o", provider: "OpenAI", spend: 8420.50, tokens: 42_100_000, requests: 128_400 },
  { model: "claude-3.5-sonnet", provider: "Anthropic", spend: 6230.80, tokens: 31_150_000, requests: 95_200 },
  { model: "gpt-4o-mini", provider: "OpenAI", spend: 3150.20, tokens: 63_000_000, requests: 210_000 },
  { model: "claude-3-haiku", provider: "Anthropic", spend: 2840.60, tokens: 56_800_000, requests: 189_000 },
  { model: "gemini-1.5-pro", provider: "Google", spend: 2210.40, tokens: 22_100_000, requests: 73_700 },
  { model: "gpt-3.5-turbo", provider: "OpenAI", spend: 1450.30, tokens: 72_500_000, requests: 241_600 },
  { model: "claude-3-opus", provider: "Anthropic", spend: 1280.90, tokens: 4_270_000, requests: 14_200 },
  { model: "gemini-1.5-flash", provider: "Google", spend: 890.10, tokens: 44_500_000, requests: 148_300 },
];

// ─── Top Teams ────────────────────────────────────────────────────────────────

export const topTeams: TeamSpend[] = [
  { team: "AI Platform", spend: 9820.40, models: 6, members: 14 },
  { team: "Search & Discovery", spend: 5430.20, models: 4, members: 8 },
  { team: "Customer Support", spend: 4210.80, models: 3, members: 12 },
  { team: "Content Generation", spend: 3650.50, models: 5, members: 6 },
  { team: "Data Science", spend: 2180.90, models: 4, members: 9 },
  { team: "DevOps", spend: 1180.00, models: 2, members: 5 },
];

// ─── Recent Activity ──────────────────────────────────────────────────────────

export const recentActivity: ActivityEvent[] = [
  { id: "a1", timestamp: ts(0, 14), type: "alert", description: "Budget warning: AI Platform team at 85% of monthly limit", team: "AI Platform", cost: 0 },
  { id: "a2", timestamp: ts(0, 13), type: "request", description: "Batch inference job completed (gpt-4o, 12K requests)", team: "Search & Discovery", cost: 342.80 },
  { id: "a3", timestamp: ts(0, 11), type: "config", description: "Rate limit updated for Content Generation team", team: "Content Generation", cost: 0 },
  { id: "a4", timestamp: ts(0, 9), type: "request", description: "RAG pipeline processed 5.2M tokens via claude-3.5-sonnet", team: "AI Platform", cost: 218.40 },
  { id: "a5", timestamp: ts(1, 16), type: "budget", description: "Monthly budget increased to $12,000 for AI Platform", team: "AI Platform", cost: 0 },
  { id: "a6", timestamp: ts(1, 14), type: "request", description: "Customer support chatbot served 8.4K conversations", team: "Customer Support", cost: 156.20 },
  { id: "a7", timestamp: ts(1, 10), type: "alert", description: "Anomaly detected: 3x spike in gpt-4o usage from Data Science", team: "Data Science", cost: 0 },
  { id: "a8", timestamp: ts(2, 15), type: "request", description: "Content pipeline generated 2,400 product descriptions", team: "Content Generation", cost: 89.60 },
  { id: "a9", timestamp: ts(2, 11), type: "config", description: "New API key provisioned for DevOps team", team: "DevOps", cost: 0 },
  { id: "a10", timestamp: ts(3, 9), type: "request", description: "Search reranking model processed 1.8M queries", team: "Search & Discovery", cost: 412.30 },
];

// ─── Explorer Events ──────────────────────────────────────────────────────────

const providers = ["OpenAI", "Anthropic", "Google"];
const models: Record<string, string[]> = {
  OpenAI: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
  Anthropic: ["claude-3.5-sonnet", "claude-3-haiku", "claude-3-opus"],
  Google: ["gemini-1.5-pro", "gemini-1.5-flash"],
};
const teams = ["AI Platform", "Search & Discovery", "Customer Support", "Content Generation", "Data Science", "DevOps"];
const projects = ["chatbot-v2", "search-reranker", "content-pipeline", "rag-system", "analytics-copilot", "code-review-bot"];
const environments = ["production", "staging", "development"];

export const explorerEvents: ExplorerEvent[] = Array.from({ length: 200 }, (_, i) => {
  const provider = providers[i % 3];
  const modelList = models[provider];
  const model = modelList[i % modelList.length];
  const daysAgo = Math.floor(i / 8);
  const hour = 8 + (i % 12);
  const inputTokens = Math.floor(500 + Math.random() * 15000);
  const outputTokens = Math.floor(100 + Math.random() * 5000);
  const costPerToken = model.includes("4o") ? 0.000005 : model.includes("opus") ? 0.000015 : model.includes("sonnet") ? 0.000003 : 0.0000005;
  return {
    id: `evt-${i}`,
    timestamp: ts(daysAgo, hour),
    provider,
    model,
    team: teams[i % teams.length],
    project: projects[i % projects.length],
    environment: environments[i % environments.length],
    inputTokens,
    outputTokens,
    cost: Math.round((inputTokens + outputTokens) * costPerToken * 100) / 100,
  };
});

// ─── Budget Alerts ────────────────────────────────────────────────────────────

export const budgetAlerts: BudgetAlert[] = [
  { id: "ba1", name: "AI Platform Monthly Cap", scope: "team", scopeValue: "AI Platform", threshold: 12000, currentSpend: 9820.40, period: "monthly", status: "warning", channels: ["email", "slack"], createdAt: "2025-12-01" },
  { id: "ba2", name: "GPT-4o Daily Limit", scope: "model", scopeValue: "gpt-4o", threshold: 500, currentSpend: 612.30, period: "daily", status: "exceeded", channels: ["slack"], createdAt: "2026-01-15" },
  { id: "ba3", name: "Customer Support Budget", scope: "team", scopeValue: "Customer Support", threshold: 6000, currentSpend: 4210.80, period: "monthly", status: "ok", channels: ["email"], createdAt: "2026-01-01" },
  { id: "ba4", name: "Content Pipeline Weekly", scope: "project", scopeValue: "content-pipeline", threshold: 1500, currentSpend: 1120.50, period: "weekly", status: "warning", channels: ["email", "slack"], createdAt: "2026-02-01" },
  { id: "ba5", name: "Data Science Monthly", scope: "team", scopeValue: "Data Science", threshold: 4000, currentSpend: 2180.90, period: "monthly", status: "ok", channels: ["email"], createdAt: "2026-01-10" },
  { id: "ba6", name: "DevOps Budget", scope: "team", scopeValue: "DevOps", threshold: 2000, currentSpend: 1180.00, period: "monthly", status: "ok", channels: ["slack"], createdAt: "2026-02-15" },
];

export const alertHistory: AlertHistoryEntry[] = [
  { id: "ah1", alertName: "GPT-4o Daily Limit", triggeredAt: ts(0, 10), level: "exceeded", message: "Daily spend of $612.30 exceeded threshold of $500.00", acknowledged: false },
  { id: "ah2", alertName: "AI Platform Monthly Cap", triggeredAt: ts(0, 8), level: "warning", message: "Monthly spend at 81.8% of $12,000.00 threshold", acknowledged: false },
  { id: "ah3", alertName: "Content Pipeline Weekly", triggeredAt: ts(1, 15), level: "warning", message: "Weekly spend at 74.7% of $1,500.00 threshold", acknowledged: true },
  { id: "ah4", alertName: "GPT-4o Daily Limit", triggeredAt: ts(1, 10), level: "exceeded", message: "Daily spend of $534.10 exceeded threshold of $500.00", acknowledged: true },
  { id: "ah5", alertName: "AI Platform Monthly Cap", triggeredAt: ts(3, 9), level: "warning", message: "Monthly spend at 75.2% of $12,000.00 threshold", acknowledged: true },
  { id: "ah6", alertName: "GPT-4o Daily Limit", triggeredAt: ts(5, 11), level: "exceeded", message: "Daily spend of $548.90 exceeded threshold of $500.00", acknowledged: true },
];

// ─── Reports ──────────────────────────────────────────────────────────────────

export const departmentCosts: DepartmentCost[] = [
  { department: "Engineering", team: "AI Platform", spend: 9820.40, tokens: 98_200_000, requests: 327_300, avgCostPerRequest: 0.030 },
  { department: "Engineering", team: "DevOps", spend: 1180.00, tokens: 23_600_000, requests: 78_600, avgCostPerRequest: 0.015 },
  { department: "Product", team: "Search & Discovery", spend: 5430.20, tokens: 54_300_000, requests: 181_000, avgCostPerRequest: 0.030 },
  { department: "Product", team: "Content Generation", spend: 3650.50, tokens: 36_500_000, requests: 121_600, avgCostPerRequest: 0.030 },
  { department: "Operations", team: "Customer Support", spend: 4210.80, tokens: 84_200_000, requests: 280_600, avgCostPerRequest: 0.015 },
  { department: "Analytics", team: "Data Science", spend: 2180.90, tokens: 21_800_000, requests: 72_600, avgCostPerRequest: 0.030 },
];

export const invoiceData = {
  tracked: 26472.80,
  invoices: [
    { provider: "OpenAI", invoiceAmount: 13250.00, trackedAmount: 13021.00, delta: 229.00 },
    { provider: "Anthropic", invoiceAmount: 10500.00, trackedAmount: 10352.30, delta: 147.70 },
    { provider: "Google", invoiceAmount: 3200.00, trackedAmount: 3100.50, delta: 99.50 },
  ],
};

// ─── Settings ─────────────────────────────────────────────────────────────────

export const apiKeys: ApiKey[] = [
  { id: "k1", name: "Production Ingest", prefix: "al_prod_8f2a", createdAt: "2025-11-15", lastUsed: ts(0, 14), status: "active" },
  { id: "k2", name: "Staging Ingest", prefix: "al_stg_3b7c", createdAt: "2026-01-10", lastUsed: ts(1, 9), status: "active" },
  { id: "k3", name: "Dev Testing", prefix: "al_dev_9d1e", createdAt: "2026-02-20", lastUsed: ts(5, 11), status: "active" },
  { id: "k4", name: "Old Production Key", prefix: "al_prod_1a4f", createdAt: "2025-08-01", lastUsed: "2025-11-14T10:00:00.000Z", status: "revoked" },
];

export const teamMembers: TeamMember[] = [
  { id: "m1", name: "Sarah Chen", email: "sarah.chen@company.com", role: "admin", team: "AI Platform" },
  { id: "m2", name: "James Wilson", email: "james.w@company.com", role: "admin", team: "Search & Discovery" },
  { id: "m3", name: "Maria Garcia", email: "m.garcia@company.com", role: "member", team: "Customer Support" },
  { id: "m4", name: "Alex Kim", email: "alex.kim@company.com", role: "member", team: "Content Generation" },
  { id: "m5", name: "Raj Patel", email: "raj.patel@company.com", role: "member", team: "Data Science" },
  { id: "m6", name: "Emily Zhang", email: "emily.z@company.com", role: "viewer", team: "DevOps" },
  { id: "m7", name: "David Okafor", email: "d.okafor@company.com", role: "member", team: "AI Platform" },
  { id: "m8", name: "Lisa Nguyen", email: "l.nguyen@company.com", role: "viewer", team: "Search & Discovery" },
];

// ─── Summary Stats ────────────────────────────────────────────────────────────

export const summaryStats = {
  mtdSpend: 26472.80,
  lastMonthSpend: 24150.60,
  changePercent: 9.6,
  activeModels: 8,
  activeTeams: 6,
  totalRequests: 1_061_200,
};
