<!--
  Autor: David Vaquero <pepesan@gmail.com>
  Licencia: GPL-3.0-only
-->
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { SCOPE_ORDER, createSource, loadConfig, scopeLabel } from './sources'
import { fmtInt, fmtPct } from './format'
import StatTile from './components/StatTile.vue'
import TopicTabs from './components/TopicTabs.vue'
import RankingBars from './components/RankingBars.vue'

const PAGE = 15
const topLabel = (n) => (n >= 1_000_000 ? '1M' : n >= 1_000 ? `${n / 1_000}k` : String(n))

const source = ref(null)         // fuente de datos (informes estáticos o API), según el flag de config.json
const options = ref([])          // informes o lotes disponibles
const current = ref('')          // informe/lote elegido ('' = todos los lotes, solo en modo API)
const scope = ref('')            // fuente de los datos ('all' = mundo/Tranco, 'es' = España/Red.es); solo con varias fuentes
const top = ref('')              // '' = sin límite; N = solo posiciones <= N del ranking
const overview = ref(null)
const topic = ref('lang_back')
const ranking = ref(null)
const limit = ref(PAGE)
const category = ref('')
// «Cargando» = arranque (config y listado) o alguna consulta vigente. Cada consulta puede tardar decenas de segundos
// en una fuente grande, así que una respuesta atrasada de una petición anterior no puede pisar a la última.
const booting = ref(true)
const overviewBusy = ref(false)
const rankingBusy = ref(false)
const loading = computed(() => booting.value || overviewBusy.value || rankingBusy.value)
const ready = ref(false)   // la carga inicial ha terminado: antes, los cambios de selector no relanzan consultas
const initializing = computed(() => !overview.value && loading.value)
const error = ref('')

const scopeRank = (s) => (SCOPE_ORDER.includes(s) ? SCOPE_ORDER.indexOf(s) : SCOPE_ORDER.length)
const scopes = computed(
  () =>
    source.value?.scopes ??
    [...new Set(options.value.map((o) => o.scope).filter(Boolean))].sort((a, b) => scopeRank(a) - scopeRank(b)),
)
// solo los informes estáticos llevan la fuente en cada opción; en modo API la fuente es un filtro aparte
const visibleOptions = computed(() =>
  options.value.some((o) => o.scope) && scopes.value.length > 1
    ? options.value.filter((o) => o.scope === scope.value)
    : options.value,
)
const topSteps = computed(() => (source.value ? source.value.topSteps(current.value) : []))
// con una fuente acotada (España) el corte por posición del ranking mundial no tiene sentido: no se ofrece
const scoped = computed(() => scope.value !== '' && scope.value !== 'all')
const coverage = computed(() =>
  overview.value && overview.value.total
    ? fmtPct((100 * overview.value.finished) / overview.value.total)
    : '—',
)

let overviewSeq = 0
let rankingSeq = 0
async function loadOverview() {
  const id = ++overviewSeq
  overviewBusy.value = true
  try {
    const data = await source.value.overview(current.value, top.value, scope.value)
    if (id === overviewSeq) overview.value = data
  } catch (e) {
    if (id === overviewSeq) throw e
  } finally {
    if (id === overviewSeq) overviewBusy.value = false
  }
}
async function loadRanking() {
  const id = ++rankingSeq
  rankingBusy.value = true
  try {
    const data = await source.value.topic(current.value, top.value, topic.value, {
      limit: limit.value,
      category: category.value,
      scope: scope.value,
    })
    if (id === rankingSeq) ranking.value = data
  } catch (e) {
    if (id === rankingSeq) throw e
  } finally {
    if (id === rankingSeq) rankingBusy.value = false
  }
}
async function run(fn) {
  error.value = ''
  try {
    await fn()
  } catch (e) {
    error.value = e.message
  }
}

// Elegido inicial: el de la URL (?batch=N | ?report=ID; "all" = todos los lotes) o, si no, el último.
function initialCurrent(list) {
  const wanted = new URLSearchParams(window.location.search).get(source.value.param)
  if (wanted === 'all' && source.value.allValue) return ''
  if (wanted && list.some((o) => String(o.value) === wanted)) return list.find((o) => String(o.value) === wanted).value
  // por defecto, el último informe de la fuente mundial (o el último que haya)
  const world = list.filter((o) => o.scope === 'all')
  const pool = world.length ? world : list
  return pool.length ? pool[pool.length - 1].value : ''
}
function initialTop() {
  const wanted = Number(new URLSearchParams(window.location.search).get('top'))
  return !scoped.value && topSteps.value.includes(wanted) ? wanted : ''
}
function syncUrl() {
  const url = new URL(window.location.href)
  url.searchParams.set(source.value.param, current.value === '' ? 'all' : current.value)
  if (top.value === '') url.searchParams.delete('top')
  else url.searchParams.set('top', top.value)
  window.history.replaceState(null, '', url)
}

