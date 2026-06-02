import { describe, expect, it } from 'vitest'
import { cx, formatDate, formatDateTime, formatNumber } from './utils'

describe('cx', () => {
  it('joins truthy class names', () => {
    expect(cx('a', 'b', 'c')).toBe('a b c')
  })

  it('filters falsy values', () => {
    expect(cx('a', false, null, undefined, 'b')).toBe('a b')
  })

  it('returns empty string when all values are falsy', () => {
    expect(cx(false, null, undefined)).toBe('')
  })
})

describe('formatDate', () => {
  it('returns em dash for null', () => {
    expect(formatDate(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(formatDate(undefined)).toBe('—')
  })

  it('returns em dash for empty string', () => {
    expect(formatDate('')).toBe('—')
  })

  it('returns the original string for an unparseable date', () => {
    expect(formatDate('not-a-date')).toBe('not-a-date')
  })

  it('formats a valid ISO date string', () => {
    const result = formatDate('2024-01-15')
    expect(result).toBeTruthy()
    expect(result).not.toBe('—')
  })
})

describe('formatDateTime', () => {
  it('returns em dash for null', () => {
    expect(formatDateTime(null)).toBe('—')
  })

  it('returns the original string for an unparseable value', () => {
    expect(formatDateTime('bad-value')).toBe('bad-value')
  })

  it('formats a valid ISO datetime string', () => {
    const result = formatDateTime('2024-01-15T10:30:00Z')
    expect(result).toBeTruthy()
    expect(result).not.toBe('—')
  })
})

describe('formatNumber', () => {
  it('returns em dash for null', () => {
    expect(formatNumber(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(formatNumber(undefined)).toBe('—')
  })

  it('formats to 2 decimal places by default', () => {
    expect(formatNumber(3.14159)).toBe('3.14')
  })

  it('respects custom digits', () => {
    expect(formatNumber(3.14159, 4)).toBe('3.1416')
  })

  it('formats zero', () => {
    expect(formatNumber(0)).toBe('0.00')
  })
})
