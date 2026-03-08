"use client";

import { useState, useMemo } from "react";
import FilterBar, { FilterOption } from "@/components/filter-bar";
import DataTable, { Column } from "@/components/data-table";
import { explorerEvents, ExplorerEvent } from "@/lib/mock-data";
import { formatCurrency, formatDateTime, formatTokens } from "@/lib/format";

const providers = ["OpenAI", "Anthropic", "Google"];
const models = [
  "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo",
  "claude-3.5-sonnet", "claude-3-haiku", "claude-3-opus",
  "gemini-1.5-pro", "gemini-1.5-flash",
];
const teams = ["AI Platform", "Search & Discovery", "Customer Support", "Content Generation", "Data Science", "DevOps"];
const projects = ["chatbot-v2", "search-reranker", "content-pipeline", "rag-system", "analytics-copilot", "code-review-bot"];
const environments = ["production", "staging", "development"];

const columns: Column<ExplorerEvent & Record<string, unknown>>[] = [
  {
    key: "timestamp",
    label: "Timestamp",
    sortable: true,
    render: (row) => (
      <span className="whitespace-nowrap text-xs">{formatDateTime(row.timestamp)}</span>
    ),
  },
  { key: "provider", label: "Provider", sortable: true },
  {
    key: "model",
    label: "Model",
    sortable: true,
    render: (row) => (
      <span className="rounded bg-surface-secondary px-2 py-0.5 font-mono text-xs">
        {row.model}
      </span>
    ),
  },
  { key: "team", label: "Team", sortable: true },
  { key: "project", label: "Project", sortable: true },
  {
    key: "inputTokens",
    label: "Tokens (in/out)",
    sortable: true,
    render: (row) => (
      <span className="text-xs">
        {formatTokens(row.inputTokens)} / {formatTokens(row.outputTokens)}
      </span>
    ),
  },
  {
    key: "cost",
    label: "Cost",
    sortable: true,
    className: "text-right",
    render: (row) => (
      <span className="font-medium">{formatCurrency(row.cost)}</span>
    ),
  },
];

export default function ExplorerPage() {
  const [providerFilter, setProviderFilter] = useState("");
  const [modelFilter, setModelFilter] = useState("");
  const [teamFilter, setTeamFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [envFilter, setEnvFilter] = useState("");

  const filters: FilterOption[] = [
    {
      key: "provider",
      label: "All Providers",
      options: providers.map((p) => ({ value: p, label: p })),
      value: providerFilter,
      onChange: setProviderFilter,
    },
    {
      key: "model",
      label: "All Models",
      options: models.map((m) => ({ value: m, label: m })),
      value: modelFilter,
      onChange: setModelFilter,
    },
    {
      key: "team",
      label: "All Teams",
      options: teams.map((t) => ({ value: t, label: t })),
      value: teamFilter,
      onChange: setTeamFilter,
    },
    {
      key: "project",
      label: "All Projects",
      options: projects.map((p) => ({ value: p, label: p })),
      value: projectFilter,
      onChange: setProjectFilter,
    },
    {
      key: "environment",
      label: "All Environments",
      options: environments.map((e) => ({ value: e, label: e })),
      value: envFilter,
      onChange: setEnvFilter,
    },
  ];

  const filtered = useMemo(() => {
    return explorerEvents.filter((e) => {
      if (providerFilter && e.provider !== providerFilter) return false;
      if (modelFilter && e.model !== modelFilter) return false;
      if (teamFilter && e.team !== teamFilter) return false;
      if (projectFilter && e.project !== projectFilter) return false;
      if (envFilter && e.environment !== envFilter) return false;
      return true;
    });
  }, [providerFilter, modelFilter, teamFilter, projectFilter, envFilter]);

  function handleReset() {
    setProviderFilter("");
    setModelFilter("");
    setTeamFilter("");
    setProjectFilter("");
    setEnvFilter("");
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Explorer</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Browse and filter individual AI usage events.
        </p>
      </div>

      <FilterBar filters={filters} onReset={handleReset} />

      <div className="text-sm text-text-muted">
        {filtered.length} events found
      </div>

      <DataTable
        columns={columns}
        data={filtered as (ExplorerEvent & Record<string, unknown>)[]}
        pageSize={15}
        keyExtractor={(row) => row.id}
      />
    </div>
  );
}
