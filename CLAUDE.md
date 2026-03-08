# CLAUDE.md — AgentLedger

## Project Overview

AgentLedger is an AI expense management platform for tracking LLM costs and managing virtual cards for AI agents. Monorepo with three packages: **backend** (FastAPI), **dashboard** (Next.js), and **sdk** (Python).

## Repository Structure

```
/
├── backend/          # FastAPI API server (Python 3.10+, SQLAlchemy, PostgreSQL)
├── dashboard/        # Next.js 14 frontend (React 18, TypeScript, Tailwind CSS 4)
├── sdk/python/       # Python SDK with CLI, MCP server, and provider wrappers
├── examples/         # Demo scripts
├── docker-compose.yml
├── .env.example
└── plan.md           # Product roadmap and technical requirements
```

---

## Development Workflows

### Prerequisites

- Python 3.10+, Node.js 20+, Docker & Docker Compose
- PostgreSQL 16 (or use Docker Compose)

### Starting Services

```bash
# Full stack via Docker
docker compose up --build

# Backend only (local dev)
cd backend && uv run uvicorn src.app.main:app --reload --port 8000

# Dashboard only (local dev)
cd dashboard && npm run dev

# SDK install (editable)
cd sdk/python && uv pip install -e ".[cli,mcp,dev]"
```

### Environment Variables

Copy `.env.example` to `.env`. Required vars:
- `SECRET_KEY` — minimum 32 characters
- `DATABASE_URL` — PostgreSQL async URL (e.g., `postgresql+asyncpg://...`)

Optional: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `CARD_ENCRYPTION_KEY`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`

### Running Tests

```bash
# Backend tests (uses in-memory SQLite, no PostgreSQL needed)
cd backend && uv run pytest -x -q

# Dashboard
cd dashboard && npm run lint

