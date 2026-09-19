import { describe, expect, it } from 'vitest'
import { toItemInputs } from '../items'
import { validateItems } from '../../components/ItemsEditor'
import type { ItemResponse } from '../../types'

// バックエンド(Pydantic v2)はDecimal型のquantityを文字列("1.00")でJSON化して返す。
const wireItem = (overrides: Partial<ItemResponse> = {}): ItemResponse => ({
  id: 10,
  item_name: '作業',
  quantity: '1.00',
  unit_price: 300000,
  tax_category: 'STANDARD_10',
  amount: 300000,
  sort_order: 0,
  ...overrides,
})

describe('toItemInputs', () => {
  it('converts string quantity from the API into a number and keeps decimals', () => {
    const [item] = toItemInputs([wireItem({ quantity: '2.50' })])
    expect(item.quantity).toBe(2.5)
    expect(typeof item.quantity).toBe('number')
  })

  it('converts numeric strings for unit_price too and passes numbers through', () => {
    const items = toItemInputs([wireItem({ quantity: 3, unit_price: '1200' })])
    expect(items[0].quantity).toBe(3)
    expect(items[0].unit_price).toBe(1200)
  })

  it('sets clientKey from id and keeps other fields', () => {
    const [item] = toItemInputs([wireItem()])
    expect(item.clientKey).toBe('10')
    expect(item.item_name).toBe('作業')
    expect(item.tax_category).toBe('STANDARD_10')
  })

  it('produces items that pass validateItems', () => {
    expect(validateItems(toItemInputs([wireItem({ quantity: '1.00' })]))).toBeNull()
  })
})
