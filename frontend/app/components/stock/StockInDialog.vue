<script setup lang="ts">
import type { AppRecord } from '~/config/admin-seed'
import { formatMoney } from '~/composables/module/useModule'

/**
 * Stock In dialog for one product — opened from the product document
 * (`/stock/[id]`), the Stock list row menu, and the Stock In history dialog.
 *
 * A Stock In is a real purchase transaction, never a direct quantity edit.
 * Clicking "Stock In" hands off to the Purchase document form
 * (`/reports/purchases/new`): the entered supplier / note
 * and this product (as the first line, with quantity + purchase price) are
 * passed through query params and pre-filled there — the purchase page owns
 * the final save (POST /api/v1/purchases), stock movement ↑ and ledger.
 *
 * Fields: Product (fixed), Supplier, Quantity, Purchase Price
 * (prefilled from the product's current cost), Note.
 */
const props = withDefaults(defineProps<{
  product?: AppRecord | null
  /** Elevate the dialog above a parent dialog (nested in QtyHistoryDialog). */
  elevated?: boolean
}>(), {
  product: null,
  elevated: false,
})

const open = defineModel<boolean>('open', { default: false })

const store = useAppDataStore()
const preferences = usePreferencesStore()
const { t } = useI18n()
const money = (value: unknown) => formatMoney(value, preferences.currency)

const supplierId = ref('')
const quantity = ref<number | undefined>()
const unitCost = ref<number | undefined>()
const note = ref('')

const supplierOptions = computed(() => store.list('suppliers')
  .filter(row => String(row.status || '').toLowerCase() === 'active')
  .map(row => ({
    label: row.code ? `${row.code} · ${row.name}` : String(row.name || ''),
    value: String(row.id),
  })))

const subtotal = computed(() => Math.round(Number(quantity.value || 0) * Number(unitCost.value || 0) * 100) / 100)

/** Only a quantity is required — the purchase form owns the rest. */
const canContinue = computed(() => Boolean(
  props.product
  && Number(quantity.value || 0) > 0
  && Number(unitCost.value || 0) >= 0,
))

const dialogUi = computed(() => props.elevated
  ? { overlay: 'z-[200]', content: 'z-[200]' }
  : undefined)

watch(open, (value) => {
  if (!value) return
  supplierId.value = ''
  quantity.value = undefined
  unitCost.value = props.product ? Number(props.product.costPrice || 0) || undefined : undefined
  note.value = ''
  void store.fetchList('suppliers')
})

const productLabel = computed(() => {
  const product = props.product
  if (!product) return ''
  return `${product.code || ''} · ${product.name || ''}`.replace(/^\s*·\s*/, '')
})

/**
 * Hand off to the Purchase document form. The purchase page reads these
 * query params on mount, pre-fills the header and adds this product as the
 * first line. Payment (Paid / balance) is handled by the purchase form,
 * which follows the grand total until edited.
 */
function continueToPurchase() {
  if (!canContinue.value || !props.product) return
  const query: Record<string, string> = { productId: String(props.product.id) }
  if (Number(quantity.value) > 0) query.quantity = String(quantity.value)
  if (unitCost.value != null) query.purchasePrice = String(unitCost.value)
  if (supplierId.value) query.supplierId = supplierId.value
  if (note.value) query.note = note.value
  open.value = false
  void navigateTo({ path: '/reports/purchases/new', query })
}
</script>

<template>
  <CommonAppDialog
    v-model:open="open"
    :title="t('app.stock.stockIn')"
    icon="i-lucide-package-plus"
    color="success"
    size="sm"
    :ui="dialogUi"
  >
    <div class="w-full space-y-3">
      <CommonAppTextField
        :model-value="productLabel"
        :label="t('app.pos.product')"
        :disabled="true"
        class="w-full"
      />
      <CommonAppSelectMenuField
        v-model="supplierId"
        :items="supplierOptions"
        :label="t('app.fields.supplier')"
        :placeholder="t('app.purchase.supplierPlaceholder')"
        :required="true"
        class="w-full"
      />
      <CommonAppNumberField
        v-model="quantity"
        :label="t('app.fields.quantity')"
        :required="true"
        :min="0"
        :step="1"
        class="w-full"
      />
      <CommonAppMoneyField
        v-model="unitCost"
        :label="t('app.purchase.purchasePrice')"
        :required="true"
        :min="0"
        :step="0.01"
        class="w-full"
      />
      <CommonAppTextareaField
        v-model="note"
        :label="t('app.fields.note')"
        :rows="2"
        class="w-full"
      />
      <div class="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2 text-sm">
        <span class="text-muted">{{ t('app.fields.total') }}</span>
        <span class="font-medium tabular-nums">{{ money(subtotal) }}</span>
      </div>
      <p class="text-xs text-muted">{{ t('app.stock.stockInHelp') }}</p>
    </div>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton
          color="neutral"
          variant="ghost"
          :label="t('common.cancel')"
          @click="open = false"
        />
        <UButton
          color="success"
          icon="i-lucide-file-plus-2"
          :disabled="!canContinue"
          :label="t('app.stock.stockIn')"
          @click="continueToPurchase"
        />
      </div>
    </template>
  </CommonAppDialog>
</template>
