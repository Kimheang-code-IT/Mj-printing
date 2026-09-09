/** Dimensional and normal line calculations (AGENT_STOCK_POS §3.2 / §6 / §7). */

export type LineCalcMode = 'normal' | 'dimensional'

const MAX_SCALE = 6

function parseDecimal(value: unknown): { negative: boolean, digits: bigint, scale: number } | null {
  const text = String(value ?? '').trim()
  if (!/^-?\d*(\.\d*)?$/.test(text) || text === '' || text === '-' || text === '.') return null
  const negative = text.startsWith('-')
  const unsigned = negative ? text.slice(1) : text
  const [intPart = '', fracPart = ''] = unsigned.split('.')
  const digits = BigInt(`${intPart || '0'}${fracPart}` || '0')
  return { negative, digits, scale: fracPart.length }
}

function scaledToNumber(digits: bigint, scale: number): number {
  let sign = 1n
  let value = digits
  if (value < 0n) {
    sign = -1n
    value = -value
  }
  if (scale > MAX_SCALE) {
    const drop = BigInt(10) ** BigInt(scale - MAX_SCALE)
    const half = drop / 2n
    value = (value + half) / drop
    scale = MAX_SCALE
  }
  const result = Number(value * sign) / 10 ** scale
  return Object.is(result, -0) ? 0 : result
}

/** Decimal-safe `a × b` — no binary-float drift. */
export function multiplyDecimalSafe(a: unknown, b: unknown): number {
  const da = parseDecimal(a)
  const db = parseDecimal(b)
  if (!da || !db) return 0
  const negative = da.negative !== db.negative
  const digits = da.digits * db.digits * (negative ? -1n : 1n)
  return scaledToNumber(digits, da.scale + db.scale)
}

/** Decimal-safe `a ÷ b`. */
export function divideDecimalSafe(a: unknown, b: unknown): number {
  const da = parseDecimal(a)
  const db = parseDecimal(b)
  if (!da || !db || db.digits === 0n) return 0
  const negative = da.negative !== db.negative
  const scaleBoost = Math.max(0, MAX_SCALE + db.scale - da.scale)
  const digits = (da.digits * BigInt(10) ** BigInt(scaleBoost)) / db.digits
  return scaledToNumber(negative ? -digits : digits, da.scale + scaleBoost - db.scale)
}

export function roundMoney(value: number): number {
  return Math.round((Number(value) || 0) * 100) / 100
}

export function roundQty(value: number): number {
  return Math.round((Number(value) || 0) * 10000) / 10000
}

/** square_meter = height × width × quantity when dimensional; else null. */
export function calcSquareMeter(
  height: number | null | undefined,
  width: number | null | undefined,
  quantity: number,
): number | null {
  const h = Number(height)
  const w = Number(width)
  const q = Number(quantity)
  if (!Number.isFinite(h) || !Number.isFinite(w) || h <= 0 || w <= 0) return null
  if (!Number.isFinite(q) || q <= 0) return null
  return roundQty(h * w * q)
}

export function lineCalcMode(
  height: number | null | undefined,
  width: number | null | undefined,
): LineCalcMode {
  const h = Number(height)
  const w = Number(width)
  if (Number.isFinite(h) && Number.isFinite(w) && h > 0 && w > 0) return 'dimensional'
  return 'normal'
}

/**
 * Dimensional: amount = square_meter × unit_price
 * Normal: amount = quantity × unit_price
 */
export function calcLineAmount(input: {
  height?: number | null
  width?: number | null
  quantity: number
  unitPrice: number
}): { mode: LineCalcMode, squareMeter: number | null, amount: number } {
  const quantity = Math.max(0, Number(input.quantity) || 0)
  const unitPrice = Math.max(0, Number(input.unitPrice) || 0)
  const mode = lineCalcMode(input.height, input.width)
  if (mode === 'dimensional') {
    const squareMeter = calcSquareMeter(input.height, input.width, quantity) ?? 0
    return { mode, squareMeter, amount: roundMoney(squareMeter * unitPrice) }
  }
  return { mode, squareMeter: null, amount: roundMoney(quantity * unitPrice) }
}

/** grand_total = subtotal + other - discount (never negative). */
export function calcGrandTotal(subtotal: number, other: number, discount: number): number {
  return roundMoney(Math.max(0, (Number(subtotal) || 0) + (Number(other) || 0) - (Number(discount) || 0)))
}

export function calcBalance(grandTotal: number, paid: number): number {
  return roundMoney(Math.max(0, (Number(grandTotal) || 0) - (Number(paid) || 0)))
}

/** Stock units consumed/added for inventory: dimensional uses m², else quantity. */
export function stockQtyForLine(input: {
  height?: number | null
  width?: number | null
  quantity: number
  squareMeter?: number | null
}): number {
  const mode = lineCalcMode(input.height, input.width)
  if (mode === 'dimensional') {
    return input.squareMeter != null
      ? roundQty(Number(input.squareMeter))
      : (calcSquareMeter(input.height, input.width, input.quantity) ?? 0)
  }
  return roundQty(Number(input.quantity) || 0)
}
