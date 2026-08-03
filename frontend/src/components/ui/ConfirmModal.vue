<script setup lang="ts">
import BaseModal from './BaseModal.vue'
import BaseButton from './BaseButton.vue'

withDefaults(defineProps<{
  show: boolean
  title: string
  message: string
  confirmLabel?: string
  loading?: boolean
  danger?: boolean
}>(), {
  confirmLabel: 'Confirm',
  loading: false,
  danger: true,
})

const emit = defineEmits<{ confirm: []; cancel: [] }>()
</script>

<template>
  <BaseModal :show="show" :title="title" @close="emit('cancel')">
    <div class="confirm-body">
      <p class="confirm-msg">{{ message }}</p>
      <div class="confirm-actions">
        <BaseButton variant="ghost" :disabled="loading" @click="emit('cancel')">Cancel</BaseButton>
        <BaseButton :variant="danger ? 'danger' : 'primary'" :disabled="loading" @click="emit('confirm')">
          <span v-if="loading" class="spinner sm"></span>
          <span v-else>{{ confirmLabel }}</span>
        </BaseButton>
      </div>
    </div>
  </BaseModal>
</template>

<style scoped>
.confirm-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 18px;
}
.confirm-msg {
  font: 400 13px var(--font-sans);
  line-height: 1.5;
  color: var(--fg-2);
  overflow-wrap: break-word;
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
