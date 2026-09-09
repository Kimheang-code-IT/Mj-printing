<script setup lang="ts">
import type { DropdownMenuItem, TableColumn, TableRow } from '@nuxt/ui'
import type { PaginationState } from '@tanstack/vue-table'
import { h } from 'vue'
import { TableAppTableCellImage, UBadge, ULink } from '#components'
import { useAppHeader } from '~/composables/layout/useAppHeader'
import { useConfirm } from '~/composables/common/useConfirm'
import { usePageSeo } from '~/composables/usePageSeo'
import {
  formatModuleCell,
  formatMoney,
  moduleStatusBadge,
  useModuleLabel,
  useModuleRoute,
} from '~/composables/module/useModule'
import { useAppLocalization } from '~/composables/settings/useAppLocalization'
import type { AppRecord } from '~/config/admin-seed'
import { appModules, type ModuleSelectOption } from '~/config/modules'
import { STOCK_OPERATION_META, STOCK_OPERATION_TYPES, type StockHistoryKind, type StockOperationType } from '~/config/pos-options'
import { isMoneyKey, isNumericKey } from '~/utils/module/field-keys'
import { limitFilterSelects, parseFilterQuery } from '~/utils/filter/values'
import { isFilterValueActive } from '~/utils/filter/select-ui'
import { listTableRowMetaColumn, listTableSelectColumn } from '~/utils/table/list-columns'
import { listTablePageSummary, listTableSelectedIds } from '~/utils/table/list-table'
import { documentSequenceTypeLabel } from '~/utils/document-sequences'
import { normalizeAuditLog, resolveAuditEntityPath } from '~/utils/module/audit-logs'
import { usePosCommands } from '~/repositories/index'
import { productImageUrl } from '~/utils/pos/cart'
import { roundQty } from '~/utils/stock/line-calc'
import { documentHasReturnableLines, type ReturnDocumentKind } from '~/utils/reports/returns'
import type { DebtPaymentKind } from '~/components/reports/DebtPaymentDialog.vue'

const { module, route } = useModuleRoute()
const store = useAppDataStore()
const auth = useAuthStore()
const { t } = useI18n()
const { fieldLabel, moduleTitle, moduleSingular } = useModuleLabel()
const { setTitle, setBreadcrumbs, clear } = useAppHeader()
const { confirm } = useConfirm()
const toast = useToast()
const posCommands = usePosCommands()
const { localization } = useAppLocalization()

const q = ref('')
const pagination = ref<PaginationState>({ pageIndex: 0, pageSize: 20 })
const filters = reactive<Record<string, string[]>>({})
const rowSelection = ref<Record<string, boolean>>({})
const busyId = ref('')
const preferences = usePreferencesStore()
const stockOperationOpen = ref(false)
const stockOperationType = ref<StockOperationType>('stock_in')
const stockOperationProduct = ref('')
const stockOperationQuantity = ref<number | undefined>()
const stockOperationNote = ref('')
const stockOperationBusy = ref(false)
const stockOperationUnitCost = ref<number | undefined>()
const dateFrom = ref('')
const dateTo = ref('')
const returnOpen = ref(false)
const returnKind = ref<ReturnDocumentKind>('sale')
const returnDocument = ref<AppRecord | null>(null)
const returnBusy = ref(false)
const debtPayOpen = ref(false)
const debtPayKind = ref<DebtPaymentKind>('customer')
const debtPayRow = ref<AppRecord | null>(null)
const debtPayBusy = ref(false)

