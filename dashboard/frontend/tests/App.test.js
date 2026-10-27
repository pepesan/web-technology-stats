// Autor: David Vaquero <pepesan@gmail.com>
// Licencia: GPL-3.0-only
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../src/App.vue'

const topics = [
  { key: 'lang_back', label: 'Lenguajes de back', distinct: 2, top: [] },
  { key: 'databases', label: 'Bases de datos', distinct: 1, top: [] },
]
const BATCHES = [
  { batch: 1, total: 10, finished: 9, failed: 0, last_activity: '2026-10-24T10:00:00' },
  { batch: 2, total: 10, finished: 4, failed: 2, last_activity: '2026-10-25T10:00:00' },
]
const overview = (extra = {}) => ({
  batch: null, total: 10, finished: 8, failed: 1, pending: 1, with_tech: 7, distinct_tech: 3, topics, ...extra,
})
const ranking = (topic, label, items) => ({
  topic, label, batch: null, base: 9, total_items: items.length, categories: [], items,
})

function mockApi(routes) {
  vi.stubGlobal('fetch', vi.fn(async (url) => {
    const path = url.split('?')[0]
    const body = { 'config.json': { source: 'api' }, ...routes }[path]
    return body === undefined
      ? { ok: false, status: 404, json: async () => ({}) }
      : { ok: true, status: 200, json: async () => body }
  }))
}

