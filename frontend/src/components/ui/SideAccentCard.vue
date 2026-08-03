<script setup lang="ts">
// SideAccentCard — a card with a colored left-edge accent strip.
//
// One primitive for the previously-drift-prone `border-left: 3px solid` pattern
// that was duplicated in DashboardView.scan-bar, EngineView.last-sig, and
// StrategyView.info-banner.
//
// Defaults to a 1px restrained strip (craft-floor compliant). Use weight="bold"
// only when the consumer specifically calls for a heavier treatment; the bold
// variant is still ≤2px so it doesn't read as the AI-tell the old 3px version was.

import { computed } from 'vue'

type Accent = 'accent' | 'amber' | 'green' | 'red' | 'blue'

const props = withDefaults(defineProps<{
  accent?: Accent
  weight?: 'thin' | 'bold'
  radius?: 'none' | 'sm' | 'md' | 'lg'
  paused?: boolean
  as?: string
}>(), {
  accent: 'accent',
  weight: 'thin',
  radius: 'lg',
  paused: false,
  as: 'div',
})

// Map accent name → existing token. Centralized so a token rename happens once.
const tokenFor: Record<Accent, string> = {
  accent: 'var(--accent)',
  amber: 'var(--amber)',
  green: 'var(--green)',
  red: 'var(--red)',
  blue: 'var(--blue)',
}

const stripColor = computed(() => {
  if (props.paused && props.accent === 'accent') return tokenFor.amber
  return tokenFor[props.accent]
})
</script>

<template>
  <component
    :is="as"
    :class="['sac', `sac-${weight}`, `sac-r-${radius}`]"
    :style="{ '--strip-color': stripColor }"
  >
    <slot />
  </component>
</template>

<style scoped>
.sac {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--border);
  border-left-width: 1px;
  border-left-color: var(--strip-color);
  isolation: isolate;
  transition: border-left-color var(--speed-normal), box-shadow var(--speed-normal);
}

.sac-bold {
  border-left-width: 2px;
}

.sac-r-none { border-radius: 0; }
.sac-r-sm   { border-radius: var(--radius-sm); }
.sac-r-md   { border-radius: var(--radius); }
.sac-r-lg   { border-radius: var(--radius-lg); }
</style>