const current = computed(() => module.value)
const pending = computed(() => Boolean(current.value && store.isLoading(current.value.collection)))
const isTableOnly = computed(() => Boolean(current.value?.tableOnly))
/** Table-only reports that still need row actions (Return / Pay). */
const showRowActions = computed(() => {
  if (!isTableOnly.value) return true
  const collection = current.value?.collection
  if (collection === 'sales') return canReturnSale.value
  if (collection === 'stockIns') return canReturnPurchase.value
  if (collection === 'customerDebts') return canPayCustomerDebt.value
  if (collection === 'supplierDebts') return canPaySupplierDebt.value
  return false
})
const permissionPrefix = computed(() => current.value?.permission.replace(/\.view$/, '') || '')
const canCreate = computed(() => {
  if (current.value?.path === '/reports/purchases' && auth.canAccessPage('purchases.create')) return true
  return Boolean(
    current.value?.canCreate
    && !current.value.readOnly
    && auth.canAccessPage(`${permissionPrefix.value}.create`),
  )
})
const canEdit = computed(() => Boolean(
  current.value
  && !current.value.readOnly
  && auth.canAccessPage(`${permissionPrefix.value}.edit`),
))
const canDelete = computed(() => Boolean(
  current.value
  && !current.value.readOnly
  && auth.canAccessPage(`${permissionPrefix.value}.delete`),
))
const canOperate = computed(() => Boolean(
  current.value
  && !current.value.readOnly
  && (auth.canAccessPage(`${permissionPrefix.value}.operate`) || auth.canAccessPage(`${permissionPrefix.value}.edit`)),
))
const canReturnSale = computed(() =>
  auth.canAccessPage('pos.operate')
  || auth.canAccessPage('pos.create')
  || auth.canAccessPage('returns.operate')
  || auth.canAccessPage('returns.create'),
)
const canReturnPurchase = computed(() =>
  auth.canAccessPage('products.edit')
  || auth.canAccessPage('products.operate')
  || auth.canAccessPage('products.create')
  || auth.canAccessPage('purchases.edit')
  || auth.canAccessPage('purchases.create')
  || auth.canAccessPage('purchases.operate'),
)
const canPayCustomerDebt = computed(() =>
  auth.canAccessPage('customers.edit')
  || auth.canAccessPage('customers.operate')
  || auth.canAccessPage('reports.view')
  || auth.canAccessPage('ALL_PAGES'),
)
const canPaySupplierDebt = computed(() =>
  auth.canAccessPage('suppliers.edit')
  || auth.canAccessPage('suppliers.operate')
  || auth.canAccessPage('reports.view')
  || auth.canAccessPage('ALL_PAGES'),
)
const deactivationOnly = computed(() => current.value?.group === 'master' || current.value?.collection === 'documentSequences')
const dateField = computed(() => {
  const fields = current.value?.fields || []
  return fields.find(field => field.type === 'date' || field.type === 'datetime' || field.key === 'date' || /date$/i.test(field.key))?.key
    || current.value?.columns.find(column => /date/i.test(column.key))?.key
})

const result = computed(() => {
  if (!current.value) return { rows: [], total: 0, all: [] }
  const queried = store.query(current.value, {
    q: q.value,
    filters,
    paginate: false,
    dateField: dateField.value,
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
  })
  if (current.value.collection === 'products') {
    const all = queried.all.map(row => {
      const quantity = Number(row.quantity || 0)
      const costPrice = Number(row.costPrice || 0)
      return {
        ...row,
        brand: String(row.brand || brandById(String(row.brandId))?.name || ''),
        stockValue: Math.round(quantity * costPrice * 100) / 100,
      }
    })
    return { rows: all, total: queried.total, all }
  }
  if (current.value.collection === 'brands') {
    const all = queried.all.map(row => ({
      ...row,
      productCount: brandProductCounts.value.get(String(row.id)) ?? 0,
    }))
    return { rows: all, total: queried.total, all }
  }
  return queried
})

/** Brand lookup for product display enrichment. */
const brandById = (id: string) => store.list('brands').find(brand => String(brand.id) === id)

/** Products linked to each brand — used to keep the brand list informative. */
const brandProductCounts = computed(() => {
  const counts = new Map<string, number>()
  for (const row of store.list('products')) {
    const brandId = String(row.brandId ?? '')
    if (!brandId) continue
    counts.set(brandId, (counts.get(brandId) || 0) + 1)
  }
  return counts
})

/** Quantity column → history dialog movement-kind filter.
 *  Current Stock (`quantity`) is display-only — it never opens the dialog. */
const STOCK_QTY_KIND: Record<string, StockHistoryKind> = {
  stockInQty: 'stock_in',
  stockOutQty: 'stock_out',
  damageQty: 'damage',
}

/** Price column → price dialog (spec: Cost Price / Sale Price cells). */
const STOCK_PRICE_KIND = {
  costPrice: 'cost',
  salePrice: 'sale',
} as const

type StockPriceKind = (typeof STOCK_PRICE_KIND)[keyof typeof STOCK_PRICE_KIND]

const stockHistoryOpen = ref(false)
const stockHistoryProduct = ref<AppRecord | null>(null)
const stockHistoryKind = ref<StockHistoryKind>('stock_in')
const stockHistoryReloadKey = ref(0)

/** Purchase-driven Stock In dialog (Stock list row menu + history add). */
const stockInOpen = ref(false)
const stockInProduct = ref<AppRecord | null>(null)

function openStockIn(row: AppRecord) {
  stockInProduct.value = row
  stockInOpen.value = true
}

