"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { DailySpend } from "@/lib/mock-data";
import { formatCurrency, formatDate } from "@/lib/format";

interface SpendChartProps {
  data: DailySpend[];
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; name: string; color: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-surface-border bg-surface px-4 py-3 shadow-lg">
      <p className="mb-2 text-sm font-medium text-text-primary">
        {label ? formatDate(label, "MMM d, yyyy") : ""}
      </p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center justify-between gap-6 text-sm">
          <div className="flex items-center gap-2">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-text-secondary capitalize">{entry.name}</span>
          </div>
          <span className="font-medium text-text-primary">
            {formatCurrency(entry.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function SpendChart({ data }: SpendChartProps) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
      <h3 className="mb-4 text-base font-semibold text-text-primary">
        Spend Over Time
      </h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="gradOpenAI" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradAnthropic" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradGoogle" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              tickFormatter={(v: string) => formatDate(v, "MMM d")}
              axisLine={{ stroke: "#e2e8f0" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 12, fill: "#94a3b8" }}
              tickFormatter={(v: number) => `$${v}`}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              verticalAlign="top"
              align="right"
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 12, paddingBottom: 8 }}
            />
            <Area
              type="monotone"
              dataKey="openai"
              name="OpenAI"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#gradOpenAI)"
              stackId="1"
            />
            <Area
              type="monotone"
              dataKey="anthropic"
              name="Anthropic"
              stroke="#8b5cf6"
              strokeWidth={2}
              fill="url(#gradAnthropic)"
              stackId="1"
            />
            <Area
              type="monotone"
              dataKey="google"
              name="Google"
              stroke="#10b981"
              strokeWidth={2}
              fill="url(#gradGoogle)"
              stackId="1"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
