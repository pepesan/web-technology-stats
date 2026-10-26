<script setup>
defineProps({ topics: Array, modelValue: String })
defineEmits(['update:modelValue'])
</script>

<template>
  <div class="tabs" role="tablist" aria-label="Temas">
    <button
      v-for="t in topics"
      :key="t.key"
      role="tab"
      type="button"
      :aria-selected="t.key === modelValue"
      :class="{ active: t.key === modelValue }"
      @click="$emit('update:modelValue', t.key)"
    >
      {{ t.label }}
      <span class="count">{{ t.distinct }}</span>
    </button>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: thin;
}
button {
  flex: 0 0 auto;
  min-height: 44px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-2);
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
button:hover { border-color: var(--accent); }
button.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.count {
  font-size: 12px;
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--track);
  color: var(--text-2);
}
.active .count { background: rgba(255, 255, 255, 0.22); color: #fff; }
</style>
