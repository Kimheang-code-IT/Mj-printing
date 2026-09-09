<script setup lang="ts">
import PosCartPanel from '~/components/pos/PosCartPanel.vue'
import PosCheckoutPanel from '~/components/pos/PosCheckoutPanel.vue'
import PosProductBrowser from '~/components/pos/PosProductBrowser.vue'
import { useAppHeader } from '~/composables/layout/useAppHeader'
import { usePosChrome } from '~/composables/layout/usePosChrome'
import { usePageSeo } from '~/composables/usePageSeo'
import { usePosCommands, useSettingsRepositories } from '~/repositories/index'
import type { PosCartLine } from '~/utils/pos/cart'
import {
  cartSubtotal,
  createCartLine,
  lineStockQty,
  refreshLineAmounts,
} from '~/utils/pos/cart'
import { roundMoney } from '~/utils/stock/line-calc'
import {
  checkoutDepositTotal,
  checkoutDue,
  checkoutOutstanding,
  checkoutSaleNet,
  type CheckoutDebtRow,
} from '~/utils/pos/checkout'
import { printSaleInvoice, type SaleInvoicePrintInput } from '~/utils/print/invoice'
import type { PrintPaperSize } from '~/utils/print/html'

/**
 * POS workspace: product card grid + cart, then checkout (customer/summary/payment).
 * Submit auto-prints the bilingual invoice (no invoice dialog).
 */
type PosStep = 'cart' | 'checkout'

const store = useAppDataStore()
const preferences = usePreferencesStore()
const auth = useAuthStore()
const { t, locale } = useI18n()
const { clear } = useAppHeader()
const { hidePosAppHeader } = usePosChrome()
const posCommands = usePosCommands()
const { appInfo } = useSettingsRepositories()
const toast = useToast()

const shopName = ref('RBL Service Printing & Advertising')
const step = ref<PosStep>('cart')
const search = ref('')
const categoryId = ref('')
const cart = ref<PosCartLine[]>([])
const customerId = ref<string | undefined>(undefined)
const customerName = ref('')
const customerPhone = ref('')
const customerLocation = ref('')
const paymentMethod = ref<string>('Cash')
const paidInput = ref<number | undefined>()
const includedDebtIds = ref<string[]>([])
const depositInput = ref(0)
const completing = ref(false)
const lastSaleNo = ref('')
const lastSaleId = ref('')

onBeforeUnmount(() => {
  hidePosAppHeader.value = false
  clear()
})
usePageSeo({ title: () => t('app.pages.pos') })

watch(step, (value) => {
  hidePosAppHeader.value = value === 'checkout'
}, { immediate: true })

onMounted(async () => {
  void store.fetchList('products')
  void store.fetchList('customers')
  void store.fetchList('categories')
  try {
    const info = await appInfo.get()
    const name = String(info.businessName || info.applicationName || '').trim()
    if (name) shopName.value = name
  }
  catch {
    // Keep default shop name when settings are unavailable.
  }
})

const canOperate = computed(() =>
  auth.canAccessPage('pos.create')
  || auth.canAccessPage('pos.edit')
  || auth.canAccessPage('pos.access')
  || auth.canAccessPage('ALL_PAGES'))

const currency = computed(() => preferences.currency)

const categoryOptions = computed(() => [
  { label: t('app.pos.allCategories'), value: '' },
  ...store.list('categories')
    .filter(row => String(row.status || 'Active') !== 'Inactive')
    .map(row => ({ label: String(row.name || ''), value: String(row.id) })),
])

const products = computed(() => {
  const q = search.value.trim().toLowerCase()
  return store.list('products')
    .filter(row => String(row.status || 'Active') !== 'Inactive')
    .filter(row => !categoryId.value || String(row.categoryId) === categoryId.value)
    .filter((row) => {
      if (!q) return true
      return [row.name, row.barcode, row.code]
        .map(value => String(value || '').toLowerCase())
        .some(value => value.includes(q))
    })
})

