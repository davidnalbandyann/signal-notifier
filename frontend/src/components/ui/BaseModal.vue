<script setup lang="ts">
import { onMounted, onUnmounted, nextTick, ref } from 'vue'
import AppIcon from './AppIcon.vue'

const props = withDefaults(defineProps<{
  show: boolean
  title?: string
  width?: number
}>(), {
  width: 440,
})

const emit = defineEmits<{ close: [] }>()
const panel = ref<HTMLElement | null>(null)

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.show) emit('close')
}

onMounted(() => document.addEventListener('keydown', onKey))
onUnmounted(() => document.removeEventListener('keydown', onKey))

async function onEnter() {
  await nextTick()
  panel.value?.focus()
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal" @enter="onEnter">
    <div v-if="show" class="modal-back" @click.self="emit('close')">
      <div
        ref="panel"
        class="modal"
        role="dialog"
        aria-modal="true"
        tabindex="-1"
        :style="{ maxWidth: width + 'px' }"
      >
        <header v-if="title || $slots.title" class="modal-head">
          <h2 class="modal-title"><slot name="title">{{ title }}</slot></h2>
          <button class="icon-btn sm" @click="emit('close')" aria-label="Close">
            <AppIcon name="x" :size="16" />
          </button>
        </header>
        <slot />
      </div>
    </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-back {
  position: fixed;
  inset: 0;
  background: oklch(0% 0 0 / 0.55);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  z-index: var(--z-modal);
  display: grid;
  place-items: center;
  padding: 24px;
}
.modal {
  width: 100%;
  background: var(--surface);
  border: 1px solid var(--border-2);
  border-radius: var(--radius-lg);
  box-shadow: 0 24px 64px oklch(0% 0 0 / 0.5);
  outline: none;
  overflow: hidden;
}
.modal:focus { outline: none; }
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}
.modal-title {
  font: 600 14px var(--font-sans);
  letter-spacing: -0.005em;
}
.modal-enter-active, .modal-leave-active {
  transition: opacity .15s var(--ease);
}
.modal-enter-active .modal, .modal-leave-active .modal {
  transition: transform .18s var(--ease-out), opacity .15s var(--ease);
}
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .modal, .modal-leave-to .modal {
  transform: translateY(8px) scale(.98);
  opacity: 0;
}
.icon-btn.sm { width: 28px; height: 28px; }
</style>