function onStockInSaved() {
  void store.fetchList('products')
  void store.fetchList('stockMovements')
  if (stockHistoryOpen.value) stockHistoryReloadKey.value += 1
}

function openStockHistory(row: Record<string, unknown>, kind: StockHistoryKind) {
  stockHistoryProduct.value = row as AppRecord
  stockHistoryKind.value = kind
  stockHistoryOpen.value = true
}

function onStockHistorySaved() {
  void store.fetchList('products')
  void store.fetchList('stockMovements')
  stockHistoryReloadKey.value += 1
}

const costPriceOpen = ref(false)
const salePriceOpen = ref(false)
const priceProduct = ref<AppRecord | null>(null)

function openPriceDialog(row: Record<string, unknown>, kind: StockPriceKind) {
  priceProduct.value = row as AppRecord
  if (kind === 'cost') costPriceOpen.value = true
  else salePriceOpen.value = true
}
const selectedIds = computed(() => listTableSelectedIds(rowSelection.value))

const hasActiveFilters = computed(() => Boolean(
  Object.values(filters).some(value => isFilterValueActive(value))
  || isFilterValueActive(dateFrom.value)
  || isFilterValueActive(dateTo.value),
))

const visibleFilters = computed(() => limitFilterSelects(
  current.value?.filters || [],
  Boolean(dateField.value),
  filter => filter.key === 'status' || filter.key === 'workflowStatus',
))

watch(current, (value) => {
  if (!value) return
  setTitle(moduleTitle(value))
  setBreadcrumbs([{ label: moduleTitle(value) }])
  rowSelection.value = {}
  for (const key of Object.keys(filters)) Reflect.deleteProperty(filters, key)
  for (const filter of value.filters || []) {
    filters[filter.key] = parseFilterQuery(route.query[filter.key])
  }
}, { immediate: true })

onBeforeUnmount(clear)

usePageSeo({
  title: () => current.value ? moduleTitle(current.value) : t('app.pages.dashboard'),
})

watch([q, filters, dateFrom, dateTo], () => {
  rowSelection.value = {}
  pagination.value = { ...pagination.value, pageIndex: 0 }
}, { deep: true })

// Client-only: reload list data after mount and when filters change. Mock
// mode fetches too — the mock repository serves the in-memory seed cheaply,
// so loading/error stays repository-driven in every mode.
function reloadModuleData() {
  if (!import.meta.client || !current.value) return
  void store.fetchList(current.value.collection, {
    q: q.value || undefined,
    startDate: dateFrom.value || undefined,
    endDate: dateTo.value || undefined,
  })
  if (current.value.collection === 'products') {
    void store.fetchList('stockMovements')
    void store.fetchList('brands')
  }
  if (current.value.collection === 'brands') void store.fetchList('products')
}

onMounted(() => {
  reloadModuleData()
})

watch([current, q, dateFrom, dateTo], () => {
  reloadModuleData()
})

function recordPath(id: unknown) {
  if (!current.value) return '/'
  return `${current.value.path}/${id}`
}

function fieldTypeForKey(key: string) {
  return current.value?.fields.find(field => field.key === key)?.type
}

function cellText(row: Record<string, unknown>, key: string) {
  const source = current.value?.collection === 'auditLogs' ? normalizeAuditLog(row as AppRecord) : row
  if (current.value?.collection === 'documentSequences' && key === 'documentType') {
    const code = String(source[key] || '')
    const label = documentSequenceTypeLabel(code)
    return label === code ? code : `${label} (${code})`
  }
  return formatModuleCell(
    source[key],
    key,
    isMoneyKey(key) ? String(source.currency || preferences.currency) : undefined,
    fieldTypeForKey(key),
  )
}

function auditEntityLinkFor(row: Record<string, unknown>) {
  if (current.value?.collection !== 'auditLogs') return ''
  return resolveAuditEntityPath(
    normalizeAuditLog(row as AppRecord),
    appModules,
    collection => store.list(collection),
    permission => auth.canAccessPage(permission),
  )
}

const pageSummary = computed(() =>
  listTablePageSummary(t, result.value.total, pagination.value),
)

const lineReportTotals = computed(() => {
  const collection = current.value?.collection
  if (collection !== 'saleReportLines' && collection !== 'purchaseReportLines') return null
  let amount = 0
  let paid = 0
  let balance = 0
  for (const row of result.value.all as Array<Record<string, unknown>>) {
    amount += Number(row.total ?? 0)
    paid += Number(row.paidAmount ?? 0)
    balance += Number(row.remainingAmount ?? 0)
  }
  return {
    invoices: result.value.all.length,
    amount: roundQty(amount),
    paid: roundQty(paid),
    balance: roundQty(balance),
  }
})

