"use client";

import { useState, useMemo } from "react";
import clsx from "clsx";
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";

export interface Column<T> {
  key: string;
  label: string;
  render?: (row: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  pageSize?: number;
  keyExtractor: (row: T) => string;
}

type SortDir = "asc" | "desc";

export default function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  pageSize = 10,
  keyExtractor,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    if (!sortKey) return data;
    return [...data].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
  }, [data, sortKey, sortDir]);

  const totalPages = Math.ceil(sorted.length / pageSize);
  const paged = sorted.slice(page * pageSize, (page + 1) * pageSize);

  function handleSort(key: string) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
    setPage(0);
  }

  return (
    <div className="overflow-hidden rounded-xl border border-surface-border bg-surface shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-surface-border bg-surface-secondary">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={clsx(
                    "px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-text-muted",
                    col.sortable && "cursor-pointer select-none hover:text-text-secondary",
                    col.className
                  )}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.label}
                    {col.sortable && sortKey === col.key && (
                      sortDir === "asc" ? (
                        <ChevronUp className="h-3.5 w-3.5" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5" />
                      )
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {paged.map((row) => (
              <tr
                key={keyExtractor(row)}
                className="transition-colors hover:bg-surface-secondary/60"
              >
                {columns.map((col) => (
                  <td key={col.key} className={clsx("px-4 py-3 text-text-primary", col.className)}>
                    {col.render ? col.render(row) : (row[col.key] as React.ReactNode)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-surface-border px-4 py-3">
          <p className="text-xs text-text-muted">
            Showing {page * pageSize + 1}–{Math.min((page + 1) * pageSize, sorted.length)} of{" "}
            {sorted.length}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-surface-secondary hover:text-text-primary disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i;
              } else if (page < 3) {
                pageNum = i;
              } else if (page > totalPages - 4) {
                pageNum = totalPages - 5 + i;
              } else {
                pageNum = page - 2 + i;
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={clsx(
                    "h-8 w-8 rounded-md text-xs font-medium transition-colors",
                    page === pageNum
                      ? "bg-primary-500 text-white"
                      : "text-text-muted hover:bg-surface-secondary hover:text-text-primary"
                  )}
                >
                  {pageNum + 1}
                </button>
              );
            })}
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page === totalPages - 1}
              className="rounded-md p-1.5 text-text-muted transition-colors hover:bg-surface-secondary hover:text-text-primary disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
