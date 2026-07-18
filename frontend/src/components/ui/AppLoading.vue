<script setup lang="ts">
withDefaults(defineProps<{
  size?: 'sm' | 'md' | 'lg'
  label?: string
}>(), { size: 'md' })
</script>

<template>
  <div :class="['loading', size]">
    <div class="spinner" :class="size"></div>
    <span v-if="label" class="lbl">{{ label }}</span>
  </div>
</template>

<style scoped>
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 64px 0;
  color: var(--muted);
}
.loading.sm { padding: 24px 0; }
.spinner {
  border: 2px solid var(--surface-3);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
.spinner.sm { width: 18px; height: 18px; border-width: 2px; }
.spinner.md { width: 24px; height: 24px; border-width: 2px; }
.spinner.lg { width: 32px; height: 32px; border-width: 3px; }
.lbl { font: 500 12.5px var(--font-mono); letter-spacing: 0.04em; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
