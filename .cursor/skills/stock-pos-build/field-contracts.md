# Field and calculation contracts

Align forms, schemas, columns, and APIs with these lists. Do not add pharmacy-legacy fields outside the lists.

## Product

Allowed on the document form: Product Code/SKU, Name, Category, Brand, Sale Price, Image, Description/Note, Status, Created At, Updated At.

**Not editable on the product document form:** Barcode, Purchase Price, Profit %, Current Stock. Purchase Price and Current Stock come from purchases only (Stock In dialog → `POST /purchases`: stock ↑, supplier ledger/debt, `cost_price` update). Profit % stays derived. Barcode remains a backend/API + POS-scan field only.

Rules:

- Code unique; barcode unique when set; name required.
- Purchase/sale price >= 0.
- Stock never silently negative (unless an existing documented setting allows it).
- Profit % = `((sale - purchase) / purchase) * 100`; if purchase is 0, return null/0 per project convention — never divide by zero.
- Prefer calculated profit % over a stored source of truth.

Forbidden: UOM, minimum stock, expiry management.

## Customer

Allowed: Code, Name, Phone, Address, Current Debt, Note, Status, timestamps.

- Code unique; name required.
- Current debt not editable via normal CRUD.
- Debt changes only from: sale on credit, customer payment, sale return, approved adjustment/opening balance.

Forbidden: credit limit.

## Supplier

Allowed: Code, Name, Phone, Address, Current Debt, Note, Status, timestamps.

- Same debt rules via purchase on credit, supplier payment, purchase return, approved adjustment/opening balance.

## Purchase / Stock In

Header: Purchase No, Supplier Invoice No, Date, Supplier, Phone/Address auto, Note, Status (if workflow needs), Created By.

Lines: Product, Height, Width, Square Meter, Quantity, Purchase Price, Amount, Note.

Totals: Subtotal, Other Cost, Discount, Grand Total, Paid, Balance.

Formulas:

- Dimensional: `square_meter = height × width × quantity`; `amount = square_meter × purchase_price`
- Normal: `amount = quantity × purchase_price`
- `grand_total = subtotal + other_cost - discount`
- `balance = grand_total - paid`

Repo naming: frontend `otherCost` ↔ API `other_cost`.

Atomic save: validate → header/lines → lock stock ↑ → movements → supplier ledger (+ payment if paid) → update supplier debt → audit → commit.

## POS / Sale

Header: Invoice No, Date, Customer (optional walk-in OK), Phone/Address auto, Seller/Cashier, Note.

Lines: Product, Barcode, Height, Width, Square Meter, Quantity, Sale Price, Amount.

Totals: Subtotal, Discount, Other Charge, Grand Total, Paid, Balance, Payment Method.

Formulas:

- Dimensional: `square_meter = height × width × quantity`; `amount = square_meter × sale_price`
- Normal: `amount = quantity × sale_price`
- `grand_total = subtotal + other_charge - discount`
- `balance = grand_total - paid`

Repo naming: frontend `otherCharge` ↔ API `other_charge`.

**Not allowed on sale:** delivery fee, needsDelivery, Delivery Note handoff, UOM conversion rows.

Atomic save: validate stock → sale → stock ↓ → movements → customer ledger/payment → debt → audit → receipt → commit.

Shared frontend math: `frontend/app/utils/stock/line-calc.ts` (`calcSquareMeter`, `calcLineAmount`, `calcGrandTotal`, `calcBalance`, `stockQtyForLine`).

## Stock page columns

Image, Product Code, Product, Category, Brand, Purchase Price, Sale Price, Stock In, Stock Out, Damaged Stock, Current Stock, Status.

Stock In / Stock Out / Damaged Stock are read-only qty columns (`stockInQty` / `stockOutQty` / `damageQty`) computed from stock movements — not editable form fields and not filterable. No Barcode column on the table; barcode stays on POS scan (not on the product form).

**Adding stock to a product:** Stock In is a purchase transaction via `StockStockInDialog` (supplier, date, quantity, purchase price, paid, supplier invoice no., note → `createPurchase`). Never a direct quantity or cost-price edit.

Filters: search, category, brand, status. No min-stock or expiry columns.

## Sales Report / Purchase Report

Line-level (one row per product line), not document totals.

**Sales Report:** Invoice No, Date, Customer Name, Phone, Address, Product, Thickness (`height`), Length (`width`), Square Meters, Quantity, Unit Price, Total Price. Header totals: Total meters + Grand total.

**Purchase Report:** Invoice No, Date, Supplier Name, Phone, Address, Product, Height, Length, Square Meters, Quantity, Unit Price, Total Price, Others (`note`). Header totals: Grand total + Paid + Balance.

**No Other Cost column on the Purchase Report** (removed completely). The purchase document still supports `otherCost` in its totals (`grand_total = subtotal + other_cost - discount`), and the value still feeds the report's grand total — it is just never shown as a report column or row field.

Create sales via POS. Create purchases via `/purchases/new`. Do not restore top-level `/sales` or `/purchases` list pages.

## Stock movements

Immutable history. Types include purchase/sale/adjustment/damage/returns (and project equivalents). No silent edits to past movements.

## Dashboard summary (frontend)

Allowed KPI-style fields that match current contracts (sales, stock value, debts, etc.).

**Do not restore:** `lowStock`, `expiryLoss`, `pendingDeliveryNotes`.
