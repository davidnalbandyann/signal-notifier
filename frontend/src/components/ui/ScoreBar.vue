<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  score: number
  size?: 'sm' | 'md' | 'lg'
  showValue?: boolean
  max?: number
  threshold?: number | null
}>(), {
  size: 'sm',
  showValue: true,
  max: 10,
  threshold: null,
})

const pct = computed(() => `${Math.min(100, (props.score / props.max) * 100)}%`)

// When a threshold is provided, levels are derived from it:
//   passing  — score ≥ threshold       (qualified for notification)
//   near     — score ≥ 70% of threshold (close, worth watching)
//   failing  — score below that         (not qualified)
// When threshold is null, fall back to legacy 70%/50% ratios.
const level = computed(() => {
  const t = props.threshold
  if (t != null && t > 0) {
    if (props.score >= t) return 'passing'
    if (props.score >= t * 0.7) return 'near'
    return 'failing'
  }
  const ratio = props.score / props.max
  if (ratio >= 0.7) return 'passing'
  if (ratio >= 0.5) return 'near'
  return 'failing'
})

const passing = computed(() => props.threshold != null && props.threshold > 0 && props.score >= props.threshold)
</script>

<template>
  <div :class="['scorebar', size, level]" :data-passing="passing ? '1' : '0'">
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
.fill.passing { background: var(--green); }
.fill.near    { background: var(--amber); }
.fill.failing { background: var(--red); }

.val { min-width: 32px; text-align: right; }
.scorebar.passing .val { color: var(--green); }
.scorebar.near    .val { color: var(--amber); }
.scorebar.failing .val { color: var(--red); }
</style>