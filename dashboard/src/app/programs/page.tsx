"use client";

import { useEffect, useState } from "react";
import { Package, Plus, Loader2, CreditCard } from "lucide-react";
import {
  fetchPrograms,
  createProgram,
  issueCardFromProgram,
  SpendProgram,
} from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/format";

export default function ProgramsPage() {
  const [programs, setPrograms] = useState<SpendProgram[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [formName, setFormName] = useState("");
  const [formLimit, setFormLimit] = useState("");
  const [formTeam, setFormTeam] = useState("");
  const [formExpireDays, setFormExpireDays] = useState("");

  async function load() {
    setLoading(true);
    try {
      setPrograms(await fetchPrograms());
    } catch {
      setPrograms([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const payload: Record<string, unknown> = { name: formName };
    if (formLimit) payload.spending_limit_usd = parseFloat(formLimit);
    if (formTeam) payload.team = formTeam;
    if (formExpireDays) payload.auto_expire_days = parseInt(formExpireDays);
    await createProgram(payload);
    setShowCreate(false);
    setFormName("");
    setFormLimit("");
    setFormTeam("");
    setFormExpireDays("");
    load();
  }

  async function handleIssue(programId: string) {
    const label = prompt("Card label (optional):");
    await issueCardFromProgram(programId, { label: label || undefined });
    alert("Card issued successfully!");
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Spend Programs</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Templates for one-call card provisioning with preset rules.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-600"
        >
          <Plus className="h-4 w-4" />
          Create Program
        </button>
      </div>

      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="rounded-xl border border-surface-border bg-surface p-6 shadow-sm"
        >
          <h3 className="mb-4 text-base font-semibold text-text-primary">New Program</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Name</label>
              <input
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="e.g. Research Agent"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Spending Limit ($)</label>
              <input
                type="number"
                value={formLimit}
                onChange={(e) => setFormLimit(e.target.value)}
                placeholder="e.g. 500"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Team</label>
              <input
                value={formTeam}
                onChange={(e) => setFormTeam(e.target.value)}
                placeholder="e.g. research"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Auto-expire (days)</label>
              <input
                type="number"
                value={formExpireDays}
                onChange={(e) => setFormExpireDays(e.target.value)}
                placeholder="e.g. 90"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400"
              />
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
      ) : programs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-surface-border p-12 text-center">
          <Package className="mx-auto h-10 w-10 text-text-muted" />
          <p className="mt-3 text-sm text-text-secondary">No programs yet. Create one for quick card provisioning.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {programs.map((p) => (
            <div key={p.id} className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-text-primary">{p.name}</h4>
                  <p className="text-xs text-text-muted mt-0.5">
                    {p.card_type === "single_use" ? "Single-use" : "Multi-use"}
                    {p.team && ` · ${p.team}`}
                  </p>
                </div>
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${p.is_active ? "bg-success-light text-success" : "bg-surface-secondary text-text-muted"}`}>
                  {p.is_active ? "Active" : "Inactive"}
                </span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-text-muted">Limit</span>
                  <p className="font-medium">{p.spending_limit_usd ? formatCurrency(p.spending_limit_usd) : "No limit"}</p>
                </div>
                {p.auto_expire_days && (
                  <div>
                    <span className="text-text-muted">Expires</span>
                    <p className="font-medium">{p.auto_expire_days} days</p>
                  </div>
                )}
              </div>
              <div className="mt-4">
                <button
                  onClick={() => handleIssue(p.id)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-primary-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-600"
                >
                  <CreditCard className="h-3.5 w-3.5" />
                  Issue Card
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
