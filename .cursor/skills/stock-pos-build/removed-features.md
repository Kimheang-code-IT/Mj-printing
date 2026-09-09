# Features that must not exist in the runtime system

When building or cleaning this project, delete or migrate away every surface of these features. Prefer safe Alembic migrations before dropping tables.

## Delivery Note

Remove: pages (`/delivery-notes*`), sidebar, components only used by delivery, repositories, API clients, types, stores, i18n, backend routes/services/schemas/models, permissions/seeds, sequence seeds, audit actions, tests, docs, dead imports.

POS must not navigate to create a delivery note after checkout. Sale extras use **Other Charge** only — never delivery fee / `needsDelivery`.

Frontend pages/print helpers for delivery notes are already removed. Still purge mock seed `deliveryNotes` in `frontend/app/mocks/` and any leftover i18n/backend routers.

Before dropping DB tables, confirm nothing else references them.

## UOM management

Remove: UOM pages (`/setup/uoms*`, legacy `/uoms*`), menu, CRUD APIs, types, translations, permissions, seeds, tests.

Remove product `uom_id` / UOM conversion pricing UI **after** migrating product data safely. Do not orphan products.

Dimensional sales use height/width/qty/m² — not Convert UOM tables. Use `line-calc.ts`, not UOM pricing rows.

Frontend UOM pages/UI are already removed. Still purge:

- mock seed `uoms` / `uomById`
- `frontend/app/utils/stock/uom-conversions.ts` UOM-specific helpers (keep only generic decimal math under a neutral name if still needed)
- comments/endpoints mentioning `/api/v1/uoms/options`

## Minimum stock

Remove: product minimum-stock field, validation, dashboard alerts, report logic, translations, API/filter fields, tests. Do not leave stale columns or labels.

Frontend stock list / product form already omit min stock. Finish backend column + any leftover i18n.

## Expired stock

Remove: Expired Stock page/report, expiry-specific filters, expiry scheduler/task if only for this feature, dedicated Telegram expiry alerts, related permissions/translations/tests.

Frontend settings expiry-alert Stock tab and product Expire tab are already removed. Finish backend scheduler/env/Compose cleanup when expiry is fully gone.

If `SCHEDULER_ENABLED` exists only for expiry, remove it from settings, Compose, and env examples. Keep unrelated background infra.

## Customer credit limit

Remove: `credit_limit` field, validation/blocks/warnings, UI, reports, translations/tests.

Customer **debt** remains required. Frontend customer forms already omit credit limit; finish backend schema/migrate.

## Dead-code scan keywords

`delivery`, `deliveryNote`, `deliveryFee`, `needsDelivery`, `uom`, `uom_id`, `Convert UOM`, `min_stock`, `minimumStock`, `Low Stock`, `expiry`, `expired`, `expiryLoss`, `credit_limit`, `creditLimit`.
