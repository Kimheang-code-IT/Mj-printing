import type { ModuleField, ModuleConfig, ModuleTable } from './modules'
import { PAYMENT_METHODS } from './pos-options'
import { ACTIVE_STATUS } from './shared-options'

/**
 * Stock & POS master-data and report modules. Registered into the
 * route-module lookup by `modules.ts` and rendered by the generic
 * workspace/document components.
 */

const f = (
  key: string,
  label: string,
  section = 'General Information',
  type: ModuleField['type'] = 'text',
  options?: ModuleField['options'],
  extra: Partial<ModuleField> = {},
): ModuleField => ({ key, label, labelKm: label, section, sectionKm: section, type, options, ...extra })

const col = (key: string, label: string, extra: Partial<ModuleField> = {}): ModuleField => ({
  key,
  label,
  labelKm: label,
  ...extra,
})

function createModule(partial: Omit<ModuleConfig, 'canCreate' | 'titleKm' | 'singularKm' | 'descriptionKm'> & {
  canCreate?: boolean
  titleKm?: string
  singularKm?: string
  descriptionKm?: string
}): ModuleConfig {
  return {
    ...partial,
    canCreate: partial.readOnly ? false : partial.canCreate !== false,
    kind: partial.kind || 'standard',
    titleKm: partial.titleKm || partial.title,
    singularKm: partial.singularKm || partial.singular,
    descriptionKm: partial.descriptionKm || partial.description,
  }
}

const DEBT_STATUS = ['UNPAID', 'PARTIAL', 'PAID'] as const
const INVOICE_STATUS = ['Paid', 'Partial', 'Unpaid', 'Completed'] as const
const ACTIVE_INACTIVE = ACTIVE_STATUS

