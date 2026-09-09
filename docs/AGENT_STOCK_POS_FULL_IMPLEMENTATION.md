# MJ Printing Stock & POS — Current Frontend UI Reference

## 0. Purpose and rules

This document describes the frontend **exactly as it exists today**. It is a reference of the current UI, not a design spec for future work.

- **No extra design. No UI updates.** Do not redesign, restyle, or reorganize any existing page. Fix regressions and bugs only, and only when explicitly requested.
- Reuse the existing shared UI (module registry, workspace/document components, dialogs). Never create page-local duplicates or a parallel design system.
- Do not add routes, pages, dialogs, fields, columns, or navigation items that are not listed here.
- The forbidden features in §4 must never be reintroduced.
- Backend, database, Alembic, Redis, Docker, and infrastructure are out of scope for frontend-only tasks.

Stack: Nuxt 4 + Vue 3 + TypeScript + Nuxt UI + Tailwind + Pinia. Validation with Zod. i18n: English + Khmer.

---

## 1. Architecture (current)

| Concern | Path |
| --- | --- |
| Module registry (stock, setup, reports) | `frontend/app/config/stock-modules.ts` |
| Module registry (administration) | `frontend/app/config/admin-modules.ts` |
| Route module merge + types | `frontend/app/config/modules.ts` |
| Sidebar menu | `frontend/app/composables/layout/useMenu.ts` |
| Generic list/workspace renderer | `frontend/app/components/module/WorkspaceView.vue` |
| Generic document renderer | `frontend/app/components/module/DocumentView.vue` |
| Document shell | `frontend/app/components/document/*` (`AppDocumentPage`, `AppDocumentForm`, `AppDocumentTabBar`, …) |
| Tables | `frontend/app/components/table/*` (`AppListTable`, `AppLineTable`, `AppRelatedRecords`, …) |
| Shared form fields | `frontend/app/components/common/*` (`AppTextField`, `AppSelectField`, `AppNumberField`, `AppMoneyField`, `AppImageUploadField`, …) |
| Page-actions header (create / refresh / export) | `frontend/app/components/layout/AppHeaderPageActions.vue` |
| Repositories (HTTP + mock) | `frontend/app/repositories/{http,mock,contracts}` |
| Line math (dimensional + totals) | `frontend/app/utils/stock/line-calc.ts` |
| POS helpers | `frontend/app/utils/pos/{cart,checkout}.ts` |
| Invoice print | `frontend/app/utils/print/invoice.ts` |
| i18n | `frontend/i18n/locales/{en,km}.json` |
| Legacy route redirects | `frontend/app/middleware/legacy-routes.global.ts` |

Every list page is a module config rendered by `WorkspaceView.vue`; every create/detail/edit page is the same config rendered by `DocumentView.vue` on a dedicated route. No page reimplements list or form behavior.

---

## 2. Routes and navigation (current)

### 2.1 Route allowlist

```text
/                                     Dashboard
/stock  /stock/new  /stock/[id]       Stock list + product create/detail/edit
/pos                                  POS workspace
/setup/{categories,brands,suppliers,customers}[/new|/[id]]
/reports/{sales,purchases,customer-debts,supplier-debts,finance}
/reports/purchases/new                Purchase (Stock In) create form
/administration/{users,roles,document-sequences}[/new|/[id]]
/administration/{settings,audit-logs}
/auth/{login,forgot-password,reset-password,setup,verify-code}
```

Do not add or restore `/products`, `/sales`, `/returns`, `/stock-movements`, `/customer-debts`, `/supplier-debts`, `/delivery-notes*`, `/setup/uoms*`, `/uoms*`, or any expired-stock route.

Legacy flat routes redirect via `middleware/legacy-routes.global.ts`:

- `/purchases` → `/reports/purchases`; `/purchases/new` → `/reports/purchases/new`
- `/customer-debts` → `/reports/customer-debts`; `/supplier-debts` → `/reports/supplier-debts`
- `/reports/customers` → `/reports/customer-debts`; `/reports/suppliers` → `/reports/supplier-debts`
- `/categories`, `/brands`, `/suppliers`, `/customers` (and sub-paths) → `/setup/...`

