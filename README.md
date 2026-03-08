# AgentLedger — AI Expense Management

Protocol-agnostic expense management for AI APIs and autonomous agents. The "Ramp for agents" — sitting above payment rails (x402, ACP, AP2) to provide spend visibility, budget controls, and financial reporting.

## Architecture

```
SDK (Python)             Ingest API            Cost Engine            Dashboard
+--------------+      +-------------+      +--------------+      +-------------+
| Wrap LLM     |----->| POST /events|----->| Normalize,   |----->| Spend views |
| clients,     |      | (batched,   |      | price,       |      | Alerts      |
| emit usage   |      |  async)     |      | aggregate,   |      | Reports     |
| events       |      +-------------+      | forecast     |      | Export      |
+--------------+                           +--------------+      +-------------+
```

## Components

| Component | Tech | Location |
|-----------|------|----------|
| Python SDK | Python, httpx, pydantic | `sdk/python/` |
| Backend API | FastAPI, SQLAlchemy, PostgreSQL | `backend/` |
| Dashboard | Next.js 14, Tailwind CSS, Recharts | `dashboard/` |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### Run with Docker Compose

```bash
docker compose up
```

- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Local Development

#### Backend
```bash
cd backend
pip install -e ".[dev]"
# Set up PostgreSQL and update DATABASE_URL
uvicorn src.app.main:app --reload
```

#### Dashboard
```bash
cd dashboard
npm install
npm run dev
```

#### SDK
```bash
cd sdk/python
pip install -e .
```

### SDK Usage

```python
import agentledger

agentledger.init(api_key="ak_...", project="pa-processor", team="underwriting")
agentledger.instrument()

# Or wrap explicitly
from agentledger.wrappers import wrap_openai
from openai import OpenAI

client = wrap_openai(OpenAI())
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)
# Usage automatically tracked!
```

## Phase 1 — AI Spend Visibility (MVP)

- Cross-provider unified dashboard (OpenAI, Anthropic)
- Spend breakdown by team, project, model, environment
- Budget alerts with predictive warnings
- Financial-grade CSV exports
- Invoice reconciliation

## Phase 2 — Agent Wallet Management

- Virtual wallets for agents with spend limits
- x402 protocol adapter for on-chain transactions
- Policy engine for merchant restrictions
- Spend-to-outcome attribution

## Phase 3 — Full Agent Expense Management

- Approval workflows
- Anomaly detection
- Multi-protocol routing (x402, ACP, AP2)
- Reconciliation and audit trail
- Predictive budgeting

## API Endpoints

### Events
- `POST /v1/events` — Ingest batched usage events

### Dashboard
- `GET /v1/dashboard/overview` — MTD spend and top breakdowns
- `GET /v1/dashboard/explore` — Filterable drill-down
- `GET /v1/dashboard/spend-over-time` — Time series data

### Alerts
- `POST /v1/alerts` — Create budget alert
- `GET /v1/alerts` — List alerts
- `PUT /v1/alerts/{id}` — Update alert
- `DELETE /v1/alerts/{id}` — Delete alert

### Reports
- `GET /v1/reports/monthly` — Monthly cost report
- `GET /v1/reports/export` — CSV export
- `GET /v1/reports/invoice-reconciliation` — Compare tracked vs actual

### Auth
- `POST /v1/auth/keys` — Create API key
- `GET /v1/auth/keys` — List API keys
- `DELETE /v1/auth/keys/{id}` — Revoke API key

## License

Proprietary — All rights reserved.
