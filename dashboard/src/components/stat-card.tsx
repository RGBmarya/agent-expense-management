import clsx from "clsx";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string;
  change?: number; // percentage
  subtitle?: string;
}

export default function StatCard({ label, value, change, subtitle }: StatCardProps) {
  const isPositive = change !== undefined && change >= 0;

  return (
    <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
      <p className="text-sm font-medium text-text-secondary">{label}</p>
      <p className="mt-1.5 text-2xl font-bold tracking-tight text-text-primary">
        {value}
      </p>
      {change !== undefined && (
        <div className="mt-2 flex items-center gap-1">
          <span
            className={clsx(
              "inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-semibold",
              isPositive
                ? "bg-danger-light text-danger"
                : "bg-success-light text-success"
            )}
          >
            {isPositive ? (
              <ArrowUpRight className="h-3 w-3" />
            ) : (
              <ArrowDownRight className="h-3 w-3" />
            )}
            {Math.abs(change).toFixed(1)}%
          </span>
          <span className="text-xs text-text-muted">vs last month</span>
        </div>
      )}
      {subtitle && (
        <p className="mt-2 text-xs text-text-muted">{subtitle}</p>
      )}
    </div>
  );
}
