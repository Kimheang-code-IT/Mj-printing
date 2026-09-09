import { describe, expect, it } from 'vitest'
import { ROLE_DOCUMENT_TYPES } from '../app/utils/role/permissions'
import { appModules } from '../app/config/modules'

describe('navigation allowlist (AGENT_STOCK_POS)', () => {
  it('does not register Delivery Note or UOM modules', () => {
    const paths = appModules.map(module => module.path)
    expect(paths).not.toContain('/delivery-notes')
    expect(paths).not.toContain('/setup/uoms')
    expect(appModules.some(module => module.collection === 'uoms')).toBe(false)
    expect(appModules.some(module => module.collection === 'deliveryNotes')).toBe(false)
  })

  it('does not expose Delivery Note or UOM in the role permission matrix', () => {
    const values = ROLE_DOCUMENT_TYPES.map(row => row.value)
    expect(values).not.toContain('uoms')
    expect(values).not.toContain('delivery')
  })

  it('does not register Stock Adjustments, Damaged Stock, or Stock Movements pages', () => {
    const paths = appModules.map(module => module.path)
    expect(paths).not.toContain('/stock-adjustments')
    expect(paths).not.toContain('/damaged-stock')
    expect(paths).not.toContain('/stock/movements')
    expect(paths).toContain('/stock')
  })

  it('registers Purchases, Sales, and report modules', () => {
    const paths = appModules.map(module => module.path)
    expect(paths).not.toContain('/purchases')
    expect(paths).not.toContain('/sales')
    expect(paths).not.toContain('/returns')
    expect(paths).not.toContain('/reports/stock')
    expect(paths).not.toContain('/reports/profit')
    expect(paths).not.toContain('/reports/customer-statement')
    expect(paths).not.toContain('/reports/supplier-statement')
    expect(paths).toContain('/reports/sales')
    expect(paths).toContain('/reports/purchases')
    expect(paths).not.toContain('/reports/customers')
    expect(paths).not.toContain('/reports/suppliers')
    expect(paths).toContain('/reports/customer-debts')
    expect(paths).toContain('/reports/supplier-debts')
    expect(paths).not.toContain('/customer-debts')
    expect(paths).not.toContain('/supplier-debts')
  })

  it('exposes purchases and stock_ops in the role permission matrix', () => {
    const values = ROLE_DOCUMENT_TYPES.map(row => row.value)
    expect(values).toContain('purchases')
    expect(values).toContain('stock_ops')
  })
})
