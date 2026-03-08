# Technical Requirements Document: Agent Expense Management

## Context & Thesis

Agents are beginning to transact autonomously. Three protocol layers have emerged:
- **A2A** (Google) — Agent-to-agent messaging and capability discovery
- **AP2** — Payment extension of A2A; defines trust delegation via cryptographic mandates
- **A2A x402** — Crypto settlement layer within AP2; uses HTTP 402 + stablecoins for instant on-chain payments (built by Google + Coinbase)

Alongside these: **ACP** (Stripe/OpenAI) for traditional-rail commerce, **Visa TAP**, **Mastercard Agent Pay**, and startups like Skyfire, Payman, and Nevermined building payment rails. The agentic economy is projected at $3-5T by 2030.

**The gap:** Everyone is building payment *rails* and *protocols*. Nobody is building the enterprise *management layer* — the equivalent of what Ramp does for corporate cards. Ramp doesn't own Visa/Mastercard rails; it sits above them providing virtual cards with spend limits, merchant restrictions, real-time visibility, and policy enforcement.

**We build the Ramp layer for agents:** protocol-agnostic expense management that sits above x402, ACP, AP2, and whatever comes next.

### Why Not Just Start With Agent Payments?

Shreyan's caution: great ideas come too early. Agent autonomy timelines are uncertain. We de-risk with a wedge that has **real demand today** — AI API cost management — while building toward agent expense management.

---

## Competitive Landscape

### Existing LLM Cost Visibility Tools

| Tool | Approach | Cost Features | Gaps |
|------|----------|--------------|------|
| **Helicone** | Proxy-based; routes API calls through their servers | Logs tokens/costs, caching, rate limiting | Shallow attribution; no financial-grade reporting; proxy adds latency/dependency |
| **LangSmith** | LangChain-native tracing | Per-query costs and latency | Ecosystem lock-in (LangChain only); cost is secondary to eval/tracing |
| **Braintrust** | Eval + observability platform | Per-request cost breakdowns, tag-based attribution, budget alerts | Primarily an eval tool; cost is a feature, not the product |
| **LiteLLM** | Open-source proxy + unified API | Spend tracking per virtual key/team | DIY; no dashboard, no financial reporting, no alerting out of the box |
| **TrueFoundry** | AI Gateway with MLOps | Budget thresholds per team/project, smart routing, semantic caching | Heavy MLOps platform; cost management is a small feature |
| **Kong AI Gateway** | Enterprise API gateway + AI plugins | LLM traffic governance | For orgs already on Kong; not purpose-built for AI cost management |

### What Has NOT Been Built

1. **Cross-provider unified cost view** — Every tool locks you into their proxy or SDK. No single pane of glass across OpenAI, Anthropic, Bedrock, Vertex, and self-hosted models.
2. **Financial-grade reporting** — Chargeback allocation by department/product. Cost center mapping. Export to ERP/accounting systems. Monthly finance reports. None of the observability tools do this.
3. **Spend-to-outcome attribution** — "We spent $12K on Claude this month, but what business value did each dollar produce?" Connecting token spend to product metrics (e.g., "cost per PA processed").
4. **Predictive budgeting** — Forecasting next month's AI spend based on usage trends, model mix, and pricing changes. Alerting *before* budgets blow, not after.
5. **Optimization engine** — "You could save 30% by using cached prompts here" or "This workflow should use Haiku instead of Sonnet." Actionable, not just observability.
6. **Path to agent transactions** — None of these tools have any concept of agents spending money on services beyond API calls. No wallet management, no policy enforcement, no multi-protocol support.

**Key stat:** 80% of companies exceed AI cost forecasts by 25%+. Only 34% have mature cost management capabilities. 90% of CIOs say managing costs limits their ability to get value from AI.

### Agentic Payment Startups

| Startup | What They Do | Funding | Our Differentiation |
|---------|-------------|---------|-------------------|
| **Skyfire** | Agent wallets with spend limits, KYAPay protocol, dashboard | $9.5M | They're building payment *rails*. We're building the expense management *layer* — policies, reporting, optimization, chargeback |
| **Nevermined** | "PayPal for AI agents"; metering, A2A/MCP/x402 support, sub-cent transactions | Undisclosed | They focus on metering and settlement. We focus on enterprise controls and financial visibility |
| **Payman** | Agent-to-human payments (ACH, USDC, wires) | Early | Narrow use case (paying contractors). We're broader |

