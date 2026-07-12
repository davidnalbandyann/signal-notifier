<script setup lang="ts">
defineProps<{
  status: 'ok' | 'error' | 'skipped'
}>()
</script>

<template>
  <span :class="['status-pill', status]">
    {{ status === 'ok' ? 'ok' : status === 'error' ? 'error' : 'paused' }}
  </span>
</template>

<style scoped>
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.status-pill::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.status-pill.ok { background: var(--green-soft); color: var(--green); }
.status-pill.ok::before { background: var(--green); }
.status-pill.error { background: var(--red-soft); color: var(--red); }
.status-pill.error::before { background: var(--red); }
.status-pill.skipped { background: var(--surface-3); color: var(--muted); }
.status-pill.skipped::before { background: var(--muted); }
</style>
