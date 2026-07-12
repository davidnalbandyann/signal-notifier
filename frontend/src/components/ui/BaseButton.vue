<script setup lang="ts">
defineProps<{
  variant?: 'primary' | 'ghost' | 'warn' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  full?: boolean
  disabled?: boolean
}>()
</script>

<template>
  <button
    :class="[
      'btn',
      variant || 'primary',
      size || 'md',
      { full, disabled }
    ]"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 36px;
  padding: 0 14px;
  background: var(--accent);
  color: var(--accent-fg);
  border: 0;
  border-radius: var(--radius);
  font: 600 13px var(--font-sans);
  cursor: pointer;
  white-space: nowrap;
  transition: background .12s;
}
.btn:hover { background: var(--accent-2); }
.btn.ghost {
  background: var(--surface);
  color: var(--fg);
  border: 1px solid var(--border);
}
.btn.ghost:hover { background: var(--surface-2); border-color: var(--border-2); }
.btn.warn { background: var(--amber); color: var(--amber-fg); }
.btn.warn:hover { background: oklch(72% 0.16 75); }
.btn.danger { background: var(--red); color: var(--red-fg); }
.btn.danger:hover { background: oklch(62% 0.20 25); }
.btn.sm { height: 28px; padding: 0 10px; font-size: 12px; }
.btn.lg { height: 44px; padding: 0 18px; font-size: 14px; }
.btn.full { width: 100%; }
.btn.disabled { opacity: 0.5; cursor: not-allowed; pointer-events: none; }
</style>
