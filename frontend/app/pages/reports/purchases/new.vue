<script setup lang="ts">
import { purchaseLinesTable } from '~/config/stock-modules'
import type { ModuleTable } from '~/config/modules'
import type { DocumentTabSchema } from '~/types/stock-pos/common'
import { formatMoney } from '~/composables/module/useModule'
import { usePageSeo } from '~/composables/usePageSeo'
import { usePosCommands } from '~/repositories/index'
import type { PurchaseCreateInput, PurchaseLineInput } from '~/repositories/contracts/entities'
import {
  calcBalance,
  roundMoney,
} from '~/utils/stock/line-calc'

/**
 * Purchase / Stock In form (AGENT_STOCK_POS §6) under the Purchase Report
 * module. One supplier header + multi-product lines rendered through the
 * reusable `AppLineTable` (config: `purchaseLinesTable` in stock-modules).
 * Dimensional lines (height & width > 0) compute
 * square_meter = height × width × qty and amount = sqm × purchase_price;
 * normal lines compute amount = qty × price.
 *
 * The header keeps only Supplier + Note; supplier invoice no., date,
 * other cost and discount are omitted (backend defaults apply). A leading
 * "Add Supplier" header button opens a create-supplier dialog and selects
 * the new supplier for this purchase; saving without a supplier opens the
 * same dialog instead of showing an inline validation error.
 *
 * The page reuses the shared document shell (`DocumentAppDocumentPage`)
 * like the stock document UI: standard header actions + save confirm, with
 * flat form sections (no card header/footer chrome) in the content shell.
 *
 * Submit goes through the existing repository `createPurchase`
 * (POST /api/v1/purchases; mock repo mirrors the stock/ledger side
 * effects), so product stock and the Stock page are updated by the
 * backend transaction — never on the client.
 */
type PurchaseRow = Record<string, unknown>

const store = useAppDataStore()
const preferences = usePreferencesStore()
const auth = useAuthStore()
const { t } = useI18n()
const posCommands = usePosCommands()
const toast = useToast()

definePageMeta({ titleKey: 'app.pages.purchases', permission: 'purchases.view' })
usePageSeo({ title: () => t('app.pages.purchases') })

const money = (value: unknown) => formatMoney(value, preferences.currency)
const moneyKhr = (value: unknown) => formatMoney(value, 'KHR')

const supplierId = ref('')
const note = ref('')
const paidInput = ref<number | undefined>(undefined)
/** Paid follows the computed grand total until the user edits the field. */
const paidDirty = ref(false)
const saving = ref(false)

/**
 * Add-supplier dialog — opened from the header leading "Add Supplier"
 * button or from save() when no supplier is selected. A supplier created
 * here is selected for this purchase immediately.
 */
const supplierDialogOpen = ref(false)
const supplierSaving = ref(false)
const supplierName = ref('')
const supplierPhone = ref('')
const supplierLocation = ref('')

function blankLine(): PurchaseRow {
  return {
    productId: '',
    height: 0,
    width: 0,
    quantity: 0,
    purchasePrice: 0,
    squareMeter: null,
    amount: 0,
    note: '',
  }
}
const lines = ref<PurchaseRow[]>([blankLine()])

const route = useRoute()

onMounted(() => {
  void store.fetchList('suppliers')
  void store.fetchList('products')
  applyStockInHandoff()
})

/**
 * Stock In dialog hand-off: `/reports/purchases/new?productId=…&quantity=…
 * &purchasePrice=…&supplierId=…&note=…`.
 * Pre-fills the header and adds the product as the first line.
 *
 * The params are intentionally NOT stripped from the URL after applying:
 * the layout mounts pages with `page-key = fullPath`, so any query change
 * (even a replace) would remount this page and wipe the pre-filled form.
 * Re-visiting the page without params applies nothing, and a refresh just
 * re-applies the same hand-off — harmless.
 */
function applyStockInHandoff() {
  const q = route.query
  const productId = String(q.productId || '')
  if (!productId) return
  const row = blankLine()
  row.productId = productId
  const quantity = Number(q.quantity)
  if (Number.isFinite(quantity) && quantity > 0) row.quantity = quantity
  const price = Number(q.purchasePrice)
  if (Number.isFinite(price) && price >= 0) row.purchasePrice = price
  lines.value = [row]
  const supplier = String(q.supplierId || '')
  if (supplier) supplierId.value = supplier
  const noteParam = String(q.note || '')
  if (noteParam) note.value = noteParam
}

