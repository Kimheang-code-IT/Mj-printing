import { describe, expect, it } from 'vitest'
import { adaptPurchaseReportRow, adaptSaleReportRow, flattenPurchaseReportLines, flattenSaleReportLines } from '../app/utils/reports/line-rows'

describe('sale/purchase report invoice rows', () => {
  it('builds one sales row per invoice with header totals', () => {
    const rows = flattenSaleReportLines(
      [{
        id: 'sale1',
        saleNo: 'SALE-01001',
        date: '2026-09-01',
        customerId: 'cus1',
        customer: 'Nita Sok',
        subtotal: 40,
        discount: 2,
        otherCharge: 0,
        total: 38,
        paidAmount: 20,
        remaining: 18,
        paymentMethod: 'Credit',
        status: 'Partial',
        cashier: 'Dara Kim',
        items: [
          {
            id: 'line1',
            name: 'Banner',
            quantity: 2,
            height: 1.2,
            width: 0.8,
            squareMeter: 1.92,
            price: 10,
            total: 19.2,
          },
          {
            id: 'line2',
            name: 'Sticker',
            quantity: 1,
            price: 20.8,
            total: 20.8,
          },
        ],
      }],
      [{ id: 'cus1', phone: '012 777 001', address: 'Toul Kork' }],
    )

    expect(rows).toHaveLength(1)
    expect(rows[0]).toMatchObject({
      id: 'sale1',
      invoiceNo: 'SALE-01001',
      customer: 'Nita Sok',
      phone: '012 777 001',
      address: 'Toul Kork',
      itemCount: 2,
      subtotal: 40,
      discount: 2,
      total: 38,
      paidAmount: 20,
      remainingAmount: 18,
      paymentMethod: 'Credit',
      status: 'Partial',
      cashier: 'Dara Kim',
    })
  })

  it('builds one purchase row per invoice (no Other Cost column)', () => {
    const rows = flattenPurchaseReportLines(
      [{
        id: 'sin1',
        purchaseNo: 'PIN-00080',
        date: '2026-09-02',
        supplierId: 'sup1',
        supplier: 'Angkor Wholesale Co.',
        subtotal: 80,
        otherCost: 5,
        discount: 0,
        total: 85,
        paidAmount: 40,
        remaining: 45,
        status: 'Partial',
        note: 'Rush',
        items: [{
          id: 'pline1',
          name: 'Vinyl',
          quantity: 1,
          height: 2,
          width: 1,
          squareMeter: 1.6,
          price: 5,
          total: 8,
        }, {
          id: 'pline2',
          name: 'Roll',
          quantity: 2,
          price: 36,
          total: 72,
        }],
      }],
      [{ id: 'sup1', phone: '012 345 678', address: 'St. 271' }],
    )

    expect(rows).toHaveLength(1)
    expect(rows[0]).toMatchObject({
      invoiceNo: 'PIN-00080',
      supplier: 'Angkor Wholesale Co.',
      phone: '012 345 678',
      itemCount: 2,
      subtotal: 80,
      total: 85,
      paidAmount: 40,
      remainingAmount: 45,
      note: 'Rush',
    })
    // Other Cost was removed from the Purchase Report completely — the
    // value still feeds the grand total but is never a report column/field.
    expect(rows[0]).not.toHaveProperty('otherCost')
  })

  it('maps backend snake_case sales report rows to invoice UI columns', () => {
    const row = adaptSaleReportRow({
      sale_id: 'sale-1',
      invoice_no: 'INV-1',
      sale_date: '2026-09-01',
      customer_name: 'Walk-in',
      customer_phone: '011',
      customer_address: 'PP',
      item_count: 3,
      subtotal: 30,
      discount_amount: 1,
      other_charge: 0,
      grand_total: 29,
      paid_amount: 29,
      debt_amount: 0,
      payment_method: 'CASH',
      payment_status: 'PAID',
      cashier_name: 'Sokha',
    })
    expect(row).toMatchObject({
      id: 'sale-1',
      invoiceNo: 'INV-1',
      customer: 'Walk-in',
      itemCount: 3,
      subtotal: 30,
      discount: 1,
      total: 29,
      paidAmount: 29,
      remainingAmount: 0,
      paymentMethod: 'CASH',
      cashier: 'Sokha',
    })
  })

  it('maps backend purchase report rows to invoice UI columns', () => {
    const row = adaptPurchaseReportRow({
      transaction_id: 'p-1',
      document_no: 'PIN-1',
      supplier_name: 'Mekong',
      item_count: 2,
      subtotal: 20,
      other_cost: 2,
      discount: 0,
      grand_total: 22,
      paid_amount: 5,
      remaining_debt: 17,
      status: 'PARTIAL',
      note: 'OK',
    })
    expect(row).toMatchObject({
      id: 'p-1',
      invoiceNo: 'PIN-1',
      supplier: 'Mekong',
      itemCount: 2,
      subtotal: 20,
      total: 22,
      paidAmount: 5,
      remainingAmount: 17,
      note: 'OK',
    })
    expect(row).not.toHaveProperty('otherCost')
  })
})