const customerOptions = computed(() =>
  store.list('customers')
    .filter(row => String(row.status) === 'Active')
    .map(row => ({ label: `${row.name} · ${row.code}`, value: String(row.id) })),
)

const openDebts = computed<CheckoutDebtRow[]>(() => {
  if (!customerId.value) return []
  const salesById = Object.fromEntries(
    store.list('sales').map(row => [String(row.id), row]),
  )
  return store.list('customerDebts')
    .filter(row => String(row.customerId) === String(customerId.value))
    .filter(row => Number(row.remainingAmount || 0) > 0)
    .map((row) => {
      const sale = salesById[String(row.saleId)]
      return {
        ...row,
        id: String(row.id),
        date: String(row.date || '').slice(0, 10),
        invoiceNo: String(row.invoiceNo || sale?.invoiceNo || sale?.saleNo || ''),
        paidAmount: Number(row.paidAmount || 0),
        remainingAmount: Number(row.remainingAmount || 0),
        paymentMethod: String(row.paymentMethod || sale?.paymentMethod || '—'),
      }
    })
    .sort((a, b) => b.date.localeCompare(a.date))
})

const subtotal = computed(() => cartSubtotal(cart.value))
const selectedDeposit = computed(() => checkoutDepositTotal(
  openDebts.value
    .filter(row => includedDebtIds.value.includes(row.id))
    .map(row => row.remainingAmount),
))
const due = computed(() => checkoutDue(
  checkoutSaleNet(subtotal.value),
  Number(depositInput.value || 0),
))
const isCredit = computed(() => paymentMethod.value === 'Credit')
const paidAmount = computed(() =>
  isCredit.value ? 0 : Math.min(Number(paidInput.value ?? 0), due.value))
const outstandingAmount = computed(() => checkoutOutstanding(due.value, paidAmount.value))

