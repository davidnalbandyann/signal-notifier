<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'

const app = useAppStore()
</script>

<template>
  <div :class="['shell', { collapsed: app.sidebarCollapsed }]">
    <AppSidebar />
    <div class="main">
      <AppTopbar />
      <main class="page">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  height: 100vh;
  transition: grid-template-columns .22s var(--ease);
}
.shell.collapsed {
  grid-template-columns: var(--sidebar-w-c) 1fr;
}
.main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100vh;
}
.page {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 22px 28px 56px;
}
@media (max-width: 720px) {
  .page { padding: 16px 14px 40px; }
  .shell, .shell.collapsed { grid-template-columns: 0 1fr; }
}
</style>
