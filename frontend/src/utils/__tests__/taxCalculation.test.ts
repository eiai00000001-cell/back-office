import { describe, expect, it } from 'vitest'
import { calculateItemAmount, calculateTotals } from '../taxCalculation'
import type { ItemInput } from '../../types'

describe('calculateItemAmount', () => {
  it('multiplies quantity and unit price', () => {
    expect(calculateItemAmount(2, 1000)).toBe(2000)
  })

  it('floors fractional results', () => {
    // 1.33 * 3 = 3.99 -> floor to 3
    expect(calculateItemAmount(1.33, 3)).toBe(3)
  })

  it('supports quantities with two decimal places', () => {
    expect(calculateItemAmount(2.5, 1000)).toBe(2500)
  })
})

describe('calculateTotals', () => {
  const baseItem = (overrides: Partial<ItemInput>): ItemInput => ({
    item_name: '品目',
    quantity: 1,
    unit_price: 0,
    tax_category: 'STANDARD_10',
    ...overrides,
  })

  it('computes subtotal, tax and total for standard-taxed items', () => {
    const items = [baseItem({ quantity: 1, unit_price: 300000, tax_category: 'STANDARD_10' })]
    const totals = calculateTotals(items)
    expect(totals.subtotalAmount).toBe(300000)
    expect(totals.taxAmount).toBe(30000)
    expect(totals.totalAmount).toBe(330000)
  })

  it('does not tax non-taxable or out-of-scope items', () => {
    const items = [
      baseItem({ quantity: 1, unit_price: 300000, tax_category: 'STANDARD_10' }),
      baseItem({ quantity: 1, unit_price: 5000, tax_category: 'NON_TAXABLE' }),
      baseItem({ quantity: 1, unit_price: 1000, tax_category: 'OUT_OF_SCOPE' }),
    ]
    const totals = calculateTotals(items)
    expect(totals.subtotalByTax.STANDARD_10).toBe(300000)
    expect(totals.subtotalByTax.NON_TAXABLE).toBe(5000)
    expect(totals.subtotalByTax.OUT_OF_SCOPE).toBe(1000)
    expect(totals.taxAmount).toBe(30000)
    expect(totals.subtotalAmount).toBe(306000)
    expect(totals.totalAmount).toBe(336000)
  })

  it('returns zero totals for an empty item list', () => {
    const totals = calculateTotals([])
    expect(totals.subtotalAmount).toBe(0)
    expect(totals.taxAmount).toBe(0)
    expect(totals.totalAmount).toBe(0)
  })

  it('floors the fractional tax amount', () => {
    const items = [baseItem({ quantity: 1, unit_price: 999, tax_category: 'STANDARD_10' })]
    const totals = calculateTotals(items)
    // 999 * 0.10 = 99.9 -> floor to 99
    expect(totals.taxAmount).toBe(99)
  })
})