onMounted(async () => {
  await run(async () => {
    source.value = createSource((await loadConfig()).source)
    options.value = await source.value.list()
    current.value = initialCurrent(options.value)
    scope.value = options.value.find((o) => o.value === current.value)?.scope ?? scopes.value[0] ?? ''
    top.value = initialTop()
    syncUrl()
    await Promise.all([loadOverview(), loadRanking()])
  })
  booting.value = false
  ready.value = true
})
watch(scope, () => {
  // al cambiar de fuente se abre el informe del mismo año (o el último) de esa fuente
  if (visibleOptions.value.some((o) => o.value === current.value)) return
  const year = options.value.find((o) => o.value === current.value)?.year
  const same = visibleOptions.value.find((o) => o.year === year)
  current.value = (same ?? visibleOptions.value[visibleOptions.value.length - 1])?.value ?? current.value
})
watch([current, scope], () => {
  // el corte por posición mundial solo tiene sentido con la fuente Mundo; el elegido puede no existir en el otro informe
  if (top.value !== '' && (scoped.value || !topSteps.value.includes(top.value))) top.value = ''
})
watch([current, top, scope], () => {
  if (!source.value || !ready.value) return
  syncUrl()
  limit.value = PAGE
  run(() => Promise.all([loadOverview(), loadRanking()]))
})
watch(topic, () => {
  limit.value = PAGE
  category.value = ''
  run(loadRanking)
})
watch([limit, category], () => run(loadRanking))

const hasData = computed(() => overview.value && overview.value.finished > 0)
const canShowMore = computed(() => ranking.value && ranking.value.total_items > limit.value)
</script>

<template>
  <main class="page">
    <header class="head">
      <div>
        <h1>Web Technology Stats</h1>
        <p class="sub">Tecnologías detectadas en los sitios del ranking Tranco, por tema.</p>
      </div>
      <div class="filters">
        <label class="batch" v-if="scopes.length > 1">
          <span>Fuente</span>
          <select v-model="scope" aria-label="Fuente" :disabled="initializing">
            <option v-for="s in scopes" :key="s" :value="s">{{ scopeLabel(s) }}</option>
          </select>
        </label>
        <label class="batch" v-if="source">
          <span>{{ source.noun }}</span>
          <select v-model="current" :aria-label="source.noun" :disabled="initializing">
            <option v-if="source.allValue" :value="source.allValue.value">{{ source.allValue.label }}</option>
            <option v-for="o in visibleOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </label>
        <label class="batch" v-if="!scoped">
          <span>Nº de sitios</span>
          <select v-model="top" aria-label="Número de sitios" :disabled="initializing">
            <option value="">Todos</option>
            <option v-for="n in topSteps" :key="n" :value="n">Top {{ topLabel(n) }}</option>
          </select>
        </label>
      </div>
    </header>

    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <div v-if="loading" class="loading-banner" role="status">
      <span class="spinner" aria-hidden="true"></span>
      <span>Cargando datos… las consultas de una fuente grande pueden tardar unos segundos.</span>
    </div>

    <template v-if="overview">
      <section class="tiles" :class="{ refreshing: loading }" aria-label="Resumen">
        <StatTile label="Sitios importados" :value="fmtInt(overview.total)" />
        <StatTile label="Sitios analizados" :value="fmtInt(overview.finished)" :hint="`${coverage} del ${source.noun.toLowerCase()}`" />
        <StatTile label="Pendientes" :value="fmtInt(overview.pending)" hint="aún sin intentar" />
        <StatTile label="Sin respuesta" :value="fmtInt(overview.failed)" hint="intentados sin éxito" />
        <StatTile label="Con tecnología detectada" :value="fmtInt(overview.with_tech)" />
        <StatTile label="Tecnologías distintas" :value="fmtInt(overview.distinct_tech)" />
      </section>

      <p v-if="overview.pending > 0 && hasData" class="partial" role="status">
        Escaneo incompleto: faltan {{ fmtInt(overview.pending) }} de {{ fmtInt(overview.total) }} sitios por intentar
        (el escaneo puede seguir en curso; recarga para ver el avance).
      </p>

      <p v-if="!hasData && !loading" class="empty">
        Aún no hay sitios analizados. Importa y escanea datos con <code>./40_get_data_top10.sh</code>.
      </p>

      <template v-else>
        <TopicTabs v-model="topic" :topics="overview.topics" />

        <section class="panel" :class="{ refreshing: loading }" :aria-busy="loading">
          <div class="panel-head" v-if="ranking">
            <h2>{{ ranking.label }}</h2>
            <p class="sub">
              % de los {{ fmtInt(ranking.base) }} sitios analizados que usan cada tecnología
              · {{ fmtInt(ranking.total_items) }} en este tema
            </p>
            <label v-if="ranking.categories.length > 1" class="batch">
              <span>Categoría</span>
              <select v-model="category">
                <option value="">Todas</option>
                <option v-for="c in ranking.categories" :key="c" :value="c">{{ c }}</option>
              </select>
            </label>
          </div>

          <p v-if="ranking && !ranking.items.length" class="empty">Sin tecnologías detectadas en este tema.</p>
          <RankingBars v-else-if="ranking" :items="ranking.items" :base="ranking.base" />

          <div class="more" v-if="canShowMore">
            <button type="button" @click="limit = Math.min(limit + 50, 500)">Mostrar más</button>
          </div>
        </section>
      </template>
    </template>

    <div v-else-if="loading" class="skeleton" role="status" aria-label="Cargando datos">
      <div class="tiles">
        <div v-for="n in 6" :key="n" class="sk sk-tile"></div>
      </div>
      <div class="sk-tabs">
        <div v-for="n in 6" :key="n" class="sk sk-tab"></div>
      </div>
      <div class="panel">
        <div class="sk sk-title"></div>
        <div v-for="n in 8" :key="n" class="sk sk-bar" :style="{ width: 100 - n * 9 + '%' }"></div>
      </div>
    </div>
  </main>