export const stockModules: ModuleConfig[] = [
  createModule({
    path: '/setup/categories',
    title: 'Categories',
    singular: 'Category',
    description: 'Product categories used to group stock items.',
    icon: 'i-lucide-tags',
    group: 'master',
    permission: 'categories.view',
    collection: 'categories',
    titleField: 'name',
    columns: [
      col('code', 'Code'),
      col('name', 'Name'),
      col('description', 'Description'),
      col('productCount', 'Products'),
      col('status', 'Status'),
    ],
    fields: [
      f('name', 'Name', 'General Information', 'text', undefined, { required: true }),
      f('code', 'Code', 'General Information', 'text', undefined, { help: 'Unique short code. Leave blank to let the system generate one.' }),
      f('description', 'Description', 'General Information', 'textarea', undefined, { colSpan: 2 }),
      f('status', 'Status', 'Status', 'select', ACTIVE_INACTIVE, { required: true }),
    ],
    filters: [
      f('status', 'Status', '', 'select', ACTIVE_INACTIVE),
    ],
  }),
  createModule({
    path: '/setup/brands',
    title: 'Brands',
    singular: 'Brand',
    description: 'Product brands used to group stock items by manufacturer.',
    icon: 'i-lucide-award',
    group: 'master',
    permission: 'brand.view',
    collection: 'brands',
    titleField: 'name',
    columns: [
      col('code', 'Code'),
      col('name', 'Name'),
      col('description', 'Description'),
      col('productCount', 'Products'),
      col('status', 'Status'),
    ],
    fields: [
      f('name', 'Brand Name', 'General Information', 'text', undefined, { required: true }),
      f('code', 'Code', 'General Information', 'text', undefined, { help: 'Unique short code. Leave blank to let the system generate one.' }),
      f('logo', 'Logo', 'General Information', 'image', undefined, { help: 'Optional brand logo.' }),
      f('description', 'Description', 'General Information', 'textarea', undefined, { colSpan: 2 }),
      f('status', 'Status', 'Status', 'select', ACTIVE_INACTIVE, { required: true }),
    ],
    filters: [
      f('status', 'Status', '', 'select', ACTIVE_INACTIVE),
    ],
  }),
  createModule({
    path: '/stock',
    title: 'Stock',
    singular: 'Product',
    description: 'Products with current stock, cost and pricing.',
    icon: 'i-lucide-package',
    group: 'master',
    permission: 'products.view',
    collection: 'products',
    titleField: 'name',
    documentForm: 'product',
    columns: [
      col('imageUrl', 'Image', { labelKm: 'រូបភាព', type: 'image' }),
      col('code', 'Code'),
      col('name', 'Product'),
      col('category', 'Category'),
      col('brand', 'Brand', { labelKm: 'ម៉ាក' }),
      col('costPrice', 'Purchase Price'),
      col('salePrice', 'Sale Price'),
      col('stockInQty', 'Stock In'),
      col('stockOutQty', 'Stock Out'),
      col('damageQty', 'Damaged Stock'),
      col('quantity', 'Current Stock'),
      col('status', 'Status'),
    ],
    // Product document form contract: identity + pricing only. Barcode,
    // Purchase Price, Profit % and Current Stock are NOT editable here —
    // purchase price / stock come from purchases (Stock In dialog).
    fields: [
      f('code', 'Product Code', 'General Information', 'text', undefined, { help: 'Unique SKU. Leave blank to auto-generate.' }),
      f('name', 'Product Name', 'General Information', 'text', undefined, { required: true, labelKey: 'app.modules.products.fields.name' }),
      f('categoryId', 'Category', 'General Information', 'select', undefined, { required: true, optionsCollection: 'categories' }),
      f('brandId', 'Brand', 'General Information', 'select', undefined, { optionsCollection: 'brands' }),
      f('imageUrl', 'Image', 'General Information', 'image'),
      f('salePrice', 'Sale Price', 'General Information', 'number', undefined, { required: true }),
      f('description', 'Description / Note', 'General Information', 'textarea', undefined, { colSpan: 2 }),
      f('status', 'Status', 'Status', 'select', ACTIVE_INACTIVE, { required: true }),
    ],
    filters: [
      f('category', 'Category', '', 'select'),
      f('brand', 'Brand', '', 'select'),
      f('status', 'Status', '', 'select', ACTIVE_INACTIVE),
    ],
  }),
  createModule({
    path: '/setup/suppliers',
    title: 'Suppliers',
    singular: 'Supplier',
    description: 'Supplier master records. Search purchase and debt history on Reports.',
    icon: 'i-lucide-truck',
    group: 'master',
    permission: 'suppliers.view',
    collection: 'suppliers',
    titleField: 'name',
    columns: [
      col('code', 'Code'),
      col('name', 'Supplier'),
      col('phone', 'Phone'),
      col('location', 'Address'),
      col('totalDebt', 'Current Debt'),
      col('status', 'Status'),
    ],
    fields: [
      f('code', 'Supplier Code', 'General Information', 'text', undefined, { help: 'Unique code. Leave blank to auto-generate.' }),
      f('name', 'Supplier Name', 'General Information', 'text', undefined, { required: true }),
      f('phone', 'Phone', 'General Information', 'text'),
      f('location', 'Address', 'General Information', 'textarea'),
      f('status', 'Status', 'Status', 'select', ACTIVE_INACTIVE, { required: true }),
    ],
    filters: [
      f('status', 'Status', '', 'select', ACTIVE_INACTIVE),
    ],
  }),
  createModule({
    path: '/setup/customers',
    title: 'Customers',
    singular: 'Customer',
    description: 'Customer master records. Search sales, debt and statement history on Reports.',
    icon: 'i-lucide-users',
    group: 'master',
    permission: 'customers.view',
    collection: 'customers',
    titleField: 'name',
    columns: [
      col('code', 'Code'),
      col('name', 'Customer'),
      col('phone', 'Phone'),
      col('location', 'Address'),
      col('debtBalance', 'Current Debt'),
      col('status', 'Status'),
    ],
    fields: [
      f('code', 'Customer Code', 'General Information', 'text', undefined, { help: 'Unique code. Leave blank to auto-generate.' }),
      f('name', 'Customer Name', 'General Information', 'text', undefined, { required: true }),
      f('phone', 'Phone', 'General Information', 'text'),
      f('location', 'Address', 'General Information', 'textarea'),
      f('status', 'Status', 'Status', 'select', ACTIVE_INACTIVE, { required: true }),
    ],
    filters: [
      f('status', 'Status', '', 'select', ACTIVE_INACTIVE),
    ],
  }),

  /* ------------------------- Reports ------------------------- */

  createModule({
    path: '/reports/sales',
    title: 'Sales Report',
    singular: 'Sale',
    description: 'One row per sale invoice with customer, payment and totals.',
    icon: 'i-lucide-receipt',
    group: 'reports',
    permission: 'reports.view',
    collection: 'saleReportLines',
    titleField: 'invoiceNo',
    kind: 'reports',
    readOnly: true,
    tableOnly: true,
    columns: [
      col('invoiceNo', 'Invoice No'),
      col('date', 'Date', { type: 'date' }),
      col('customer', 'Customer'),
      col('phone', 'Phone'),
      col('address', 'Address'),
      col('itemCount', 'Items'),
      col('subtotal', 'Subtotal'),
      col('total', 'Grand Total'),
      col('paidAmount', 'Paid'),
      col('remainingAmount', 'Balance'),
      col('paymentMethod', 'Payment Method'),
      col('status', 'Status'),
      col('cashier', 'Cashier'),
    ],
    fields: [],
    filters: [
      f('customer', 'Customer', '', 'select'),
      f('status', 'Status', '', 'select', INVOICE_STATUS),
      f('paymentMethod', 'Payment Method', '', 'select', [...PAYMENT_METHODS]),
    ],
  }),
  createModule({
    path: '/reports/purchases',
    title: 'Purchase Report',
    singular: 'Purchase',
    description: 'One row per purchase invoice with supplier, payment and totals.',
    icon: 'i-lucide-shopping-cart',
    group: 'reports',
    permission: 'reports.view',
    collection: 'purchaseReportLines',
    titleField: 'invoiceNo',
    kind: 'reports',
    tableOnly: true,
    canCreate: true,
    columns: [
      col('invoiceNo', 'Invoice No'),
      col('date', 'Date', { type: 'date' }),
      col('supplier', 'Supplier'),
      col('phone', 'Phone'),
      col('address', 'Address'),
      col('itemCount', 'Items'),
      col('subtotal', 'Subtotal'),
      col('total', 'Grand Total'),
      col('paidAmount', 'Paid'),
      col('remainingAmount', 'Balance'),
      col('status', 'Status'),
      col('note', 'Note'),
    ],
    fields: [],
    filters: [
      f('supplier', 'Supplier', '', 'select'),
      f('status', 'Status', '', 'select', INVOICE_STATUS),
    ],
  }),
  createModule({
    path: '/reports/customer-debts',
    title: 'Customer Debt Report',
    singular: 'Customer Debt',
    description: 'Invoice-level customer debts with invoice total, paid and remaining amounts.',
    icon: 'i-lucide-hand-coins',
    group: 'reports',
    permission: 'reports.view',
    collection: 'customerDebts',
    titleField: 'invoiceNo',
    kind: 'reports',
    readOnly: true,
    tableOnly: true,
    columns: [
      col('date', 'Date', { type: 'date' }),
      col('invoiceNo', 'Invoice No.'),
      col('customer', 'Customer'),
      col('invoiceTotal', 'Invoice Total'),
      col('paidAmount', 'Paid Amount'),
      col('remainingAmount', 'Remaining Amount'),
      col('dueDate', 'Due Date', { type: 'date' }),
      col('status', 'Status'),
    ],
    fields: [
      f('date', 'Date', 'Debt', 'date'),
      f('invoiceNo', 'Invoice No.', 'Debt', 'text', undefined, { computed: true }),
      f('customer', 'Customer', 'Debt', 'text', undefined, { computed: true }),
      f('invoiceTotal', 'Invoice Total', 'Debt', 'number', undefined, { computed: true }),
      f('paidAmount', 'Paid Amount', 'Debt', 'number', undefined, { computed: true }),
      f('remainingAmount', 'Remaining Amount', 'Debt', 'number', undefined, { computed: true }),
      f('dueDate', 'Due Date', 'Debt', 'date'),
    ],
    filters: [
      f('customer', 'Customer', '', 'select'),
      f('status', 'Status', '', 'select', DEBT_STATUS),
    ],
  }),
  createModule({
    path: '/reports/supplier-debts',
    title: 'Supplier Debt Report',
    singular: 'Supplier Debt',
    description: 'Document-level supplier debts with purchase total, paid and remaining amounts.',
    icon: 'i-lucide-landmark',
    group: 'reports',
    permission: 'reports.view',
    collection: 'supplierDebts',
    titleField: 'purchaseNo',
    kind: 'reports',
    readOnly: true,
    tableOnly: true,
    columns: [
      col('date', 'Date', { type: 'date' }),
      col('purchaseNo', 'Invoice No. / Purchase No.'),
      col('supplier', 'Supplier'),
      col('totalAmount', 'Total Amount'),
      col('paidAmount', 'Paid Amount'),
      col('remainingAmount', 'Remaining Amount'),
      col('dueDate', 'Due Date', { type: 'date' }),
      col('status', 'Status'),
    ],
    fields: [
      f('date', 'Date', 'Debt', 'date'),
      f('purchaseNo', 'Invoice No. / Purchase No.', 'Debt', 'text', undefined, { computed: true }),
      f('supplier', 'Supplier', 'Debt', 'text', undefined, { computed: true }),
      f('totalAmount', 'Total Amount', 'Debt', 'number', undefined, { computed: true }),
      f('paidAmount', 'Paid Amount', 'Debt', 'number', undefined, { computed: true }),
      f('remainingAmount', 'Remaining Amount', 'Debt', 'number', undefined, { computed: true }),
      f('dueDate', 'Due Date', 'Debt', 'date'),
    ],
    filters: [
      f('supplier', 'Supplier', '', 'select'),
      f('status', 'Status', '', 'select', DEBT_STATUS),
    ],
  }),

]

