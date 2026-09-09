import type { ApiMeta } from '~/types/stock-pos/common'
import type { AppRecord } from '~/config/admin-seed'

/** Query translation of the workspace list controls into named API parameters. */
export interface EntityListQuery {
  q?: string
  page?: number
  limit?: number
  sort?: string
  status?: string
  startDate?: string
  endDate?: string
  customerId?: string
  supplierId?: string
  productId?: string
  paymentMethod?: string
  type?: string
}

export interface EntityListResult<T extends object = AppRecord> {
  items: T[]
  meta: ApiMeta | null
}

/** Typed CRUD contract shared by every `/api/v1` entity collection. */
export interface EntityRepository {
  list(collection: string, query?: EntityListQuery): Promise<EntityListResult>
  get(collection: string, id: string): Promise<AppRecord | null>
  create(collection: string, input: Record<string, unknown>): Promise<AppRecord>
  update(collection: string, id: string, input: Record<string, unknown>): Promise<AppRecord>
  remove(collection: string, id: string): Promise<void>
  setStatus?(collection: string, id: string, status: string): Promise<AppRecord>
}

export interface PosSaleItemInput {
  productId: string
  quantity: number
  /** Optional override; when omitted the product sale price is used. */
  unitPrice?: number
  /** Per-line percent discount (0–100). */
  discountPercent?: number
  height?: number | null
  width?: number | null
  squareMeter?: number | null
  calcMode?: 'normal' | 'dimensional'
}

export interface PosCompleteSaleInput {
  customerId?: string | null
  customerName?: string | null
  items: PosSaleItemInput[]
  paymentMethod: string
  paidAmount: number
  discount?: number
  note?: string | null
  /** Open customer-debt rows to include on this invoice and settle from paid now. */
  includedDebtIds?: string[]
  /** Other charge added to grand total (AGENT_STOCK_POS §7). */
  otherCharge?: number
  /** Extra amount due on this invoice (selected debts and/or typed deposit). */
  deposit?: number
}

/** Multi-line purchase / stock-in header (AGENT_STOCK_POS §6). */
export interface PurchaseLineInput {
  productId: string
  quantity: number
  purchasePrice: number
  height?: number | null
  width?: number | null
  squareMeter?: number | null
  calcMode?: 'normal' | 'dimensional'
  note?: string | null
}

export interface PurchaseCreateInput {
  supplierId: string
  supplierInvoiceNo?: string | null
  date?: string | null
  note?: string | null
  otherCost?: number
  discount?: number
  paid?: number
  items: PurchaseLineInput[]
}

/** Movement-kind filter for the product history dialog (Current Stock is display-only). */
export type StockHistoryKind = 'stock_in' | 'stock_out' | 'damage'

/** One product-scoped stock movement row (UI camelCase; GET /stock/products/{id}/history). */
export interface ProductHistoryRow {
  id: string
  date: string
  /** Backend movement label, e.g. 'Stock In' / 'Sale' / 'Damage'. */
  type: string
  /** Signed base-UOM quantity (negative = stock out). */
  quantity: number
  reference: string
  user: string
  note: string
  kind: StockHistoryKind
}

/** One Stock In cost lot of a product (UI camelCase; GET /stock/products/{id}/cost-history). */
export interface ProductCostHistoryRow {
  id: string
  date: string
  product: string
  unitCost: number
  quantity: number
  /** quantity × unitCost (decimal-safe). */
  amount: number
  /** 1 = oldest lot, incremented per newer lot; displayed newest first. */
  version: number
  documentNo: string
}

/** One sale-price version of a product (UI camelCase; /products/{id}/sale-prices). */
export interface ProductSalePriceRow {
  id: string
  productId: string
  product: string
  salePrice: number
  date: string
  /** Exactly one version per product is POS-active. */
  isActive: boolean
  version: number
}

/** Query accepted by the product-scoped history / price dialogs. */
export interface ProductScopedQuery {
  q?: string
  startDate?: string
  endDate?: string
  page?: number
  limit?: number
}

/** Read-only product-scoped queries used by the Stock list dialogs. */
export interface StockQueryRepository {
  /** Movement history of one product; `type` filters by dialog kind. */
  listProductHistory(productId: string, query?: ProductScopedQuery & { type?: StockHistoryKind }): Promise<EntityListResult<ProductHistoryRow>>
  /** Stock In cost lots of one product (versions assigned oldest → newest). */
  listProductCostHistory(productId: string, query?: ProductScopedQuery): Promise<EntityListResult<ProductCostHistoryRow>>
  /** Sale-price versions of one product (newest first). */
  listSalePrices(productId: string, query?: ProductScopedQuery): Promise<EntityListResult<ProductSalePriceRow>>
  /** Add a new POS-active version (version = MAX+1; copies onto products.salePrice). */
  addSalePrice(productId: string, input: { date: string, salePrice: number }): Promise<ProductSalePriceRow>
  /** Activate one version — exactly one stays active; copies onto products.salePrice. */
  activateSalePrice(productId: string, priceId: string): Promise<ProductSalePriceRow>
}

