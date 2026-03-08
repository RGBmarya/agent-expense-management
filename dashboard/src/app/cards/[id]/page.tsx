"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import clsx from "clsx";
import { ArrowLeft, Snowflake, X, Loader2 } from "lucide-react";
import {
  fetchCard,
  fetchCardBalance,
  fetchCardTransactions,
  freezeCard,
  unfreezeCard,
  closeCard,
  VirtualCard,
  CardBalance,
  CardTransaction,
} from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/format";
import Link from "next/link";

const statusColors: Record<string, string> = {
  active: "bg-success-light text-success",
  frozen: "bg-warning-light text-warning",
  closed: "bg-danger-light text-danger",
  pending: "bg-surface-secondary text-text-muted",
};

const txnStatusColors: Record<string, string> = {
  completed: "text-success",
  pending: "text-warning",
  declined: "text-danger",
  reversed: "text-text-muted",
};

export default function CardDetailPage() {
  const params = useParams();
  const router = useRouter();
  const cardId = params.id as string;

  const [card, setCard] = useState<VirtualCard | null>(null);
  const [balance, setBalance] = useState<CardBalance | null>(null);
  const [transactions, setTransactions] = useState<CardTransaction[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const [c, b, t] = await Promise.all([
        fetchCard(cardId),
        fetchCardBalance(cardId),
        fetchCardTransactions(cardId),
      ]);
      setCard(c);
      setBalance(b);
      setTransactions(t);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [cardId]);

  async function handleFreeze() {
    await freezeCard(cardId);
    load();
  }

  async function handleUnfreeze() {
    await unfreezeCard(cardId);
    load();
  }

  async function handleClose() {
    if (confirm("Permanently close this card?")) {
      await closeCard(cardId);
      load();
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
      </div>
    );
  }

  if (!card) {
    return <p className="py-12 text-center text-text-muted">Card not found.</p>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/cards"
          className="rounded-lg border border-surface-border p-2 hover:bg-surface-secondary"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-text-primary">
            {card.label || `Card ${card.last4 ? `****${card.last4}` : card.id.slice(0, 8)}`}
          </h1>
          <p className="mt-0.5 text-sm text-text-muted">{card.id}</p>
        </div>
        <span
          className={clsx(
            "rounded-full px-3 py-1.5 text-sm font-semibold",
            statusColors[card.status]
          )}
        >
          {card.status}
        </span>
      </div>

      {/* Detail Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Card Info */}
        <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm lg:col-span-2">
          <h3 className="mb-4 text-base font-semibold text-text-primary">Card Details</h3>
          <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
            <div>
              <span className="text-text-muted">Type</span>
              <p className="font-medium">{card.card_type === "single_use" ? "Single-use" : "Multi-use"}</p>
            </div>
            <div>
              <span className="text-text-muted">Agent</span>
              <p className="font-medium">{card.agent_id || "-"}</p>
            </div>
            <div>
              <span className="text-text-muted">Team</span>
              <p className="font-medium">{card.team || "-"}</p>
            </div>
            <div>
              <span className="text-text-muted">Project</span>
              <p className="font-medium">{card.project || "-"}</p>
            </div>
            <div>
              <span className="text-text-muted">Environment</span>
              <p className="font-medium">{card.environment || "-"}</p>
            </div>
            <div>
              <span className="text-text-muted">Created</span>
              <p className="font-medium">{formatDateTime(card.created_at)}</p>
            </div>
            {card.expires_at && (
              <div>
                <span className="text-text-muted">Expires</span>
                <p className="font-medium">{formatDateTime(card.expires_at)}</p>
              </div>
            )}
            {card.last4 && (
              <div>
                <span className="text-text-muted">Last 4</span>
                <p className="font-medium font-mono">****{card.last4}</p>
              </div>
            )}
          </div>

          {/* Actions */}
          {card.status !== "closed" && (
            <div className="mt-6 flex gap-3 border-t border-surface-border pt-4">
              {card.status === "active" && (
                <button
                  onClick={handleFreeze}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-surface-border px-3 py-2 text-sm font-medium text-text-secondary hover:bg-surface-secondary"
                >
                  <Snowflake className="h-4 w-4" />
                  Freeze
                </button>
              )}
              {card.status === "frozen" && (
                <button
                  onClick={handleUnfreeze}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-surface-border px-3 py-2 text-sm font-medium text-text-secondary hover:bg-surface-secondary"
                >
                  Unfreeze
                </button>
              )}
              <button
                onClick={handleClose}
                className="inline-flex items-center gap-1.5 rounded-lg border border-danger/20 px-3 py-2 text-sm font-medium text-danger hover:bg-danger-light"
              >
                <X className="h-4 w-4" />
                Close Card
              </button>
            </div>
          )}
        </div>

        {/* Balance */}
        {balance && (
          <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
            <h3 className="mb-4 text-base font-semibold text-text-primary">Balance</h3>
            <div className="space-y-3">
              <div>
                <span className="text-xs text-text-muted">Total Spent</span>
                <p className="text-2xl font-bold text-text-primary">
                  {formatCurrency(balance.total_spent_usd)}
                </p>
              </div>
              {balance.remaining_usd !== null && (
                <div>
                  <span className="text-xs text-text-muted">Remaining</span>
                  <p className="text-lg font-semibold text-success">
                    {formatCurrency(balance.remaining_usd)}
                  </p>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-surface-secondary">
                    <div
                      className="h-full rounded-full bg-primary-500"
                      style={{
                        width: `${balance.spending_limit_usd ? Math.min((balance.total_spent_usd / balance.spending_limit_usd) * 100, 100) : 0}%`,
                      }}
                    />
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3 border-t border-surface-border pt-3">
                <div>
                  <span className="text-xs text-text-muted">Daily</span>
                  <p className="text-sm font-medium">
                    {formatCurrency(balance.daily_spent_usd)}
                    {balance.daily_limit_usd && (
                      <span className="text-text-muted"> / {formatCurrency(balance.daily_limit_usd)}</span>
                    )}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-text-muted">Monthly</span>
                  <p className="text-sm font-medium">
                    {formatCurrency(balance.monthly_spent_usd)}
                    {balance.monthly_limit_usd && (
                      <span className="text-text-muted"> / {formatCurrency(balance.monthly_limit_usd)}</span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Transactions */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
        <h3 className="mb-4 text-base font-semibold text-text-primary">
          Transactions ({transactions.length})
        </h3>
        {transactions.length === 0 ? (
          <p className="py-8 text-center text-sm text-text-muted">No transactions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-text-muted">Date</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-text-muted">Merchant</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-text-muted">MCC</th>
                  <th className="px-3 py-2 text-right text-xs font-semibold uppercase text-text-muted">Amount</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold uppercase text-text-muted">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {transactions.map((txn) => (
                  <tr key={txn.id} className="hover:bg-surface-secondary/30">
                    <td className="px-3 py-2.5 text-text-secondary whitespace-nowrap">
                      {formatDateTime(txn.created_at)}
                    </td>
                    <td className="px-3 py-2.5 text-text-primary">{txn.merchant_name || "-"}</td>
                    <td className="px-3 py-2.5 text-text-muted font-mono text-xs">{txn.merchant_mcc || "-"}</td>
                    <td className="px-3 py-2.5 text-right font-medium text-text-primary">
                      {formatCurrency(txn.amount_usd)}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={clsx("text-xs font-semibold", txnStatusColors[txn.status])}>
                        {txn.status}
                      </span>
                      {txn.decline_reason && (
                        <span className="ml-1 text-xs text-text-muted">({txn.decline_reason})</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
