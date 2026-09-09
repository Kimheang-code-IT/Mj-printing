import { describe, expect, it } from 'vitest'
import {
  calcBalance,
  calcGrandTotal,
  calcLineAmount,
  calcSquareMeter,
  stockQtyForLine,
} from '../app/utils/stock/line-calc'

describe('line-calc (AGENT_STOCK_POS §3.2)', () => {
  it('computes dimensional square meter and amount', () => {
    expect(calcSquareMeter(2, 3, 2)).toBe(12)
    const line = calcLineAmount({ height: 2, width: 3, quantity: 2, unitPrice: 5 })
    expect(line.mode).toBe('dimensional')
    expect(line.squareMeter).toBe(12)
    expect(line.amount).toBe(60)
  })

  it('uses quantity × price for normal lines', () => {
    const line = calcLineAmount({ quantity: 4, unitPrice: 2.5 })
    expect(line.mode).toBe('normal')
    expect(line.squareMeter).toBeNull()
    expect(line.amount).toBe(10)
  })

  it('computes grand total and balance', () => {
    expect(calcGrandTotal(100, 10, 5)).toBe(105)
    expect(calcBalance(105, 40)).toBe(65)
  })

  it('stock qty uses m² when dimensional', () => {
    expect(stockQtyForLine({ height: 1.5, width: 2, quantity: 2 })).toBe(6)
    expect(stockQtyForLine({ quantity: 3 })).toBe(3)
  })
})
