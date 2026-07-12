<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  delta?: string
  deltaUp?: boolean
}>()
</script>

<template>
  <div class="stat">
    <div class="k">{{ label }}</div>
    <div class="v num">{{ value }}</div>
    <div v-if="delta" :class="['d', deltaUp ? 'up' : deltaUp === false ? 'down' : '']">
      {{ delta }}
    </div>
  </div>
</template>

<style scoped>
.stat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.k {
  color: var(--muted);
  font-size: 11px;
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 600;
}
.v {
  font-family: var(--font-mono);
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.015em;
}
.d {
  font-size: 12px;
  color: var(--muted);
}
.d.up { color: var(--green); }
.d.down { color: var(--red); }
</style>
