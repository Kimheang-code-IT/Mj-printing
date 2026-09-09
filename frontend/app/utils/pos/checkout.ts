import { roundMoney } from '~/utils/stock/line-calc'

export type CheckoutDebtRow = Record<string, unknown> & {
  id: string
  date: string
  invoiceNo: string
  paidAmount: number
  remainingAmount: number
  paymentMethod: string
}

/** Other charge on the sale (AGENT_STOCK_POS §7). */
export function checkoutOtherCharge(otherCharge: number) {
  return roundMoney(Math.max(0, Number(otherCharge) || 0))
}

/** Sale net = subtotal + other charge (discount is not used in this project). */
export function checkoutSaleNet(subtotal: number, otherCharge = 0) {
  return roundMoney((Number(subtotal) || 0) + checkoutOtherCharge(otherCharge))
}

/** Selected open invoices included on this checkout (added to amount due). */
export function checkoutDepositTotal(remainings: number[]) {
  return roundMoney(remainings.reduce((sum, value) => sum + (Number(value) || 0), 0))
}

export function checkoutDue(saleNet: number, depositTotal: number) {
  return roundMoney(saleNet + depositTotal)
}

export function checkoutOutstanding(due: number, paidNow: number) {
  return roundMoney(Math.max(0, due - (Number(paidNow) || 0)))
}
