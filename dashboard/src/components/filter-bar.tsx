"use client";

import { SlidersHorizontal } from "lucide-react";

export interface FilterOption {
  key: string;
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
}

interface FilterBarProps {
  filters: FilterOption[];
  onReset?: () => void;
}

export default function FilterBar({ filters, onReset }: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-surface-border bg-surface p-4 shadow-sm">
      <div className="flex items-center gap-2 text-sm font-medium text-text-secondary">
        <SlidersHorizontal className="h-4 w-4" />
        Filters
      </div>
      <div className="h-6 w-px bg-surface-border" />
      {filters.map((f) => (
        <select
          key={f.key}
          value={f.value}
          onChange={(e) => f.onChange(e.target.value)}
          className="rounded-lg border border-surface-border bg-surface-secondary px-3 py-1.5 text-sm text-text-primary outline-none transition-colors focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
        >
          <option value="">{f.label}</option>
          {f.options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ))}
      {onReset && (
        <button
          onClick={onReset}
          className="ml-auto text-xs font-medium text-primary-500 hover:text-primary-700"
        >
          Reset filters
        </button>
      )}
    </div>
  );
}
