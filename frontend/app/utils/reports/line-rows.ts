import type { AppRecord } from '~/config/admin-seed'
import { calcGrandTotal, roundMoney } from '~/utils/stock/line-calc'

function partyContact(party: AppRecord | undefined) {
  return {
    phone: String(party?.phone ?? ''),
    address: String(party?.address || party?.location || ''),
  }
}

function money(value: unknown) {
  return roundMoney(Number(value || 0))
}

function itemCount(doc: AppRecord) {
  if (doc.itemCount != null || doc.lineCount != null) {
    return Number(doc.itemCount ?? doc.lineCount ?? 0)
  }
  const items = Array.isArray(doc.items) ? doc.items : []
  return items.length
}

function paymentStatus(total: number, paid: number, explicit?: unknown) {
  if (explicit != null && String(explicit).trim()) return String(explicit)
  if (paid >= total && total > 0) return 'Paid'
  if (paid > 0) return 'Partial'
  return 'Unpaid'
}

/** One table row per sale invoice (header totals — not line items). */
export function flattenSaleReportLines(sales: AppRecord[], customers: AppRecord[]): AppRecord[] {
  const byId = new Map(customers.map(row => [String(row.id), row]))
  return sales.map((sale) => {
    const customer = byId.get(String(sale.customerId || ''))
    const contact = partyContact(customer)
    const items = Array.isArray(sale.items) ? sale.items as AppRecord[] : []
    const linesSubtotal = roundMoney(items.reduce((sum, item) => {
      return sum + Number(item.total ?? item.amount ?? 0)
    }, 0))
    const subtotal = money(sale.subtotal ?? linesSubtotal)
    const discount = money(sale.discount ?? sale.discountAmount ?? 0)
    const otherCharge = money(sale.otherCharge ?? 0)
    const total = money(sale.total ?? sale.grandTotal ?? calcGrandTotal(subtotal, otherCharge, discount))
    const paidAmount = money(sale.paidAmount ?? 0)
    const remainingAmount = money(sale.remaining ?? sale.remainingAmount ?? sale.debt_amount ?? Math.max(0, total - paidAmount))
    return {
      id: String(sale.id),
      invoiceNo: sale.invoiceNo || sale.saleNo,
      date: sale.date || sale.createdAt || sale.sale_date,
      customer: sale.customer || customer?.name || '',
      phone: contact.phone || String(sale.customerPhone ?? sale.phone ?? ''),
      address: contact.address || String(sale.customerLocation ?? sale.address ?? ''),
      itemCount: itemCount(sale),
      subtotal,
      discount,
      otherCharge,
      total,
      paidAmount,
      remainingAmount,
      paymentMethod: String(sale.paymentMethod ?? ''),
      status: paymentStatus(total, paidAmount, sale.status || sale.payment_status),
      cashier: String(sale.cashier ?? sale.cashier_name ?? ''),
    }
  })
}