**Positioning:** We are complementary to these startups, not competitive. They build rails; we build the finance layer on top. In Phase 2, we integrate with Skyfire/Nevermined as protocol adapters.

---

## Protocol Architecture

### The Stack (Confirmed)

```
+---------------------------------------------------+
|              Our Product (AgentLedger)             |
|   Expense management, policies, visibility         |
+---------------------------------------------------+
|         Protocol Adapters (Phase 2)                |
+----------+----------+----------+------------------+
|   x402   |   ACP    |   AP2    |   Future         |
| (Coinbase|  (Stripe/ | (Google) |   protocols      |
|  + CF)   |  OpenAI) |          |                  |
+----------+----------+----------+------------------+
|              Settlement Rails                      |
|   Stablecoins (USDC)  |  Fiat (Stripe, ACH)       |
+---------------------------------------------------+
```

### Protocol Summary

| Protocol | Backed By | Rails | Trust Model | Status |
|----------|-----------|-------|-------------|--------|
| **x402** | Coinbase, Cloudflare | Stablecoins on Base/Solana | On-chain verification | 35M+ txns, $10M+ volume |
| **ACP** | Stripe, OpenAI | Traditional (cards, bank) | Shared Payment Tokens | Live in ChatGPT (Etsy, Shopify) |
| **AP2** | Google + 60 partners | Both crypto and fiat | Cryptographic mandates (Intent + Cart) | V0.1, phased rollout |
| **A2A x402** | Google + Coinbase | Stablecoins | AP2 mandates + x402 settlement | Extension of AP2 |

### Our Protocol Stance

**x402-first, protocol-agnostic architecture.** x402 has the most traction (35M+ txns), simplest integration (HTTP-native), and is embedded within AP2 as the settlement layer. But we design with a **hot-swappable adapter pattern** so adding ACP or new protocols is a configuration change, not a rewrite.

---

## Product Vision (Phased)

### Phase 1 — AI Spend Visibility (MVP: 4 weeks)
*"Where is our AI budget going?"*

- SDK wraps LLM clients to capture token costs (no proxy dependency)
- Cross-provider unified dashboard: spend by team/project/model/env
- Budget alerts before costs blow up
- Financial-grade exports (CSV, API) for finance teams
- **Differentiator vs. Helicone/LangSmith:** Purpose-built for cost management, not observability. Cross-provider. Financial reporting. No proxy lock-in.

### Phase 2 — Agent Wallet Management (Month 2-3)
*"Give each agent a budget and rules."*

- Virtual wallets for agents with spend limits, merchant/category restrictions, expiration
- x402 adapter: intercept agent transactions, enforce policies pre-settlement
- Real-time transaction feed across protocols
- Spend-to-outcome attribution (connect agent spend to business metrics)
- **Trigger:** When design partners deploy agents that transact autonomously OR when we see strong protocol adoption signals

### Phase 3 — Full Agent Expense Management (Month 4-6)
*"Ramp for agents."*

- Approval workflows (spend above threshold -> human approval via Slack/email)
- Anomaly detection: flag unusual spend patterns
- Multi-protocol routing: optimize for cost/speed across rails
- Reconciliation: match transactions to business outcomes
- Audit trail leveraging AP2 mandates + x402 on-chain proofs
- Predictive budgeting and optimization recommendations

---

## MVP Technical Specification (Phase 1)

### Target User
- **Primary:** Engineering leads / platform teams at companies spending $5K+/month on AI APIs
- **Secondary:** Finance teams needing to allocate AI costs across departments

### Core User Stories
1. **As an eng lead**, I see total AI spend broken down by provider, model, team, and project in one place
2. **As an eng lead**, I set budget alerts so I know *before* costs exceed thresholds
3. **As a platform engineer**, I integrate in <10 minutes — no proxy, no infra changes
4. **As a finance lead**, I get monthly cost reports with department-level allocation for chargeback

### Architecture

