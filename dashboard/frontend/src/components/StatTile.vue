<script setup>
defineProps({ label: String, value: String, hint: String })
</script>

<template>
  <div class="tile">
    <span class="label">{{ label }}</span>
    <span class="value">{{ value }}</span>
    <span v-if="hint" class="hint">{{ hint }}</span>
  </div>
</template>

<style scoped>
.tile {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.label { color: var(--text-2); font-size: 13px; }
.value { font-size: 28px; font-weight: 600; line-height: 1.15; }
.hint { color: var(--text-3); font-size: 12px; }
@media (max-width: 520px) {
  .value { font-size: 24px; }
}
</style>