const createLabel = computed(() => {
  if (current.value?.path === '/reports/purchases') return t('app.pages.purchaseNew')
  return t('app.ui.newEntity', { entity: current.value ? moduleSingular(current.value) : '' })
})

function rowMenuItems(row: Record<string, unknown>): DropdownMenuItem[][] {
  const collection = current.value?.collection
  if (collection === 'sales') {
    if (!canReturnSale.value) return []
    return [[{
      label: t('app.reports.return'),
      icon: 'i-lucide-undo-2',
      color: 'warning',
      disabled: !documentHasReturnableLines(row as AppRecord),
      onSelect: () => openReturn('sale', row as AppRecord),
    }]]
  }
  if (collection === 'stockIns') {
    if (!canReturnPurchase.value) return []
    return [[{
      label: t('app.reports.return'),
      icon: 'i-lucide-undo-2',
      color: 'warning',
      disabled: !documentHasReturnableLines(row as AppRecord),
      onSelect: () => openReturn('purchase', row as AppRecord),
    }]]
  }
  if (collection === 'customerDebts') {
    if (!canPayCustomerDebt.value) return []
    return [[{
      label: t('app.reports.pay'),
      icon: 'i-lucide-hand-coins',
      color: 'success',
      disabled: Number(row.remainingAmount || 0) <= 0,
      onSelect: () => openDebtPayment('customer', row as AppRecord),
    }]]
  }
  if (collection === 'supplierDebts') {
    if (!canPaySupplierDebt.value) return []
    return [[{
      label: t('app.reports.pay'),
      icon: 'i-lucide-hand-coins',
      color: 'success',
      disabled: Number(row.remainingAmount || 0) <= 0,
      onSelect: () => openDebtPayment('supplier', row as AppRecord),
    }]]
  }
  const items: DropdownMenuItem[] = [
    {
      label: t('app.ui.open'),
      icon: 'i-lucide-eye',
      onSelect: () => openRow(row),
    },
  ]
  if (collection === 'documentSequences') {
    if (canEdit.value) {
      const active = String(row.status || '').toUpperCase() === 'ACTIVE'
      items.push({
        label: active ? t('core.rowActions.deactivate') : t('core.rowActions.activate'),
        icon: active ? 'i-lucide-circle-off' : 'i-lucide-circle-check',
        color: active ? 'warning' : 'success',
        onSelect: () => setDocumentSequenceStatus(row, active ? 'INACTIVE' : 'ACTIVE'),
      })
    }
    return [items]
  }
  if (collection === 'products' && canOperate.value) {
    for (const type of STOCK_OPERATION_TYPES) {
      const meta = STOCK_OPERATION_META[type]
      // Stock In = purchase-driven StockInDialog (stored on purchases),
      // never a direct quantity edit.
      if (type === 'stock_in') {
        items.push({
          label: meta.label,
          icon: meta.icon,
          color: meta.color,
          onSelect: () => openStockIn(row as AppRecord),
        })
        continue
      }
      items.push({
        label: meta.label,
        icon: meta.icon,
        color: meta.color,
        onSelect: () => openStockOperation(type, String(row.id || '')),
      })
    }
  }
  if (collection === 'users') {
    const status = String(row.status || 'Active')
    if (canEdit.value && status === 'Active') {
      items.push({
        label: t('core.rowActions.deactivate'),
        icon: 'i-lucide-circle-off',
        color: 'warning',
        onSelect: () => { void setUserStatus(row, 'Inactive') },
      })
    }
    if (canEdit.value && status === 'Inactive') {
      items.push({
        label: t('core.rowActions.activate'),
        icon: 'i-lucide-circle-check',
        color: 'success',
        onSelect: () => { void setUserStatus(row, 'Active') },
      })
    }
  }
  if (canDelete.value && !deactivationOnly.value) {
    items.push({
      label: t('app.ui.delete'),
      icon: 'i-lucide-trash-2',
      color: 'error',
      onSelect: () => { void deleteIds([String(row.id)]) },
    })
  }
  if (canEdit.value && deactivationOnly.value) {
    items.push({
      label: t('app.ui.deactivate'),
      icon: 'i-lucide-circle-off',
      color: 'warning',
      onSelect: () => { void deactivateIds([String(row.id)]) },
    })
  }
  return [items]
}

