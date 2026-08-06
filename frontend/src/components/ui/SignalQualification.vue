<script setup lang="ts">
// SignalQualification — the dominant comparison on every signal row.
//
// Shows the three facts an operator needs to read a signal in one glance:
//   1. Did the score cross threshold?
//   2. Was the direction eligible for notification?
//   3. Was it delivered?
//
// Reused across Dashboard, History, Notifications, and AnalysisDetail so
// threshold truth has exactly one visual treatment.

import { computed } from 'vue'
import type { Direction } from '@/types'

const props = withDefaults(defineProps<{
  score?: number | null
  threshold?: number | null
  direction?: Direction | string | null
  sent?: boolean | null
  notifyEnabled?: boolean | null
  density?: 'compact' | 'rich'
}>(), {
  score: 0,
  threshold: null,
  direction: 'NEUTRAL',
  sent: null,
  notifyEnabled: null,
  density: 'compact',
})

const fmtScore = computed(() => props.score != null ? props.score.toFixed(1) : '—')
const fmtThreshold = computed(() =>
  props.threshold != null ? props.threshold.toFixed(1) : '—'
)

const passing = computed(() =>
  props.threshold != null && props.threshold > 0 && props.score != null && props.score >= props.threshold
)

const eligible = computed(() => {
  const d = props.direction
  if (!d || d === 'NEUTRAL') return false
  if (props.notifyEnabled === false) return false
  return true
})

const deliveryLabel = computed(() => {
  if (props.sent === true) return 'Delivered'
  if (props.sent === false) return 'Failed'
  return 'Not sent'
})
const deliveryKind = computed(() => {
  if (props.sent === true) return 'ok'
  if (props.sent === false) return 'fail'
  return 'none'
})

const op = computed(() => (passing.value ? '≥' : '<'))
const compareClass = computed(() => (passing.value ? 'pass' : 'fail'))
</script>

<template>
  <div :class="['sq', density, compareClass]">
    <span class="sq-score">
      <span class="score-val mono">{{ fmtScore }}</span>
      <span class="op mono">{{ op }}</span>
      <span class="thr-val mono">{{ fmtThreshold }}</span>
      <span class="thr-label">threshold</span>
    </span>
    <span class="sep" aria-hidden="true">·</span>
    <span :class="['sq-elig', { off: !eligible }]">
      {{ direction }}
      <span class="elig-suffix">{{ eligible ? 'eligible' : 'ineligible' }}</span>
    </span>
    <span class="sep" aria-hidden="true">·</span>
    <span :class="['sq-deliv', deliveryKind]">
      <span class="dot" aria-hidden="true"></span>
      {{ deliveryLabel }}
    </span>
  </div>
</template>

<style scoped>
.sq {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  flex-wrap: wrap;
  min-width: 0;
}
.sq.compact { font-size: 12px; }
.sq.rich { font-size: 13.5px; gap: 10px; }

.sq-score {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
}
.score-val {
  font-weight: 700;
  letter-spacing: -0.01em;
}
.sq.rich .score-val { font-size: 18px; }
.sq.compact .score-val { font-size: 13px; }
.op {
  font-weight: 600;
  color: var(--muted-2);
  padding: 0 2px;
}
.thr-val {
  font-weight: 600;
  color: var(--fg-2);
}
.thr-label {
  font-weight: 500;
  font-size: 0.85em;
  color: var(--muted);
  margin-left: 2px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.sq.pass .score-val { color: var(--green); }
.sq.fail .score-val { color: var(--red); }

.sep {
  color: var(--muted-2);
  font-weight: 500;
  user-select: none;
}

.sq-elig {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  font-weight: 600;
  color: var(--fg-2);
}
.sq-elig.off { color: var(--muted); }
.elig-suffix {
  font-weight: 500;
  color: var(--muted);
  font-size: 0.9em;
}

.sq-deliv {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 600;
  color: var(--muted);
}
.sq-deliv .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.sq-deliv.ok { color: var(--green); }
.sq-deliv.fail { color: var(--red); }
.sq-deliv.none { color: var(--muted); }
</style>