Keep the middleware until old links have migrated; it never appears in navigation.

### 2.2 Sidebar (exact order and grouping)

```text
Dashboard
Stock
POS

Setup
  Categories
  Brands
  Suppliers
  Customers

Reports
  Sales Report
  Purchase Report
  Customer Debt Report
  Supplier Debt Report
  Finance Report

Administration
  Users
  Roles & Permissions
  Document Sequences
  Audit Logs
  Settings
```

Items are hidden when the user lacks the route permission (see §6). Collapsed state persists in `localStorage` (`stock-pos:sidebar:collapsed`); below 1023 px the sidebar becomes a drawer.

### 2.3 Page permissions

| Route | Permission |
| --- | --- |
| `/` | `dashboard.view` |
| `/stock` | `products.view` |
| `/pos` | `pos.view` |
| `/setup/categories` | `categories.view` |
| `/setup/brands` | `brand.view` |
| `/setup/suppliers` | `suppliers.view` |
| `/setup/customers` | `customers.view` |
| `/reports/*` | `reports.view` (`/reports/purchases/new` also uses `purchases.view`) |
| `/administration/users` | `admin.users.view` |
| `/administration/roles` | `admin.roles.view` |
| `/administration/document-sequences` | `configuration.view` |
| `/administration/settings` | `settings.app_config.view` |
| `/administration/audit-logs` | `admin.audit_logs.view` |

---

## 3. Dialogs (complete current inventory)

These are all the dialogs in the app. Nothing else opens a modal or drawer.

| # | Dialog | Component | Used from |
| - | ------ | --------- | --------- |
| 1 | Stock In (purchase) | `components/stock/StockInDialog.vue` | Stock row menu, product document more-menu, Stock In history add — posts `createPurchase` → `POST /api/v1/purchases` |
| 2 | Stock Adjustment / Damage | stock-operation dialog in `WorkspaceView.vue` | Stock row/product actions — posts `createStockOperation` (`stock_in` \| `adjustment` \| `damage`) |
| 3 | Sale Price | `components/stock/SalePriceDialog.vue` | Stock row/product actions |
| 4 | Cost History (read-only) | `components/stock/CostHistoryDialog.vue` | Product document |
| 5 | Quantity History (read-only) | `components/stock/QtyHistoryDialog.vue` | Stock row/product actions |
| 6 | Pay Debt (`customer` \| `supplier`) | `components/reports/DebtPaymentDialog.vue` | Customer/Supplier Debt Report rows |
| 7 | Return (customer/supplier) | `components/reports/DocumentReturnDialog.vue` | Sales Report (customer return), Purchase Report (supplier return) |
| 8 | Export | `components/common/AppExportDialog.vue` | Page-actions header |
| 9 | Add Expense | modal in `pages/reports/finance/index.vue` | Finance Report header (gated by `expense.create`) |
| 10 | POS Outstanding Debt | `components/pos/PosOutstandingDebtDialog.vue` | POS checkout panel |
| 11 | POS Print Size | `components/pos/PosPrintSizeDialog.vue` | POS receipt printing |
| 12 | Confirm / About / User Profile | `AppConfirmDialog` + `AppConfirmHost`, `AppAboutDialog`, `AppUserProfileDialog` | Destructive confirmations and app chrome |

All dialogs disable repeat submission while saving and close only after success.

---

## 4. Domain boundaries (must never be reintroduced)

The following must not appear in the UI, forms, filters, columns, dialogs, navigation, i18n keys, or seed data:

- Delivery Note, delivery fee, `needsDelivery`
- UOM management, `uom_id`, UOM conversion pricing
- Minimum stock / low-stock alerts
- Expired stock, expiry dates, expiry alerts
- Customer credit limit
- Separate Stock Movement, Return, Sales list, Purchase list, or Statement page routes
- **Discount and Other Cost/Charge inputs** — the UI exposes none anywhere. POS submits `discount: 0` / `otherCharge: 0`; the purchase form omits `other_cost` / `discount` (backend defaults 0).

Field naming and math (shared `line-calc.ts`):

