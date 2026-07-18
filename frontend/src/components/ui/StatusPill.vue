<script setup lang="ts">
withDefaults(defineProps<{
  status: 'ok' | 'error' | 'skipped' | 'sent' | 'fail'
  label?: string
}>(), {})
const map: Record<string, string> = {
  ok: 'OK', error: 'ERROR', skipped: 'SKIPPED', sent: 'SENT', fail: 'FAILED',
}
const kindMap: Record<string, string> = {
  ok: 'ok', sent: 'ok', error: 'error', fail: 'error', skipped: 'skipped',
}
</script>

<template>
  <span :class="['pill', kindMap[status]]">
    <span class="d"></span>
    {{ label || map[status] || status }}
  </span>
</template>

<style scoped>
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px 2px 7px;
  border-radius: 999px;
  font: 600 10.5px var(--font-mono);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  white-space: nowrap;
}
.d { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.ok { background: var(--green-soft); color: var(--green); }
.error { background: var(--red-soft); color: var(--red); }
.skipped { background: var(--surface-3); color: var(--muted); }
</style>
