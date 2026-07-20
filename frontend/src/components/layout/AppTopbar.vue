<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import AppIcon from '@/components/ui/AppIcon.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()

const crumbs = computed(() => {
  const c = (route.meta.crumbs as string[] | undefined)
  return c && c.length ? c : ['Dashboard']
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <header class="topbar">
    <button
      class="mobile-menu icon-btn"
      @click="app.openMobileSidebar()"
      aria-label="Open navigation menu"
    >
      <AppIcon name="menu" :size="16" />
    </button>

    <div class="crumbs">
      <span class="crumb-root">MONITOR</span>
      <span class="crumb-sep">/</span>
      <span v-for="(c, i) in crumbs" :key="i" class="crumb">
        <span v-if="i > 0" class="crumb-sep">/</span>
        <span :class="['crumb-text', { last: i === crumbs.length - 1 }]">{{ c }}</span>
      </span>
    </div>

    <div class="spacer"></div>

    <button
      class="icon-btn"
      @click="app.toggleTheme()"
      :title="app.theme === 'dark' ? 'Switch to light' : 'Switch to dark'"
      :aria-label="app.theme === 'dark' ? 'Switch to light' : 'Switch to dark'"
    >
      <AppIcon :name="app.theme === 'dark' ? 'sun' : 'moon'" :size="15" />
    </button>

    <div class="user">
      <div class="avatar">DA</div>
      <div class="user-meta">
        <div class="user-name">david@local</div>
        <div class="user-role">owner</div>
      </div>
      <button class="icon-btn sm logout" @click="logout" title="Log out" aria-label="Log out">
        <AppIcon name="logout" :size="14" />
      </button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: var(--z-topbar);
  height: var(--topbar-h);
  background: oklch(14% 0.014 264 / 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 10px;
  flex-shrink: 0;
}
[data-theme="light"] .topbar { background: oklch(99% 0.002 250 / 0.85); }

.mobile-menu {
  display: none;
}

.crumbs {
  display: flex;
  align-items: center;
  gap: 6px;
  font: 600 11px var(--font-mono);
  letter-spacing: 0.06em;
  min-width: 0;
  overflow: hidden;
}
.crumb-root { color: var(--muted); text-transform: uppercase; }
.crumb { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.crumb-sep { color: var(--muted-2); }
.crumb-text { color: var(--fg-2); text-transform: capitalize; }
.crumb-text.last { color: var(--fg); }

.spacer { flex: 1; }

.icon-btn { width: 30px; height: 30px; }

.user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 3px 6px 3px 4px;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--border);
  transition: border-color var(--speed-fast);
}
.user:hover { border-color: var(--border-2); }
.avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--accent);
  color: var(--accent-fg);
  display: grid;
  place-items: center;
  font: 700 9.5px var(--font-mono);
  letter-spacing: 0.02em;
  flex-shrink: 0;
}
.user-meta { display: flex; flex-direction: column; line-height: 1.2; min-width: 0; }
.user-name { font: 600 11.5px var(--font-sans); color: var(--fg); }
.user-role { font: 500 9.5px var(--font-mono); color: var(--muted); letter-spacing: 0.05em; text-transform: uppercase; }
.icon-btn.sm { width: 24px; height: 24px; }
.icon-btn.sm.logout:hover { color: var(--red); background: var(--red-soft); border-color: transparent; }

@media (max-width: 768px) {
  .mobile-menu { display: grid; }
  .user-meta { display: none; }
  .crumbs .crumb-root { display: none; }
}
</style>