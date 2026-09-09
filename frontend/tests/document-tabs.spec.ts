import { describe, expect, it } from 'vitest'
import type { ModuleConfig } from '../app/config/modules'
import { stockModules } from '../app/config/stock-modules'
import { moduleDocumentTabs } from '../app/utils/module/document-tabs'

function moduleFixture(overrides: Partial<ModuleConfig> = {}): ModuleConfig {
  return {
    path: '/records',
    title: 'Records',
    titleKm: 'Records',
    singular: 'Record',
    singularKm: 'Record',
    description: '',
    descriptionKm: '',
    icon: 'i-lucide-file',
    group: 'test',
    permission: 'records.view',
    collection: 'records',
    titleField: 'name',
    columns: [],
    fields: [
      { key: 'name', label: 'Name', section: 'General', type: 'text' },
      { key: 'status', label: 'Status', section: 'Status', type: 'select', options: ['Active', 'Inactive'] },
    ],
    statuses: ['Active', 'Inactive'],
    ...overrides,
  }
}

describe('product document tabs (AGENT_STOCK_POS §3)', () => {
  const productModule = stockModules.find(item => item.collection === 'products')!

  it('has a single General tab — no Pricing / Expire / UOM tabs', () => {
    const tabs = moduleDocumentTabs(productModule)
    expect(tabs.map(tab => tab.id)).toEqual(['general'])
    expect(tabs.map(tab => tab.labelKey)).toEqual(['app.stock.tabGeneral'])
  })

  it('keeps General to the allowed product field contract', () => {
    const tabs = moduleDocumentTabs(productModule)
    const generalKeys = tabs[0]!.sections.flatMap(section =>
      section.fields.map(field => field.key))
    expect(generalKeys).toContain('code')
    expect(generalKeys).toContain('name')
    expect(generalKeys).toContain('categoryId')
    expect(generalKeys).toContain('brandId')
    expect(generalKeys).toContain('salePrice')
    expect(generalKeys).toContain('description')
    // Barcode / Purchase Price / Profit % / Current Stock are not editable on
    // the product document — purchase price and stock come from purchases
    // (Stock In dialog).
    expect(generalKeys).not.toContain('barcode')
    expect(generalKeys).not.toContain('costPrice')
    expect(generalKeys).not.toContain('profitPercent')
    expect(generalKeys).not.toContain('quantity')
    expect(generalKeys).not.toContain('uomId')
    expect(generalKeys).not.toContain('supplierId')
    expect(generalKeys).not.toContain('uomConversions')
    expect(generalKeys).not.toContain('expiryTracking')
    expect(generalKeys).not.toContain('expiryDate')
  })

  it('does not expose UOM or expiry columns on the stock module', () => {
    const columnKeys = productModule.columns.map(col => col.key)
    expect(columnKeys).not.toContain('uomSymbol')
    expect(columnKeys).not.toContain('expiryDate')
    expect(columnKeys).toContain('salePrice')
    expect(columnKeys).toContain('costPrice')
  })
})

describe('document lifecycle status', () => {
  it('omits status fields and their now-empty sections from generated forms', () => {
    const tabs = moduleDocumentTabs(moduleFixture())
    const sections = tabs.flatMap(tab => tab.sections)
    const fields = sections.flatMap(section => section.fields)

    expect(fields.some(field => field.key === 'status')).toBe(false)
    expect(sections.some(section => section.id === 'status')).toBe(false)
    expect(fields.some(field => field.key === 'name')).toBe(true)
  })

  it('omits Active/Inactive status from the user form', () => {
    const tabs = moduleDocumentTabs(moduleFixture({
      path: '/administration/users',
      collection: 'users',
      permission: 'admin.users.view',
    }))
    const fields = tabs.flatMap(tab => tab.sections).flatMap(section => section.fields)
    expect(fields.some(field => field.key === 'status')).toBe(false)
  })
})
