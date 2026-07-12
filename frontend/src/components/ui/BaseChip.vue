<script setup lang="ts">
const props = defineProps<{
  variant?: 'LONG' | 'SHORT' | 'NEUTRAL' | 'sent' | 'fail'
  direction?: 'LONG' | 'SHORT' | 'NEUTRAL'
  status?: 'sent' | 'fail'
}>()

const tag = props.variant || props.direction || props.status || 'NEUTRAL'
</script>

<template>
  <span :class="['chip', tag]">
    <slot />
  </span>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-family: var(--font-mono);
}
.chip.LONG { background: var(--green-soft); color: var(--green); }
.chip.SHORT { background: var(--red-soft); color: var(--red); }
.chip.NEUTRAL { background: var(--surface-3); color: var(--fg-2); }
.chip.sent { background: var(--accent-soft); color: var(--accent-2); border: 1px solid oklch(60% 0.18 262 / 0.4); }
.chip.fail { background: var(--red-soft); color: var(--red); border: 1px solid oklch(68% 0.20 25 / 0.35); }
</style>