const columns = computed<TableColumn<Record<string, unknown>>[]>(() => {
  if (!current.value) return []
  void localization.value.dateFormat
  void localization.value.timeFormat
  void localization.value.timezone
  const titleKey = current.value.titleField
  const dataColumns = current.value.columns.map((column, index) => ({
    accessorKey: column.key,
    enableSorting: false,
    header: fieldLabel(column),
    meta: isNumericKey(column.key) || isMoneyKey(column.key)
      ? { class: { td: 'text-end tabular-nums whitespace-nowrap', th: 'text-end' } }
      : undefined,
    cell: ({ row }: { row: { original: Record<string, unknown> } }) => {
      if (column.type === 'image') {
        return h(TableAppTableCellImage, {
          src: productImageUrl(row.original),
          alt: String(row.original.name ?? ''),
        })
      }
      const text = cellText(row.original, column.key)
      const isTitle = column.key === titleKey || (index === 0 && !current.value!.columns.some(item => item.key === titleKey))
      const entityTo = column.key === 'entity' ? auditEntityLinkFor(row.original) : ''
      if (entityTo) {
        return h(ULink, {
          to: entityTo,
          class: 'font-medium text-highlighted hover:text-primary hover:underline',
        }, () => text)
      }
      const qtyKind = current.value!.collection === 'products' ? STOCK_QTY_KIND[column.key] : undefined
      if (qtyKind) {
        return h('button', {
          type: 'button',
          class: 'font-medium tabular-nums text-primary hover:underline',
          onClick: () => openStockHistory(row.original, qtyKind),
        }, text)
      }
      const priceKind = current.value!.collection === 'products' ? STOCK_PRICE_KIND[column.key as keyof typeof STOCK_PRICE_KIND] : undefined
      if (priceKind) {
        return h('button', {
          type: 'button',
          class: 'font-medium tabular-nums text-primary hover:underline',
          onClick: () => openPriceDialog(row.original, priceKind),
        }, text)
      }
      if (isTitle && !isTableOnly.value) {
        return h(ULink, {
          to: recordPath(row.original.id),
          class: 'font-medium text-highlighted hover:text-primary hover:underline',
        }, () => text)
      }
      if (column.key === 'status' || column.key.toLowerCase().includes('status')) {
        return moduleStatusBadge(
          row.original[column.key] || row.original.workflowStatus || row.original.status,
          column.key,
          text,
        )
      }
      if (column.key === 'type') {
        return h(UBadge, { color: 'info', variant: 'subtle', size: 'sm' }, () => text)
      }
      if (column.key === 'customer' || column.key === 'supplier' || column.key === 'product') {
        return h('span', { class: 'block max-w-48 truncate text-default', title: text }, text)
      }
      return h('span', { class: 'text-sm text-default' }, text)
    },
  }))

  return [
    ...(!isTableOnly.value ? [listTableSelectColumn<Record<string, unknown>>(t)] : []),
    ...dataColumns,
    ...(showRowActions.value
      ? [listTableRowMetaColumn<Record<string, unknown>>({
          summary: pageSummary.value,
          items: rowMenuItems,
          loadingId: busyId.value
            || (returnBusy.value ? String(returnDocument.value?.id || '') : '')
            || (debtPayBusy.value ? String(debtPayRow.value?.id || '') : ''),
        })]
      : []),
  ]
})

function openReturn(kind: ReturnDocumentKind, row: AppRecord) {
  returnKind.value = kind
  returnDocument.value = row
  returnOpen.value = true
}

function openDebtPayment(kind: DebtPaymentKind, row: AppRecord) {
  debtPayKind.value = kind
  debtPayRow.value = row
  debtPayOpen.value = true
}

async function submitReturn(payload: {
  kind: ReturnDocumentKind
  documentId: string
  reason: string
  lines: Array<{ lineId: string, quantity: number, restock: boolean }>
}) {
  returnBusy.value = true
  busyId.value = payload.documentId
  try {
    if (payload.kind === 'sale') {
      await posCommands.returnSale({
        saleId: payload.documentId,
        reason: payload.reason,
        lines: payload.lines,
      })
    }
    else {
      await posCommands.returnPurchase({
        stockInId: payload.documentId,
        reason: payload.reason,
        lines: payload.lines.map(line => ({ lineId: line.lineId, quantity: line.quantity })),
      })
    }
    if (current.value) await store.fetchList(current.value.collection)
    if (payload.kind === 'sale') await store.fetchList('products')
    else {
      await store.fetchList('products')
      await store.fetchList('stockIns')
    }
    returnOpen.value = false
    toast.add({ title: t('app.reports.returnSaved'), color: 'success' })
  }
  catch (error: unknown) {
    toast.add({
      title: t('app.reports.returnFailed'),
      description: error instanceof Error ? error.message : String(error),
      color: 'error',
    })
  }
  finally {
    returnBusy.value = false
    busyId.value = ''
  }
}

