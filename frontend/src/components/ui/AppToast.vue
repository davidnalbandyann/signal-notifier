<script setup lang="ts">
import { computed } from 'vue'
import { useToast } from '@/composables/useToast'
import AppIcon from './AppIcon.vue'

const { state, dismiss } = useToast()

const kind = computed(() => state.value.kind)
const iconName = computed(() => ({
  success: 'check',
  error: 'alert',
  info: 'info',
}[kind.value]))
</script>

<template>
  <Teleport to="body">
    <Transition name="toast">
      <div
        v-if="state.show"
        :class="['toast', kind]"
        role="status"
        aria-live="polite"
      >
        <AppIcon :name="iconName" :size="14" :stroke="2.5" />
        <span class="msg">{{ state.message }}</span>
        <button class="x" @click="dismiss" aria-label="Dismiss">
          <AppIcon name="x" :size="13" :stroke="2.5" />
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 10px 12px 10px 14px;
  border-radius: var(--radius);
  font: 500 13px var(--font-sans);
  box-shadow: 0 12px 28px oklch(0% 0 0 / 0.35);
  display: flex;
  align-items: center;
  gap: 9px;
  z-index: var(--z-toast);
  border: 1px solid var(--border-2);
  background: var(--surface);
  color: var(--fg);
  max-width: 360px;
}
.toast .msg { flex: 1; }
.toast.success { border-color: var(--green); color: var(--green); }
.toast.success .msg { color: var(--fg); }
.toast.error { border-color: var(--red); color: var(--red); }
.toast.error .msg { color: var(--fg); }
.toast.info { border-color: var(--accent); color: var(--accent); }
.toast.info .msg { color: var(--fg); }
.x {
  background: none;
  border: 0;
  cursor: pointer;
  color: var(--muted);
  padding: 2px;
  display: grid;
  place-items: center;
  border-radius: 3px;
}
.x:hover { background: var(--surface-2); color: var(--fg); }

.toast-enter-active, .toast-leave-active { transition: opacity .2s var(--ease), transform .2s var(--ease); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(10px); }
</style>
