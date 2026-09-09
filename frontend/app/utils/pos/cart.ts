import {
  calcLineAmount,
  roundMoney,
  stockQtyForLine,
  type LineCalcMode,
} from '~/utils/stock/line-calc'

export type PosCartLine = {
  productId: string
  name: string
  barcode: string
  imageUrl: string | null
  /** Remaining stock in product base units (qty or m²). */
  availableStock: number
  unitPrice: number
  quantity: number
  /** Nullable — when both height & width > 0, line is dimensional. */
  height: number | null
  width: number | null
  squareMeter: number | null
  calcMode: LineCalcMode
  amount: number
}

export function refreshLineAmounts(line: PosCartLine): PosCartLine {
  const { mode, squareMeter, amount } = calcLineAmount({
    height: line.height,
    width: line.width,
    quantity: line.quantity,
    unitPrice: line.unitPrice,
  })
  return {
    ...line,
    calcMode: mode,
    squareMeter,
    amount,
  }
}

export function lineGross(line: PosCartLine): number {
  const { amount } = calcLineAmount({
    height: line.height,
    width: line.width,
    quantity: line.quantity,
    unitPrice: line.unitPrice,
  })
  return amount
}

export function cartSubtotal(lines: PosCartLine[]): number {
  return roundMoney(lines.reduce((sum, line) => sum + lineGross(line), 0))
}

export function productImageUrl(row: Record<string, unknown>): string | null {
  const candidates = [row.imageUrl, row.image, row.photoUrl, row.thumbnailUrl]
  for (const value of candidates) {
    const text = String(value || '').trim()
    if (text) return text
  }
  return null
}

/** Stock units this cart line will consume. */
export function lineStockQty(line: PosCartLine): number {
  return stockQtyForLine({
    height: line.height,
    width: line.width,
    quantity: line.quantity,
    squareMeter: line.squareMeter,
  })
}

export function createCartLine(row: Record<string, unknown>): PosCartLine {
  const stock = Number(row.quantity || 0)
  const unitPrice = roundMoney(Number(row.salePrice || 0))
  return refreshLineAmounts({
    productId: String(row.id),
    name: String(row.name || ''),
    barcode: String(row.barcode || ''),
    imageUrl: productImageUrl(row),
    availableStock: stock,
    unitPrice,
    quantity: 1,
    height: null,
    width: null,
    squareMeter: null,
    calcMode: 'normal',
    amount: unitPrice,
  })
}
