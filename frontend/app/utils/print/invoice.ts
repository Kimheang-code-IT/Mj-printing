import { formatMoney } from '~/utils/format/format-service'
import {
  cartSubtotal,
  refreshLineAmounts,
  type PosCartLine,
} from '~/utils/pos/cart'
import { escapeHtml, PAPER_STYLES, printHtmlDocument, type PrintPaperSize } from '~/utils/print/html'

export type SaleInvoicePrintLine = Pick<
  PosCartLine,
  'name' | 'quantity' | 'unitPrice'
> & {
  height?: number | null
  width?: number | null
  squareMeter?: number | null
}

export type SaleInvoicePrintInput = {
  shopName: string
  invoiceNo: string
  dateLabel: string
  customerName: string
  cashier: string
  currency: string
  lines: SaleInvoicePrintLine[]
  otherCharge: number
  depositAmount: number
  outstandingAmount: number
}

function asCartLine(line: SaleInvoicePrintLine): PosCartLine {
  return refreshLineAmounts({
    productId: '',
    barcode: '',
    imageUrl: null,
    availableStock: 0,
    name: line.name,
    quantity: line.quantity,
    unitPrice: line.unitPrice,
    height: line.height ?? null,
    width: line.width ?? null,
    squareMeter: line.squareMeter ?? null,
    calcMode: 'normal',
    amount: 0,
  })
}

function unitLabel(line: PosCartLine): string {
  if (line.squareMeter != null) return `${line.squareMeter} m²`
  return ''
}

/**
 * Empty filler rows so the lines grid fills ~70% of the printable page
 * height (shop-form look) without forcing a short sale onto page 2 when
 * product rows already cover that space.
 */
function emptyInvoiceRows(filled: number, paperSize: PrintPaperSize): string {
  const style = PAPER_STYLES[paperSize]
  const targetMm = style.printableMm * 0.7
  const headerMm = style.rowMm * 1.6
  const bodyMm = Math.max(0, targetMm - headerMm)
  const totalRows = Math.max(filled, Math.floor(bodyMm / style.rowMm))
  // Trim 3 filler rows so the grid stays shorter and totals fit on page 1.
  const missing = Math.max(0, totalRows - filled - 3)
  return Array.from({ length: missing }, () => `
    <tr class="empty">
      <td class="num">&nbsp;</td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
      <td></td>
    </tr>`).join('')
}

function summaryRow(label: string, amountHtml: string, strong = false): string {
  const cls = strong ? ' class="strong"' : ''
  return `
      <tr${cls}>
        <td class="spacer" colspan="3"></td>
        <td class="label" colspan="2">${label}</td>
        <td class="num">${amountHtml}</td>
      </tr>`
}

/**
 * Build invoice HTML. Product rows + empty fillers (~70% page height).
 * Totals label aligns with Price; amount aligns with Amount.
 */
export function buildSaleInvoiceHtml(
  input: SaleInvoicePrintInput,
  paperSize: PrintPaperSize = 'A4',
): string {
  const money = (value: unknown) => escapeHtml(formatMoney(value, input.currency))
  const lines = input.lines.map(asCartLine)
  const total = cartSubtotal(lines)
  const rows = lines.map((line, index) => `
    <tr>
      <td class="num">${index + 1}</td>
      <td class="product">${escapeHtml(line.name)}</td>
      <td>${escapeHtml(unitLabel(line) || '—')}</td>
      <td class="num">${escapeHtml(line.quantity)}</td>
      <td class="num">${money(line.unitPrice)}</td>
      <td class="num">${money(line.amount)}</td>
    </tr>`).join('')

  const colgroup = `
    <colgroup>
      <col class="col-no">
      <col class="col-product">
      <col class="col-unit">
      <col class="col-qty">
      <col class="col-price">
      <col class="col-amount">
    </colgroup>`

  return `
<article class="doc">
  <p class="title">វិក្កយបត្រ / INVOICE</p>
  <div class="meta">
    <div>
      <p>លេខ Invoice : <strong>${escapeHtml(input.invoiceNo)}</strong></p>
      <p>កាលបរិច្ឆេទ Date : <strong>${escapeHtml(input.dateLabel)}</strong></p>
    </div>
    <div class="right">
      <p>អតិថិជន Customer : <strong>${escapeHtml(input.customerName)}</strong></p>
      <p>បេឡា Cashier : <strong>${escapeHtml(input.cashier)}</strong></p>
    </div>
  </div>
  <table class="lines">
    ${colgroup}
    <thead>
      <tr>
        <th>ល.រ<span>N°</span></th>
        <th>មុខទំនិញ<span>Product</span></th>
        <th>ឯកតា<span>Unit</span></th>
        <th class="num">ចំនួន<span>Qty</span></th>
        <th class="num">តម្លៃ<span>Price</span></th>
        <th class="num">តម្លៃសរុប<span>Amount</span></th>
      </tr>
    </thead>
    <tbody>${rows}${emptyInvoiceRows(lines.length, paperSize)}</tbody>
  </table>
  <div class="totals">
    <table class="summary">
      ${colgroup}
      ${summaryRow('ទឹកប្រាក់សរុប / Total Amount', money(total))}
      ${summaryRow('ថ្លៃផ្សេងៗ / Other charge', money(input.otherCharge))}
      ${summaryRow('បានទូទាត់_____/_____/_____', money(input.depositAmount))}
      ${summaryRow('ខ្វះសរុប', money(input.outstandingAmount), true)}
    </table>
  </div>
  <div class="signs"> 
    <div class="sign">
      <div class="line"></div>
      <p>អ្នកទិញ / Buyer</p>
    </div>
    <div class="sign">
      <div class="line"></div>
      <p>អ្នកលក់ / Seller</p>
    </div>
  </div>
</article>`
}

/** Print the invoice in the chosen paper size (POS chooser: A4 default). */
export function printSaleInvoice(input: SaleInvoicePrintInput, paperSize: PrintPaperSize = 'A4'): Promise<void> {
  return printHtmlDocument(buildSaleInvoiceHtml(input, paperSize), input.invoiceNo || 'Invoice', { paperSize })
}
