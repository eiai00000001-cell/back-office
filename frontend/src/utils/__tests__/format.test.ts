import { describe, expect, it } from 'vitest'
import { formatCurrency, formatLast12MonthsRangeLabel, formatMonthLabel, isOverdueDate } from '../format'

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

describe('formatMonthLabel', () => {
  it('converts a YYYY-MM month key into a 2-digit year/month label', () => {
    expect(formatMonthLabel('2025-10')).toBe('25/10')
  })

  it('handles single-digit months', () => {
    expect(formatMonthLabel('2026-01')).toBe('26/1')
  })
})

describe('formatLast12MonthsRangeLabel', () => {
  it('describes the 12-month range ending at the given base date', () => {
    expect(formatLast12MonthsRangeLabel(new Date(2026, 8, 17))).toBe('直近12ヶ月(2025年10月〜2026年9月)')
  })

  it('handles a base date in January by wrapping to the previous year', () => {
    expect(formatLast12MonthsRangeLabel(new Date(2026, 0, 5))).toBe('直近12ヶ月(2025年2月〜2026年1月)')
  })
})