const canCreate = computed(() =>
  auth.canAccessPage('purchases.create')
  || auth.canAccessPage('stock.in')
  || auth.canAccessPage('product.update')
  || auth.canAccessPage('ALL_PAGES'))

const supplierOptions = computed(() => store.list('suppliers')
  .filter(row => String(row.status || '').toLowerCase() === 'active')
  .map(row => ({
    label: row.code ? `${row.code} · ${row.name}` : String(row.name || ''),
    value: String(row.id),
  })))

const productOptions = computed(() => store.list('products')
  .filter(row => String(row.status || 'Active') !== 'Inactive')
  .map(row => ({
    label: row.code ? `${row.code} · ${row.name}` : String(row.name || ''),
    value: String(row.id),
  })))

/** Reusable line-table config with the live product options injected. */
const purchaseTable = computed<ModuleTable>(() => purchaseLinesTable(productOptions.value))

/* --------------------- document shell (single tab) ---------------------- */

/** The purchase form is a custom slot form, but the shell requires a tab. */
const tabs = computed<DocumentTabSchema[]>(() => [{
  id: 'purchase',
  labelKey: 'app.pages.purchases',
  sections: [{ id: 'header', fields: [] }],
}])
const activeTab = ref('purchase')
const fieldValue = () => undefined
const setFieldValue = () => {}

/* ------------------------------ line math ------------------------------ */

function rowAmounts(row: PurchaseRow) {
  return calcLineAmount({
    height: row.height == null ? null : Number(row.height),
    width: row.width == null ? null : Number(row.width),
    quantity: Number(row.quantity || 0),
    unitPrice: Number(row.purchasePrice || 0),
  })
}

const subtotal = computed(() => roundMoney(
  lines.value.reduce((sum, row) => sum + rowAmounts(row).amount, 0),
))
const grandTotal = computed(() => subtotal.value)
const paid = computed(() => paidDirty.value
  ? roundMoney(Math.max(0, Number(paidInput.value || 0)))
  : grandTotal.value)
const balance = computed(() => calcBalance(grandTotal.value, paid.value))

/** USD → KHR rate for the KHR balance display (default 4100 KHR per USD). */
const exchangeRate = ref(4100)
const balanceKhr = computed(() =>
  Math.round(balance.value * Math.max(0, Number(exchangeRate.value || 0))))

/* ----------------------------- validation ------------------------------ */

/** Fully empty lines are ignored (treated as absent) so an extra blank row
 *  never blocks saving. */
function isBlankLine(row: PurchaseRow): boolean {
  return !String(row.productId || '')
    && !(Number(row.quantity) > 0)
    && !(Number(row.purchasePrice) > 0)
    && !(Number(row.height) > 0)
    && !(Number(row.width) > 0)
    && !String(row.note || '')
}

const activeLines = computed(() =>
  lines.value.map((row, index) => ({ row, index })).filter(({ row }) => !isBlankLine(row)))

const rowErrors = computed<Record<number, string>>(() => {
  const errors: Record<number, string> = {}
  const seen = new Set<string>()
  for (const { row, index } of activeLines.value) {
    const productId = String(row.productId || '')
    if (!productId) {
      errors[index] = t('app.purchase.needProduct')
      continue
    }
    if (seen.has(productId)) errors[index] = t('app.purchase.duplicateProduct')
    seen.add(productId)
    if (!(Number(row.quantity) > 0)) errors[index] = t('app.purchase.needQuantity')
    if (Number(row.height ?? 0) < 0 || Number(row.width ?? 0) < 0) {
      errors[index] = t('app.purchase.needQuantity')
    }
    if (Number(row.purchasePrice ?? 0) < 0) errors[index] = t('app.purchase.needQuantity')
  }
  return errors
})

const headerError = computed<string | null>(() => {
  if (!activeLines.value.length) return t('app.purchase.needLine')
  if (paid.value > grandTotal.value) return t('app.purchase.paidTooLarge')
  return null
})

const canSave = computed(() =>
  canCreate.value
  && !saving.value
  && !headerError.value
  && Object.keys(rowErrors.value).length === 0)

/* ------------------------------- actions ------------------------------- */

function resetForm() {
  supplierId.value = ''
  note.value = ''
  paidInput.value = undefined
  paidDirty.value = false
  lines.value = [blankLine()]
}