async function submitDebtPayment(payload: {
  kind: DebtPaymentKind
  debtId: string
  partyId: string
  amount: number
  paymentMethod: string
  reference: string | null
}) {
  debtPayBusy.value = true
  busyId.value = payload.debtId
  try {
    if (payload.kind === 'customer') {
      await posCommands.payCustomerDebt({
        customerId: payload.partyId,
        debtId: payload.debtId,
        amount: payload.amount,
        paymentMethod: payload.paymentMethod,
        reference: payload.reference,
      })
      await store.fetchList('customerDebts')
      await store.fetchList('customers')
    }
    else {
      await posCommands.paySupplierDebt({
        supplierId: payload.partyId,
        debtId: payload.debtId,
        amount: payload.amount,
        paymentMethod: payload.paymentMethod,
        reference: payload.reference,
      })
      await store.fetchList('supplierDebts')
      await store.fetchList('suppliers')
    }
    debtPayOpen.value = false
    toast.add({ title: t('app.reports.paymentSaved'), color: 'success' })
  }
  catch (error: unknown) {
    toast.add({
      title: t('app.reports.paymentFailed'),
      description: error instanceof Error ? error.message : String(error),
      color: 'error',
    })
  }
  finally {
    debtPayBusy.value = false
    busyId.value = ''
  }
}

function openCreate() {
  if (!current.value) return
  if (current.value.path === '/reports/purchases') {
    navigateTo('/reports/purchases/new')
    return
  }
  navigateTo(`${current.value.path}/new`)
}

function openRow(row: Record<string, unknown>) {
  if (!current.value || !row.id) return
  navigateTo(recordPath(row.id))
}

function onRowSelect(event: Event, row: TableRow<Record<string, unknown>>) {
  if (isTableOnly.value) return
  const target = event.target as HTMLElement | null
  if (target?.closest('a, button, input, [role="checkbox"], [role="menuitem"], [data-slot="dropdown-menu"]')) return
  openRow(row.original)
}

async function deleteIds(ids: string[]) {
  if (!current.value || !canDelete.value || !ids.length) return
  const ok = await confirm({ kind: 'delete', count: ids.length })
  if (!ok) return
  busyId.value = ids[0] || ''
  try {
    await store.deleteRemote(current.value.collection, ids)
    rowSelection.value = {}
    toast.add({ title: t('core.actions.deletedItems', { n: ids.length }), color: 'success' })
  }
  catch (error: unknown) {
    toast.add({
      title: t('api.errorTitle', { status: (error as { statusCode?: number })?.statusCode || 400 }),
      description: error instanceof Error ? error.message : String(error),
      color: 'error',
    })
  }
  finally {
    busyId.value = ''
  }
}

async function deactivateIds(ids: string[]) {
  if (!current.value || !canEdit.value || !ids.length) return
  busyId.value = ids[0] || ''
  try {
    for (const id of ids) {
      const status = current.value.collection === 'documentSequences' ? 'INACTIVE' : 'Inactive'
      await store.updateRemote(current.value.collection, id, { status })
    }
    rowSelection.value = {}
    toast.add({ title: t('app.ui.deactivated'), color: 'success' })
  }
  finally {
    busyId.value = ''
  }
}

async function setUserStatus(row: Record<string, unknown>, status: 'Active' | 'Inactive') {
  if (!current.value || current.value.collection !== 'users') return
  const id = String(row.id || '')
  busyId.value = id
  try {
    await store.updateRemote('users', id, { status })
    toast.add({
      title: t(status === 'Active' ? 'core.common.activated' : 'core.common.deactivated'),
      color: 'success',
    })
  }
  finally {
    busyId.value = ''
  }
}

async function setDocumentSequenceStatus(row: Record<string, unknown>, status: 'ACTIVE' | 'INACTIVE') {
  if (!current.value || !canEdit.value) return
  busyId.value = String(row.id || '')
  try {
    await store.updateRemote(current.value.collection, String(row.id || ''), { status })
    toast.add({ title: t(status === 'ACTIVE' ? 'core.common.activated' : 'core.common.deactivated'), color: 'success' })
  }
  finally {
    busyId.value = ''
  }
}

function refresh() {
  // Always reload through the repository (mock mode re-reads the in-memory seed).
  if (current.value) {
    void store.reloadCollection(current.value.collection)
    return
  }
  store.reload()
}

/* ------------------------- Stock operations ------------------------- */

