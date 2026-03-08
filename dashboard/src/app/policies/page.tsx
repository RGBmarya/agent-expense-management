"use client";

import { useEffect, useState } from "react";
import { Shield, Plus, Trash2, Loader2 } from "lucide-react";
import {
  fetchPolicies,
  createPolicy,
  deletePolicy,
  SpendPolicy,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<SpendPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [formName, setFormName] = useState("");
  const [formMaxTxn, setFormMaxTxn] = useState("");
  const [formDailyLimit, setFormDailyLimit] = useState("");
  const [formMonthlyLimit, setFormMonthlyLimit] = useState("");
  const [formApprovalAbove, setFormApprovalAbove] = useState("");
  const [formDefault, setFormDefault] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await fetchPolicies();
      setPolicies(data);
    } catch {
      setPolicies([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const payload: Record<string, unknown> = { name: formName };
    if (formMaxTxn) payload.max_transaction_usd = parseFloat(formMaxTxn);
    if (formDailyLimit) payload.daily_limit_usd = parseFloat(formDailyLimit);
    if (formMonthlyLimit) payload.monthly_limit_usd = parseFloat(formMonthlyLimit);
    if (formApprovalAbove) payload.require_approval_above_usd = parseFloat(formApprovalAbove);
    if (formDefault) payload.is_default = true;
    await createPolicy(payload);
    setShowCreate(false);
    setFormName("");
    setFormMaxTxn("");
    setFormDailyLimit("");
    setFormMonthlyLimit("");
    setFormApprovalAbove("");
    setFormDefault(false);
    load();
  }

  async function handleDelete(id: string) {
    if (confirm("Delete this policy?")) {
      await deletePolicy(id);
      load();
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Spend Policies</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Reusable rule templates that can be attached to cards.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-600"
        >
          <Plus className="h-4 w-4" />
          Create Policy
        </button>
      </div>

      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="rounded-xl border border-surface-border bg-surface p-6 shadow-sm"
        >
          <h3 className="mb-4 text-base font-semibold text-text-primary">New Policy</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Name</label>
              <input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Engineering SaaS"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Max Transaction ($)</label>
              <input
                type="number"
                value={formMaxTxn}
                onChange={(e) => setFormMaxTxn(e.target.value)}
                placeholder="e.g. 200"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Daily Limit ($)</label>
              <input
                type="number"
                value={formDailyLimit}
                onChange={(e) => setFormDailyLimit(e.target.value)}
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Monthly Limit ($)</label>
              <input
                type="number"
                value={formMonthlyLimit}
                onChange={(e) => setFormMonthlyLimit(e.target.value)}
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Require Approval Above ($)</label>
              <input
                type="number"
                value={formApprovalAbove}
                onChange={(e) => setFormApprovalAbove(e.target.value)}
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formDefault}
                  onChange={(e) => setFormDefault(e.target.checked)}
                  className="rounded border-surface-border"
                />
                Org-wide default
              </label>
            </div>
          </div>
          <div className="mt-5 flex gap-3">
            <button type="submit" className="rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600">
              Create
            </button>
            <button type="button" onClick={() => setShowCreate(false)} className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-text-secondary hover:bg-surface-secondary">
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
        </div>
      ) : policies.length === 0 ? (
        <div className="rounded-xl border border-dashed border-surface-border p-12 text-center">
          <Shield className="mx-auto h-10 w-10 text-text-muted" />
          <p className="mt-3 text-sm text-text-secondary">No policies yet. Create one to enforce spending rules.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {policies.map((p) => (
            <div key={p.id} className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-text-primary">{p.name}</h4>
                  <p className="text-xs text-text-muted mt-0.5">
                    Scope: {p.scope}
                    {p.is_default && " (default)"}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(p.id)}
                  className="rounded p-1 text-text-muted hover:text-danger hover:bg-danger-light"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                {p.max_transaction_usd && (
                  <div>
                    <span className="text-text-muted">Max Txn</span>
                    <p className="font-medium">{formatCurrency(p.max_transaction_usd)}</p>
                  </div>
                )}
                {p.daily_limit_usd && (
                  <div>
                    <span className="text-text-muted">Daily Limit</span>
                    <p className="font-medium">{formatCurrency(p.daily_limit_usd)}</p>
                  </div>
                )}
                {p.monthly_limit_usd && (
                  <div>
                    <span className="text-text-muted">Monthly Limit</span>
                    <p className="font-medium">{formatCurrency(p.monthly_limit_usd)}</p>
                  </div>
                )}
                {p.require_approval_above_usd && (
                  <div>
                    <span className="text-text-muted">Approval Above</span>
                    <p className="font-medium">{formatCurrency(p.require_approval_above_usd)}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
