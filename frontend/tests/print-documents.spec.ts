import { describe, expect, it, beforeEach } from 'vitest'
import {
  configureFormats,
  DEFAULT_FORMAT_CONFIG,
} from '../app/utils/format/format-service'
import { escapeHtml, PRINT_IFRAME_SIZES, printPageCss } from '../app/utils/print/html'

describe('print documents', () => {
  beforeEach(() => {
    configureFormats(DEFAULT_FORMAT_CONFIG)
  })

  it('escapes HTML in print values', () => {
    expect(escapeHtml('<script>alert(1)</script>')).toBe('&lt;script&gt;alert(1)&lt;/script&gt;')
  })

  it('uses A4 page CSS and iframe size by default and when A4 is chosen', () => {
    const css = printPageCss('A4')
    expect(css).toContain('@page { size: A4; margin: 8mm; }')
    expect(css).toContain('font-family: "Khmer OS Content", "Khmer OS", "Noto Sans Khmer", "Hanuman", sans-serif')
    expect(PRINT_IFRAME_SIZES.A4).toBeTruthy()
  })

  it('supports A5 paper size', () => {
    const css = printPageCss('A5')
    expect(css).toContain('@page { size: A5')
    expect(PRINT_IFRAME_SIZES.A5).toBeTruthy()
  })
})
