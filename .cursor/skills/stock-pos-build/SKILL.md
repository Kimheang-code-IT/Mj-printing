---
name: stock-pos-build
description: >-
  Builds and refactors the MJ Printing Stock & POS system from
  docs/AGENT_STOCK_POS_FULL_IMPLEMENTATION.md. Use when implementing products,
  purchases, POS, stock, debts, statements, reports, removing Delivery Note /
  UOM / minimum stock / expired stock / credit limit, or syncing frontend,
  backend, PostgreSQL, Alembic, Redis, Docker, or tests.
disable-model-invocation: false
---

# Stock & POS Build Skill

Canonical spec: [docs/AGENT_STOCK_POS_FULL_IMPLEMENTATION.md](../../../docs/AGENT_STOCK_POS_FULL_IMPLEMENTATION.md)

Modify the existing system. Do **not** rebuild from scratch. Do not introduce microservices.

## Before any change

1. Read this skill + linked references below.
2. Inspect current code under `backend/app/`, `backend/alembic/`, `frontend/app/`, `frontend/i18n/`, `infrastructure/`, Compose files, `.env*.example`, `.github/workflows/`.
3. Prefer editing existing modules over duplicates.
4. Keep frontend, backend, DB, permissions, i18n, and tests synchronized.
5. Use reversible Alembic migrations; never destroy production data blindly.

## Architecture (preserve)

| Layer | Stack |
| --- | --- |
| API | FastAPI modular monolith, prefix `/api/v1` |
| DB | PostgreSQL + SQLAlchemy + Alembic |
| Cache | Redis (optional-safe; app must work if Redis is down) |
| UI | Nuxt 4 + Vue 3 + TS + Nuxt UI + Tailwind + Pinia |
| Validation | Zod (frontend) / existing backend stack |
| Tests | Pytest + Vitest |
| Envelopes | Success `{ data, meta }` / Error `{ detail: { code, message, field_errors? } }` |

Money: `Decimal` / `NUMERIC` only — never binary float.

## Allowed product areas

Dashboard · Products/Categories/Brands · Customers/Suppliers · Stock / Stock In / Adjustment / Damaged / Movements · POS / Sales / Returns / Invoice · Customer & Supplier Debt · Reports (sales, purchase, stock, profit, customer, supplier, statements) · Admin (users, roles, permissions, settings, audit logs)

## Must remove completely

| Feature | Remove from |
| --- | --- |
| Delivery Note | pages, menu, APIs, models, permissions, i18n, tests, docs |
| UOM management + `uom_id` | pages, menu, APIs, product FK (after safe migrate), conversions UI |
| Minimum stock | fields, alerts, reports, filters, i18n |
| Expired stock | page, reports, scheduler/Telegram expiry if only for this, settings |
| Customer credit limit | field, validation, UI, reports |

See [removed-features.md](removed-features.md).

## Field contracts (UI + API)

- **Product:** code/SKU, name, category, brand, sale price, image, description/note, status, timestamps. Purchase price, profit % and current stock are **purchase-driven** — never editable on the product document form; they update through purchases (Stock In dialog → `POST /purchases`). Barcode is not on the product document form either (POS barcode lookup stays). **No** UOM, min stock, expiry.
- **Customer / Supplier:** code, name, phone, address, current debt (read-only in CRUD), note, status, timestamps. **No** credit limit. Debt only via financial transactions.
- **Dimensional lines:** `square_meter = height × width × quantity`; `amount = square_meter × unit_price`. Persist snapshots on save.
- **Normal lines:** `amount = quantity × unit_price`.
- **Purchase totals:** `grand_total = subtotal + other_cost - discount`; `balance = grand_total - paid`.
- **Sale totals:** `grand_total = subtotal + other_charge - discount`; `balance = grand_total - paid`.

Naming in this repo:

| Concept | Frontend camelCase | API / DB snake_case |
| --- | --- | --- |
| Sale add-on | `otherCharge` | `other_charge` |
| Purchase add-on | `otherCost` | `other_cost` |
| Line m² | `squareMeter` | `square_meter` |

See [field-contracts.md](field-contracts.md).

## Route allowlist (this repo)

```text
/  /stock  /stock/new  /stock/[id]
/setup/categories  /setup/brands  /setup/customers  /setup/suppliers
/purchases/new
/pos
/reports/{sales,purchases,customers,suppliers,
          customer-debts,supplier-debts,finance}
/administration/{users,roles,settings,audit-logs,document-sequences}
/administration/{users,roles,settings,audit-logs,document-sequences}
```

**Do not add or restore:** `/delivery-notes*`, `/setup/uoms*`, `/uoms*`, expired-stock routes.

Stock In / Stock Out / Damaged Stock appear as read-only qty columns on `/stock` (no standalone pages; stock-adjustment / damage / movements APIs remain).

## Frontend status (done)

Treat the following as **already implemented** unless a regression appears:

