<script setup lang="ts">
defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<template>
  <label class="toggle">
    <input
      type="checkbox"
      :checked="modelValue"
      @change="emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <span class="sw"></span>
    <span class="tl"><slot /></span>
  </label>
</template>

<style scoped>
.toggle {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}
.toggle input { display: none; }
.sw {
  width: 36px;
  height: 20px;
  background: var(--surface-3);
  border-radius: 999px;
  transition: background .15s;
  position: relative;
  flex-shrink: 0;
}
.sw::after {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 16px;
  height: 16px;
  background: var(--fg);
  border-radius: 50%;
  transition: transform .15s;
}
.toggle input:checked + .sw { background: var(--accent); }
.toggle input:checked + .sw::after { transform: translateX(16px); background: white; }
.tl { font-size: 13px; color: var(--fg-2); }
</style>
