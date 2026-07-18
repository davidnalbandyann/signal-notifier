<script setup lang="ts">
import AppIcon from './AppIcon.vue'

defineProps<{
  label: string
  value: string | number
  icon?: string
  hint?: string
  delta?: string
  deltaUp?: boolean
}>()
</script>

<template>
  <div class="stat">
    <div class="head">
      <span v-if="icon" class="ic"><AppIcon :name="icon" :size="13" /></span>
      <span class="k">{{ label }}</span>
    </div>
    <div class="v num">{{ value }}</div>
    <div v-if="delta || hint" class="foot">
      <span v-if="delta" :class="['delta', deltaUp ? 'up' : deltaUp === false ? 'down' : '']">{{ delta }}</span>
      <span v-else class="hint">{{ hint }}</span>
    </div>
  </div>
</template>

<style scoped>
.stat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  position: relative;
}
.head {
  display: flex;
  align-items: center;
  gap: 6px;
}
.ic { color: var(--muted); display: grid; place-items: center; }
.k {
  color: var(--muted);
  font: 600 10.5px var(--font-mono);
  letter-spacing: 0.09em;
  text-transform: uppercase;
}
.v {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.foot { display: flex; align-items: center; gap: 6px; }
.delta, .hint { font-size: 11.5px; color: var(--muted); }
.delta.up { color: var(--green); }
.delta.down { color: var(--red); }
</style>
