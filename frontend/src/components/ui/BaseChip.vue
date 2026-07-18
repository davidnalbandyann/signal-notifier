<script setup lang="ts">
import { computed } from 'vue'
import type { Direction } from '@/types'

const props = withDefaults(defineProps<{
  direction?: Direction | string
  status?: 'sent' | 'fail' | 'ok' | 'error' | 'skipped'
  variant?: Direction | 'sent' | 'fail' | 'ok' | 'error' | 'skipped' | 'neutral'
  dot?: boolean
  upper?: boolean
}>(), { upper: true })

const tag = computed(() => {
  const v = props.variant || props.direction || props.status || 'neutral'
  if (v === 'LONG' || v === 'ok' || v === 'sent') return 'long'
  if (v === 'SHORT' || v === 'fail' || v === 'error') return 'short'
  if (v === 'NEUTRAL' || v === 'skipped' || v === 'neutral') return 'neutral'
  return 'neutral'
})
</script>

<template>
  <span :class="['chip', tag, { dot, upper }]">
    <span v-if="dot" class="d"></span>
    <slot />
  </span>
</template>

<style scoped>
.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: 999px;
  font: 700 10.5px var(--font-mono);
  letter-spacing: 0.06em;
  white-space: nowrap;
  line-height: 1.5;
}
.chip.upper { text-transform: uppercase; }
.chip .d {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.chip.long { background: var(--green-soft); color: var(--green); }
.chip.short { background: var(--red-soft); color: var(--red); }
.chip.neutral { background: var(--surface-3); color: var(--fg-2); }
</style>
