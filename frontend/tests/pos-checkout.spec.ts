import { describe, expect, it } from 'vitest'
import {
  checkoutDepositTotal,
  checkoutDue,
  checkoutOtherCharge,
  checkoutOutstanding,
  checkoutSaleNet,
} from '../app/utils/pos/checkout'

describe('POS checkout totals', () => {
  it('builds sale net with other charge, deposit total, due, and outstanding from paid now', () => {
    const saleNet = checkoutSaleNet(100, 5)
    const deposit = checkoutDepositTotal([25, 15])
    const due = checkoutDue(saleNet, deposit)
    expect(saleNet).toBe(105)
    expect(deposit).toBe(40)
    expect(due).toBe(145)
    expect(checkoutOutstanding(due, 80)).toBe(65)
    expect(checkoutOutstanding(due, 145)).toBe(0)
    expect(checkoutOutstanding(due, 200)).toBe(0)
  })

  it('clamps other charge to non-negative', () => {
    expect(checkoutOtherCharge(-12)).toBe(0)
    expect(checkoutOtherCharge(12)).toBe(12)
    expect(checkoutSaleNet(100, checkoutOtherCharge(0))).toBe(100)
  })
})
