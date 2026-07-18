<script setup lang="ts">
import AppIcon from './AppIcon.vue'

withDefaults(defineProps<{
  icon?: string
  title: string
  description?: string
  action?: string
}>(), { icon: 'list' })
defineEmits<{ action: [] }>()
</script>

<template>
  <div class="empty">
    <div class="ic"><AppIcon :name="icon" :size="26" :stroke="1.5" /></div>
    <div class="t">{{ title }}</div>
    <div v-if="description" class="d">{{ description }}</div>
    <button v-if="action" class="btn sm" @click="$emit('action')">{{ action }}</button>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 56px 24px;
  text-align: center;
  color: var(--muted);
}
.ic {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--muted-2);
  margin-bottom: 4px;
}
.t { font: 600 13.5px var(--font-sans); color: var(--fg-2); }
.d { font: 400 12.5px var(--font-sans); color: var(--muted); max-width: 360px; }
</style>
