// Autor: David Vaquero <pepesan@gmail.com>
// Licencia: GPL-3.0-only
import { describe, expect, it } from 'vitest'
import { fmtInt, fmtPct } from '../src/format'

describe('format', () => {
  it('formatea enteros con separador de millares para cifras grandes', () => {
    expect(fmtInt(1234567).replace(/\s/g, '')).toMatch(/^1[.  ]?234[.  ]?567$/)
    expect(fmtInt(0)).toBe('0')
  })
  it('agrupa siempre los millares, también con cuatro cifras', () => {
    expect(fmtInt(1456)).toBe('1.456')
    expect(fmtInt(998220)).toBe('998.220')
    expect(fmtInt(1000000)).toBe('1.000.000')
    expect(fmtInt(324)).toBe('324')
  })
  it('formatea porcentajes con un decimal', () => {
    expect(fmtPct(66.7)).toBe('66,7 %')
    expect(fmtPct(50)).toBe('50,0 %')
  })
})