- Sale add-on `otherCharge` / API `other_charge`; purchase add-on `otherCost` / `other_cost` — contract-only, no UI inputs.
- Dimensional line: `squareMeter = height × width × quantity`; `amount = squareMeter × unitPrice`.
- Normal line: `amount = quantity × unitPrice`.
- Totals: `grandTotal = subtotal + other - discount`; `balance = grandTotal - paid`.
- Money never uses binary floating point; use the shared decimal helpers.

---

## 5. Page-by-page current UI

### 5.1 Dashboard (`/`) — frozen

Do not modify. Compact header, four summary cards (Sales Today, Income, Expense, Outstanding Debt), Income vs Expense chart with date controls, Business Summary panel (Customer Debt, Supplier Debt, Outstanding Debt, Total Products, Out of Stock, Damage Loss). Values are dynamic; layout is fixed.

### 5.2 Stock (`/stock`, `/stock/new`, `/stock/[id]`)

List columns: Image, Code, Product, Category, Brand, Purchase Price (read-only), Sale Price, Stock In, Stock Out, Damaged Stock, Current Stock, Status, row actions. Filters: Category, Brand, Status.

Product document (single General tab), editable fields: Product Code (auto-generate when blank), Product Name*, Category*, Brand, Image, Sale Price*, Description/Note, Status*. (*required)

Not editable / not present on the form: Barcode, Purchase Price, Profit %, Current Stock, UOM, minimum stock, expiry. Purchase price, current stock, and profit are purchase-driven via Stock In only.

Stock In paths (both post `createPurchase`; stock/ledger/cost updates happen in the transaction, never on the client):

1. **Stock In dialog** — single product, from Stock row menu / product more-menu / Stock In history add.
2. **Purchase form** at `/reports/purchases/new` — multi-line: supplier header (Supplier, Date, Supplier invoice no., Note) + `AppLineTable` lines (Product, Height, Width, Square Meter, Quantity, Purchase Price, Amount, Note) + totals (Subtotal, Grand Total, Paid, Balance). No Other Cost and no Discount fields.

Quantity-changing dialogs show current and projected stock and reject forbidden negative stock.

### 5.3 POS (`/pos`)

Full-height split workspace: product browser (search by barcode/code/name, category/brand filters, product cards with image/code/name/stock/sale price) on the left; cart + checkout on the right.

Cart line: product, Height, Width, Square Meter, Quantity, Sale Price, Amount, remove. Recalculated through `line-calc.ts`; no UOM rows.

Checkout panel: Customer (walk-in allowed), phone and location when selected, Outstanding (selectable open debt invoices), Subtotal and Total, Deposit Total, Payment Method, Paid Now, Outstanding Amount, Complete Sale. Payload sends `discount: 0` / `otherCharge: 0`; no input fields for them. No delivery anything.

Completion: validate → disable submit → in-page receipt state with invoice number and totals → Print Receipt (paper size via Print Size dialog) and New Sale. Stays on `/pos`.

### 5.4 Setup pages (`/setup/*` + `/new`, `/[id]`)

| Page | List columns | Document fields |
| --- | --- | --- |
| Categories | Code, Name, Description, Products, Status | Name*, Code (auto), Description, Status* |
| Brands | Code, Name, Description, Products, Status | Brand Name*, Code (auto), Logo, Description, Status* |
| Suppliers | Code, Supplier, Phone, Address, Current Debt, Status | Supplier Code (auto), Supplier Name*, Phone, Address, Status* |
| Customers | Code, Customer, Phone, Address, Current Debt, Status | Customer Code (auto), Customer Name*, Phone, Address, Status* |

Current Debt is read-only and changes only through financial transactions. No credit limit. All create/detail/edit uses the shared document routes.

### 5.5 Sales Report (`/reports/sales`)

