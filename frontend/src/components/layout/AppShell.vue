<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'
import { useAppStore } from '@/stores/app'

const app = useAppStore()

defineProps<{
  crumbs?: string[]
}>()
</script>

<template>
  <div :class="['app', { collapsed: app.sidebarCollapsed }]">
    <AppSidebar />
    <div class="main">
      <AppTopbar :crumbs="crumbs" />
      <main class="page">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  min-height: 100vh;
  transition: grid-template-columns .25s cubic-bezier(0.4, 0, 0.2, 1);
}
.app:not(.collapsed) { grid-template-columns: var(--sidebar-w-h) 1fr; }
.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.page {
  padding: 24px 32px 48px;
  max-width: 1600px;
}
</style>