</template>

<style scoped>
.page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 24px 16px calc(32px + env(safe-area-inset-bottom, 0px));
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.head { display: flex; flex-wrap: wrap; gap: 12px 24px; justify-content: space-between; align-items: flex-end; }
h1 { margin: 0; font-size: 26px; line-height: 1.2; }
h2 { margin: 0; font-size: 19px; }
.sub { margin: 4px 0 0; color: var(--text-2); font-size: 14px; }
.filters { display: flex; flex-wrap: wrap; gap: 12px; }
.batch { display: inline-flex; flex-direction: column; gap: 4px; font-size: 13px; color: var(--text-2); min-width: 0; max-width: 100%; }
select {
  min-height: 44px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  min-width: 160px;
  max-width: 100%;
  text-overflow: ellipsis;
}
.tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.panel-head { display: flex; flex-wrap: wrap; gap: 4px 16px; align-items: flex-end; justify-content: space-between; }
.panel-head > div, .panel-head h2 { flex: 1 1 100%; }
.more { display: flex; justify-content: center; }
.more button {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  cursor: pointer;
}
.more button:hover { border-color: var(--accent); }
.empty { color: var(--text-2); margin: 8px 0; }
.partial {
  margin: 0;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
  border-left: 4px solid var(--accent);
  background: var(--surface);
  color: var(--text-2);
  font-size: 14px;
}
.error {
  margin: 0;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid #e34948;
  color: #e34948;
}
@media (max-width: 760px) {
  .filters, .batch { width: 100%; }
  .batch select { width: 100%; }
  .tiles { grid-template-columns: repeat(2, 1fr); }
  h1 { font-size: 22px; }
  .panel { padding: 12px; }
}
.skeleton { display: flex; flex-direction: column; gap: 20px; }
.sk {
  border-radius: 8px;
  background: linear-gradient(90deg, var(--track) 25%, var(--border) 50%, var(--track) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.2s linear infinite;
}
.sk-tile { height: 84px; border-radius: 12px; }
.sk-tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.sk-tab { height: 40px; width: 110px; }
.sk-title { height: 22px; width: 40%; margin-bottom: 8px; }
.sk-bar { height: 22px; min-width: 15%; }
@keyframes shimmer { to { background-position: -200% 0; } }
.loading-banner {
  position: sticky;
  top: 8px;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid var(--accent);
  background: var(--accent-soft);
  color: var(--text);
  font-weight: 600;
  box-shadow: 0 4px 14px rgb(0 0 0 / 18%);
}
.spinner {
  flex: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 3px solid var(--accent);
  border-right-color: transparent;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.tiles, .panel { transition: opacity 0.15s; }
.tiles.refreshing, .panel.refreshing { opacity: 0.45; }
@media (prefers-reduced-motion: reduce) {
  .sk, .spinner { animation: none; }
}
</style>