function openSupplierDialog() {
  supplierName.value = ''
  supplierPhone.value = ''
  supplierLocation.value = ''
  supplierDialogOpen.value = true
}

/**
 * Create the supplier from the dialog and select it for this purchase.
 * Goes through store.createRemote('suppliers') so the supplier exists as a
 * real master record (Setup → Suppliers) before the purchase is saved.
 */
async function saveSupplier() {
  if (!String(supplierName.value || '').trim() || supplierSaving.value) return
  supplierSaving.value = true
  try {
    const created = await store.createRemote('suppliers', {
      name: String(supplierName.value).trim(),
      phone: String(supplierPhone.value || '').trim(),
      location: String(supplierLocation.value || '').trim(),
      address: String(supplierLocation.value || '').trim(),
      status: 'Active',
    })
    supplierId.value = String(created.id)
    supplierDialogOpen.value = false
    toast.add({
      title: t('app.purchase.supplierCreated'),
      description: String(created.name || ''),
      color: 'success',
    })
  }
  catch (error: unknown) {
    toast.add({
      title: t('app.purchase.supplierCreateFailed'),
      description: error instanceof Error ? error.message : String(error),
      color: 'error',
    })
  }
  finally {
    supplierSaving.value = false
  }
}

async function save() {
  if (!canSave.value) return
  // Supplier is still required by the backend (supplier_id), but instead of
  // an inline error the user is guided straight into the add-supplier dialog.
  if (!supplierId.value) {
    toast.add({ title: t('app.purchase.needSupplier'), color: 'warning' })
    openSupplierDialog()
    return
  }
  saving.value = true
  try {
    const items: PurchaseLineInput[] = activeLines.value.map(({ row }) => {
      const amounts = rowAmounts(row)
      const dimensional = amounts.mode === 'dimensional'
      return {
        productId: String(row.productId),
        quantity: Number(row.quantity),
        purchasePrice: Number(row.purchasePrice || 0),
        height: dimensional ? Number(row.height) : null,
        width: dimensional ? Number(row.width) : null,
        squareMeter: dimensional ? amounts.squareMeter : null,
        calcMode: amounts.mode,
        note: String(row.note || '') || null,
      }
    })
    // supplierInvoiceNo / purchase_date / other_cost / discount are omitted —
    // the backend defaults them (null date → now, 0 cost / discount).
    const input: PurchaseCreateInput = {
      supplierId: supplierId.value,
      note: note.value || null,
      paid: paid.value,
      items,
    }
    const record = await posCommands.createPurchase(input)
    const purchaseNo = String(record.purchaseNo ?? record.purchase_no ?? '')
    // Stock + supplier debt changed server-side — refresh the cached
    // collections so the Stock page and reports show fresh quantities.
    void store.fetchList('products')
    void store.fetchList('suppliers')
    toast.add({
      title: purchaseNo
        ? `${t('app.purchase.saved')} · ${purchaseNo}`
        : t('app.purchase.saved'),
      color: 'success',
    })
    resetForm()
    await navigateTo('/reports/purchases')
  }
  catch (error: unknown) {
    toast.add({
      title: t('app.purchase.saveFailed'),
      description: error instanceof Error ? error.message : String(error),
      color: 'error',
    })
  }
  finally {
    saving.value = false
  }
}
</script>

