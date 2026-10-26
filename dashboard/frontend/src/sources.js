// Fuentes de datos del dashboard, elegidas por el flag `source` de config.json (o `?source=` en la URL):
//  - 'reports': informes estáticos (JSON generados con wts-export-report), sin servidor ni base de datos.
//  - 'api':     API FastAPI en vivo, por lotes.
// Las dos exponen la misma interfaz, así que los componentes no saben cuál usan.
import { fetchBatches, fetchOverview, fetchTopic } from './api'
import { fmtInt } from './format'

export const DEFAULT_SOURCE = 'reports'
// Cortes del ranking Tranco: 100, 1k, 10k, 100k, 200k ... 900k, 1M.
export const TOP_STEPS = [100, 1_000, 10_000, 100_000, ...Array.from({ length: 8 }, (_, i) => (i + 2) * 100_000), 1_000_000]

export async function loadConfig() {
  let source = DEFAULT_SOURCE
  try {
    const res = await fetch('config.json')
    if (res.ok) source = (await res.json())?.source ?? source
  } catch {
    // sin config.json se usa el valor por defecto
  }
  const forced = new URLSearchParams(window.location.search).get('source')
  if (forced === 'api' || forced === 'reports') source = forced
  return { source: source === 'api' ? 'api' : DEFAULT_SOURCE }
}

export function createSource(source) {
  return source === 'api' ? apiSource() : reportsSource()
}

function apiSource() {
  return {
    kind: 'api',
    param: 'batch',
    noun: 'Lote',
    allValue: { value: '', label: 'Todos los lotes' },
    async list() {
      const batches = await fetchBatches()
      return batches.map((b) => ({
        value: b.batch,
        label:
          `Lote ${b.batch} · ${fmtInt(b.finished)} de ${fmtInt(b.total)} analizados` +
          (b.last_activity ? ` · ${b.last_activity.slice(0, 10)}` : ''),
      }))
    },
    topSteps: () => TOP_STEPS,
    overview: (value, top) => fetchOverview(value === '' ? null : value, top === '' ? null : top),
    topic: (value, top, topic, { limit, category }) =>
      fetchTopic(topic, {
        batch: value === '' ? null : value,
        limit,
        category,
        maxPosition: top === '' ? null : top,
      }),
  }
}

async function getJson(path) {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`Error ${res.status} al leer ${path}`)
  return res.json()
}

function reportsSource() {
  let reports = []
  const cuts = new Map()
  const cut = (id, top) => {
    const file = `reports/${id}/top-${top === '' ? 'all' : top}.json`
    if (!cuts.has(file)) cuts.set(file, getJson(file))
    return cuts.get(file)
  }
  return {
    kind: 'reports',
    param: 'report',
    noun: 'Informe',
    allValue: null,
    async list() {
      reports = (await getJson('reports/index.json')).reports
      return reports.map((r) => ({
        value: r.id,
        label: `${r.label} · ${fmtInt(r.finished)} de ${fmtInt(r.total)} analizados`,
      }))
    },
    topSteps: (id) => reports.find((r) => r.id === id)?.tops ?? [],
    async overview(id, top) {
      const { summary, topics } = await cut(id, top)
      return {
        batch: null,
        ...summary,
        topics: topics.map((t) => ({ key: t.key, label: t.label, distinct: t.distinct, top: t.items.slice(0, 3) })),
      }
    },
    async topic(id, top, topic, { limit, category }) {
      const { summary, topics } = await cut(id, top)
      const t = topics.find((x) => x.key === topic)
      if (!t) throw new Error(`Tema desconocido: ${topic}`)
      const items = category ? t.items.filter((i) => i.category === category) : t.items
      return {
        topic: t.key,
        label: t.label,
        batch: null,
        base: summary.finished,
        total_items: items.length,
        categories: t.categories,
        items: items.slice(0, limit),
      }
    },
  }
}
