<script setup lang="ts">
import { formatMoney } from '~/composables/module/useModule'
import type { PosCartLine } from '~/utils/pos/cart'
import { lineStockQty, refreshLineAmounts } from '~/utils/pos/cart'

const props = defineProps<{
  cart: PosCartLine[]
  currency: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  changeQty: [productId: string, delta: number]
  updateLine: [productId: string, patch: Partial<PosCartLine>]
  remove: [productId: string]
  clear: []
}>()

const { t } = useI18n()
const money = (value: unknown) => formatMoney(value, props.currency)

function padQty(qty: number) {
  return String(qty).padStart(2, '0')
}

function patch(productId: string, partial: Partial<PosCartLine>) {
  emit('updateLine', productId, partial)
}

function lineStockBlocked(line: PosCartLine) {
  const next = refreshLineAmounts({ ...line, quantity: line.quantity + 1 })
  return lineStockQty(next) > line.availableStock
}
</script>

<template>
  <section class="flex w-full min-h-0 flex-[3] flex-col overflow-hidden rounded-sm border border-default bg-default lg:max-w-md">
    <div class="flex items-center justify-between border-b border-default px-3 py-2.5">
      <h2 class="text-sm font-semibold">
        {{ t('app.pos.cart') }}
        <span
          v-if="cart.length"
          class="ml-1 text-muted"
        >({{ cart.length }})</span>
      </h2>
      <UButton
        size="xs"
        color="neutral"
        variant="ghost"
        :disabled="!cart.length || disabled"
        :label="t('app.pos.clearCart')"
        @click="emit('clear')"
      />
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto">
      <div
        v-for="line in cart"
        :key="line.productId"
        class="border-b border-default px-3 py-3"
      >
        <div class="flex gap-2.5">
          <div class="size-12 shrink-0 overflow-hidden rounded-sm bg-elevated">
            <img
              v-if="line.imageUrl"
              :src="line.imageUrl"
              :alt="line.name"
              class="h-full w-full object-cover"
            >
            <div
              v-else
              class="flex h-full w-full items-center justify-center text-muted"
            >
              <UIcon
                name="i-lucide-package"
                class="size-5 opacity-40"
              />
            </div>
          </div>

          <div class="min-w-0 flex-1">
            <div class="flex items-start gap-1">
              <p class="min-w-0 flex-1 truncate text-sm font-medium">
                {{ line.name }}
              </p>
              <UButton
                size="xs"
                color="neutral"
                variant="ghost"
                icon="i-lucide-trash-2"
                class="shrink-0"
                :disabled="disabled"
                :aria-label="t('app.pos.removeItem')"
                @click="emit('remove', line.productId)"
              />
            </div>

            <div class="mt-2 flex items-center gap-2">
              <div class="flex items-center gap-1">
                <UButton
                  size="xs"
                  color="neutral"
                  variant="soft"
                  icon="i-lucide-minus"
                  square
                  :disabled="disabled || line.quantity <= 1"
                  @click="emit('changeQty', line.productId, -1)"
                />
                <span class="min-w-8 text-center text-sm font-medium tabular-nums">
                  {{ padQty(line.quantity) }}
                </span>
                <UButton
                  size="xs"
                  color="neutral"
                  variant="soft"
                  icon="i-lucide-plus"
                  square
                  :disabled="disabled || lineStockBlocked(line)"
                  @click="emit('changeQty', line.productId, 1)"
                />
              </div>
              <span
                v-if="line.calcMode === 'dimensional' && line.squareMeter != null"
                class="text-xs text-muted"
              >
                {{ line.squareMeter }} m²
              </span>
              <span class="ml-auto text-sm font-semibold tabular-nums">
                {{ money(line.amount) }}
              </span>
            </div>

            <div class="mt-2 grid grid-cols-2 gap-2">
              <UFormField
                :label="t('app.pos.height')"
                size="xs"
              >
                <UInputNumber
                  :model-value="line.height ?? undefined"
                  :min="0"
                  :step="0.01"
                  :increment="false"
                  :decrement="false"
                  size="md"
                  class="w-full"
                  :ui="{ base: 'text-base tabular-nums' }"
                  :disabled="disabled"
                  @update:model-value="patch(line.productId, { height: $event == null ? null : Number($event) })"
                />
              </UFormField>
              <UFormField
                :label="t('app.pos.width')"
                size="xs"
              >
                <UInputNumber
                  :model-value="line.width ?? undefined"
                  :min="0"
                  :step="0.01"
                  :increment="false"
                  :decrement="false"
                  size="md"
                  class="w-full"
                  :ui="{ base: 'text-base tabular-nums' }"
                  :disabled="disabled"
                  @update:model-value="patch(line.productId, { width: $event == null ? null : Number($event) })"
                />
              </UFormField>
              <UFormField
                :label="t('app.pos.unitPrice')"
                size="xs"
              >
                <UInputNumber
                  :model-value="line.unitPrice"
                  :min="0"
                  :step="0.01"
                  :increment="false"
                  :decrement="false"
                  size="md"
                  class="w-full"
                  :ui="{ base: 'text-base tabular-nums' }"
                  :disabled="disabled"
                  @update:model-value="patch(line.productId, { unitPrice: Number($event ?? 0) })"
                />
              </UFormField>
            </div>
          </div>
        </div>
      </div>

      <p
        v-if="!cart.length"
        class="p-4 text-sm text-muted"
      >
        {{ t('app.pos.emptyCart') }}
      </p>
    </div>
  </section>
</template>
