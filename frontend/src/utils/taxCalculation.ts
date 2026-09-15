// 税額計算ロジック(詳細設計書4.1ステップ1〜5)。
// サーバー側 TaxCalculationService と同一ロジックをフロントエンドでも再計算し、
// 画面上にリアルタイム表示する(保存時はサーバー側の計算結果を正とする)。
import type { ItemInput, TaxCategory } from '../types'

const STANDARD_TAX_RATE = 0.1

export function calculateItemAmount(quantity: number, unitPrice: number): number {
  return Math.floor(quantity * unitPrice)
}

export interface TotalsResult {
  itemAmounts: number[]
  subtotalByTax: Partial<Record<TaxCategory, number>>
  subtotalAmount: number
  taxAmount: number
  totalAmount: number
}

export function calculateTotals(items: ItemInput[]): TotalsResult {
  const itemAmounts = items.map((item) => calculateItemAmount(item.quantity, item.unit_price))
  const subtotalByTax: Partial<Record<TaxCategory, number>> = {}
  items.forEach((item, index) => {
    subtotalByTax[item.tax_category] = (subtotalByTax[item.tax_category] ?? 0) + itemAmounts[index]
  })
  const taxAmount = Math.floor((subtotalByTax.STANDARD_10 ?? 0) * STANDARD_TAX_RATE)
  const subtotalAmount = Object.values(subtotalByTax).reduce((sum, value) => sum + (value ?? 0), 0)
  const totalAmount = subtotalAmount + taxAmount
  return { itemAmounts, subtotalByTax, subtotalAmount, taxAmount, totalAmount }
}