/** One table row per purchase invoice (header totals — not line items). */
export function flattenPurchaseReportLines(purchases: AppRecord[], suppliers: AppRecord[]): AppRecord[] {
  const byId = new Map(suppliers.map(row => [String(row.id), row]))
  return purchases.map((purchase) => {
    const supplier = byId.get(String(purchase.supplierId || ''))
    const contact = partyContact(supplier)
    const items = Array.isArray(purchase.items) ? purchase.items as AppRecord[] : []
    const linesSubtotal = roundMoney(items.reduce((sum, item) => {
      return sum + Number(item.total ?? item.amount ?? (Number(item.price || item.unitPrice || 0) * Number(item.quantity || 0)))
    }, 0))
    const subtotal = money(purchase.subtotal ?? linesSubtotal)
    // Other cost still feeds the grand-total fallback (purchase totals
    // contract) but is NOT exposed as a report column.
    const otherCost = money(purchase.otherCost ?? 0)
    const discount = money(purchase.discount ?? purchase.discountAmount ?? 0)
    const total = money(purchase.total ?? purchase.grandTotal ?? calcGrandTotal(subtotal, otherCost, discount))
    const paidAmount = money(purchase.paidAmount ?? 0)
    const remainingAmount = money(purchase.remaining ?? purchase.remainingAmount ?? purchase.balance_amount ?? Math.max(0, total - paidAmount))
    return {
      id: String(purchase.id),
      invoiceNo: purchase.purchaseNo || purchase.invoiceNo || purchase.document_no,
      date: purchase.date || purchase.createdAt || purchase.transaction_date,
      supplier: purchase.supplier || supplier?.name || '',
      phone: contact.phone || String(purchase.supplierPhone ?? purchase.phone ?? ''),
      address: contact.address || String(purchase.address ?? ''),
      itemCount: itemCount(purchase),
      subtotal,
      discount,
      total,
      paidAmount,
      remainingAmount,
      status: String(purchase.status || paymentStatus(total, paidAmount)),
      note: String(purchase.note ?? ''),
    }
  })
}

export function adaptSaleReportRow(row: Record<string, unknown>): AppRecord {
  const total = Number(row.total ?? row.grand_total ?? row.grandTotal ?? row.sales_amount ?? 0)
  const paidAmount = Number(row.paidAmount ?? row.paid_amount ?? 0)
  const remainingAmount = Number(
    row.remainingAmount
    ?? row.remaining_amount
    ?? row.debt_amount
    ?? Math.max(0, total - paidAmount),
  )
  return {
    ...row,
    id: String(row.sale_id ?? row.saleId ?? row.id ?? ''),
    invoiceNo: row.invoiceNo ?? row.invoice_no ?? '',
    date: row.date ?? row.sale_date ?? row.saleDate,
    customer: row.customer ?? row.customer_name ?? '',
    phone: row.phone ?? row.customer_phone ?? '',
    address: row.address ?? row.customer_address ?? '',
    itemCount: Number(row.itemCount ?? row.item_count ?? row.lineCount ?? 0),
    subtotal: Number(row.subtotal ?? 0),
    discount: Number(row.discount ?? row.discount_amount ?? 0),
    otherCharge: Number(row.otherCharge ?? row.other_charge ?? 0),
    total,
    paidAmount,
    remainingAmount,
    paymentMethod: row.paymentMethod ?? row.payment_method ?? '',
    status: row.status ?? row.payment_status ?? paymentStatus(total, paidAmount),
    cashier: row.cashier ?? row.cashier_name ?? '',
  }
}

export function adaptPurchaseReportRow(row: Record<string, unknown>): AppRecord {
  const total = Number(row.total ?? row.grand_total ?? row.grandTotal ?? row.total_cost ?? 0)
  const paidAmount = Number(row.paidAmount ?? row.paid_amount ?? 0)
  const remainingAmount = Number(
    row.remainingAmount
    ?? row.remaining_amount
    ?? row.remaining_debt
    ?? row.balance_amount
    ?? Math.max(0, total - paidAmount),
  )
  return {
    ...row,
    id: String(row.transaction_id ?? row.purchase_id ?? row.id ?? ''),
    invoiceNo: row.invoiceNo ?? row.document_no ?? row.purchaseNo ?? '',
    date: row.date ?? row.transaction_date ?? row.transactionDate ?? row.purchase_date,
    supplier: row.supplier ?? row.supplier_name ?? '',
    phone: row.phone ?? row.supplier_phone ?? '',
    address: row.address ?? row.supplier_address ?? '',
    itemCount: Number(row.itemCount ?? row.item_count ?? row.lineCount ?? 0),
    subtotal: Number(row.subtotal ?? 0),
    discount: Number(row.discount ?? row.discount_amount ?? 0),
    total,
    paidAmount,
    remainingAmount,
    status: String(row.status ?? paymentStatus(total, paidAmount)),
    note: row.note ?? '',
  }
}
