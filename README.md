# Stock & POS — MJ Printing

A stock, printing and point-of-sale management platform built for a printing
business: product catalogue, inventory movements, point-of-sale, debts, delivery
notes and reporting.

This is an earlier generation of the stack that later moved to its own
MJ-specific repository, but it already contains production overlays, a
Telegram integration and CI workflows.

## Stack

| Area | Technology |
| --- | --- |
| API | FastAPI, Uvicorn, Pydantic v2, pydantic-settings |
| Data | PostgreSQL (asyncpg), SQLAlchemy 2, Alembic, Redis |
| Background jobs | Celery with the Redis broker |
| Auth | JWT (PyJWT), Argon2 password hashing |
| Reports | ReportLab, OpenPyXL |
| Frontend | Nuxt, Vue 3, Nuxt UI, Tailwind CSS, Pinia |
| Infrastructure | Docker Compose (dev + production overlay), nginx, Vercel |
| CI | GitHub Actions |
| Tests | pytest, Vitest |

## Repository layout

```text
backend/                   FastAPI application (modular monolith)
frontend/                  Nuxt application
infrastructure/            Compose files, env templates, nginx config
docs/                      Project documentation
docker-compose.yml         Development stack
docker-compose.prod.yml    Production overlay
.env.example               Shared env template
.env.production.example    Production-specific overrides
vercel.json                Frontend hosting configuration
opencode.json              Agent tooling configuration
AGENTS.md                  Agent/contributor guidance for this codebase
```

## Backend layout

```text
backend/
├── app/
│   ├── main.py
│   ├── core/          # config, security, database, redis, exceptions
│   ├── modules/       # auth, dashboard, categories, stock, suppliers,
│   │                  # pos, customers, reports, administration, image
│   ├── shared/        # audit, documents, telegram, pagination
│   └── api/v1/        # versioned route registration
├── alembic/
├── tests/
└── requirements.txt
```

## API surface

All business endpoints live under `/api/v1`.

| Family | Endpoints |
| --- | --- |
| Auth | `/api/v1/auth/*` — setup, login, refresh, me, logout, Telegram password reset |
| Dashboard | `/api/v1/dashboard/summary` |
| Master data | `categories`, `uoms`, `brands`, `products`, `suppliers`, `customers` |
| Stock | `/api/v1/stock/*` — in, adjust, damage, expire, movements, product history |
| POS | `/api/v1/pos/*` — search, barcode, sales, returns |
| Debts | `/customers/{id}/debts/*`, `/suppliers/{id}/debts/*` |
| Delivery notes | `/api/v1/delivery-notes/*` |

## Running it

```bash
cp .env.example .env
docker compose up -d --build

# production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