```
SDK (Python)             Ingest API            Cost Engine            Dashboard
+--------------+      +-------------+      +--------------+      +-------------+
| Wrap LLM     |----->| POST /events|----->| Normalize,   |----->| Spend views |
| clients,     |      | (batched,   |      | price,       |      | Alerts      |
| emit usage   |      |  async)     |      | aggregate,   |      | Reports     |
| events       |      +-------------+      | forecast     |      | Export      |
+--------------+                           +--------------+      +-------------+
       |
       | Phase 2+: Also captures agent
       | transactions via protocol adapters
```

### Components

#### 1. Python SDK
**Integration:** Drop-in wrapper / monkey-patch. No proxy required (key differentiator vs. Helicone).

```python
import agentledger

agentledger.init(api_key="ak_...", project="pa-processor", team="underwriting")

# Auto-instrument all supported clients
agentledger.instrument()

# Or explicit wrapper
from agentledger.wrappers import wrap_openai
client = wrap_openai(OpenAI())
```

**Captures per request:**
- Provider, model, timestamp
- Input/output/cached/reasoning tokens
- Latency
- Tags: team, project, environment, custom labels

**Design constraints:**
- Async, non-blocking — zero degradation to host app
- Batch locally, flush every 5s or 100 events. On buffer full, drop oldest events (never backpressure the host app)
- Graceful degradation — LLM calls always work even if our backend is down
- <5 lines to integrate
- **Streaming support** — aggregate tokens from streamed responses across providers (OpenAI chunks, Anthropic events). Most production LLM calls use streaming; this is not optional.
- **Cached token detection** — correctly identify cached vs. non-cached tokens per provider (OpenAI `cached_tokens`, Anthropic prompt caching). Cost accuracy depends on this.
- **Extensible event schema** — the same pipeline will accept agent transaction events in Phase 2

#### 2. Ingest API
- `POST /v1/events` — batched usage events
- API key auth per organization
- Validates, deduplicates (idempotency key), writes to event store
- **Tech:** FastAPI

#### 3. Cost Engine
- Maps `(provider, model, token_type, timestamp)` -> unit cost
- Pricing table tracking provider pricing changes over time
- Handles: cached token discounts, batch API pricing, reasoning tokens
- Materializes rollups by org/team/project/model at hourly/daily granularity
- **Phase 2 extension:** Same engine prices agent transactions (x402 gas fees, ACP processing fees)
- **Tech:** PostgreSQL

#### 4. Dashboard
- **Overview:** MTD spend, 30-day trend, top breakdowns by model/team/project
- **Explorer:** Filterable drill-down (date range, provider, model, team, project, env)
- **Alerts:** Budget thresholds per team/project (email + Slack webhook). Predictive: "At current rate, team X will exceed budget by March 15"
- **Reports:** Monthly cost report with department allocation. CSV/PDF export.
- **Settings:** API keys, team management, notification preferences
- **Tech:** Next.js, Tailwind, Recharts

### Data Privacy Stance (MVP)

**Metadata only — no prompt content.** The SDK captures token counts, model, latency, and tags. It never sends prompt text or completions to our backend. This is a hard architectural constraint that avoids enterprise privacy/compliance blockers and simplifies our data handling. If spend-to-outcome attribution (Phase 2) needs prompt-level data, it stays client-side.

### Invoice Reconciliation (MVP)

Simple "sanity check" view: users manually input their monthly provider invoice total, and we show our tracked total alongside it with the delta. This builds trust in the 2% accuracy claim before we automate provider billing API integrations.

### Data Model

```sql
organizations (id, name, created_at)
api_keys (id, org_id, key_hash, label, created_at, revoked_at)

-- Unified event table (supports both token usage AND agent transactions)
events (
  id, org_id, idempotency_key,
  event_type,        -- 'llm_usage' | 'agent_transaction' (Phase 2)
  provider,          -- openai | anthropic | x402 | acp (Phase 2)
  model,             -- gpt-4o | claude-sonnet-4-20250514 | null for transactions
  timestamp,
  -- Token fields (Phase 1)
  input_tokens, output_tokens, cached_tokens, reasoning_tokens,
  latency_ms,
  -- Transaction fields (Phase 2, nullable for now)
  amount_usd, merchant, transaction_hash,
  -- Common
  environment,       -- dev | staging | prod
  team, project, agent_id,
  custom_tags jsonb,
  estimated_cost_usd
)

cost_rollups (
  org_id, period, period_start,
  event_type, provider, model, team, project, environment,
  total_cost_usd, request_count
)

budget_alerts (
  id, org_id,
  scope, scope_value,
  period, threshold_usd,
  notify_channels jsonb,
  predictive boolean default false  -- alert before breach, not after
)

pricing_table (
  provider, model, token_type,
  effective_from, effective_to,
  cost_per_million_tokens
)
```

