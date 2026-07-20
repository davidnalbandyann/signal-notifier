<script setup lang="ts">
import { useAppStore } from '@/stores/app'

const app = useAppStore()
</script>

<template>
  <router-view v-slot="{ Component, route }">
    <transition :name="(route.meta.transition as string) || 'page'" mode="out-in">
      <component :is="Component" :key="route.path" />
    </transition>
  </router-view>
</template>