/** Printable receipt payload for a completed sale (no PDF/MinIO required). */
export interface SaleReceipt {
  saleId: string
  saleNo: string
  invoiceNo: string
  date: string
  customer: string
  cashier: string
  paymentMethod: string
  note: string
  items: Array<{
    name: string
    quantity: number
    height?: number | null
    width?: number | null
    squareMeter?: number | null
    unitPrice: number
    discount: number
    total: number
  }>
  subtotal: number
  discount: number
  otherCharge: number
  deposit: number
  total: number
  paidAmount: number
  remaining: number
}

/**
 * Operational commands for POS checkout. Implementations must treat the whole
 * checkout as one transaction on the backend side (sale + items + payment or
 * debt + stock movements + document number + audit entry).
 */
export interface PosCommandRepository {
  completeSale(input: PosCompleteSaleInput): Promise<AppRecord>
  createPurchase(input: PurchaseCreateInput): Promise<AppRecord>
  createStockOperation(input: {
    type: 'stock_in' | 'adjustment' | 'damage'
    productId: string
    quantity: number
    note?: string | null
    unitCost?: number
    height?: number | null
    width?: number | null
    squareMeter?: number | null
  }): Promise<AppRecord>
  payCustomerDebt(input: {
    customerId: string
    /** When known, the backend path is POST /customers/{id}/debts/{debt_id}/payments. */
    debtId?: string
    amount: number
    paymentMethod: string
    reference?: string | null
  }): Promise<AppRecord>
  paySupplierDebt(input: {
    supplierId: string
    /** When known, the backend path is POST /suppliers/{id}/debts/{debt_id}/payments. */
    debtId?: string
    amount: number
    paymentMethod: string
    reference?: string | null
  }): Promise<AppRecord>
  /** Printable receipt payload derived from the stored sale (mock: in-memory). */
  getSaleReceipt(saleId: string): Promise<SaleReceipt>
  /** Customer return against a confirmed sale (POST /pos/sales/{id}/return). */
  returnSale(input: {
    saleId: string
    reason: string
    lines: Array<{ lineId: string, quantity: number, restock: boolean }>
  }): Promise<AppRecord>
  /** Supplier return against a confirmed Stock In (POST /stock/in/{id}/return). */
  returnPurchase(input: {
    stockInId: string
    reason: string
    lines: Array<{ lineId: string, quantity: number }>
  }): Promise<AppRecord>
}

/**
 * Business Summary snapshot for the dashboard (AGENT_STOCK_POS §1).
 */
export interface DashboardSummary {
  productsTotal: number
  outOfStockCount: number
  salesToday: number
  salesTodayAmount: number
  salesThisMonth: number
  salesThisMonthAmount: number
  income: number
  expense: number
  grossProfit: number | null
  netIncome: number | null
  customerDebt: number
  supplierDebt: number
  damageLoss: number
  salesByDay: Array<{ date: string, count: number }>
  incomeByDay: Array<{ date: string, amount: number }>
  expenseByDay: Array<{ date: string, amount: number }>
  startDate?: string | null
  endDate?: string | null
}

export interface FinanceSummary {
  income: number
  expense: number
  net: number
  outstanding: number
  startDate?: string | null
  endDate?: string | null
}

export type FinanceEntryType = 'income' | 'expense'

/**
 * One combined Finance Report ledger row (spec: Finance Report is an income
 * & expense table, not a chart). Income rows are system-derived from
 * confirmed POS sales / paid amounts; expense rows are user-managed
 * operating expenses. No chart, no standalone expense page.
 */
export interface FinanceEntry {
  id: string
  date: string
  type: FinanceEntryType
  /** Income: sale / invoice number. Expense: optional document reference. */
  reference: string
  /** Income: source label (e.g. Sales). Expense: operating category. */
  category: string
  description: string
  amount: number
  paymentMethod: string
  user: string
}

export interface FinanceExpenseInput {
  date: string
  category: string
  description: string
  /** Must be > 0. */
  amount: number
  paymentMethod: string
  reference?: string | null
  user?: string
}

export interface FinanceRepository {
  dashboard(startDate?: string, endDate?: string, requestKey?: string): Promise<DashboardSummary>
  financeSummary(startDate?: string, endDate?: string): Promise<FinanceSummary>
  /** Combined income + expense rows for the Finance table (date-filtered). */
  entries(startDate?: string, endDate?: string): Promise<FinanceEntry[]>
  /** Create an operating expense via the Add Expense modal (Finance only). */
  createExpense(input: FinanceExpenseInput): Promise<FinanceEntry>
}

export interface SearchHitItem {
  id: string
  type: string
  title: string
  subtitle?: string | null
  url: string
}

export interface SearchRepository {
  search(q: string, limit?: number): Promise<SearchHitItem[]>
}