const productOptions = computed(() => store.list('products').map(product => ({
  label: `${product.code} · ${product.name}`,
  value: String(product.id),
})))

function openStockOperation(type: StockOperationType, productId = '') {
  stockOperationType.value = type
  stockOperationProduct.value = productId
  stockOperationQuantity.value = undefined
  stockOperationNote.value = ''
  const product = store.list('products').find(row => String(row.id) === String(productId))
  stockOperationUnitCost.value = product ? Number(product.costPrice || 0) || undefined : undefined
  stockOperationOpen.value = true
}

const stockOperationMeta = computed(() => STOCK_OPERATION_META[stockOperationType.value])

async function submitStockOperation() {
  if (!stockOperationProduct.value || !stockOperationQuantity.value) return
  stockOperationBusy.value = true
  try {
    const record = await posCommands.createStockOperation({
      type: stockOperationType.value,
      productId: stockOperationProduct.value,
      quantity: Number(stockOperationQuantity.value),
      note: stockOperationNote.value || null,
      ...(stockOperationType.value === 'stock_in' && stockOperationUnitCost.value != null
        ? { unitCost: Number(stockOperationUnitCost.value) }
        : {}),
    })
    stockOperationOpen.value = false
    void store.fetchList('products')
    void store.fetchList('stockMovements')
    if (stockHistoryOpen.value) stockHistoryReloadKey.value += 1
    toast.add({
      title: `${stockOperationMeta.value.label}: ${record.reference}`,
      description: `${record.product} · Qty ${record.quantity}`,
      color: 'success',
    })
  }
  catch (error: unknown) {
    toast.add({
      title: t('app.ui.operationFailed'),
      description: error instanceof Error ? error.message : String(error),
      color: 'error',
    })
  }
  finally {
    stockOperationBusy.value = false
  }
}

function optionValue(option: ModuleSelectOption) {
  return typeof option === 'string' ? option : option.value
}

function filterItems(filter: { options?: readonly ModuleSelectOption[] | ModuleSelectOption[], key: string }) {
  const fromOptions = (filter.options || []).map(optionValue)
  const sourceRows = current.value
    ? store.list(current.value.collection).map(row => current.value?.collection === 'auditLogs' ? normalizeAuditLog(row) : row)
    : []
  const fromData = [...new Set(sourceRows.map(row => String(row[filter.key] ?? '').trim()).filter(Boolean))]
  return [...new Set([...fromOptions, ...fromData])]
    .map(value => String(value).trim())
    .filter(Boolean)
    .map((value) => {
      const label = filter.key === 'documentType'
        ? documentSequenceTypeLabel(value)
        : filter.key === 'workflowStatus'
          ? value.replaceAll('_', ' ')
          : value
      return { label, value }
    })
}
</script>