afterEach(() => {
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

describe('App', () => {
  it('carga resumen y ranking, y cambia de tema al pulsar una pestaña', async () => {
    mockApi({
      '/api/batches': BATCHES,
      '/api/overview': overview(),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', [
        { tech: 'PHP', count: 6, pct: 66.7, category: 'Programming languages' },
      ]),
      '/api/topics/databases': ranking('databases', 'Bases de datos', [
        { tech: 'MySQL', count: 3, pct: 33.3, category: 'Databases' },
      ]),
    })
    const w = mount(App)
    await flushPromises()
    expect(w.text()).toContain('Sitios analizados')
    expect(w.text()).toContain('PHP')
    const options = w.findAll('select[aria-label="Lote"] option').map((o) => o.text())
    expect(options[0]).toBe('Todos los lotes')
    expect(options[1]).toContain('Lote 1')
    expect(options[2]).toMatch(/Lote 2 · 4 de 10 analizados · 2026-10-25/)

    await w.findAll('[role=tab]')[1].trigger('click')
    await flushPromises()
    expect(w.text()).toContain('MySQL')
    expect(w.text()).not.toContain('PHP')
  })

  it('pasa el lote seleccionado a la API', async () => {
    mockApi({
      '/api/batches': BATCHES,
      '/api/overview': overview(),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', []),
    })
    const w = mount(App)
    await flushPromises()
    // por defecto abre el último lote y lo refleja en la URL
    expect(fetch.mock.calls.map((c) => c[0])).toContain('/api/overview?batch=2&source=tranco')
    expect(window.location.search).toBe('?batch=2')
    await w.find('select[aria-label="Lote"]').setValue(1)
    await flushPromises()
    expect(window.location.search).toBe('?batch=1')
    await w.find('select[aria-label="Lote"]').setValue('')
    await flushPromises()
    expect(window.location.search).toBe('?batch=all')
    const urls = fetch.mock.calls.map((c) => c[0])
    expect(urls).toContain('/api/overview?batch=1&source=tranco')
    expect(urls).toContain('/api/topics/lang_back?batch=1&limit=15&source=tranco')
    expect(urls).toContain('/api/overview?source=tranco')
  })

  it('avisa de que los datos son parciales mientras queden sitios pendientes', async () => {
    mockApi({
      '/api/batches': BATCHES,
      '/api/overview': overview(),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', []),
    })
    const w = mount(App)
    await flushPromises()
    expect(w.find('.partial').text()).toMatch(/Escaneo incompleto: faltan 1 de 10 sitios por intentar/)
  })

  it('muestra por separado analizados, sin respuesta y pendientes', async () => {
    mockApi({
      '/api/batches': BATCHES,
      '/api/overview': overview(),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', []),
    })
    const w = mount(App)
    await flushPromises()
    const tiles = Object.fromEntries(
      w.findAll('.tile').map((t) => [t.find('.label').text(), t.find('.value').text()]),
    )
    expect(tiles['Sitios analizados']).toBe('8')
    expect(tiles['Sin respuesta']).toBe('1')
    expect(tiles['Pendientes']).toBe('1')
  })

  it('no avisa cuando el lote está completo', async () => {
    mockApi({
      '/api/batches': BATCHES,
      '/api/overview': overview({ pending: 0, failed: 1, finished: 9 }),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', []),
    })
    const w = mount(App)
    await flushPromises()
    expect(w.find('.partial').exists()).toBe(false) // los sin respuesta no son pendientes
  })

  it('muestra un estado vacío guiado si no hay sitios analizados', async () => {
    mockApi({
      '/api/batches': [],
      '/api/overview': overview({ total: 0, finished: 0, pending: 0, with_tech: 0, distinct_tech: 0 }),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', []),
    })
    const w = mount(App)
    await flushPromises()
    expect(w.text()).toContain('Aún no hay sitios analizados')
    expect(w.find('[role=tablist]').exists()).toBe(false)
  })

  it('muestra el error si la API falla', async () => {
    mockApi({})
    const w = mount(App)
    await flushPromises()
    expect(w.find('[role=alert]').text()).toContain('Error 404')
  })

  it('filtra por número de sitios (top N) y lo refleja en la URL y en la API', async () => {
    mockApi({
      '/api/batches': BATCHES,
      '/api/overview': overview(),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', []),
    })
    const w = mount(App)
    await flushPromises()
    const select = w.find('select[aria-label="Número de sitios"]')
    const labels = select.findAll('option').map((o) => o.text())
    expect(labels).toEqual([
      'Todos', 'Top 100', 'Top 1k', 'Top 10k', 'Top 100k', 'Top 200k', 'Top 300k', 'Top 400k',
      'Top 500k', 'Top 600k', 'Top 700k', 'Top 800k', 'Top 900k', 'Top 1M',
    ])
    await select.setValue(1000)
    await flushPromises()
    const urls = fetch.mock.calls.map((c) => c[0])
    expect(urls.some((u) => u.startsWith('/api/overview') && u.includes('max_position=1000'))).toBe(true)
    expect(urls.some((u) => u.startsWith('/api/topics/lang_back') && u.includes('max_position=1000'))).toBe(true)
    expect(new URLSearchParams(window.location.search).get('top')).toBe('1000')
  })

  it('modo API: el selector de fuente filtra por listado (Tranco / Red.es) en overview y ranking', async () => {
    mockApi({
      '/api/batches': BATCHES,
      '/api/overview': overview(),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', []),
    })
    const w = mount(App)
    await flushPromises()
    const select = w.find('select[aria-label="Fuente"]')
    expect(select.findAll('option').map((o) => o.text())).toEqual(['Mundo (Tranco)', 'España 2026 (Red.es)'])
    expect(select.element.value).toBe('all')
    expect(fetch.mock.calls.map((c) => c[0]).some((u) => u.startsWith('/api/overview') && u.includes('source=tranco'))).toBe(true)
    await select.setValue('es')
    await flushPromises()
    const urls = fetch.mock.calls.map((c) => c[0])
    expect(urls.some((u) => u.startsWith('/api/overview') && u.includes('source=risp2026'))).toBe(true)
    expect(urls.some((u) => u.startsWith('/api/topics/lang_back') && u.includes('source=risp2026'))).toBe(true)
    // el lote elegido se conserva al cambiar de fuente
    expect(w.find('select[aria-label="Lote"]').element.value).toBe('2')
  })

  it('modo API: con la fuente España se oculta el selector de nº de sitios y se descarta el corte elegido', async () => {
    mockApi({
      '/api/batches': BATCHES,
      '/api/overview': overview(),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', []),
    })
    const w = mount(App)
    await flushPromises()
    await w.find('select[aria-label="Número de sitios"]').setValue(1000)
    await flushPromises()
    await w.find('select[aria-label="Fuente"]').setValue('es')
    await flushPromises()
    expect(w.find('select[aria-label="Número de sitios"]').exists()).toBe(false)
    const urls = fetch.mock.calls.map((c) => c[0])
    const last = urls.filter((u) => u.startsWith('/api/overview')).at(-1)
    expect(last).toContain('source=risp2026')
    expect(last).not.toContain('max_position')
    expect(new URLSearchParams(window.location.search).get('top')).toBeNull()
    await w.find('select[aria-label="Fuente"]').setValue('all')
    await flushPromises()
    expect(w.find('select[aria-label="Número de sitios"]').exists()).toBe(true)
  })

  it('al cambiar de fuente muestra un aviso de carga visible mientras llegan los datos y lo quita después', async () => {
    mockApi({
      '/api/batches': BATCHES,
      '/api/overview': overview(),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', []),
    })
    const w = mount(App)
    await flushPromises()
    expect(w.find('.loading-banner').exists()).toBe(false)
    // a partir de aquí las respuestas de la API se retienen hasta soltarlas (consulta lenta de una fuente grande)
    const answer = fetch
    let release
    const gate = new Promise((resolve) => { release = resolve })
    vi.stubGlobal('fetch', vi.fn(async (url) => { await gate; return answer(url) }))
    await w.find('select[aria-label="Fuente"]').setValue('es')
    await w.vm.$nextTick()
    const banner = w.find('.loading-banner')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('Cargando')
    expect(w.find('.tiles').classes()).toContain('refreshing')  // las cifras antiguas se ven apagadas, no como definitivas
    release()
    await flushPromises()
    expect(w.find('.loading-banner').exists()).toBe(false)
    expect(w.find('.tiles').classes()).not.toContain('refreshing')
  })

  describe('primera carga y respuestas lentas (modo API)', () => {
    // La API de una fuente grande tarda decenas de segundos: aquí se retienen las respuestas de datos hasta soltarlas.
    function slowApi(gates = {}) {
      const routes = {
        'config.json': { source: 'api' },
        '/api/batches': BATCHES,
        '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', []),
      }
      vi.stubGlobal('fetch', vi.fn(async (url) => {
        const [path, query = ''] = url.split('?')
        if (path === '/api/overview') {
          const params = new URLSearchParams(query)
          const gate = gates[params.get('source')]
          if (gate) await gate.promise
          return { ok: true, status: 200, json: async () => overview({ total: gate?.total ?? 111 }) }
        }
        const body = routes[path]
        return body === undefined
          ? { ok: false, status: 404, json: async () => ({}) }
          : { ok: true, status: 200, json: async () => body }
      }))
    }
    const gate = (total) => {
      let release
      const promise = new Promise((resolve) => { release = resolve })
      return { promise, release, total }
    }

    it('en la primera carga muestra el aviso de carga (no solo el esqueleto) y bloquea los selectores hasta tener datos', async () => {
      const tranco = gate(1000)
      slowApi({ tranco })
      const w = mount(App)
      await flushPromises()
      expect(w.find('.skeleton').exists()).toBe(true)
      expect(w.find('.loading-banner').exists()).toBe(true)
      expect(w.find('.loading-banner').text()).toContain('Cargando')
      for (const label of ['Fuente', 'Lote', 'Número de sitios']) {
        expect(w.find(`select[aria-label="${label}"]`).attributes('disabled')).toBeDefined()
      }
      tranco.release()
      await flushPromises()
      expect(w.find('.loading-banner').exists()).toBe(false)
      expect(w.find('select[aria-label="Fuente"]').attributes('disabled')).toBeUndefined()
      expect(w.find('select[aria-label="Fuente"]').element.value).toBe('all')
    })

    it('la primera carga pide el resumen y el ranking una sola vez (cada consulta tarda decenas de segundos)', async () => {
      slowApi()
      mount(App)
      await flushPromises()
      const urls = fetch.mock.calls.map((c) => c[0])
      expect(urls.filter((u) => u.startsWith('/api/overview'))).toHaveLength(1)
      expect(urls.filter((u) => u.startsWith('/api/topics/lang_back'))).toHaveLength(1)
    })

    it('una respuesta lenta de una fuente anterior no pisa los datos de la fuente elegida después', async () => {
      const slow = gate(111)
      slowApi({ risp2026: slow })
      const w = mount(App)
      await flushPromises()
      const tile = () => w.find('.tile .value').text()
      await w.find('select[aria-label="Fuente"]').setValue('es')      // risp2026: retenida
      await w.find('select[aria-label="Fuente"]').setValue('all')     // tranco: responde ya (111)
      await flushPromises()
      expect(w.find('.loading-banner').exists()).toBe(false)
      slow.total = 999
      slow.release()                                                  // llega tarde la de risp2026
      await flushPromises()
      expect(w.find('select[aria-label="Fuente"]').element.value).toBe('all')
      expect(tile()).toBe('111')  // sigue siendo el resultado de Mundo, no el de España que llegó tarde
    })
  })
})

