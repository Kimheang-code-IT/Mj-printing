# Prompt: Frontend dead-code purge (Stock & POS)

Copy/paste this into Cursor when you want another full unused-code cleanup pass.

---

## Task

Audit and remove **unused / forbidden** frontend code in `frontend/` for the MJ Printing Stock & POS app. Follow `.cursor/skills/stock-pos-build/SKILL.md`, `removed-features.md`, `frontend-map.md`, and `docs/AGENT_STOCK_POS_FULL_IMPLEMENTATION.md`.

## Goals

1. Find files, exports, types, mocks, i18n keys, and tests that are **not used** or belong to **forbidden features**.
2. Delete or slim them safely (prefer delete over comment-out).
3. Keep frontend, permissions, menu, modules, i18n, and tests synchronized.
4. Do **not** rebuild the app or add new features.

## Forbidden leftovers (must remove if found)

| Feature | Patterns to search |
| --- | --- |
| Delivery Note | `deliveryNotes`, `delivery-note`, `DeliveryNote`, `needsDelivery`, `deliveryFee`, `deliveryPrice`, `/delivery-notes` |
| UOM management | `uoms`, `uomId`, `uom_id`, `uomConversions`, `normalizeUomConversions`, `Convert UOM`, `/setup/uoms`, `uom-conversions` |
| Minimum stock | `min_stock`, `minimumStock`, `lowStockLevel` (settings), Low Stock columns/alerts |
| Expired stock | `expiryTracking`, `expiryDate`, `expiryAlert`, `trackExpiry`, Expired Stock pages |
| Credit limit | `credit_limit`, `creditLimit` |
| Sale delivery fee | `deliveryFee`, `needsDelivery` (sale extras = `otherCharge` only) |

**Keep (not forbidden):** `notifications.deliveryRetries`, password/session expiry settings, credit **payment** method (`creditRequiresCustomer`), POS local low-stock badge by qty, optional print `uom?:` label for m².

## Allowed surfaces (do not delete)

- Allowlist pages: `/`, `/stock*`, `/setup/{categories,brands,customers,suppliers}`, `/purchases*`, `/stock-adjustments`, `/damaged-stock`, `/pos`, `/sales`, `/returns`, `/customer-debts`, `/supplier-debts`, `/reports/*`, `/administration/*`, `/auth/*`
- `utils/stock/line-calc.ts`, `utils/pos/cart.ts`, `utils/pos/checkout.ts`, `utils/print/invoice.ts`
- Active repositories under `repositories/{contracts,http,mock}/`
- Regression tests that assert forbidden features stay gone (`nav-allowlist`, `document-tabs`, `telegram-settings`)

## Method

1. **Scan** with ripgrep for the patterns above across `frontend/app`, `frontend/i18n`, `frontend/tests`.
2. **Classify** each hit: DELETE file · EDIT strip symbols · KEEP with reason.
3. **Nuxt caution:** auto-imports mean an export can look unused in grep but still be global — confirm with no page/composable/repo callers before deleting utils.
4. **Dynamic routes / string collections:** check `stock-modules.ts`, `useMenu.ts`, `permissions.ts`, mock `db.ts` collection keys.
5. **Purge order:** broken imports → mock seeds → dead utils → repo aliases → settings types → i18n en+km together → update tests.
6. **Verify:** from `frontend/` run `pnpm exec vitest run` (at least nav-allowlist, document-tabs, telegram-settings, line-calc, pos-checkout, mock-repositories, repositories, print-documents) and ensure `pnpm dev` has no parse/duplicate-import errors.

## Output expected

- List of deleted files
- List of edited files (what removed)
- Anything skipped and why
- Test results summary

## Constraints

- Money stays `Decimal`/safe helpers in `line-calc` — never reintroduce float UOM pricing tables.
- Sale total extras: `otherCharge` / `other_charge` only.
- Purchase total extras: `otherCost` / `other_cost` only.
- Do not touch backend unless a frontend mock import requires it.
- Do not commit unless asked.
