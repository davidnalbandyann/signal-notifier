<script setup lang="ts">
defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
}>()
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="modal-back" @click.self="emit('close')" @keydown.esc="emit('close')">
      <div class="modal" role="dialog" aria-modal="true" tabindex="-1">
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-back {
  position: fixed;
  inset: 0;
  background: oklch(0% 0 0 / 0.6);
  backdrop-filter: blur(4px);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal {
  width: 420px;
  max-width: 90vw;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: 0 30px 80px rgba(0,0,0,0.5);
}
.modal:focus { outline: none; }
</style>