describe('App con informes estáticos (flag source=reports)', () => {
  const cutFile = (max, finished) => ({
    report: '2026',
    max_position: max,
    summary: { total: 1000, finished, pending: 0, failed: 1000 - finished, with_tech: finished, distinct_tech: 3 },
    topics: [
      {
        key: 'lang_back', label: 'Lenguajes de back', distinct: 2, categories: ['Programming languages', 'Web servers'],
        items: [
          { tech: 'PHP', count: 600, pct: 60, category: 'Programming languages' },
          { tech: 'Python', count: 100, pct: 10, category: 'Programming languages' },
          { tech: 'Node.js', count: 50, pct: 5, category: 'Web servers' },
        ],
      },
      { key: 'databases', label: 'Bases de datos', distinct: 1, categories: ['Databases'], items: [
        { tech: 'MySQL', count: 300, pct: 30, category: 'Databases' },
      ] },
    ],
  })
  const INDEX = { reports: [
    { id: '2025', label: 'Tranco 2025', year: 2025, batch: 1, total: 1000, finished: 800, failed: 200, tops: [100] },
    { id: '2026', label: 'Tranco 2026', year: 2026, batch: 2, total: 1000, finished: 900, failed: 100, tops: [100, 1000] },
  ] }
  const routes = () => ({
    'config.json': { source: 'reports' },
    'reports/index.json': INDEX,
    'reports/2026/top-all.json': cutFile(null, 900),
    'reports/2026/top-1000.json': cutFile(1000, 700),
    'reports/2026/top-100.json': cutFile(100, 90),
    'reports/2025/top-all.json': cutFile(null, 800),
  })

  it('sin config.json usa los informes estáticos por defecto, sin llamar a /api', async () => {
    const r = routes()
    r['config.json'] = undefined // 404: sin fichero de configuración
    mockApi(r)
    const w = mount(App)
    await flushPromises()
    const urls = fetch.mock.calls.map((c) => c[0])
    expect(urls.some((u) => u.startsWith('/api/'))).toBe(false)
    expect(w.text()).toContain('PHP')
  })

  it('lista informes por año, abre el último y no ofrece "todos los lotes"', async () => {
    mockApi(routes())
    const w = mount(App)
    await flushPromises()
    const select = w.find('select[aria-label="Informe"]')
    const options = select.findAll('option').map((o) => o.text())
    expect(options).toHaveLength(2)
    expect(options[1]).toMatch(/Tranco 2026 · 900 de 1\.000 analizados/)
    expect(select.element.value).toBe('2026')
    expect(w.text()).toContain('Sitios analizados')
    expect(w.text()).toContain('PHP')
  })

  it('el selector de sitios solo ofrece los cortes del informe y cambia de fichero', async () => {
    mockApi(routes())
    const w = mount(App)
    await flushPromises()
    const top = w.find('select[aria-label="Número de sitios"]')
    expect(top.findAll('option').map((o) => o.text())).toEqual(['Todos', 'Top 100', 'Top 1k'])
    await top.setValue(1000)
    await flushPromises()
    const urls = fetch.mock.calls.map((c) => c[0])
    expect(urls).toContain('reports/2026/top-1000.json')
    expect(new URLSearchParams(window.location.search).get('top')).toBe('1000')
    expect(new URLSearchParams(window.location.search).get('report')).toBe('2026')
  })

  it('cambiar de informe descarta un corte que ese informe no tiene', async () => {
    mockApi(routes())
    const w = mount(App)
    await flushPromises()
    await w.find('select[aria-label="Número de sitios"]').setValue(1000)
    await flushPromises()
    await w.find('select[aria-label="Informe"]').setValue('2025')
    await flushPromises()
    expect(w.find('select[aria-label="Número de sitios"]').element.value).toBe('')
    expect(fetch.mock.calls.map((c) => c[0])).toContain('reports/2025/top-all.json')
  })

  it('filtra por categoría y limita en el navegador, sin más peticiones', async () => {
    mockApi(routes())
    window.history.replaceState(null, '', '/?report=2026')
    const w = mount(App)
    await flushPromises()
    const before = fetch.mock.calls.length
    await w.find('select:not([aria-label])').setValue('Web servers')
    await flushPromises()
    expect(w.text()).toContain('Node.js')
    expect(w.text()).not.toContain('PHP')
    expect(fetch.mock.calls.length).toBe(before)
  })

  it('?source=api fuerza la API en vivo aunque config.json diga reports', async () => {
    mockApi({
      ...routes(),
      '/api/batches': BATCHES,
      '/api/overview': overview(),
      '/api/topics/lang_back': ranking('lang_back', 'Lenguajes de back', [
        { tech: 'Go', count: 5, pct: 50, category: 'Programming languages' },
      ]),
    })
    window.history.replaceState(null, '', '/?source=api')
    const w = mount(App)
    await flushPromises()
    expect(w.find('select[aria-label="Lote"]').exists()).toBe(true)
    expect(w.text()).toContain('Go')
  })

  describe('fuente (mundo / España)', () => {
    const withScopes = () => ({
      ...routes(),
      'reports/index.json': { reports: [
        { id: '2025-es', label: 'Tranco 2025 · España', year: 2025, scope: 'es', tld: 'es', batch: 1, total: 40, finished: 30, failed: 10, tops: [] },
        { id: '2026', label: 'Tranco 2026 · mundo', year: 2026, scope: 'all', batch: 1, total: 1000, finished: 900, failed: 100, tops: [100, 1000] },
        { id: '2026-es', label: 'Tranco 2026 · España', year: 2026, scope: 'es', tld: 'es', batch: 1, total: 50, finished: 40, failed: 10, tops: [1000] },
      ] },
      'reports/2026-es/top-all.json': { ...cutFile(null, 40), report: '2026-es', tld: 'es' },
      'reports/2026-es/top-1000.json': { ...cutFile(1000, 35), report: '2026-es', tld: 'es' },
    })

    it('sin varias fuentes no se muestra el selector', async () => {
      mockApi(routes())
      const w = mount(App)
      await flushPromises()
      expect(w.find('select[aria-label="Fuente"]').exists()).toBe(false)
    })

    it('con varias fuentes lista Mundo y España y solo los informes de la fuente activa', async () => {
      mockApi(withScopes())
      const w = mount(App)
      await flushPromises()
      const scope = w.find('select[aria-label="Fuente"]')
      // orden fijo (Mundo, España), aunque el índice liste antes un informe de España
      expect(scope.findAll('option').map((o) => o.text())).toEqual(['Mundo (Tranco)', 'España 2026 (Red.es)'])
      expect(scope.element.value).toBe('all')
      expect(w.find('select[aria-label="Informe"]').findAll('option')).toHaveLength(1)
    })

    it('al elegir España abre el informe del mismo año y carga sus ficheros', async () => {
      mockApi(withScopes())
      const w = mount(App)
      await flushPromises()
      await w.find('select[aria-label="Fuente"]').setValue('es')
      await flushPromises()
      expect(w.find('select[aria-label="Informe"]').element.value).toBe('2026-es')
      expect(w.find('select[aria-label="Informe"]').findAll('option')).toHaveLength(2)
      expect(fetch.mock.calls.map((c) => c[0])).toContain('reports/2026-es/top-all.json')
      expect(new URLSearchParams(window.location.search).get('report')).toBe('2026-es')
    })

    it('con la fuente España no hay selector de nº de sitios, y sí en Mundo', async () => {
      mockApi(withScopes())
      const w = mount(App)
      await flushPromises()
      expect(w.find('select[aria-label="Número de sitios"]').exists()).toBe(true)
      await w.find('select[aria-label="Fuente"]').setValue('es')
      await flushPromises()
      expect(w.find('select[aria-label="Número de sitios"]').exists()).toBe(false)
    })

    it('una URL con ?report=2026-es abre directamente la fuente España', async () => {
      mockApi(withScopes())
      window.history.replaceState(null, '', '/?report=2026-es')
      const w = mount(App)
      await flushPromises()
      expect(w.find('select[aria-label="Fuente"]').element.value).toBe('es')
      expect(w.find('select[aria-label="Informe"]').element.value).toBe('2026-es')
    })
  })
})