- Allowlist pages for purchases, stock adjustments, damaged stock, sales, returns, debts redirects, and report shells.
- POS cart: height / width / m² / qty; checkout uses **`otherCharge`** (not delivery fee / `needsDelivery`).
- Product form: single General tab — no Pricing UOM / Expire tabs, and no Barcode / Purchase Price / Profit % / Current Stock inputs (purchase-driven fields).
- Stock In = purchase: `StockStockInDialog` (product document ·/stock/[id] more-menu, Stock list row menu, Stock In history dialog) posts `createPurchase` → purchase document + supplier ledger/debt + stock ↑ + `costPrice` update.
- Product document save() validates sale price only (no costPrice/profitPercent recompute).
- Stock columns: no UOM / expiry / Low Stock; includes stock value at cost.
- Customer/Supplier: code, address, note, read-only debt; no credit limit.
- Settings: no expiry-alert Stock tab.
- Menu + `stock-modules.ts` + `ROLE_DOCUMENT_TYPES` + i18n en/km aligned for current routes.
- Shared math: `frontend/app/utils/stock/line-calc.ts` (+ `tests/line-calc.spec.ts`).
- POS helpers: `frontend/app/utils/pos/cart.ts`, `checkout.ts`; print invoice uses `otherCharge`.
- Mock `createPurchase` writes stockIns + movements + stock + supplier debt.
- Deleted delivery pages/repos/print helpers and Pricing UOM UI.

Key wiring files — see [frontend-map.md](frontend-map.md).

## Backend status (still open)

Prefer Phase 4 removal **after** safe migrate/backfill:

1. Unregister Delivery Note / UOM / expiry-only routers and seeds.
2. Alembic: drop product `uom_id`, min stock, expiry fields, customer `credit_limit` after data safety.
3. Purchase/sale/returns APIs must accept dimensional line snapshots + `other_cost` / `other_charge`.
4. Report/statement endpoints + PDF/Excel for full filtered sets.
5. Drop expiry scheduler / Telegram expiry if only used for removed features; keep Redis optional-safe.

## Implementation order

1. Audit current map
2. DB foundation (ledgers, dimensional fields, movements)
3. Backend core (stock mutation, purchase/sale/returns, debts, reports, exports)
4. Remove legacy features (after safe migrate/backfill)
5. Frontend forms/menu/i18n/RBAC — **largely complete; only polish/regressions**
6. Infra (drop expiry scheduler if unused)
7. Tests + dead-code scan (`delivery`, `uom`, `min_stock`, `expiry`, `credit_limit`)

## Frontend rules

- No direct API calls from random pages — use repositories/composables.
- Pages / repos / types / permissions / i18n stay in sync.
- Line math: import from `~/utils/stock/line-calc` — do **not** reintroduce UOM pricing rows.
- Sale extras field is `otherCharge` / `other_charge` only — never `deliveryFee` / `needsDelivery`.
- Purchase extras field is `otherCost` / `other_cost`.
- Reuse report UI pieces; disable double-submit; confirm destructive actions.
- Statement/profit report pages were removed; keep ModuleWorkspaceView patterns for the remaining report routes.

## Backend rules

- One DB transaction per purchase/sale/return/payment/adjustment.
- Central stock mutation + immutable stock movements.
- Customer/supplier ledgers own debt history; summary fields are derived.
- Never allow silent negative stock.

## Remaining cleanup

1. ~~Purge leftover mock seed collections `uoms` / `deliveryNotes`~~ **done**
2. ~~Replace/delete `uom-conversions.ts`~~ **done** (decimal helpers live in `line-calc.ts`)
3. ~~Trim unused i18n keys for delivery / UOM / expiry~~ **largely done** — re-scan if new keys appear
4. ~~Deepen statement / profit report pages~~ — pages removed; statements stay on the customer/supplier debt report routes
5. Backend Phase 4 removal + Alembic (delivery/uom/expiry/credit_limit/min_stock)

Reusable purge prompt: [dead-code-cleanup-prompt.md](dead-code-cleanup-prompt.md)

## Verification

Frontend: `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm build` (from `frontend/`)  
Backend: pytest for products, purchase, sale, returns, stock, statements, exports, RBAC, migrations  
Compose: healthy postgres/redis/api/frontend; no UOM/Delivery routes; no expiry scheduler errors

Dead-code scan keywords: `delivery`, `deliveryNote`, `uom`, `uom_id`, `min_stock`, `minimumStock`, `expiry`, `expired`, `credit_limit`, `creditLimit`, `needsDelivery`, `deliveryFee`.

## References

- Full spec: [docs/AGENT_STOCK_POS_FULL_IMPLEMENTATION.md](../../../docs/AGENT_STOCK_POS_FULL_IMPLEMENTATION.md)
- [removed-features.md](removed-features.md)
- [field-contracts.md](field-contracts.md)
- [frontend-map.md](frontend-map.md)
- [acceptance.md](acceptance.md)
