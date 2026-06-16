import { describe, it, expect } from 'vitest'
import { num, pct } from '../lib/format.js'

describe('num()', () => {
  it('formats numbers to 2 decimal places by default', () => {
    expect(num(1.23456)).toBe('1.23')
    expect(num(0)).toBe('0.00')
    expect(num(5, 0)).toBe('5')
  })
  it('handles null / undefined → "-"', () => {
    expect(num(null)).toBe('-')
    expect(num(undefined)).toBe('-')
  })
  it('handles NaN and Infinity → "-"', () => {
    expect(num(NaN)).toBe('-')
    expect(num(Infinity)).toBe('-')
    expect(num(-Infinity)).toBe('-')
  })
  it('rounds correctly', () => {
    expect(num(1.5, 0)).toBe('2')
  })
})

describe('pct()', () => {
  it('formats percentages to 1 decimal', () => {
    expect(pct(53.61)).toBe('53.6%')
    expect(pct(0)).toBe('0.0%')
    expect(pct(100)).toBe('100.0%')
  })
  it('handles null / NaN / Infinity → "-"', () => {
    expect(pct(null)).toBe('-')
    expect(pct(NaN)).toBe('-')
    expect(pct(Infinity)).toBe('-')
  })
})
