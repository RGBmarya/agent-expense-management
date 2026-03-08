"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import clsx from "clsx";
import { CreditCard, Plus, Snowflake, X, Loader2 } from "lucide-react";
import {
  fetchCards,
  createCard,
  freezeCard,
  unfreezeCard,
  closeCard,
  VirtualCard,
  CreateCardPayload,
} from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/format";

const statusColors: Record<string, string> = {
  active: "bg-success-light text-success",
  frozen: "bg-warning-light text-warning",
  closed: "bg-danger-light text-danger",
  pending: "bg-surface-secondary text-text-muted",
};

export default function CardsPage() {
  const [cards, setCards] = useState<VirtualCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formLabel, setFormLabel] = useState("");
  const [formLimit, setFormLimit] = useState("");
  const [formTeam, setFormTeam] = useState("");
  const [formProject, setFormProject] = useState("");
  const [formSingleUse, setFormSingleUse] = useState(false);

  async function loadCards() {
    setLoading(true);
    try {
      const data = await fetchCards(statusFilter ? { status: statusFilter } : {});
      setCards(data);
    } catch {
      setCards([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadCards(); }, [statusFilter]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    try {
      const payload: CreateCardPayload = { label: formLabel };
      if (formLimit) payload.spending_limit_usd = parseFloat(formLimit);
      if (formTeam) payload.team = formTeam;
      if (formProject) payload.project = formProject;
      if (formSingleUse) payload.card_type = "single_use";
      await createCard(payload);
      setShowCreate(false);
      setFormLabel("");
      setFormLimit("");
      setFormTeam("");
      setFormProject("");
      setFormSingleUse(false);
      loadCards();
    } finally {
      setCreating(false);
    }
  }

  async function handleFreeze(id: string) {
    await freezeCard(id);
    loadCards();
  }

  async function handleUnfreeze(id: string) {
    await unfreezeCard(id);
    loadCards();
  }

  async function handleClose(id: string) {
    if (confirm("Permanently close this card?")) {
      await closeCard(id);
      loadCards();
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Virtual Cards</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Manage agent virtual cards for purchases and subscriptions.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-600"
        >
          <Plus className="h-4 w-4" />
          Create Card
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {["", "active", "frozen", "closed"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={clsx(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              statusFilter === s
                ? "bg-primary-500 text-white"
                : "bg-surface-secondary text-text-secondary hover:bg-surface-border"
            )}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {/* Create Form */}
      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="rounded-xl border border-surface-border bg-surface p-6 shadow-sm"
        >
          <h3 className="mb-4 text-base font-semibold text-text-primary">New Card</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Label</label>
              <input
                value={formLabel}
                onChange={(e) => setFormLabel(e.target.value)}
                placeholder="e.g. research-agent-42"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Spending Limit ($)</label>
              <input
                type="number"
                value={formLimit}
                onChange={(e) => setFormLimit(e.target.value)}
                placeholder="e.g. 500"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Team</label>
              <input
                value={formTeam}
                onChange={(e) => setFormTeam(e.target.value)}
                placeholder="e.g. engineering"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-text-secondary">Project</label>
              <input
                value={formProject}
                onChange={(e) => setFormProject(e.target.value)}
                placeholder="e.g. chatbot-v2"
                className="w-full rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={formSingleUse}
                  onChange={(e) => setFormSingleUse(e.target.checked)}
                  className="rounded border-surface-border"
                />
                Single-use card
              </label>
            </div>
          </div>
          <div className="mt-5 flex gap-3">
            <button
              type="submit"
              disabled={creating}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600 disabled:opacity-50"
            >
              {creating && <Loader2 className="h-4 w-4 animate-spin" />}
              Create
            </button>
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-text-secondary hover:bg-surface-secondary"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Card Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
        </div>
      ) : cards.length === 0 ? (
        <div className="rounded-xl border border-dashed border-surface-border p-12 text-center">
          <CreditCard className="mx-auto h-10 w-10 text-text-muted" />
          <p className="mt-3 text-sm text-text-secondary">No cards found. Create your first card.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {cards.map((card) => (
            <div
              key={card.id}
              className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div>
                  <Link
                    href={`/cards/${card.id}`}
                    className="text-sm font-semibold text-text-primary hover:text-primary-600"
                  >
                    {card.label || `Card ${card.last4 ? `****${card.last4}` : card.id.slice(0, 8)}`}
                  </Link>
                  <p className="mt-0.5 text-xs text-text-muted">
                    {card.card_type === "single_use" ? "Single-use" : "Multi-use"}
                    {card.agent_id && ` · ${card.agent_id}`}
                  </p>
                </div>
                <span
                  className={clsx(
                    "rounded-full px-2.5 py-1 text-xs font-semibold",
                    statusColors[card.status]
                  )}
                >
                  {card.status}
                </span>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-text-muted">Limit</span>
                  <p className="font-medium text-text-primary">
                    {card.spending_limit_usd ? formatCurrency(card.spending_limit_usd) : "No limit"}
                  </p>
                </div>
                <div>
                  <span className="text-text-muted">Team</span>
                  <p className="font-medium text-text-primary">{card.team || "-"}</p>
                </div>
                <div>
                  <span className="text-text-muted">Project</span>
                  <p className="font-medium text-text-primary">{card.project || "-"}</p>
                </div>
                <div>
                  <span className="text-text-muted">Created</span>
                  <p className="font-medium text-text-primary">{formatDateTime(card.created_at)}</p>
                </div>
              </div>

              {card.status !== "closed" && (
                <div className="mt-4 flex gap-2">
                  {card.status === "active" && (
                    <button
                      onClick={() => handleFreeze(card.id)}
                      className="inline-flex items-center gap-1 rounded-lg border border-surface-border px-2.5 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface-secondary"
                    >
                      <Snowflake className="h-3 w-3" />
                      Freeze
                    </button>
                  )}
                  {card.status === "frozen" && (
                    <button
                      onClick={() => handleUnfreeze(card.id)}
                      className="inline-flex items-center gap-1 rounded-lg border border-surface-border px-2.5 py-1.5 text-xs font-medium text-text-secondary hover:bg-surface-secondary"
                    >
                      Unfreeze
                    </button>
                  )}
                  <button
                    onClick={() => handleClose(card.id)}
                    className="inline-flex items-center gap-1 rounded-lg border border-danger/20 px-2.5 py-1.5 text-xs font-medium text-danger hover:bg-danger-light"
                  >
                    <X className="h-3 w-3" />
                    Close
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