<template>
  <div v-if="current" class="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-muted/20">
    <LayoutAppHeaderPageActions
      :can-create="canCreate"
      :can-export="false"
      :export-fields="[]"
      :exporting="false"
      :create-label="createLabel"
      :refreshing="pending"
      @create="openCreate"
      @refresh="refresh"
    />

    <div
      v-if="lineReportTotals"
      class="flex flex-wrap items-center justify-end gap-4 px-3 py-2 text-sm"
    >
      <span>
        {{ t('app.reports.invoiceCount') }}
        <strong class="tabular-nums">{{ lineReportTotals.invoices }}</strong>
      </span>
      <span>
        {{ t('app.reports.grandTotal') }}
        <strong class="tabular-nums">{{ formatMoney(lineReportTotals.amount, preferences.currency) }}</strong>
      </span>
      <span>
        {{ t('app.reports.paidTotal') }}
        <strong class="tabular-nums">{{ formatMoney(lineReportTotals.paid, preferences.currency) }}</strong>
      </span>
      <span>
        {{ t('app.reports.balanceTotal') }}
        <strong class="tabular-nums">{{ formatMoney(lineReportTotals.balance, preferences.currency) }}</strong>
      </span>
    </div>

    <TableAppListTable
      v-model:search="q"
      v-model:date-start="dateFrom"
      v-model:date-end="dateTo"
      v-model:row-selection="rowSelection"
      v-model:pagination="pagination"
      :data="result.all"
      :columns="columns"
      :loading="pending"
      :show-date-range="Boolean(dateField)"
      :filters-active="hasActiveFilters"
      :empty-actions="canCreate ? [{ icon: 'i-lucide-plus', label: createLabel, onClick: openCreate }] : []"
      @select="onRowSelect"
    >
      <template #filters="{ compact }">
        <CommonAppFilterSelect
          v-for="filter in visibleFilters"
          :key="filter.key"
          :model-value="filters[filter.key] ?? []"
          :items="filterItems(filter)"
          :placeholder="fieldLabel(filter)"
          :class="compact ? 'w-full' : 'w-40'"
          @update:model-value="filters[filter.key] = parseFilterQuery($event)"
        />
      </template>
      <template #actions>
        <template v-if="selectedIds.length && (canEdit || canDelete)">
          <UButton
            :color="deactivationOnly ? 'warning' : 'error'"
            variant="soft"
            size="sm"
            :icon="deactivationOnly ? 'i-lucide-circle-off' : 'i-lucide-trash-2'"
            class="shrink-0"
            :label="`${deactivationOnly ? t('app.ui.deactivate') : t('app.ui.delete')} (${selectedIds.length})`"
            @click="deactivationOnly ? deactivateIds(selectedIds) : deleteIds(selectedIds)"
          />
          <UButton
            color="neutral"
            variant="ghost"
            size="sm"
            class="shrink-0"
            :label="t('app.ui.clear')"
            @click="rowSelection = {}"
          />
        </template>
      </template>
    </TableAppListTable>

    <CommonAppDialog
      v-model:open="stockOperationOpen"
      :title="stockOperationMeta.label"
      :icon="stockOperationMeta.icon"
      :color="stockOperationMeta.color"
      size="sm"
      :loading="stockOperationBusy"
    >
      <div class="w-full space-y-3">
        <CommonAppSelectMenuField
          v-model="stockOperationProduct"
          :items="productOptions"
          :label="t('app.pos.product')"
          :required="true"
          class="w-full"
        />
        <CommonAppNumberField
          v-model="stockOperationQuantity"
          :label="stockOperationType === 'stock_in' ? t('app.fields.quantity') : `${t('app.fields.quantity')} (${stockOperationType === 'adjustment' ? '+/−' : '−'})`"
          :required="true"
          :min="stockOperationType === 'adjustment' ? undefined : 0"
          :step="1"
          class="w-full"
        />
        <CommonAppMoneyField
          v-if="stockOperationType === 'stock_in'"
          v-model="stockOperationUnitCost"
          :label="t('app.modules.products.fields.costPrice') || t('app.pos.unitPrice')"
          :min="0"
          :step="0.01"
          class="w-full"
        />
        <CommonAppTextareaField
          v-model="stockOperationNote"
          :label="t('app.fields.note')"
          :rows="2"
          class="w-full"
        />
        <p
          v-if="stockOperationType === 'damage'"
          class="text-xs text-muted"
        >
          {{ t('app.stock.negativeHint') }}
        </p>
      </div>

      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <UButton
            color="neutral"
            variant="ghost"
            :label="t('common.cancel')"
            @click="stockOperationOpen = false"
          />
          <UButton
            :color="stockOperationMeta.color"
            :icon="stockOperationMeta.icon"
            :loading="stockOperationBusy"
            :disabled="!stockOperationProduct || !stockOperationQuantity"
            :label="stockOperationMeta.label"
            @click="submitStockOperation"
          />
        </div>
      </template>
    </CommonAppDialog>

    <StockQtyHistoryDialog
      v-model:open="stockHistoryOpen"
      :product="stockHistoryProduct"
      :kind="stockHistoryKind"
      :can-add="canOperate"
      :reload-key="stockHistoryReloadKey"
      @saved="onStockHistorySaved"
    />

    <StockStockInDialog
      v-model:open="stockInOpen"
      :product="stockInProduct"
      :elevated="stockHistoryOpen"
      @saved="onStockInSaved"
    />

    <StockCostHistoryDialog
      v-model:open="costPriceOpen"
      :product="priceProduct"
    />

    <StockSalePriceDialog
      v-model:open="salePriceOpen"
      :product="priceProduct"
    />

    <ReportsDocumentReturnDialog
      v-model:open="returnOpen"
      :kind="returnKind"
      :document="returnDocument"
      :currency="preferences.currency"
      @submit="submitReturn"
    />

    <ReportsDebtPaymentDialog
      v-model:open="debtPayOpen"
      :kind="debtPayKind"
      :debt="debtPayRow"
      :currency="preferences.currency"
      @submit="submitDebtPayment"
    />
  </div>
  <div v-else class="grid h-full min-h-0 flex-1 place-items-center p-8">
    <UEmpty
      variant="naked"
      icon="i-lucide-unplug"
      :title="t('app.ui.pageNotWired')"
      :description="t('app.ui.pageNotWiredHint')"
    />
  </div>
</template>

