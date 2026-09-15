import { describe, expect, it } from 'vitest'
import { formatCurrency, isOverdueDate } from '../format'

describe('formatCurrency', () => {
  it('formats an integer with thousands separators and a yen suffix', () => {
    expect(formatCurrency(330000)).toBe('330,000円')
  })

  it('formats zero', () => {
    expect(formatCurrency(0)).toBe('0円')
  })

  it('formats small numbers without separators', () => {
    expect(formatCurrency(500)).toBe('500円')
  })
})

describe('isOverdueDate', () => {
  it('returns true for a date before today', () => {
    expect(isOverdueDate('2000-01-01')).toBe(true)
  })

  it('returns false for a date far in the future', () => {
    expect(isOverdueDate('2999-01-01')).toBe(false)
  })

  it('returns false for null', () => {
    expect(isOverdueDate(null)).toBe(false)
  })
})
