<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  score: number
  size?: 'sm' | 'md' | 'lg'
  showValue?: boolean
  max?: number
}>(), {
  size: 'sm',
  showValue: true,
  max: 10,
})

const pct = computed(() => `${Math.min(100, (props.score / props.max) * 100)}%`)
const level = computed(() => {
  const ratio = props.score / props.max
  if (ratio >= 0.7) return 'high'
  if (ratio >= 0.5) return 'mid'
  return 'low'
})
</script>

<template>
  <div :class="['scorebar', size, level]">
    <div class="track"><span :class="['fill', level]" :style="{ width: pct }"></span></div>
    <span v-if="showValue" class="val">{{ score.toFixed(1) }}</span>
  </div>
</template>

<style scoped>
.scorebar {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.scorebar.sm { font-size: 12px; }
.scorebar.md { font-size: 13px; }
.scorebar.lg { font-size: 18px; gap: 12px; }

.track {
  background: var(--surface-3);
  border-radius: 999px;
  overflow: hidden;
  flex-shrink: 0;
}
.scorebar.sm .track { width: 48px; height: 4px; }
.scorebar.md .track { width: 72px; height: 5px; }
.scorebar.lg .track { width: 140px; height: 8px; }
.fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  transition: width .3s var(--ease);
}
.fill.high { background: var(--green); }
.fill.mid  { background: var(--amber); }
.fill.low  { background: var(--red); }

.val { min-width: 32px; text-align: right; }
.scorebar.high .val { color: var(--green); }
.scorebar.mid  .val { color: var(--amber); }
.scorebar.low  .val { color: var(--red); }
</style>
