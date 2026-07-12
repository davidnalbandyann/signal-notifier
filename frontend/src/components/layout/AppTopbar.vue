<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useRouter } from 'vue-router'

defineProps<{
  crumbs?: string[]
}>()

const auth = useAuthStore()
const app = useAppStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <header class="topbar">
    <div class="crumbs">
      MONITOR · <b>{{ crumbs?.[crumbs.length - 1] || 'Dashboard' }}</b>
    </div>
    <div class="topbar-spacer"></div>
    <button class="theme-toggle" @click="app.toggleTheme" :title="app.theme === 'dark' ? 'Switch to light' : 'Switch to dark'">
      <svg v-if="app.theme === 'dark'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/>
        <line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/>
        <line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
      </svg>
      <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
      </svg>
    </button>
    <div class="user">
      <div class="avatar">DA</div>
      <div class="user-name">david@local <span class="role">· owner</span></div>
      <button class="logout" title="Log out" @click="logout">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
          <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
      </button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  height: var(--topbar-h);
  background: oklch(15% 0.012 252 / 0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 16px;
}
[data-theme="light"] .topbar { background: oklch(99% 0.002 240 / 0.85); }
.crumbs {
  color: var(--muted);
  font-size: 12px;
  font-family: var(--font-mono);
  letter-spacing: 0.05em;
}
.crumbs b { color: var(--fg); font-weight: 600; }
.topbar-spacer { flex: 1; }
.theme-toggle {
  width: 32px;
  height: 32px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--muted);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: background .12s, color .12s;
}
.theme-toggle:hover { background: var(--surface-2); color: var(--fg); }
.user {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px 4px 4px;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--border);
}
.avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: linear-gradient(135deg, oklch(60% 0.18 262), oklch(48% 0.20 280));
  display: grid;
  place-items: center;
  color: white;
  font-size: 11px;
  font-weight: 700;
}
.user-name { font-size: 12px; font-weight: 500; }
.user-name .role { color: var(--muted); font-weight: 400; }
.logout {
  width: 28px;
  height: 28px;
  background: transparent;
  border: 0;
  cursor: pointer;
  color: var(--muted);
  display: grid;
  place-items: center;
  border-radius: 4px;
  transition: background .12s, color .12s;
}
.logout:hover { background: var(--surface-2); color: var(--fg); }
</style>
