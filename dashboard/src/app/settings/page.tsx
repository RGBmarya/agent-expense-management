"use client";

import { useState } from "react";
import clsx from "clsx";
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Users,
  Mail,
  MessageSquare,
  Shield,
  Eye,
  UserCircle,
} from "lucide-react";
import { apiKeys, teamMembers, ApiKey, TeamMember } from "@/lib/mock-data";
import { formatDate, formatDateTime } from "@/lib/format";

const roleConfig: Record<TeamMember["role"], { label: string; className: string; icon: typeof Shield }> = {
  admin: { label: "Admin", className: "bg-primary-100 text-primary-700", icon: Shield },
  member: { label: "Member", className: "bg-surface-secondary text-text-secondary", icon: UserCircle },
  viewer: { label: "Viewer", className: "bg-surface-secondary text-text-muted", icon: Eye },
};

export default function SettingsPage() {
  const [keys, setKeys] = useState(apiKeys);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [slackWebhook, setSlackWebhook] = useState("https://hooks.slack.com/services/T00.../B00.../xxxx");
  const [newKeyName, setNewKeyName] = useState("");
  const [showNewKeyInput, setShowNewKeyInput] = useState(false);

  function handleCreateKey(e: React.FormEvent) {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    const newKey: ApiKey = {
      id: `k${keys.length + 1}`,
      name: newKeyName,
      prefix: `al_new_${Math.random().toString(36).slice(2, 6)}`,
      createdAt: new Date().toISOString().split("T")[0],
      lastUsed: null,
      status: "active",
    };
    setKeys([newKey, ...keys]);
    setNewKeyName("");
    setShowNewKeyInput(false);
  }

  function handleRevokeKey(id: string) {
    setKeys((prev) =>
      prev.map((k) => (k.id === id ? { ...k, status: "revoked" as const } : k))
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Manage API keys, teams, and notification preferences.
        </p>
      </div>

      {/* API Keys */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5 text-text-secondary" />
            <h3 className="text-base font-semibold text-text-primary">API Keys</h3>
          </div>
          <button
            onClick={() => setShowNewKeyInput(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-600"
          >
            <Plus className="h-4 w-4" />
            Create Key
          </button>
        </div>

        {showNewKeyInput && (
          <form onSubmit={handleCreateKey} className="mt-4 flex items-center gap-3">
            <input
              autoFocus
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="Key name (e.g. Production Ingest)"
              className="flex-1 rounded-lg border border-surface-border px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
              required
            />
            <button
              type="submit"
              className="rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600"
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => setShowNewKeyInput(false)}
              className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-text-secondary hover:bg-surface-secondary"
            >
              Cancel
            </button>
          </form>
        )}

        <div className="mt-4 divide-y divide-surface-border">
          {keys.map((key) => (
            <div key={key.id} className="flex items-center gap-4 py-3">
              <div
                className={clsx(
                  "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
                  key.status === "active"
                    ? "bg-success-light text-success"
                    : "bg-surface-secondary text-text-muted"
                )}
              >
                <Key className="h-4 w-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-text-primary">{key.name}</p>
                  {key.status === "revoked" && (
                    <span className="rounded bg-danger-light px-1.5 py-0.5 text-xs font-medium text-danger">
                      Revoked
                    </span>
                  )}
                </div>
                <div className="mt-0.5 flex items-center gap-3 text-xs text-text-muted">
                  <span className="font-mono">{key.prefix}...</span>
                  <span>Created {formatDate(key.createdAt)}</span>
                  {key.lastUsed && <span>Last used {formatDateTime(key.lastUsed)}</span>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="rounded-md p-1.5 text-text-muted hover:bg-surface-secondary hover:text-text-primary"
                  title="Copy key prefix"
                >
                  <Copy className="h-4 w-4" />
                </button>
                {key.status === "active" && (
                  <button
                    onClick={() => handleRevokeKey(key.id)}
                    className="rounded-md p-1.5 text-text-muted hover:bg-danger-light hover:text-danger"
                    title="Revoke key"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Team Management */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-text-secondary" />
          <h3 className="text-base font-semibold text-text-primary">Team Members</h3>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border">
                <th className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Name
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Email
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Team
                </th>
                <th className="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Role
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {teamMembers.map((member) => {
                const cfg = roleConfig[member.role];
                return (
                  <tr key={member.id} className="hover:bg-surface-secondary/30">
                    <td className="px-3 py-2.5 font-medium text-text-primary">{member.name}</td>
                    <td className="px-3 py-2.5 text-text-secondary">{member.email}</td>
                    <td className="px-3 py-2.5 text-text-secondary">{member.team}</td>
                    <td className="px-3 py-2.5">
                      <span
                        className={clsx(
                          "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
                          cfg.className
                        )}
                      >
                        {cfg.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Notification Preferences */}
      <div className="rounded-xl border border-surface-border bg-surface p-5 shadow-sm">
        <div className="flex items-center gap-2">
          <Mail className="h-5 w-5 text-text-secondary" />
          <h3 className="text-base font-semibold text-text-primary">Notification Preferences</h3>
        </div>

        <div className="mt-4 space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-text-primary">Email Notifications</p>
              <p className="text-xs text-text-muted">Receive budget alerts and weekly summaries via email.</p>
            </div>
            <button
              onClick={() => setEmailEnabled(!emailEnabled)}
              className={clsx(
                "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors",
                emailEnabled ? "bg-primary-500" : "bg-surface-border"
              )}
            >
              <span
                className={clsx(
                  "inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform",
                  emailEnabled ? "translate-x-5.5 mt-0.5 ml-0.5" : "translate-x-0.5 mt-0.5"
                )}
              />
            </button>
          </div>

          <div className="border-t border-surface-border pt-5">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="h-4 w-4 text-text-secondary" />
              <p className="text-sm font-medium text-text-primary">Slack Webhook URL</p>
            </div>
            <p className="mb-3 text-xs text-text-muted">
              Budget alerts will be posted to this Slack channel.
            </p>
            <div className="flex gap-3">
              <input
                value={slackWebhook}
                onChange={(e) => setSlackWebhook(e.target.value)}
                className="flex-1 rounded-lg border border-surface-border px-3 py-2 text-sm font-mono outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
              />
              <button className="rounded-lg bg-primary-500 px-4 py-2 text-sm font-medium text-white hover:bg-primary-600">
                Save
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