# SDK
cd sdk/python && uv run pytest
```

### Database Migrations

```bash
cd backend
uv run alembic upgrade head          # Apply all migrations
uv run alembic revision --autogenerate -m "description"  # Generate new migration
```

Migration files live in `backend/alembic/versions/`. Naming: `NNN_description.py` (sequential numbering).

---

## Backend Conventions (FastAPI + SQLAlchemy)

### File Organization

| File | Purpose |
|------|---------|
| `main.py` | App factory, lifespan, router registration |
| `config.py` | Pydantic Settings (env vars) |
| `database.py` | Async engine + session factory |
| `auth.py` | API key auth dependency |
| `models.py` | All SQLAlchemy ORM models |
| `schemas.py` | Pydantic request/response schemas |
| `schemas_cards.py` | Card-specific schemas |
| `routers/*.py` | Route handlers grouped by domain |
| `cost_engine.py` | Pricing lookup + cost calculation |
| `policy_engine.py` | Transaction approval logic |
| `stripe_service.py` | Stripe Issuing API wrapper |
| `queries.py` | Shared query helpers |
| `rollup.py` | Materialized cost aggregation |

### Router Pattern

Every router follows this structure:

```python
router = APIRouter()

@router.post("/resource", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    body: ResourceCreate,
    org: Organization = Depends(get_current_org),
    session: AsyncSession = Depends(get_session),
) -> ResourceResponse:
    ...
```

Rules:
- All route handlers are **async**
- Use `Depends(get_current_org)` for authentication on every protected endpoint
- Use `Depends(get_session)` for database access — session auto-commits on success, auto-rollbacks on error
- Return appropriate HTTP status codes: `201` for creation, `204` for deletion, `404` for not found
- Raise `HTTPException` for errors — never return error dicts
- Prefix all routes with `/v1/` (applied via `app.include_router(..., prefix="/v1")`)
- Internal helper functions prefixed with `_`

### Model Pattern

```python
class MyModel(Base):
    __tablename__ = "my_models"
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_my_model_name"),
        Index("ix_my_models_org_status", "org_id", "status"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

Rules:
- **UUID primary keys** stored as strings (`UUID(as_uuid=False)`)
- **All models have `org_id`** — multi-tenancy is enforced at the query level
- Use `server_default=func.now()` for timestamps, not Python-side defaults
- Use `Mapped[...]` with `mapped_column()` (SQLAlchemy 2.0 style)
- Money columns: `Numeric(14, 2)` or `Numeric(12, 6)` — never use floats
- Flexible metadata: `JSONB` columns (nullable)
- Enums: Python `enum.Enum` + SQLAlchemy `Enum` type
- Add indexes on frequently queried columns (especially `org_id` + timestamp combos)

### Schema Pattern

Three schemas per resource:

```python
class ResourceCreate(BaseModel):       # Input for POST — no id, no timestamps
    name: str
    ...

class ResourceUpdate(BaseModel):       # Input for PUT/PATCH — all fields optional
    name: str | None = None
    ...

class ResourceResponse(BaseModel):     # Output — includes id, timestamps
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    created_at: datetime
    ...
```

Rules:
- Use `model_config = ConfigDict(from_attributes=True)` on response schemas
- Use `str | None` union syntax (not `Optional[str]`)
- Separate schemas for cards live in `schemas_cards.py`

### Authentication

- Header-based: `X-API-Key` header
- Keys stored as SHA-256 hashes in the `api_keys` table
- `get_current_org()` dependency returns an `Organization` object
- Soft-delete for key revocation (`revoked_at` timestamp, not row deletion)

### Error Handling

```python
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
```

- Use `fastapi.status` constants, not raw integers
- Keep error messages concise and user-facing
- Never expose internal details in error responses

### Rate Limiting

- Default: 100 requests/minute per IP
- Auth endpoints: 20/minute
- Webhooks: 50/minute
- Configured via slowapi in `rate_limit.py`

---

## Dashboard Conventions (Next.js + TypeScript + Tailwind)

### File Organization

```
dashboard/src/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout (sidebar + main area)
│   ├── page.tsx           # Overview dashboard
│   ├── explorer/page.tsx  # Event explorer
│   ├── cards/             # Cards list + [id] detail
│   ├── policies/page.tsx
│   ├── programs/page.tsx
│   ├── approvals/page.tsx
│   ├── alerts/page.tsx
│   ├── reports/page.tsx
│   └── settings/page.tsx
├── components/            # Reusable UI components
│   ├── sidebar.tsx
│   ├── stat-card.tsx
│   ├── spend-chart.tsx
│   ├── data-table.tsx     # Generic sortable/paginated table
│   └── filter-bar.tsx
└── lib/
    ├── api.ts             # Typed API client (all backend endpoints)
    ├── format.ts          # Formatting utilities
    └── mock-data.ts       # Fallback mock data for development
```

### Component Rules

- All interactive components use `"use client"` directive
- State management: React hooks only (useState, useEffect, useMemo, useCallback) — no Redux/Zustand
- Data fetching: `useEffect` on mount, falls back to mock data on API failure
- Generic components use TypeScript generics (e.g., `DataTable<T>`)
- Props are fully typed — no `any` types

### Styling

- **Tailwind CSS v4.0** with PostCSS
- Custom design tokens defined in `globals.css` under `@theme { ... }`
- Color system: `primary-*`, `sidebar-*`, `surface-*`, `text-*`, semantic (`success`, `warning`, `danger`)
- Utility-first approach — no CSS modules or styled-components
- Use `clsx()` for conditional class names

### API Client (`lib/api.ts`)

- Base URL from `NEXT_PUBLIC_API_URL` env var (defaults to `http://localhost:8000/v1`)
- Auth token stored in `localStorage` as `al_token`
- All responses are fully typed with TypeScript interfaces
- Custom `ApiError` class for error handling
- Every backend endpoint has a corresponding typed function

### TypeScript

- Strict mode enabled
- Path alias: `@/*` maps to `./src/*`
- Use `interface` for API response shapes, `type` for unions/utility types
- No `any` — use `unknown` if type is truly unknown

### Page Pattern

```tsx
"use client";

export default function MyPage() {
  const [data, setData] = useState<MyType[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMyData()
      .then(setData)
      .catch(() => setData(mockData))
      .finally(() => setLoading(false));
  }, []);

  return ( ... );
}
```

---

## SDK Conventions (Python)

### Package Structure

```
sdk/python/src/agentledger/
├── __init__.py          # Public API: init(), instrument(), shutdown()
├── config.py            # AgentLedgerConfig dataclass + global singleton
├── events.py            # UsageEvent pydantic model + EventType enum
├── batcher.py           # Async event batching with bounded buffer
├── instrument.py        # Auto-patching for OpenAI/Anthropic
├── cards.py             # CardClient for programmatic card management
├── wrappers/
│   ├── openai_wrapper.py    # wrap_openai() — sync + async + streaming
│   └── anthropic_wrapper.py # wrap_anthropic() — sync + async + streaming
├── cli/
│   ├── main.py          # Typer CLI entry point
│   ├── auth.py          # Credential management (keyring + file fallback)
│   ├── cards.py         # Card CLI commands
│   ├── policies.py      # Policy CLI commands
│   └── output.py        # Rich table formatting
└── mcp/
    ├── server.py        # MCP server (10 tools)
    ├── client.py        # Async HTTP client with SSRF protection
    └── tools.py         # MCP tool implementations
```

### SDK Design Principles

- **Zero back-pressure**: Bounded deque, drops oldest events on overflow — never blocks the caller
- **Non-blocking**: Synchronous `enqueue()`, daemon thread handles HTTP
- **Graceful degradation**: Network errors are logged, never raised to the application
- **Idempotent patching**: `instrument()` uses guards to prevent double-patching
- **Env var overrides**: All config supports `AGENTLEDGER_*` environment variables

### Wrapper Rules

- Support both sync and async clients
- Support both streaming and non-streaming responses
- Parse provider-specific usage fields (cached tokens, reasoning tokens)
- Never break client behavior — wrap in try/except, log errors
- Use `_StreamInterceptor` / `_AsyncStreamInterceptor` pattern for streams

### CLI Rules

- Built with `typer` + `rich` for output
- Credential storage: OS keyring (preferred) > `~/.agentledger/config.json` (fallback, 0o600 perms)
- Use `rich.table.Table` for formatted output via helpers in `output.py`

---

## Cross-Cutting Conventions

### Code Style

**Python (backend + SDK):**
- Type hints on all function signatures
- `str | None` union syntax (not `Optional[str]`)
- f-strings for string formatting
- `from __future__ import annotations` not used — use native 3.10+ syntax
- Async/await throughout backend and SDK batcher
- No unused imports or variables

**TypeScript (dashboard):**
- Strict mode, no `any`
- Functional components only (no class components)
- Named exports for components, default export for pages
- `const` by default, `let` only when reassignment needed

### Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Python files | snake_case | `cost_engine.py` |
| Python classes | PascalCase | `BudgetAlert` |
| Python functions | snake_case | `get_current_org` |
| Python constants | UPPER_SNAKE | `DEFAULT_BATCH_SIZE` |
| DB tables | snake_case plural | `budget_alerts` |
| DB columns | snake_case | `org_id`, `created_at` |
| TS files | kebab-case | `stat-card.tsx` |
| TS components | PascalCase | `StatCard` |
| TS functions | camelCase | `formatCurrency` |
| API routes | kebab-case plural | `/v1/budget-alerts` |
| Env vars | UPPER_SNAKE | `DATABASE_URL` |

### Git & Branching

- Main branch: `main`
- Feature branches: `claude/<description>` or `feature/<description>`
- Commit messages: imperative mood, concise (e.g., "Add card freeze endpoint")
- Don't commit `.env` files, secrets, or `node_modules`

### Security Rules

- Never store card numbers, CVCs, or secrets in the database
- Sensitive card data: fetch from Stripe on-demand, encrypt with AES-256-GCM in transit
- API keys: store only SHA-256 hashes
- SSRF protection: validate URLs in MCP client, block private IP ranges
- CORS: configured via `CORS_ORIGINS` setting, not hardcoded
- Validate `SECRET_KEY` length (>= 32 chars) and `CARD_ENCRYPTION_KEY` format at startup
- Use `HTTPException` for auth failures — never leak internal state

### Multi-Tenancy

- Every database query MUST filter by `org_id`
- The `get_current_org` dependency provides the authenticated org
- Never allow cross-org data access — this is the most critical security invariant

### Adding a New Backend Resource

1. Add model to `models.py` with UUID PK, `org_id` FK, timestamps
2. Add schemas to `schemas.py` (Create, Update, Response)
3. Create router in `routers/` following the standard pattern
4. Register router in `main.py` with `/v1` prefix and tag
5. Create alembic migration: `alembic revision --autogenerate -m "add resource"`
6. Add tests in `tests/test_api_resource.py`

### Adding a New Dashboard Page

1. Create `dashboard/src/app/<route>/page.tsx` with `"use client"`
2. Add API functions to `lib/api.ts` with typed interfaces
3. Add navigation entry to `components/sidebar.tsx`
4. Add mock data to `lib/mock-data.ts` for development fallback
5. Use existing components (`DataTable`, `FilterBar`, `StatCard`) where possible

### Adding a New SDK Provider Wrapper

1. Create `wrappers/<provider>_wrapper.py` with `wrap_<provider>(client)` function
2. Handle sync + async clients, streaming + non-streaming
3. Add auto-detection in `instrument.py`
4. Re-export from `wrappers/__init__.py`
5. Add provider to optional dependencies in `pyproject.toml`