### Tech Stack

| Decision | Choice | Rationale |
|---|---|---|
| SDK | Python | Matches AI ecosystem |
| Backend | FastAPI | Fast to ship; same language as SDK |
| Database | PostgreSQL | Rich aggregation; MVP scale sufficient |
| Frontend | Next.js + Tailwind | Fast to build |
| Auth | API keys (SDK), magic links (dashboard) | Minimal friction |
| Hosting | Fly.io or AWS | Simple ops |
| Pricing data | Manual table | <10 models; automation not worth it yet. Update within 24hrs of provider price changes — assign owner. |

---

## Go-To-Market Strategy

### Design Partners (Month 1-2)
- Target: 3-5 companies spending $5K+/month on AI APIs
- **Where to find them:**
  - Teams already using Helicone/LangSmith who complain about cost visibility gaps
  - AI-native startups with growing token bills (your network + Shreyan's)
  - Companies with multiple LLM providers (cross-provider pain is sharpest)
- **Offer:** Free access in exchange for weekly feedback calls
- **Goal:** Validate that cost visibility alone is compelling enough to onboard

### Positioning
- **Against observability tools (Helicone, LangSmith):** "They show you traces. We show you where your money goes." Complementary, not competitive. We don't do evals or tracing — we do cost management.
- **Against cloud cost tools (Datadog, CloudHealth):** "They don't understand tokens." Generic cloud cost tools can't parse token-level pricing, cached vs. non-cached, reasoning tokens, etc.
- **Against agent payment startups (Skyfire, Nevermined):** "They build rails. We build the finance layer." We integrate with them, not against them.

### Pricing (Post Design Partner)
- **Free tier:** Up to $1K/month tracked AI spend (hooks small teams, creates pipeline)
- **Pro:** Percentage of tracked spend (e.g., 1-2%) or flat $99-299/month per team. Need design partner feedback.
- **Enterprise:** Custom pricing with SSO, RBAC, SLA, chargeback features

### Expansion Motion
- Land with engineering team (SDK integration, dashboard)
- Expand to finance (monthly reports, department allocation, chargeback)
- Upsell to agent expense management as agents start transacting (Phase 2-3)

---

## Forward Architecture: Protocol-Agnostic Adapter Pattern

Designed for hot-swappability:

```
Agent --> AgentLedger SDK --> Policy Engine --> Adapter Registry
                                                    |
                                    +---------------+---------------+
                                    v               v               v
                              x402 Adapter    ACP Adapter     AP2 Adapter
                              (stablecoin)    (Stripe rail)   (mandate +
                                                               settlement)
```

**Adapter interface (Phase 2):**
```python
class ProtocolAdapter(ABC):
    async def authorize(self, wallet_id, amount, merchant, metadata) -> AuthResult
    async def execute(self, authorization) -> TransactionResult
    async def verify(self, transaction_id) -> VerificationResult
    def normalize_event(self, raw_event) -> AgentLedgerEvent
```

Each adapter:
1. **Authorizes** against our policy engine (budget check, merchant restriction, approval workflow)
2. **Executes** via the native protocol
3. **Normalizes** the transaction into our unified event schema
4. **Verifies** settlement (on-chain for x402, payment confirmation for ACP)

Adding a new protocol = implementing 4 methods. No core system changes.

---

## Build Plan (Compressed Timelines)

### Week 1-2: Core Pipeline
- [ ] Python SDK: OpenAI + Anthropic wrappers, async batching, graceful degradation
- [ ] Ingest API: FastAPI, validation, dedup, PostgreSQL storage
- [ ] Cost engine: pricing table, cost computation at ingest
- [ ] Seed pricing data for OpenAI + Anthropic models

### Week 3-4: Dashboard + Alerts + Ship
- [ ] Auth: magic link login
- [ ] Dashboard: overview, explorer, budget alerts (email + Slack)
- [ ] Financial export (CSV)
- [ ] SDK: PyPI publish, README, integration guide
- [ ] Design partner onboarding (aim for 3 partners by end of week 4)

### Month 2-3: Agent Wallets (Phase 2)
- [ ] Adapter interface + x402 adapter implementation
- [ ] Agent wallet model (virtual spending accounts)
- [ ] Policy engine (spend limits, merchant restrictions)
- [ ] Agent transaction dashboard view
- [ ] TS SDK

### Month 4-6: Full Expense Management (Phase 3)
- [ ] Approval workflows
- [ ] Anomaly detection
- [ ] Multi-protocol routing
- [ ] Reconciliation + audit trail
- [ ] Predictive budgeting

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Integration time | `pip install` to dashboard data in <10 minutes |
| SDK overhead | <5ms p99 added latency |
| Cost accuracy | Within 2% of actual provider invoices |
| Design partners | 3-5 companies by end of month 1 |
| Phase 2 signal | At least 1 design partner with agents transacting autonomously |

---

## Open Questions

1. **Naming:** "AgentLedger" is the working name — needs validation. Other candidates?
2. **Pricing model:** Need design partner input. Usage-based (% of tracked spend) vs. flat fee?
3. **x402 integration depth:** Do we run our own x402 facilitator node, or integrate at the SDK level intercepting agent HTTP calls?
4. **Skyfire/Nevermined partnership:** Approach as integration partners from day one, or build independently first?
5. **Shreyan as advisor:** Strong fit given BillPay scaling experience at Ramp + agentic pay deal flow visibility at Elad Gil's fund

---

## Sources
- [x402 Protocol](https://www.x402.org/)
- [Cloudflare x402 Launch](https://blog.cloudflare.com/x402/)
- [Stripe ACP](https://stripe.com/blog/developing-an-open-standard-for-agentic-commerce)
- [Google AP2 Announcement](https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol)
- [A2A x402 Extension (GitHub)](https://github.com/google-agentic-commerce/a2a-x402)
- [Google + Coinbase x402](https://www.coinbase.com/developer-platform/discover/launches/google_x402)
- [Agentic Payments: ACP, AP2, x402 Comparison](https://orium.com/blog/agentic-payments-acp-ap2-x402)
- [F-Prime Agentic Payments Deep Dive](https://fintechprimetime.substack.com/p/agentic-payments-deep-dive)
- [Trends.vc Agentic Payments](https://trends.vc/agentic-payments-payments-market-split-know-your-agent-micro-agency-model/)
- [CIO: Agentic Payments Are Coming](https://www.cio.com/article/4137893/agentic-payments-are-coming-is-your-company-ready.html)
- [Helicone vs Competitors](https://www.helicone.ai/blog/the-complete-guide-to-LLM-observability-platforms)
- [Braintrust LLM Monitoring 2026](https://www.braintrust.dev/articles/best-llm-monitoring-tools-2026)
- [LiteLLM](https://www.litellm.ai/)
- [TrueFoundry LLM Cost Tracking](https://www.truefoundry.com/blog/llm-cost-tracking-solution)
- [Top AI Gateways 2026](https://www.getmaxim.ai/articles/top-5-ai-gateways-to-reduce-llm-cost-in-2026/)
- [Ramp Virtual Cards](https://ramp.com/virtual-cards)
- [Ramp Enterprise Expense Management](https://ramp.com/enterprise/expense-management-software)
- [Skyfire (TechCrunch)](https://techcrunch.com/2024/08/21/skyfire-lets-ai-agents-spend-your-money/)
- [Nevermined + x402/A2A/AP2](https://nevermined.ai/blog/building-agentic-payments-with-nevermined-x402-a2a-and-ap2)
- [Sifted: Infrastructure Changing Agentic Payments](https://sifted.eu/articles/infrastructure-agentic-payments-brnd)
- [AI Cloud Cost Statistics 2026](https://www.appverticals.com/blog/ai-cloud-cost-statistics-trends-insights-optimization/)