Read-only invoice-level report (`kind: 'reports'`, `tableOnly`). Filters: Customer, Status (Paid/Partial/Unpaid/Completed), Payment Method. Columns: Invoice No, Date, Customer, Phone, Address, Items, Subtotal, Grand Total, Paid, Balance, Payment Method, Status, Cashier. Row actions: read-only detail and customer Return (dialog #7). Sale creation lives only in POS.

### 5.6 Purchase Report (`/reports/purchases`, `/reports/purchases/new`)

Invoice-level report. Filters: Supplier, Status. Columns: Invoice No, Date, Supplier, Phone, Address, Items, Subtotal, Grand Total, Paid, Balance, Status, Note. Row actions: read-only detail and supplier Return (dialog #7). Header primary action → purchase create form (§5.2). No Other Cost column.

### 5.7 Customer Debt Report (`/reports/customer-debts`)

Read-only, invoice-level. Filters: Customer, Status (Unpaid/Partial/Paid). Columns: Date, Invoice No., Customer, Invoice Total, Paid Amount, Remaining Amount, Due Date, Status, Actions (Pay Debt — dialog #6, `customer` kind). Debt is ledger-driven; no separate statement route.

### 5.8 Supplier Debt Report (`/reports/supplier-debts`)

Same pattern with supplier terminology. Columns: Date, Invoice No. / Purchase No., Supplier, Total Amount, Paid Amount, Remaining Amount, Due Date, Status, Actions (Pay Debt — dialog #6, `supplier` kind).

### 5.9 Finance Report (`/reports/finance`)

Custom page: income & expense **table**, no charts. Header holds title + breadcrumbs + Add Expense only (no date range, no Refresh). Filters live on the table toolbar. Income rows are system-derived from confirmed POS sales; expense rows come only from the Add Expense modal (gated `expense.create`; credit payment method excluded). Net Result = income − recorded expenses. There is no `/expenses` route.

### 5.10 Users (`/administration/users` + `/new`, `/[id]`)

List columns: Username, Display Name, Email, Role, Telegram, Status, Last Login. Document fields: Username*, Display Name*, Email*, Password* (create-only, never displayed after save), Role* (options from `/api/v1/admin/roles/options`), Telegram Username / Chat ID (computed, linked by the bot, hidden on create).

### 5.11 Roles & Permissions (`/administration/roles` + `/new`, `/[id]`)

Role list with the shared document routes; the role document embeds `AppRolePermissionMatrix`. System roles are marked and protected. Removed modules (Delivery Note, UOM, expiry, …) do not appear in the matrix.

### 5.12 Document Sequences (`/administration/document-sequences` + `/new`, `/[id]`)

Sequence config per document type with prefix, next number, padding, preview, status. No Delivery Note sequences.

### 5.13 Audit Logs (`/administration/audit-logs`)

Read-only. Filters: date/time, user, action, entity, result, search. Sensitive data (secrets, tokens, passwords) is masked.

### 5.14 Settings (`/administration/settings`)

Rendered by `SystemSettingsPage.vue` with document tabs for the allowed groups (Company, Localization, Sales/POS, Purchases/Stock, Documents/Printing, System/Integrations). Secrets masked. No expiry-alert, minimum-stock, Delivery Note, UOM, or credit-limit settings.

---

## 6. Localization

- All user-visible copy comes from i18n keys (`app.*`, `core.*`); English and Khmer (`en.json`, `km.json`) stay structurally aligned.
- Every new key is added to both locales.
- Forbidden-feature keys are never reintroduced.

---

## 7. Verification

From `frontend/`:

```bash
pnpm typecheck
pnpm typecheck:unused
pnpm lint
pnpm test
pnpm build
```

Key tests to keep green: `nav-allowlist.spec.ts`, `line-calc.spec.ts`, `rbac.spec.ts`, `repositories.spec.ts`, `mock-repositories.spec.ts`, `print-documents.spec.ts`, `pos-checkout.spec.ts`, `header-actions.spec.ts`, `list-table.spec.ts`, `document-tabs.spec.ts`.

Dead-code scan keywords (evaluate matches; do not delete blindly):

```text
delivery, deliveryNote, deliveryFee, needsDelivery
uom, uom_id, minimumStock, min_stock, expiry, expired
creditLimit, credit_limit
/sales, /returns, /stock-movements
```

`/stock/new`, `/stock/[id]`, and `/reports/purchases/new` are **valid allowlisted routes** — do not flag them.
