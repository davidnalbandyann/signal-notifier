<script setup lang="ts">
defineProps<{
  state: 'running' | 'paused' | 'error' | 'stopped'
}>()
</script>

<template>
  <div :class="['pulse', state]">
    <span class="b"></span>
    {{ state === 'running' ? 'Running' : state === 'paused' ? 'Paused' : 'Error' }}
  </div>
</template>

<style scoped>
.pulse {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.pulse .b {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.pulse.running {
  background: var(--green-soft);
  color: var(--green);
}
.pulse.running .b {
  background: var(--green);
  animation: pulse 2s infinite;
}
.pulse.paused {
  background: var(--amber-soft);
  color: var(--amber);
}
.pulse.paused .b { background: var(--amber); }
.pulse.error {
  background: var(--red-soft);
  color: var(--red);
}
.pulse.error .b { background: var(--red); }
.pulse.stopped {
  background: var(--surface-3);
  color: var(--muted);
}
.pulse.stopped .b { background: var(--muted); animation: none; }

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 oklch(72% 0.18 150 / 0.5); }
  70% { box-shadow: 0 0 0 8px oklch(72% 0.18 150 / 0); }
  100% { box-shadow: 0 0 0 0 oklch(72% 0.18 150 / 0); }
}
</style>
