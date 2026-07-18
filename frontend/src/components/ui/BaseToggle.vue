<script setup lang="ts">
withDefaults(defineProps<{
  modelValue: boolean
  disabled?: boolean
}>(), {})
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

function onToggle(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).checked)
}
</script>

<template>
  <label :class="['toggle', { disabled }]">
    <input type="checkbox" :checked="modelValue" :disabled="disabled" @change="onToggle" />
    <span class="sw"></span>
    <span v-if="$slots.default" class="tl"><slot /></span>
  </label>
</template>

<style scoped>
.toggle.disabled { opacity: 0.5; cursor: not-allowed; }
.toggle .tl { font-size: 12.5px; color: var(--fg-2); }
</style>