<template>
  <DocumentAppDocumentPage
    :tabs="tabs"
    :active-tab="activeTab"
    :field-value="fieldValue"
    :set-field-value="setFieldValue"
    :show-tabs="false"
    :show-meta-rail="false"
    :is-create="true"
    :saving="saving"
    :can-save="canCreate"
    :save-label="t('app.purchase.save')"
    :show-cancel="true"
    list-to="/reports/purchases"
    content-wide
    @update:active-tab="activeTab = $event"
    @save="save"
  >
    <template #leading>
      <UButton
        icon="i-lucide-user-plus"
        :label="t('app.purchase.addSupplier')"
        variant="soft"
        size="sm"
        @click="openSupplierDialog"
      />
    </template>
    <template #form>
      <DocumentAppDocumentContentShell
        wide
        class="space-y-8 py-6"
      >
        <!-- Header (spec §6) -->
        <section class="space-y-4">
          <div>
            <h3 class="text-sm font-medium text-highlighted">
              {{ t('app.purchase.header') }}
            </h3>
          </div>
          <div class="grid gap-3 md:grid-cols-2">
            <CommonAppSelectMenuField
              v-model="supplierId"
              :items="supplierOptions"
              :label="t('app.fields.supplier')"
              :placeholder="t('app.purchase.supplierPlaceholder')"
              class="w-full"
            />
            <CommonAppTextareaField
              v-model="note"
              :label="t('app.fields.note')"
              :rows="2"
              class="w-full"
            />
          </div>
        </section>

        <!-- Lines (spec §6 Items) — reusable config-driven line table -->
        <section class="space-y-4 border-t border-default pt-6">
          <div>
            <h3 class="text-sm font-medium text-highlighted">
              {{ t('app.purchase.lines') }}
            </h3>
          </div>
          <TableAppLineTable
            v-model="lines"
            :table="purchaseTable"
            :disabled="!canCreate"
          />
          <div
            v-if="Object.keys(rowErrors).length"
            class="space-y-1 px-1"
          >
            <p
              v-for="(message, index) in rowErrors"
              :key="index"
              class="text-xs text-error"
            >
              {{ t('app.purchase.lineN', { n: Number(index) + 1 }) }}: {{ message }}
            </p>
          </div>
        </section>

        <!-- Totals (spec §6 Totals) -->
        <section class="space-y-4 border-t border-default pt-6">
          <div>
            <h3 class="text-sm font-medium text-highlighted">
              {{ t('app.purchase.totals') }}
            </h3>
          </div>
          <div class="grid gap-3 md:grid-cols-3">
            <div class="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2 text-sm">
              <span class="text-muted">{{ t('app.purchase.totalUsd') }}</span>
              <span class="font-semibold tabular-nums">{{ money(grandTotal) }}</span>
            </div>
            <CommonAppMoneyField
              :model-value="paidDirty ? paidInput : paid"
              :label="t('app.purchase.deposit')"
              :min="0"
              :step="0.01"
              class="w-full"
              @update:model-value="(value: number | undefined) => {
                paidDirty = true
                paidInput = value
              }"
            />
            <div class="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2 text-sm">
              <span class="text-muted">{{ t('app.purchase.balanceUsd') }}</span>
              <span
                class="font-medium tabular-nums"
                :class="balance > 0 ? 'text-warning' : 'text-success'"
              >
                {{ money(balance) }}
              </span>
            </div>
            <CommonAppNumberField
              v-model="exchangeRate"
              :label="t('app.purchase.exchangeRate')"
              :min="0"
              :step="1"
              class="w-full"
            />
            <div class="flex items-center justify-between rounded-md bg-primary/10 px-3 py-2 text-sm">
              <span class="text-muted">{{ t('app.purchase.balanceKhr') }}</span>
              <span class="font-semibold tabular-nums">{{ moneyKhr(balanceKhr) }}</span>
            </div>
          </div>

          <UAlert
            v-if="headerError"
            color="error"
            variant="soft"
            icon="i-lucide-alert-triangle"
            :title="headerError"
          />
        </section>
      </DocumentAppDocumentContentShell>
    </template>
  </DocumentAppDocumentPage>

  <!-- Add supplier dialog (header leading button / save guard) -->
  <CommonAppDialog
    v-model:open="supplierDialogOpen"
    :title="t('app.purchase.supplierDialogTitle')"
    icon="i-lucide-user-plus"
    color="primary"
    size="sm"
    :loading="supplierSaving"
  >
    <div class="w-full space-y-3">
      <CommonAppTextField
        v-model="supplierName"
        :label="t('app.fields.name')"
        :required="true"
        class="w-full"
      />
      <CommonAppTextField
        v-model="supplierPhone"
        :label="t('app.fields.phone')"
        class="w-full"
      />
      <CommonAppTextareaField
        v-model="supplierLocation"
        :label="t('app.fields.address')"
        :rows="2"
        class="w-full"
      />
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton
          color="neutral"
          variant="ghost"
          :label="t('common.cancel')"
          @click="supplierDialogOpen = false"
        />
        <UButton
          icon="i-lucide-user-plus"
          :loading="supplierSaving"
          :disabled="!String(supplierName || '').trim()"
          :label="t('app.purchase.addSupplier')"
          @click="saveSupplier"
        />
      </div>
    </template>
  </CommonAppDialog>
</template>
