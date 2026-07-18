<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'primary' | 'ghost' | 'warn' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  full?: boolean
  disabled?: boolean
  type?: 'button' | 'submit'
}>(), {
  variant: 'primary',
  size: 'md',
  type: 'button',
})
</script>

<template>
  <button
    :class="['btn', variant, size, { full }]"
    :type="type"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>
