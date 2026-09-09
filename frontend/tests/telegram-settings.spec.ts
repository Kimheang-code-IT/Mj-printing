import { describe, expect, it } from 'vitest'
import { systemSettingsTabs } from '../app/config/settings-schemas'
import { MOCK_APP_CONFIG } from '../app/repositories/mock/settings'
import { applyAdminSettingsGroups, toAdminSettingsValues } from '../app/repositories/http/admin-settings'
import type { AppConfig } from '../app/types/stock-pos/settings'

describe('telegram settings', () => {
  const telegramFields = systemSettingsTabs
    .find(tab => tab.id === 'telegram')
    ?.sections.flatMap(section => section.fields) ?? []

  it('configures the Stock & POS password-reset Telegram bot connection', () => {
    const keys = telegramFields.map(field => field.key)
    expect(keys).toContain('telegram.enabled')
    expect(keys).toContain('telegram.botToken')
    expect(keys).toContain('telegram.chatId')
    expect(keys).toContain('__telegramConnection')
  })

  it('exposes the Phase 8 Telegram feature toggles', () => {
    const byKey = new Map(telegramFields.map(field => [field.key, field]))
    expect(byKey.get('telegram.passwordResetEnabled')?.type).toBe('boolean')
    expect(byKey.get('telegram.paymentInvoiceNotifyEnabled')?.type).toBe('boolean')
    expect(byKey.get('telegram.stockInquiryEnabled')?.type).toBe('boolean')
  })

  it('never exposes an editable bot token input (env-only secret)', () => {
    const tokenField = telegramFields.find(field => field.key === 'telegram.botToken')
    expect(tokenField).toBeDefined()
    expect(tokenField?.type).not.toBe('secret')
    expect(tokenField?.readOnly).toBe(true)
  })

  it('does not expose legacy rental notification settings', () => {
    const keys = telegramFields.map(field => field.key)
    expect(keys).not.toContain('telegram.notifyNewRental')
    expect(keys).not.toContain('telegram.deadlineReminderEnabled')
    expect(keys).not.toContain('telegram.deadlineReminderDuration')
    expect(keys).not.toContain('telegram.userAccess')
  })

  it('keeps the mock Telegram config free of rental/motorcycle state', () => {
    const telegram = MOCK_APP_CONFIG.telegram as Record<string, unknown>
    for (const key of Object.keys(telegram)) {
      expect(key.toLowerCase()).not.toContain('rental')
      expect(key.toLowerCase()).not.toContain('motorcycle')
    }
    expect(telegram.passwordResetEnabled).toBe(true)
    expect(telegram.paymentInvoiceNotifyEnabled).toBe(true)
    expect(telegram.stockInquiryEnabled).toBe(true)
  })
})

describe('stock settings removed (AGENT_STOCK_POS §2.4)', () => {
  it('does not expose a Stock expiry-alerts settings tab', () => {
    expect(systemSettingsTabs.find(tab => tab.id === 'stock')).toBeUndefined()
    const keys = systemSettingsTabs.flatMap(tab =>
      tab.sections.flatMap(section => section.fields.map(field => field.key)))
    expect(keys).not.toContain('stock.expiryAlert1Days')
    expect(keys).not.toContain('stock.expiryAlert2Days')
    expect(keys).not.toContain('stock.telegramExpiryAlertsEnabled')
  })
})

describe('security settings', () => {
  const securityFields = systemSettingsTabs
    .find(tab => tab.id === 'security')
    ?.sections.flatMap(section => section.fields) ?? []

  it('keeps password-reset delivery on Telegram with a code expiry window', () => {
    const byKey = new Map(securityFields.map(field => [field.key, field]))
    const channel = byKey.get('security.passwordResetChannel')
    expect(channel?.type).toBe('select')
    expect(channel?.options?.map(option => option.value)).toEqual(['telegram'])
    expect(byKey.has('security.passwordResetCodeExpiryMinutes')).toBe(true)
  })
})

describe('admin settings mapping (PATCH /api/v1/admin/settings)', () => {
  const base = structuredClone(MOCK_APP_CONFIG) as AppConfig

  it('does not map removed expiry stock settings into the patch payload', () => {
    const values = toAdminSettingsValues({
      stock: {},
    })
    expect(values.stock).toBeUndefined()
  })

  it('maps the Telegram feature toggles to backend keys', () => {
    const values = toAdminSettingsValues({
      telegram: { ...base.telegram, passwordResetEnabled: false, paymentInvoiceNotifyEnabled: false, stockInquiryEnabled: false },
    })
    expect(values).toEqual({
      telegram: {
        enable_password_reset: false,
        payment_invoice_notify_enabled: false,
        stock_inquiry_enabled: false,
      },
    })
  })

  it('never sends the Telegram bot token (env-only secret)', () => {
    const values = toAdminSettingsValues(base) as Record<string, Record<string, unknown>>
    expect(values.telegram?.bot_token).toBeUndefined()
    expect(JSON.stringify(values)).not.toContain('bot_token')
  })

  it('applies returned backend groups back onto the form model', () => {
    const next = applyAdminSettingsGroups(base, {
      telegram: { enable_password_reset: false },
    })
    expect(next.telegram.passwordResetEnabled).toBe(false)
    // Unmapped sections are untouched.
    expect(next.localization).toEqual(base.localization)
  })

  it('returns an empty patch when no mappable sections change', () => {
    expect(toAdminSettingsValues({ localization: { ...base.localization } })).toEqual({})
  })
})
