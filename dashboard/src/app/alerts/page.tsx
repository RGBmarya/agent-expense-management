"use client";

import { useState } from "react";
import clsx from "clsx";
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  Plus,
  Bell,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";
import { budgetAlerts, alertHistory, BudgetAlert } from "@/lib/mock-data";
import { formatCurrency, formatDateTime } from "@/lib/format";

const statusConfig: Record<
  BudgetAlert["status"],
  { label: string; icon: typeof Shield; className: string; barColor: string }
> = {
  ok: {
    label: "OK",
    icon: ShieldCheck,
    className: "text-success bg-success-light",
    barColor: "bg-success",
  },
  warning: {
    label: "Warning",
    icon: ShieldAlert,
    className: "text-warning bg-warning-light",
    barColor: "bg-warning",
  },
  exceeded: {
    label: "Exceeded",
    icon: XCircle,
    className: "text-danger bg-danger-light",
    barColor: "bg-danger",
  },
};

export default function AlertsPage() {
  const [showForm, setShowForm] = useState(false);
  const [formScope, setFormScope] = useState<"team" | "project" | "model">("team");
  const [formName, setFormName] = useState("");
  const [formScopeValue, setFormScopeValue] = useState("");
  const [formThreshold, setFormThreshold] = useState("");
  const [formPeriod, setFormPeriod] = useState<"daily" | "weekly" | "monthly">("monthly");
  const [formEmail, setFormEmail] = useState(true);
  const [formSlack, setFormSlack] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    // In a real app, this would call the API
    alert(`Alert "${formName}" created (demo only)`);
    setShowForm(false);
    setFormName("");
    setFormScopeValue("");
    setFormThreshold("");
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Budget Alerts</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Configure spend thresholds and receive notifications.
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-600"
        >
          <Plus className="h-4 w-4" />
          Create Alert
        </button>
      </div>

      {/* Create Alert Form */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-surface-border bg-surface p-6 shadow-sm"
        >
          <h3 className="mb-4 text-base font-semibold text-text-primary">
            New Budget Alert
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">
                Alert Name
              </label>
              <input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Engineering Monthly Cap"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">
                Scope
              </label>
              <select
                value={formScope}
                onChange={(e) => setFormScope(e.target.value as "team" | "project" | "model")}
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
              >
                <option value="team">Team</option>
                <option value="project">Project</option>
                <option value="model">Model</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">
                Scope Value
              </label>
              <input
                value={formScopeValue}
                onChange={(e) => setFormScopeValue(e.target.value)}
                placeholder={`e.g. ${formScope === "team" ? "AI Platform" : formScope === "project" ? "chatbot-v2" : "gpt-4o"}`}
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">
                Threshold ($)
              </label>
              <input
                type="number"
                value={formThreshold}
                onChange={(e) => setFormThreshold(e.target.value)}
                placeholder="e.g. 5000"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
                required
                min={1}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">
                Period
              </label>
              <select
                value={formPeriod}
                onChange={(e) => setFormPeriod(e.target.value as "daily" | "weekly" | "monthly")}
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">
                Notification Channels
              </label>
              <div className="flex items-center gap-4 pt-2">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={formEmail}
                    onChange={(e) => setFormEmail(e.target.checked)}
                    className="rounded border-surface-border"
                  />
                  Email
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={formSlack}
                    onChange={(e) => setFormSlack(e.target.checked)}
                    className="rounded border-surface-border"
                  />
                  Slack
                </label>
              </div>
            </div>
          </div>
          <div className="mt-5 flex gap-3">
            <button
              type="submit"
              className="rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600"
            >
              Create Alert
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-text-secondary hover:bg-surface-secondary"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Active Alerts */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {budgetAlerts.map((alert) => {
          const cfg = statusConfig[alert.status];
          const Icon = cfg.icon;
          const pct = Math.min((alert.currentSpend / alert.threshold) * 100, 100);

          return (
            <div
              key={alert.id}
              className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-text-primary">{alert.name}</h4>
                  <p className="mt-0.5 text-xs text-text-muted">
                    {alert.scope}: {alert.scopeValue} &middot; {alert.period}
                  </p>
                </div>
                <span
                  className={clsx(
                    "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold",
                    cfg.className
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {cfg.label}
                </span>
              </div>

              <div className="mt-4">
                <div className="flex items-baseline justify-between text-sm">
                  <span className="font-medium text-text-primary">
                    {formatCurrency(alert.currentSpend)}
                  </span>
                  <span className="text-text-muted">
                    of {formatCurrency(alert.threshold)}
                  </span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-secondary">
                  <div
                    className={clsx("h-full rounded-full transition-all", cfg.barColor)}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <p className="mt-1.5 text-xs text-text-muted">{pct.toFixed(1)}% used</p>
              </div>

              <div className="mt-3 flex items-center gap-2">
                {alert.channels.map((ch) => (
                  <span
                    key={ch}
                    className="rounded bg-surface-secondary px-2 py-0.5 text-xs font-medium text-text-secondary capitalize"
                  >
                    {ch}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Alert History */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-text-primary">
          Alert History
        </h3>
        <div className="divide-y divide-surface-border">
          {alertHistory.map((entry) => (
            <div key={entry.id} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
              <div
                className={clsx(
                  "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                  entry.level === "exceeded"
                    ? "bg-danger-light text-danger"
                    : "bg-warning-light text-warning"
                )}
              >
                <Bell className="h-4 w-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-text-primary">{entry.alertName}</p>
                  <span
                    className={clsx(
                      "rounded-full px-2 py-0.5 text-xs font-semibold",
                      entry.level === "exceeded"
                        ? "bg-danger-light text-danger"
                        : "bg-warning-light text-warning"
                    )}
                  >
                    {entry.level}
                  </span>
                </div>
                <p className="mt-0.5 text-sm text-text-secondary">{entry.message}</p>
                <div className="mt-1 flex items-center gap-3 text-xs text-text-muted">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDateTime(entry.triggeredAt)}
                  </span>
                  <span className="flex items-center gap-1">
                    {entry.acknowledged ? (
                      <>
                        <CheckCircle2 className="h-3 w-3 text-success" />
                        Acknowledged
                      </>
                    ) : (
                      <>
                        <XCircle className="h-3 w-3 text-text-muted" />
                        Pending
                      </>
                    )}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