/**
 * Purchase / Stock In line table (AGENT_STOCK_POS §6) — reused by the
 * `/reports/purchases/new` form. Column order: No (row number, rendered by
 * AppLineTable) · Product · Height · Width · m² · Qty · Unit price · Amount.
 * `squareMeter` + `amount` are recomputed by `AppLineTable` (purchaseLines
 * case); product options are injected by the caller from the products
 * collection.
 */
export function purchaseLinesTable(
  productItems: Array<{ label: string, value: string }>,
): ModuleTable {
  return {
    key: 'purchaseLines',
    title: 'Purchase lines',
    titleKm: 'ជួរទំនិញ',
    addLabelKey: 'app.purchase.addLine',
    columns: [
      { key: 'productId', label: 'Product', labelKm: 'ផលិតផល', labelKey: 'app.pos.product', type: 'select', optionItems: productItems, required: true },
      { key: 'height', label: 'Height', labelKm: 'កម្ពស់', labelKey: 'app.purchase.height', type: 'number' },
      { key: 'width', label: 'Width', labelKm: 'ទទឹង', labelKey: 'app.purchase.width', type: 'number' },
      { key: 'squareMeter', label: 'm²', labelKm: 'm²', labelKey: 'app.purchase.squareMeter', type: 'number', computed: true },
      { key: 'quantity', label: 'Qty', labelKm: 'បរិមាណ', labelKey: 'app.fields.quantity', type: 'number', required: true },
      { key: 'purchasePrice', label: 'Unit price', labelKm: 'តម្លៃឯកតា', labelKey: 'app.purchase.purchasePrice', type: 'number', required: true },
      { key: 'amount', label: 'Amount', labelKm: 'ចំនួនទឹកប្រាក់', labelKey: 'app.fields.amount', type: 'number', computed: true },
    ],
  }
}