# Acceptance checklist (abbrev)

Job is done only when these hold. Full list: docs §55.

Markers: `[x]` = done in current frontend pass · `[ ]` = still open (usually backend or leftover purge).

## Removed

- [x] No Delivery Note in frontend UI / menu / print helpers
- [x] No Delivery Note in mock seeds (`deliveryNotes`) / broken delivery utils import
- [ ] No Delivery Note in API / DB (backend)
- [x] No UOM management / product UOM UI pages
- [x] No product UOM mock seed / `uom-conversions.ts` pricing helpers
- [ ] No product `uom_id` / UOM APIs (backend)
- [x] No Minimum Stock in product form / stock columns / dashboard
- [ ] No Minimum Stock in backend schemas / migrations
- [x] No Expired Stock page / expiry settings tab / product Expire tab / mock expiry fields
- [ ] No expiry-only scheduler / Telegram / backend fields
- [x] No Customer Credit Limit in frontend forms
- [ ] No Customer Credit Limit in backend
- [x] Frontend dead-code scan for delivery/UOM/expiry aliases (re-run with `dead-code-cleanup-prompt.md` as needed)
- [ ] No broken references after final dead-code scan (BE)

## Core flows

- [x] Product CRUD UI (code, category, brand, sale price, image — no Barcode / Purchase Price / Profit % / Quantity inputs; purchase-driven)
- [x] Stock In dialog (`StockStockInDialog`) stores a purchase (supplier, qty, purchase price, paid) and updates stock — product document + Stock list + history dialog
- [x] Purchase UI: dimensional + normal lines, `otherCost`, mock `createPurchase` side effects
- [ ] Purchase API + DB: dimensional snapshots, stock ↑, supplier debt/ledger/movement (verify end-to-end)
- [x] POS UI: barcode, dimensional lines, `otherCharge`, invoice print, no Delivery Note
- [ ] POS API: stock ↓, no silent negative, ledger/debt (verify end-to-end)
- [x] Sales / Returns workspace pages wired
- [ ] Returns transactional with correct stock/debt (API + full UI depth)
- [x] Stock adjustment + damaged stock pages
- [ ] Stock adjustment / damage APIs verified transactional
- [x] Stock Movements page present
- [ ] Stock Movements filters + export complete
- [x] Customer/Supplier debt menu → report routes
- [ ] Customer/Supplier debt payments end-to-end
- [x] Statement / profit report page shells
- [ ] Statements (opening, debit, credit, running, closing) + PDF/Excel of full filtered set
- [ ] Reports + PDF/Excel export of full filtered set

## Quality

- [ ] Frontend typecheck/lint/test/build pass (run after `pnpm install` in `frontend/`)
- [ ] Backend tests + migrations upgrade pass
- [ ] Docker lean stack healthy
- [x] Permissions/i18n/menu aligned for current allowlist routes (trim stale keys still pending)
