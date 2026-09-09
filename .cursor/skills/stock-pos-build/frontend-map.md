# Frontend map (Stock & POS)

Use these paths when extending or regressing the frontend. Prefer editing these over inventing parallel modules.

## Config / nav / RBAC

| Concern | Path |
| --- | --- |
| Module registry (stock + reports) | `frontend/app/config/stock-modules.ts` |
| Route module merge | `frontend/app/config/modules.ts` |
| Sidebar menu | `frontend/app/composables/layout/useMenu.ts` |
| Role document types / permissions | `frontend/app/utils/role/permissions.ts` |
| i18n | `frontend/i18n/locales/en.json`, `km.json` |

## Pages (allowlist)

| Area | Paths |
| --- | --- |
| Products / stock | `pages/stock/index.vue`, `new.vue`, `[id].vue` |
| Master data | `pages/setup/{categories,brands,customers,suppliers}/` |
| Purchases | `pages/reports/purchases/new.vue` (`/purchases` route removed — the form lives only at `/reports/purchases/new`) |
| POS / sales | `pages/pos/index.vue` (`/sales` redirects to `/reports/sales`) |
| Debt redirects | legacy `/customer-debts` + `/supplier-debts` pages removed — handled by `middleware/legacy-routes.global.ts` |
| Reports | `pages/reports/{sales,purchases,customers,suppliers,customer-debts,supplier-debts,finance}/` |
| Admin | `pages/administration/{users,roles,settings,audit-logs,document-sequences}/` |

## Math / POS / print

| Concern | Path |
| --- | --- |
| Dimensional + totals math | `frontend/app/utils/stock/line-calc.ts` |
| POS cart helpers | `frontend/app/utils/pos/cart.ts` |
| POS checkout payload | `frontend/app/utils/pos/checkout.ts` |
| Invoice print | `frontend/app/utils/print/invoice.ts` |
| Legacy UOM helpers (purge) | `frontend/app/utils/stock/uom-conversions.ts` — do not add new callers |

## Repositories / contracts

| Concern | Path |
| --- | --- |
| Types / inputs | `frontend/app/repositories/contracts/entities.ts` |
| HTTP client | `frontend/app/repositories/http/entities.ts` |
| Mock client | `frontend/app/repositories/mock/entities.ts` |
| Mock seed / DB | `frontend/app/mocks/seed.ts`, `stock-seed.ts`, `db.ts` |

`PosSaleItemInput` / `PosCompleteSaleInput` must carry dimensional fields + `otherCharge`.  
`createPurchase` → `POST /api/v1/purchases` (HTTP) with mock side effects in mock repo.

## Workspace / forms

| Concern | Path |
| --- | --- |
| Generic list/workspace | `frontend/app/components/module/WorkspaceView.vue` |
| Product document form | product form under components (single General tab, no Barcode / Purchase Price / Profit % / Quantity inputs) |
| Stock In (purchase) dialog | `frontend/app/components/stock/StockInDialog.vue` — product document more-menu, Stock list row menu, Stock In history add |
| Dashboard | `frontend/app/pages/index.vue` — no lowStock / expiryLoss / pendingDeliveryNotes |

## Tests to keep green

- `frontend/tests/line-calc.spec.ts`
- `frontend/tests/nav-allowlist.spec.ts`
- `frontend/tests/repositories.spec.ts`
- `frontend/tests/mock-repositories.spec.ts`
- `frontend/tests/print-documents.spec.ts` (no delivery-note imports)

## Forbidden UI patterns

- Delivery Note after POS checkout
- UOM convert / pricing rows on product or cart
- Min-stock or expiry columns / alerts
- Credit limit on customer forms
- `deliveryFee` / `needsDelivery` on sale checkout
