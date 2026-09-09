import type { AppConfig } from '~/types/stock-pos/settings'

/**
 * Mapping between the frontend settings form model (AppConfig) and the
 * grouped backend settings payload served by `PATCH/GET /api/v1/admin/settings`
 * (`{ values: { <group>: { <key>: value } } }`).
 *
 * Only keys that exist in the backend `SETTING_GROUPS` catalog are mapped;
 * unknown keys would be rejected by the API. The Telegram bot token is
 * env-only (`TELEGRAM_BOT_TOKEN`) and is never sent or stored from the UI.
 *
 * Expiry-alert stock settings are removed from the UI (AGENT_STOCK_POS §2.4)
 * and are no longer patched from this form.
 */

export type AdminSettingsGroups = Record<string, Record<string, unknown>>

export function toAdminSettingsValues(input: Partial<AppConfig>): AdminSettingsGroups {
  const values: AdminSettingsGroups = {}

  const telegram: Record<string, unknown> = {}
  const telegramInput = input.telegram
  if (telegramInput) {
    if (telegramInput.passwordResetEnabled !== undefined) telegram.enable_password_reset = telegramInput.passwordResetEnabled
    if (telegramInput.paymentInvoiceNotifyEnabled !== undefined) telegram.payment_invoice_notify_enabled = telegramInput.paymentInvoiceNotifyEnabled
    if (telegramInput.stockInquiryEnabled !== undefined) telegram.stock_inquiry_enabled = telegramInput.stockInquiryEnabled
  }
  if (Object.keys(telegram).length > 0) values.telegram = telegram

  return values
}

function asBoolean(value: unknown, fallback: boolean): boolean {
  return typeof value === 'boolean' ? value : fallback
}

/** Overlay backend settings groups onto a config model (returns a new object). */
export function applyAdminSettingsGroups(config: AppConfig, groups: AdminSettingsGroups): AppConfig {
  const next: AppConfig = {
    ...config,
    stock: { ...config.stock },
    telegram: { ...config.telegram },
  }

  const telegram = groups.telegram
  if (telegram) {
    if (telegram.enable_password_reset !== undefined) next.telegram.passwordResetEnabled = asBoolean(telegram.enable_password_reset, next.telegram.passwordResetEnabled)
    if (telegram.payment_invoice_notify_enabled !== undefined) next.telegram.paymentInvoiceNotifyEnabled = asBoolean(telegram.payment_invoice_notify_enabled, next.telegram.paymentInvoiceNotifyEnabled)
    if (telegram.stock_inquiry_enabled !== undefined) next.telegram.stockInquiryEnabled = asBoolean(telegram.stock_inquiry_enabled, next.telegram.stockInquiryEnabled)
  }

  return next
}
