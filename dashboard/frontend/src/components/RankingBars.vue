<!--
  Autor: David Vaquero <pepesan@gmail.com>
  Licencia: GPL-3.0-only
-->
<script setup>
import { computed, ref } from 'vue'
import { fmtInt, fmtPct } from '../format'

const props = defineProps({
  items: { type: Array, required: true },
  base: { type: Number, default: 0 },
})

const asTable = ref(false)
const active = ref(null)
// Las barras parten de cero; la más larga ocupa todo el carril.
const maxCount = computed(() => Math.max(1, ...props.items.map((i) => i.count)))
const width = (item) => `${(item.count / maxCount.value) * 100}%`
</script>

<template>
  <div class="ranking">
    <div class="toolbar">
      <button type="button" class="link" @click="asTable = !asTable">
        {{ asTable ? 'Ver barras' : 'Ver como tabla' }}
      </button>
    </div>

    <table v-if="asTable" class="table">
      <thead>
        <tr><th>Tecnología</th><th>Categoría</th><th class="num">Sitios</th><th class="num">%</th></tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.tech">
          <td>{{ item.tech }}</td>
          <td>{{ item.category }}</td>
          <td class="num">{{ fmtInt(item.count) }}</td>
          <td class="num">{{ fmtPct(item.pct) }}</td>
        </tr>
      </tbody>
    </table>

    <ol v-else class="bars">
      <li
        v-for="item in items"
        :key="item.tech"
        class="row"
        tabindex="0"
        @mouseenter="active = item.tech"
        @mouseleave="active = null"
        @focus="active = item.tech"
        @blur="active = null"
      >
        <span class="name">{{ item.tech }}</span>
        <span class="value">{{ fmtInt(item.count) }} <span class="pct">· {{ fmtPct(item.pct) }}</span></span>
        <span class="track"><span class="bar" :style="{ width: width(item) }"></span></span>
        <span v-if="active === item.tech" class="tip" role="tooltip">
          <strong>{{ item.tech }}</strong>
          <span v-if="item.category"> · {{ item.category }}</span><br />
          {{ fmtInt(item.count) }} de {{ fmtInt(base) }} sitios analizados ({{ fmtPct(item.pct) }})
        </span>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: flex-end; margin-bottom: 6px; }
.link {
  background: none;
  border: 0;
  color: var(--accent);
  cursor: pointer;
  min-height: 44px;
  padding: 0 4px;
}
.bars { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.row {
  position: relative;
  display: grid;
  grid-template-columns: minmax(120px, 220px) 1fr auto;
  grid-template-areas: 'name track value';
  align-items: center;
  column-gap: 12px;
  min-height: 36px;
  padding: 4px 8px;
  border-radius: 8px;
}
.row:hover, .row:focus-visible { background: var(--track); }
.name { grid-area: name; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.value { grid-area: value; text-align: right; font-variant-numeric: tabular-nums; }
.pct { color: var(--text-2); }
.track { grid-area: track; height: 20px; display: flex; align-items: center; }
.bar {
  display: block;
  height: 20px;
  min-width: 2px;
  background: var(--accent);
  /* extremo de datos redondeado, base cuadrada */
  border-radius: 0 4px 4px 0;
}
.tip {
  position: absolute;
  z-index: 2;
  right: 8px;
  bottom: calc(100% - 2px);
  max-width: min(320px, 90vw);
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--text);
  color: var(--bg);
  font-size: 13px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
  pointer-events: none;
}
.table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid var(--border); }
th { color: var(--text-2); font-weight: 500; font-size: 13px; }
.num { text-align: right; }

@media (max-width: 640px) {
  .row {
    grid-template-columns: 1fr auto;
    grid-template-areas: 'name value' 'track track';
    row-gap: 4px;
    padding: 8px;
  }
  .tip { left: 8px; right: 8px; max-width: none; }
}
</style>
