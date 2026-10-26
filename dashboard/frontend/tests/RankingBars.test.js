// Autor: David Vaquero <pepesan@gmail.com>
// Licencia: GPL-3.0-only
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import RankingBars from '../src/components/RankingBars.vue'

const items = [
  { tech: 'PHP', count: 80, pct: 80, category: 'Programming languages' },
  { tech: 'Go', count: 20, pct: 20, category: 'Programming languages' },
]

describe('RankingBars', () => {
  it('pinta una fila por tecnología, la mayor al 100 % del carril', () => {
    const w = mount(RankingBars, { props: { items, base: 100 } })
    const rows = w.findAll('li.row')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('PHP')
    expect(rows[0].find('.bar').attributes('style')).toContain('width: 100%')
    expect(rows[1].find('.bar').attributes('style')).toContain('width: 25%')
  })

  it('muestra un tooltip con el detalle al pasar el ratón', async () => {
    const w = mount(RankingBars, { props: { items, base: 100 } })
    expect(w.find('.tip').exists()).toBe(false)
    await w.findAll('li.row')[1].trigger('mouseenter')
    expect(w.find('.tip').text()).toContain('20 de 100 sitios analizados')
    await w.findAll('li.row')[1].trigger('mouseleave')
    expect(w.find('.tip').exists()).toBe(false)
  })

  it('permite alternar a vista de tabla', async () => {
    const w = mount(RankingBars, { props: { items, base: 100 } })
    await w.find('button.link').trigger('click')
    expect(w.find('table').exists()).toBe(true)
    expect(w.findAll('tbody tr')).toHaveLength(2)
    expect(w.find('li.row').exists()).toBe(false)
  })
})
