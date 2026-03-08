"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import StatCard from "@/components/stat-card";
import SpendChart from "@/components/spend-chart";
import {
  dailySpendData,
  topModels,
  topTeams,
  recentActivity,
  summaryStats,
} from "@/lib/mock-data";
import { formatCurrency, formatNumber, formatDateTime } from "@/lib/format";
import { Activity, AlertTriangle, Settings2, Cpu } from "lucide-react";
import clsx from "clsx";

const typeIcons: Record<string, typeof Activity> = {
  request: Activity,
  alert: AlertTriangle,
  config: Settings2,
  budget: Cpu,
};

const typeColors: Record<string, string> = {
  request: "text-primary-500 bg-primary-50",
  alert: "text-warning bg-warning-light",
  config: "text-text-secondary bg-surface-secondary",
  budget: "text-success bg-success-light",
};

function BarTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-surface-border bg-surface px-3 py-2 shadow-lg">
      <p className="text-xs font-medium text-text-primary">{label}</p>
      <p className="text-sm font-bold text-primary-600">{formatCurrency(payload[0].value)}</p>
    </div>
  );
}

export default function OverviewPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Overview</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Month-to-date AI spend across all providers and teams.
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="MTD Spend"
          value={formatCurrency(summaryStats.mtdSpend)}
          change={summaryStats.changePercent}
        />
        <StatCard
          label="Total Requests"
          value={formatNumber(summaryStats.totalRequests)}
          subtitle="Across all models"
        />
        <StatCard
          label="Active Models"
          value={String(summaryStats.activeModels)}
          subtitle="Across 3 providers"
        />
        <StatCard
          label="Active Teams"
          value={String(summaryStats.activeTeams)}
          subtitle={`${formatCurrency(summaryStats.mtdSpend / summaryStats.activeTeams)} avg per team`}
        />
      </div>

      {/* Spend Over Time Chart */}
      <SpendChart data={dailySpendData} />

      {/* Bar Charts Row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Top Models */}
        <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-text-primary">
            Top Models by Spend
          </h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={topModels}
                layout="vertical"
                margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="model"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  width={120}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<BarTooltip />} />
                <Bar dataKey="spend" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Teams */}
        <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
          <h3 className="mb-4 text-base font-semibold text-text-primary">
            Top Teams by Spend
          </h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={topTeams}
                layout="vertical"
                margin={{ top: 0, right: 10, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                  tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="team"
                  tick={{ fontSize: 11, fill: "#475569" }}
                  width={130}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<BarTooltip />} />
                <Bar dataKey="spend" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-text-primary">
          Recent Activity
        </h3>
        <div className="divide-y divide-surface-border">
          {recentActivity.map((event) => {
            const Icon = typeIcons[event.type] ?? Activity;
            return (
              <div key={event.id} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
                <div
                  className={clsx(
                    "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                    typeColors[event.type]
                  )}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary">{event.description}</p>
                  <div className="mt-0.5 flex items-center gap-3 text-xs text-text-muted">
                    <span>{formatDateTime(event.timestamp)}</span>
                    <span className="rounded bg-surface-secondary px-1.5 py-0.5 font-medium">
                      {event.team}
                    </span>
                  </div>
                </div>
                {event.cost > 0 && (
                  <span className="shrink-0 text-sm font-medium text-text-primary">
                    {formatCurrency(event.cost)}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
