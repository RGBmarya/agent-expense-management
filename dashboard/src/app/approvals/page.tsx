"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { CheckCircle, XCircle, Clock, Loader2 } from "lucide-react";
import {
  fetchApprovals,
  approveRequest,
  denyRequest,
  ApprovalRequest,
} from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/format";

const statusConfig = {
  pending: { label: "Pending", className: "bg-warning-light text-warning", icon: Clock },
  approved: { label: "Approved", className: "bg-success-light text-success", icon: CheckCircle },
  denied: { label: "Denied", className: "bg-danger-light text-danger", icon: XCircle },
};

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  async function load() {
    setLoading(true);
    try {
      setApprovals(await fetchApprovals(filter || undefined));
    } catch {
      setApprovals([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filter]);

  async function handleApprove(id: string) {
    await approveRequest(id);
    load();
  }

  async function handleDeny(id: string) {
    const reason = prompt("Denial reason (optional):");
    await denyRequest(id, reason || undefined);
    load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Approvals</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Review and decide on transactions that exceed policy thresholds.
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {["", "pending", "approved", "denied"].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={clsx(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              filter === s
                ? "bg-primary-500 text-white"
                : "bg-surface-secondary text-text-secondary hover:bg-surface-border"
            )}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
        </div>
      ) : approvals.length === 0 ? (
        <div className="rounded-xl border border-dashed border-surface-border p-12 text-center">
          <CheckCircle className="mx-auto h-10 w-10 text-text-muted" />
          <p className="mt-3 text-sm text-text-secondary">No approval requests found.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {approvals.map((a) => {
            const cfg = statusConfig[a.status];
            const Icon = cfg.icon;
            return (
              <div
                key={a.id}
                className="flex items-center gap-4 rounded-xl border border-surface-border bg-surface p-5 shadow-sm"
              >
                <div className={clsx("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", cfg.className)}>
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-text-primary">
                      {formatCurrency(a.amount_usd)}
                    </p>
                    <span className={clsx("rounded-full px-2 py-0.5 text-xs font-semibold", cfg.className)}>
                      {cfg.label}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-text-muted">
                    {a.merchant_name || "Unknown merchant"} · Card {a.card_id.slice(0, 8)}
                  </p>
                  <p className="text-xs text-text-muted">{formatDateTime(a.requested_at)}</p>
                  {a.reason && (
                    <p className="mt-1 text-xs text-text-secondary">Reason: {a.reason}</p>
                  )}
                </div>
                {a.status === "pending" && (
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => handleApprove(a.id)}
                      className="inline-flex items-center gap-1 rounded-lg bg-success px-3 py-1.5 text-xs font-medium text-white hover:bg-success/90"
                    >
                      <CheckCircle className="h-3.5 w-3.5" />
                      Approve
                    </button>
                    <button
                      onClick={() => handleDeny(a.id)}
                      className="inline-flex items-center gap-1 rounded-lg bg-danger px-3 py-1.5 text-xs font-medium text-white hover:bg-danger/90"
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      Deny
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
