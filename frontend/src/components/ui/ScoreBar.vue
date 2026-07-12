<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  score: number
  size?: 'sm' | 'md' | 'lg'
}>()

const level = computed(() => {
  if (props.score >= 8) return 'high'
  if (props.score >= 5) return 'mid'
  return 'low'
})

const pct = computed(() => `${Math.min(100, props.score * 10)}%`)
</script>

<template>
  <div :class="['score', level, size || 'sm']">
    <div class="bar"><span :class="level" :style="{ width: pct }"></span></div>
    <span class="v">{{ score.toFixed(1) }}</span>
  </div>
</template>

<style scoped>
.score {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-weight: 600;
}
.score.sm { font-size: 12px; }
.score.md { font-size: 14px; }
.score.lg { font-size: 18px; }
.bar {
  height: 4px;
  background: var(--surface-3);
  border-radius: 999px;
  overflow: hidden;
  flex-shrink: 0;
}
.score.sm .bar { width: 50px; }
.score.md .bar { width: 80px; }
.score.lg .bar { width: 120px; height: 6px; }
.bar > span {
  display: block;
  height: 100%;
  border-radius: 999px;
  transition: width .3s;
}
.bar > span.high { background: var(--green); }
.bar > span.mid { background: var(--amber); }
.bar > span.low { background: var(--red); }
.score.high { color: var(--green); }
.score.mid { color: var(--amber); }
.score.low { color: var(--red); }
.v { min-width: 36px; text-align: right; }
</style>
