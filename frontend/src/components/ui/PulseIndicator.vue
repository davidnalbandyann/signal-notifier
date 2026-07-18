<script setup lang="ts">
withDefaults(defineProps<{
  state: 'running' | 'paused' | 'error' | 'stopped' | 'idle'
  label?: string
  pulse?: boolean
}>(), { pulse: true })
</script>

<template>
  <span :class="['pulse', state]">
    <span class="dot"></span>
    <span class="t">{{ label || state }}</span>
  </span>
</template>

<style scoped>
.pulse {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 10px 4px 8px;
  border-radius: 999px;
  font: 600 11px var(--font-mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  white-space: nowrap;
  line-height: 1.5;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}
.running { background: var(--green-soft); color: var(--green); }
.running .dot { animation: pulse 2.2s infinite; }
.paused { background: var(--amber-soft); color: var(--amber); }
.error { background: var(--red-soft); color: var(--red); }
.stopped { background: var(--surface-3); color: var(--muted); }
.stopped .dot { animation: none; }
.idle { background: var(--surface-3); color: var(--muted); }

@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 oklch(74% 0.17 152 / 0.5); }
  70%  { box-shadow: 0 0 0 7px oklch(74% 0.17 152 / 0); }
  100% { box-shadow: 0 0 0 0 oklch(74% 0.17 152 / 0); }
}
</style>
