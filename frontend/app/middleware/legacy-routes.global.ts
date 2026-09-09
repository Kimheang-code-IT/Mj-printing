/**
 * Temporary redirects from legacy flat routes to their current homes.
 * Remove once old bookmarks and external links have migrated.
 */
const LEGACY_SETUP_PREFIXES = [
  '/categories',
  '/brands',
  '/suppliers',
  '/customers',
] as const

const LEGACY_EXACT_REDIRECTS: Record<string, string> = {
  '/supplier-debts': '/reports/supplier-debts',
  '/customer-debts': '/reports/customer-debts',
  '/purchases': '/reports/purchases',
  '/purchases/new': '/reports/purchases/new',
  '/reports/suppliers': '/reports/supplier-debts',
  '/reports/customers': '/reports/customer-debts',
}

export default defineNuxtRouteMiddleware((to) => {
  const path = to.path.replace(/\/+$/, '') || '/'

  const exact = LEGACY_EXACT_REDIRECTS[path]
  if (exact) {
    return navigateTo(
      { path: exact, query: to.query, hash: to.hash },
      { replace: true },
    )
  }

  const isLegacySetup = LEGACY_SETUP_PREFIXES.some(
    prefix => path === prefix || path.startsWith(`${prefix}/`),
  )
  if (!isLegacySetup) return

  return navigateTo(
    { path: `/setup${path}`, query: to.query, hash: to.hash },
    { replace: true },
  )
})
