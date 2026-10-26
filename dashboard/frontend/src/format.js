const intFmt = new Intl.NumberFormat('es-ES', { useGrouping: 'always' })
const pctFmt = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

export const fmtInt = (n) => intFmt.format(n)
export const fmtPct = (n) => `${pctFmt.format(n)} %`