const dateLabel = computed(() => {
  const now = new Date()
  return new Intl.DateTimeFormat(locale.value === 'km' ? 'km-KH' : 'en-GB', {
    year: '2-digit',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(now)
})

const cashierName = computed(() => String(auth.user?.name || auth.user?.email || 'Cashier'))

function addProduct(row: Record<string, unknown>) {
  const id = String(row.id)
  const stock = Number(row.quantity || 0)
  if (stock <= 0) {
    toast.add({ title: t('app.pos.outOfStock'), color: 'warning' })
    return
  }
  const existing = cart.value.find(line => line.productId === id)
  if (existing) {
    const candidate = refreshLineAmounts({ ...existing, quantity: existing.quantity + 1 })
    if (lineStockQty(candidate) > existing.availableStock) {
      toast.add({ title: t('app.pos.stockLimit'), color: 'warning' })
      return
    }
    Object.assign(existing, candidate)
    return
  }
  cart.value.push(createCartLine(row))
}

function onSearchEnter() {
  const exact = products.value.find(row => String(row.barcode || '') === search.value.trim())
  if (exact) {
    addProduct(exact)
    search.value = ''
  }
}

function changeQty(productId: string, delta: number) {
  const line = cart.value.find(item => item.productId === productId)
  if (!line) return
  const nextQty = Math.max(1, line.quantity + delta)
  const candidate = refreshLineAmounts({ ...line, quantity: nextQty })
  if (lineStockQty(candidate) > line.availableStock) {
    toast.add({ title: t('app.pos.stockLimit'), color: 'warning' })
    return
  }
  Object.assign(line, candidate)
}

function updateLine(productId: string, patch: Partial<PosCartLine>) {
  const line = cart.value.find(item => item.productId === productId)
  if (!line) return
  const candidate = refreshLineAmounts({
    ...line,
    ...patch,
    unitPrice: patch.unitPrice != null ? Math.max(0, roundMoney(patch.unitPrice)) : line.unitPrice,
  })
  if (lineStockQty(candidate) > candidate.availableStock) {
    toast.add({ title: t('app.pos.stockLimit'), color: 'warning' })
    return
  }
  Object.assign(line, candidate)
}

function removeLine(productId: string) {
  cart.value = cart.value.filter(line => line.productId !== productId)
}

function clearCart() {
  cart.value = []
  paidInput.value = undefined
  customerId.value = undefined
  customerName.value = ''
  customerPhone.value = ''
  customerLocation.value = ''
  includedDebtIds.value = []
  depositInput.value = 0
  paymentMethod.value = 'Cash'
  step.value = 'cart'
}

function goNext() {
  if (!cart.value.length) return
  void store.fetchList('customers')
  void store.fetchList('customerDebts')
  void store.fetchList('sales')
  step.value = 'checkout'
}

function goBack() {
  step.value = 'cart'
}

watch(includedDebtIds, () => {
  depositInput.value = selectedDeposit.value
}, { deep: true })

watch(customerId, (id) => {
  includedDebtIds.value = []
  if (!id) {
    customerPhone.value = ''
    customerLocation.value = ''
    return
  }
  const row = store.get('customers', String(id))
  if (!row) return
  customerName.value = String(row.name || '')
  customerPhone.value = String(row.phone || '')
  customerLocation.value = String(row.location || row.address || '')
})

watch(paymentMethod, (method) => {
  if (method === 'Credit') paidInput.value = 0
  else paidInput.value = undefined
})

/* ------------------------- Invoice print size chooser ------------------------- */

/** Paper-size chooser opened after a successful Submit (A4 default). */
const printSizeOpen = ref(false)
let printSizeResolver: ((size: PrintPaperSize | null) => void) | null = null

/** Resolves with the chosen size, or null when the cashier closes/cancels. */
function choosePrintSize(): Promise<PrintPaperSize | null> {
  return new Promise((resolve) => {
    printSizeResolver = resolve
    printSizeOpen.value = true
  })
}

function onPrintSizeConfirm(size: PrintPaperSize) {
  printSizeOpen.value = false
  printSizeResolver?.(size)
  printSizeResolver = null
}

watch(printSizeOpen, (open) => {
  if (!open && printSizeResolver) {
    const resolve = printSizeResolver
    printSizeResolver = null
    resolve(null) // closed/cancelled — sale already succeeded, skip print
  }
})

async function completeSale() {
  if (!cart.value.length || !canOperate.value || completing.value) return
  if (outstandingAmount.value > 0 && !customerId.value) {
    toast.add({ title: t('app.pos.creditRequiresCustomer'), color: 'warning' })
    return
  }
  completing.value = true
  try {
    const snapshot = cart.value.map(line => ({ ...line }))
    const sale = await posCommands.completeSale({
      customerId: customerId.value ? String(customerId.value) : null,
      customerName: customerName.value || null,
      items: cart.value.map(line => ({
        productId: line.productId,
        quantity: line.quantity,
        unitPrice: line.unitPrice,
        height: line.height,
        width: line.width,
        squareMeter: line.squareMeter,
        calcMode: line.calcMode,
      })),
      paymentMethod: paymentMethod.value,
      paidAmount: paidAmount.value,
      discount: 0,
      otherCharge: 0,
      deposit: depositInput.value,
      includedDebtIds: includedDebtIds.value,
    })
    lastSaleNo.value = String(sale.invoiceNo || sale.saleNo || '')
    lastSaleId.value = String(sale.id || '')
    // Invoice payload comes from the sale receipt contract (mock: derived
    // from the stored sale; HTTP: GET /pos/sales/{id}/receipt). Falls back to
    // the cart snapshot if the receipt cannot be read. No invoice.pdf call.
    let printLines: SaleInvoicePrintInput['lines'] = snapshot.map(line => ({
      name: line.name,
      quantity: line.quantity,
      unitPrice: line.unitPrice,
      height: line.height,
      width: line.width,
      squareMeter: line.squareMeter,
    }))
    try {
      const receipt = await posCommands.getSaleReceipt(lastSaleId.value)
      printLines = receipt.items.map(item => ({
        name: item.name,
        quantity: item.quantity,
        unitPrice: item.unitPrice,
        height: item.height ?? null,
        width: item.width ?? null,
        squareMeter: item.squareMeter ?? null,
      }))
    }
    catch {
      // Keep the snapshot lines — printing must not fail because of the receipt.
    }
    const printInput: SaleInvoicePrintInput = {
      shopName: shopName.value,
      invoiceNo: lastSaleNo.value,
      dateLabel: dateLabel.value,
      customerName: customerName.value || String(sale.customer || t('app.pos.walkIn')),
      cashier: cashierName.value,
      currency: currency.value,
      lines: printLines,
      otherCharge: 0,
      depositAmount: Number(depositInput.value || 0),
      outstandingAmount: outstandingAmount.value,
    }
    toast.add({
      title: `${t('app.pos.saleCompleted')} · ${lastSaleNo.value}`,
      color: 'success',
    })
    cart.value = []
    paidInput.value = undefined
    customerId.value = undefined
    customerName.value = ''
    customerPhone.value = ''
    customerLocation.value = ''
    includedDebtIds.value = []
    depositInput.value = 0
    paymentMethod.value = 'Cash'
    step.value = 'cart'
    void store.fetchList('products')
    void store.fetchList('sales')
    void store.fetchList('customers')
    void store.fetchList('customerDebts')
    void store.fetchList('stockMovements')
    // Ask which paper size to print (A4/A5); closing the dialog skips print.
    const paperSize = await choosePrintSize()
    if (paperSize) await printSaleInvoice(printInput, paperSize)
  }
  catch (error: unknown) {
    toast.add({
      title: t('app.pos.saleFailed'),
      description: error instanceof Error ? error.message : String(error),
      color: 'error',
    })
  }
  finally {
    completing.value = false
  }
}

</script>

<template>
  <div class="flex h-full min-h-0 flex-1 flex-col overflow-hidden">
    <LayoutAppHeaderPageActions
      v-if="step === 'cart'"
      :can-create="false"
      :can-export="false"
      :show-more-actions="false"
      @refresh="() => { void store.fetchList('products') }"
    >
      <UButton
        color="primary"
        icon="i-lucide-arrow-right"
        trailing
        class="rounded-sm"
        :disabled="!canOperate || !cart.length"
        :label="t('app.pos.next')"
        @click="goNext"
      />
    </LayoutAppHeaderPageActions>

    <div
      v-if="step === 'cart'"
      class="flex h-full min-h-0 flex-1 flex-col gap-3 overflow-hidden p-3 lg:flex-row"
    >
      <PosProductBrowser
        v-model:search="search"
        v-model:category-id="categoryId"
        :products="products"
        :categories="categoryOptions"
        :currency="currency"
        :disabled="!canOperate"
        @add="addProduct"
        @search-enter="onSearchEnter"
      />
      <PosCartPanel
        :cart="cart"
        :currency="currency"
        :disabled="!canOperate"
        @change-qty="changeQty"
        @update-line="updateLine"
        @remove="removeLine"
        @clear="clearCart"
      />
    </div>

    <PosCheckoutPanel
      v-else
      v-model:customer-id="customerId"
      v-model:customer-name="customerName"
      v-model:customer-phone="customerPhone"
      v-model:customer-location="customerLocation"
      v-model:payment-method="paymentMethod"
      v-model:paid-input="paidInput"
      v-model:deposit-input="depositInput"
      v-model:included-debt-ids="includedDebtIds"
      :cart="cart"
      :currency="currency"
      :debts="openDebts"
      :customer-options="customerOptions"
      :can-operate="canOperate"
      :completing="completing"
      @back="goBack"
      @complete="completeSale"
    />

    <PosPrintSizeDialog
      v-model:open="printSizeOpen"
      @confirm="onPrintSizeConfirm"
    />
  </div>
</template>
