<script setup lang="ts">
defineProps<{
  show: boolean
  message: string
}>()

const emit = defineEmits<{
  dismiss: []
}>()
</script>

<template>
  <Teleport to="body">
    <Transition name="toast">
      <div v-if="show" class="toast" role="status" aria-live="polite">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <span>{{ message }}</span>
        <button @click="emit('dismiss')" aria-label="Dismiss" class="dismiss">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  padding: 12px 16px;
  background: var(--green);
  color: oklch(20% 0.04 150);
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 500;
  box-shadow: 0 12px 30px rgba(0,0,0,0.3);
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 1000;
}
.dismiss {
  background: none;
  border: 0;
  color: inherit;
  cursor: pointer;
  padding: 2px;
  margin-left: 4px;
  display: grid;
  place-items: center;
}
.toast-enter-active,
.toast-leave-active {
  transition: opacity .2s, transform .2s;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
